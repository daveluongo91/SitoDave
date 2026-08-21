"""
backend/app/services/csv_service.py
Importazione ed Esportazione CSV per i contatti CRM.
- Anteprima strutturata, rilevamento codifica e delimitatore
- Prevenzione Formula Injection
- Strategie duplicati (skip, update_empty, update_selected, conflict)
- UTF-8 con BOM per Excel
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from backend.app.models.contact import Contact
from backend.app.models.contact_interaction import ContactInteraction
from backend.app.models.tag import Tag
from backend.app.services.crm_service import normalize_email, normalize_phone

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_value(val: Any) -> str:
    """Previene formula injection anteponendo un apostrofo se necessario."""
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in _FORMULA_PREFIXES:
        return "'" + s
    return s


def detect_csv_format(raw_bytes: bytes) -> Tuple[str, str]:
    """Rileva codifica (utf-8-sig, utf-8, latin-1) e delimitatore (, ; tab)."""
    # Prova decodifiche
    text = ""
    encoding = "utf-8"
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw_bytes.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue

    # Rileva delimitatore analizzando le prime 5 righe
    lines = [l for l in text.splitlines() if l.strip()][:5]
    sample = "\n".join(lines)
    delimiter = ","
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=";,|\t")
        delimiter = dialect.delimiter
    except Exception:
        # Fallback euristico
        if sample.count(";") > sample.count(","):
            delimiter = ";"
        elif sample.count("\t") > sample.count(","):
            delimiter = "\t"

    return encoding, delimiter


def parse_csv_preview(raw_bytes: bytes, max_rows: int = 10) -> Dict[str, Any]:
    """Genera l'anteprima delle prime righe del CSV per la mappatura colonne."""
    encoding, delimiter = detect_csv_format(raw_bytes)
    text = raw_bytes.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    
    rows = list(reader)
    if not rows:
        return {"headers": [], "rows": [], "totalRows": 0, "delimiter": delimiter, "encoding": encoding}

    headers = [h.strip() for h in rows[0]]
    sample_rows = [[_sanitize_csv_value(c) for c in r] for r in rows[1:max_rows + 1]]

    # Proposta euristica di mappatura
    mapping_suggestions = {}
    standard_fields = {
        "first_name": ["nome", "first_name", "firstname", "name"],
        "last_name": ["cognome", "last_name", "lastname", "surname"],
        "email": ["email", "e-mail", "posta", "mail"],
        "phone": ["telefono", "phone", "cellulare", "mobile", "tel"],
        "country": ["paese", "country", "stato", "nazione"],
        "status": ["stato_commerciale", "status", "fase"],
        "priority": ["priorita", "priority"],
        "notes": ["note", "notes", "messaggio", "dettagli"],
        "tags": ["tag", "tags", "etichette", "interessi"],
        "next_followup_at": ["follow_up", "followup", "richiamare_il", "prossimo_contatto"],
    }

    for idx, h in enumerate(headers):
        h_clean = re.sub(r"[^a-zA-Z0-9_]", "", h.lower().replace(" ", "_"))
        for field, keywords in standard_fields.items():
            if any(k in h_clean for k in keywords):
                if field not in mapping_suggestions:
                    mapping_suggestions[field] = idx

    return {
        "headers": headers,
        "rows": sample_rows,
        "totalRows": max(0, len(rows) - 1),
        "delimiter": delimiter,
        "encoding": encoding,
        "mappingSuggestions": mapping_suggestions,
    }


def execute_csv_import(
    db: Session,
    raw_bytes: bytes,
    column_mapping: Dict[str, int],  # es. {"email": 0, "first_name": 1, ...}
    duplicate_strategy: str = "update_empty",  # skip | update_empty | overwrite | conflict
    default_source: str = "csv_import",
    admin_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Esegue l'importazione effettiva dei contatti con strategia di risoluzione duplicati."""
    encoding, delimiter = detect_csv_format(raw_bytes)
    text = raw_bytes.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    
    rows = list(reader)
    if len(rows) <= 1:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["File CSV vuoto o contenente solo intestazione."]}

    now = datetime.now(timezone.utc).isoformat()
    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors: List[str] = []

    # Valid status values
    valid_statuses = {"new_lead", "to_contact", "contacted", "qualified", "quote_sent", "customer", "loyal_customer", "lost_lead", "inactive"}

    for line_idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue  # Salta righe vuote

        def get_val(key: str) -> str:
            col_idx = column_mapping.get(key)
            if col_idx is not None and 0 <= col_idx < len(row):
                return row[col_idx].strip()
            return ""

        email = normalize_email(get_val("email"))
        phone = normalize_phone(get_val("phone"))
        first_name = get_val("first_name")
        last_name = get_val("last_name")
        country = get_val("country") or "IT"
        status_val = get_val("status").lower()
        if status_val not in valid_statuses:
            status_val = "new_lead"
        notes = get_val("notes")
        tags_raw = get_val("tags")
        followup_date = get_val("next_followup_at")

        if not email and not phone:
            errors.append(f"Riga {line_idx}: Nessuna email o telefono valido specificato.")
            skipped_count += 1
            continue

        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append(f"Riga {line_idx}: Email '{email}' non valida.")
            skipped_count += 1
            continue

        # Cerca contatto esistente per email o telefono
        existing = None
        if email:
            existing = db.query(Contact).filter(Contact.email == email, Contact.is_deleted.is_(False)).first()
        if not existing and phone:
            existing = db.query(Contact).filter(Contact.phone == phone, Contact.is_deleted.is_(False)).first()

        if existing:
            if duplicate_strategy == "skip":
                skipped_count += 1
                continue
            elif duplicate_strategy == "update_empty":
                if not existing.first_name and first_name: existing.first_name = first_name
                if not existing.last_name and last_name: existing.last_name = last_name
                if not existing.phone and phone: existing.phone = phone
                if not existing.notes and notes: existing.notes = notes
                if not existing.next_followup_at and followup_date: existing.next_followup_at = followup_date
                existing.updated_at = now
                updated_count += 1
            elif duplicate_strategy == "overwrite":
                if first_name: existing.first_name = first_name
                if last_name: existing.last_name = last_name
                if phone: existing.phone = phone
                if notes: existing.notes = (existing.notes + "\n" + notes).strip() if existing.notes else notes
                if followup_date: existing.next_followup_at = followup_date
                existing.status = status_val
                existing.updated_at = now
                updated_count += 1
            elif duplicate_strategy == "conflict":
                # Marca con nota di conflitto
                existing.notes = (existing.notes or "") + f"\n[CONFLITTO IMPORT CSV {now[:10]}]: {first_name} {last_name}, {phone}, {notes}"
                existing.updated_at = now
                updated_count += 1

            target_contact = existing
        else:
            # Creazione nuovo contatto
            target_contact = Contact(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                country=country,
                status=status_val,
                first_source=default_source,
                last_source=default_source,
                notes=notes,
                next_followup_at=followup_date if followup_date else None,
                created_at=now,
                updated_at=now,
            )
            db.add(target_contact)
            db.flush()
            created_count += 1

        # Gestione tag
        if tags_raw:
            tag_names = [t.strip().lower() for t in re.split(r"[,;|]", tags_raw) if t.strip()]
            for tn in tag_names:
                tag_obj = db.query(Tag).filter(Tag.name == tn).first()
                if not tag_obj:
                    tag_obj = Tag(name=tn, label=tn.capitalize(), color="#38bdf8", created_at=now)
                    db.add(tag_obj)
                    db.flush()
                if tag_obj not in target_contact.tags:
                    target_contact.tags.append(tag_obj)

        # Registra interazione di importazione
        interaction = ContactInteraction(
            contact_id=target_contact.id,
            type="import",
            created_at=now,
            source=default_source,
            subject=f"Importazione da CSV (Riga {line_idx})",
            note=f"Importato con strategia: {duplicate_strategy}",
            admin_user_id=admin_user_id,
        )
        db.add(interaction)

    db.commit()

    return {
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors[:50],  # Limita per sicurezza
    }


def generate_contacts_export_csv(contacts: List[Contact]) -> bytes:
    """Genera il file CSV per i contatti con codifica UTF-8 BOM e prevenzione formule."""
    output = io.StringIO()
    # Scrivi intestazioni
    fieldnames = [
        "ID",
        "Nome",
        "Cognome",
        "Email",
        "Telefono",
        "Paese",
        "Lingua",
        "Stato Commerciale",
        "Priorità",
        "Fonte Iniziale",
        "Ultima Fonte",
        "Blacklist",
        "Motivo Blacklist",
        "Data Creazione",
        "Ultimo Contatto",
        "Prossimo Follow-up",
        "Totale Speso (€)",
        "Tag",
        "Consenso Privacy",
        "Consenso Marketing Email",
        "Note",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    for c in contacts:
        tags_str = ", ".join(t.label for t in c.tags) if c.tags else ""
        spent_euro = f"{c.total_spent_cents / 100:.2f}"
        
        row_dict = {
            "ID": _sanitize_csv_value(c.id),
            "Nome": _sanitize_csv_value(c.first_name),
            "Cognome": _sanitize_csv_value(c.last_name),
            "Email": _sanitize_csv_value(c.email),
            "Telefono": _sanitize_csv_value(str(c.phone or "")),
            "Paese": _sanitize_csv_value(c.country or "IT"),
            "Lingua": _sanitize_csv_value(c.language or "it"),
            "Stato Commerciale": _sanitize_csv_value(c.status),
            "Priorità": _sanitize_csv_value(c.priority),
            "Fonte Iniziale": _sanitize_csv_value(c.first_source),
            "Ultima Fonte": _sanitize_csv_value(c.last_source),
            "Blacklist": "Sì" if c.is_blacklisted else "No",
            "Motivo Blacklist": _sanitize_csv_value(c.blacklist_reason or ""),
            "Data Creazione": _sanitize_csv_value(c.created_at[:10] if c.created_at else ""),
            "Ultimo Contatto": _sanitize_csv_value(c.last_contact_at[:10] if c.last_contact_at else ""),
            "Prossimo Follow-up": _sanitize_csv_value(c.next_followup_at[:10] if c.next_followup_at else ""),
            "Totale Speso (€)": spent_euro,
            "Tag": _sanitize_csv_value(tags_str),
            "Consenso Privacy": "Sì" if c.privacy_consent else "No",
            "Consenso Marketing Email": "Sì" if c.marketing_email_consent else "No",
            "Note": _sanitize_csv_value(c.notes or ""),
        }
        writer.writerow(row_dict)

    # Aggiunge UTF-8 BOM (\xef\xbb\xbf) affinché Excel apra correttamente i caratteri accentati
    csv_bytes = b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")
    return csv_bytes