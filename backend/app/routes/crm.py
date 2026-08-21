"""
backend/app/routes/crm.py
Router per la gestione CRM: contatti, interazioni, tag, blacklist, import/export CSV e statistiche.
Solo admin autenticati con controlli CSRF sulle mutazioni.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.contact import Contact
from backend.app.models.contact_interaction import ContactInteraction
from backend.app.models.tag import Tag
from backend.app.models.user import User
from backend.app.services.crm_service import (
    normalize_email,
    normalize_phone,
    get_crm_dashboard_metrics,
)
from backend.app.services.csv_service import (
    parse_csv_preview,
    execute_csv_import,
    generate_contacts_export_csv,
)

router = APIRouter(prefix="/api/admin/crm", tags=["admin-crm"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ContactCreateRequest(BaseModel):
    firstName: str
    lastName: str = ""
    email: str
    phone: Optional[str] = None
    country: Optional[str] = "IT"
    status: Optional[str] = "new_lead"
    priority: Optional[str] = "medium"
    notes: Optional[str] = None
    nextFollowupAt: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("firstName", "email")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obbligatorio.")
        return v.strip()


class ContactUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    nextFollowupAt: Optional[str] = None
    tags: Optional[List[str]] = None


class InteractionCreateRequest(BaseModel):
    type: str  # phone_call | email | whatsapp | quote | internal_note | status_change
    subject: Optional[str] = None
    note: str
    workshopOrTripKey: Optional[str] = None


class BlacklistRequest(BaseModel):
    isBlacklisted: bool
    reason: Optional[str] = None


class BulkActionRequest(BaseModel):
    contactIds: List[int]
    action: str  # set_status | add_tag | remove_tag | blacklist | delete
    statusValue: Optional[str] = None
    tagName: Optional[str] = None
    blacklistReason: Optional[str] = None


class TagCreateRequest(BaseModel):
    name: str
    label: str
    color: Optional[str] = "#38bdf8"


# ── 1. Metriche Dashboard ───────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Restituisce le statistiche aggregate per la dashboard CRM."""
    return get_crm_dashboard_metrics(db)


# ── 2. Lista e Ricerca Contatti ──────────────────────────────────────────────

@router.get("/contacts")
async def list_contacts(
    search: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    priority: Optional[str] = None,
    isBlacklisted: Optional[bool] = None,
    followupFilter: Optional[str] = None,  # today | overdue | future
    page: int = 1,
    limit: int = 50,
    sortBy: str = "createdAt",
    sortOrder: str = "desc",
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Lista contatti filtrabile, paginata e ordinabile."""
    query = db.query(Contact).filter(Contact.is_deleted.is_(False))

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Contact.first_name.ilike(s),
                Contact.last_name.ilike(s),
                Contact.email.ilike(s),
                Contact.phone.ilike(s),
                Contact.notes.ilike(s),
            )
        )

    if status:
        query = query.filter(Contact.status == status)

    if priority:
        query = query.filter(Contact.priority == priority)

    if isBlacklisted is not None:
        query = query.filter(Contact.is_blacklisted == isBlacklisted)

    if tag:
        query = query.join(Contact.tags).filter(Tag.name == tag.strip().lower())

    if followupFilter:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if followupFilter == "today":
            query = query.filter(Contact.next_followup_at.like(f"{today_str}%"))
        elif followupFilter == "overdue":
            query = query.filter(
                Contact.next_followup_at < today_str,
                Contact.next_followup_at.isnot(None),
                Contact.status.notin_(["customer", "loyal_customer", "lost_lead", "inactive"]),
            )

    # Conteggio totale
    total = query.count()

    # Ordinamento
    order_col = Contact.created_at
    if sortBy == "name":
        order_col = Contact.first_name
    elif sortBy == "email":
        order_col = Contact.email
    elif sortBy == "lastContact":
        order_col = Contact.last_contact_at
    elif sortBy == "nextFollowup":
        order_col = Contact.next_followup_at
    elif sortBy == "totalSpent":
        order_col = Contact.total_spent_cents

    if sortOrder == "asc":
        query = query.order_by(asc(order_col))
    else:
        query = query.order_by(desc(order_col))

    # Paginazione
    offset = max(0, (page - 1) * limit)
    contacts = query.offset(offset).limit(limit).all()

    return {
        "contacts": [c.to_dict() for c in contacts],
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": max(1, (total + limit - 1) // limit),
    }


# ── 3. Dettaglio Contatto ────────────────────────────────────────────────────

@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Restituisce il dettaglio completo del contatto con cronologia interazioni."""
    c = db.query(Contact).filter(Contact.id == contact_id, Contact.is_deleted.is_(False)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contatto non trovato.")

    interactions = [i.to_dict() for i in c.interactions]
    contact_data = c.to_dict()
    contact_data["interactions"] = interactions
    return contact_data


# ── 4. Creazione Contatto ────────────────────────────────────────────────────

@router.post("/contacts", dependencies=[Depends(verify_csrf)])
async def create_contact(
    request: Request,
    body: ContactCreateRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Crea un nuovo contatto manualmente."""
    norm_email = normalize_email(body.email)
    existing = db.query(Contact).filter(Contact.email == norm_email, Contact.is_deleted.is_(False)).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Un contatto con email '{norm_email}' esiste già.")

    now = datetime.now(timezone.utc).isoformat()
    contact = Contact(
        first_name=body.firstName.strip(),
        last_name=body.lastName.strip(),
        email=norm_email,
        phone=normalize_phone(body.phone),
        country=body.country or "IT",
        status=body.status or "new_lead",
        priority=body.priority or "medium",
        notes=body.notes,
        next_followup_at=body.nextFollowupAt,
        first_source="manual_entry",
        last_source="manual_entry",
        created_at=now,
        updated_at=now,
        last_contact_at=now,
    )
    db.add(contact)
    db.flush()

    if body.tags:
        for t_name in body.tags:
            tn = t_name.strip().lower()
            tag_obj = db.query(Tag).filter(Tag.name == tn).first()
            if not tag_obj:
                tag_obj = Tag(name=tn, label=tn.capitalize(), color="#38bdf8", created_at=now)
                db.add(tag_obj)
                db.flush()
            contact.tags.append(tag_obj)

    # Registra interazione di creazione
    interaction = ContactInteraction(
        contact_id=contact.id,
        type="internal_note",
        created_at=now,
        source="manual_entry",
        subject="Contatto creato manualmente",
        note="Inserito dall'amministratore.",
        admin_user_id=current_user.id,
    )
    db.add(interaction)
    db.commit()

    log_action(db, "contact_create", user_id=current_user.id, resource_type="contact", resource_id=str(contact.id), ip=request.client.host if request.client else None)
    return contact.to_dict()


# ── 5. Modifica Contatto ─────────────────────────────────────────────────────

@router.put("/contacts/{contact_id}", dependencies=[Depends(verify_csrf)])
async def update_contact(
    request: Request,
    contact_id: int,
    body: ContactUpdateRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Aggiorna i dati di un contatto."""
    c = db.query(Contact).filter(Contact.id == contact_id, Contact.is_deleted.is_(False)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contatto non trovato.")

    now = datetime.now(timezone.utc).isoformat()
    changes = []

    if body.firstName is not None:
        c.first_name = body.firstName.strip()
    if body.lastName is not None:
        c.last_name = body.lastName.strip()
    if body.email is not None:
        c.email = normalize_email(body.email)
    if body.phone is not None:
        c.phone = normalize_phone(body.phone)
    if body.country is not None:
        c.country = body.country.strip()
    if body.priority is not None:
        c.priority = body.priority
    if body.notes is not None:
        c.notes = body.notes
    if body.nextFollowupAt is not None:
        c.next_followup_at = body.nextFollowupAt

    if body.status is not None and body.status != c.status:
        old_status = c.status
        c.status = body.status
        changes.append(f"Stato: {old_status} -> {body.status}")
        # Registra interazione di cambio stato
        db.add(ContactInteraction(
            contact_id=c.id,
            type="status_change",
            created_at=now,
            subject="Modifica stato commerciale",
            note=f"Stato modificato da '{old_status}' a '{body.status}'",
            admin_user_id=current_user.id,
        ))

    if body.tags is not None:
        c.tags.clear()
        for tn in body.tags:
            t_clean = tn.strip().lower()
            tag_obj = db.query(Tag).filter(Tag.name == t_clean).first()
            if not tag_obj:
                tag_obj = Tag(name=t_clean, label=t_clean.capitalize(), color="#38bdf8", created_at=now)
                db.add(tag_obj)
                db.flush()
            c.tags.append(tag_obj)

    c.updated_at = now
    db.commit()

    log_action(db, "contact_update", user_id=current_user.id, resource_type="contact", resource_id=str(c.id), details={"changes": changes}, ip=request.client.host if request.client else None)
    return c.to_dict()


# ── 6. Blacklist Contatto ────────────────────────────────────────────────────

@router.post("/contacts/{contact_id}/blacklist", dependencies=[Depends(verify_csrf)])
async def toggle_blacklist(
    request: Request,
    contact_id: int,
    body: BlacklistRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Inserisce o rimuove un contatto dalla blacklist."""
    c = db.query(Contact).filter(Contact.id == contact_id, Contact.is_deleted.is_(False)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contatto non trovato.")

    now = datetime.now(timezone.utc).isoformat()
    c.is_blacklisted = body.isBlacklisted
    if body.isBlacklisted:
        c.blacklist_reason = body.reason or "Non specificato"
        c.blacklisted_at = now
    else:
        c.blacklist_reason = None
        c.blacklisted_at = None

    c.updated_at = now
    # Interazione
    db.add(ContactInteraction(
        contact_id=c.id,
        type="internal_note",
        created_at=now,
        subject="Blacklist aggiornata",
        note=f"{'Inserito in' if body.isBlacklisted else 'Rimosso da'} Blacklist. Motivo: {body.reason or 'N/A'}",
        admin_user_id=current_user.id,
    ))
    db.commit()

    log_action(db, "contact_blacklist_toggle", user_id=current_user.id, resource_type="contact", resource_id=str(c.id), details={"isBlacklisted": body.isBlacklisted}, ip=request.client.host if request.client else None)
    return {"status": "ok", "isBlacklisted": c.is_blacklisted}


# ── 7. Nuova Interazione Manuale ─────────────────────────────────────────────

@router.post("/contacts/{contact_id}/interactions", dependencies=[Depends(verify_csrf)])
async def add_interaction(
    request: Request,
    contact_id: int,
    body: InteractionCreateRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Aggiunge una nuova interazione manuale (telefonata, nota, email, whatsapp, preventivo)."""
    c = db.query(Contact).filter(Contact.id == contact_id, Contact.is_deleted.is_(False)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contatto non trovato.")

    now = datetime.now(timezone.utc).isoformat()
    interaction = ContactInteraction(
        contact_id=c.id,
        type=body.type,
        created_at=now,
        source="manual_admin",
        subject=body.subject or body.type.replace("_", " ").capitalize(),
        note=body.note[:4000],
        workshop_or_trip_key=body.workshopOrTripKey,
        admin_user_id=current_user.id,
    )
    db.add(interaction)
    c.last_contact_at = now
    c.updated_at = now
    db.commit()

    log_action(db, "contact_interaction_add", user_id=current_user.id, resource_type="contact", resource_id=str(c.id), details={"type": body.type}, ip=request.client.host if request.client else None)
    return interaction.to_dict()


# ── 8. Azioni di Gruppo (Bulk Actions) ───────────────────────────────────────

@router.post("/contacts/bulk-action", dependencies=[Depends(verify_csrf)])
async def bulk_action(
    request: Request,
    body: BulkActionRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Esegue operazioni massive su una lista di contatti selezionati."""
    if not body.contactIds:
        raise HTTPException(status_code=400, detail="Nessun contatto selezionato.")

    contacts = db.query(Contact).filter(Contact.id.in_(body.contactIds), Contact.is_deleted.is_(False)).all()
    now = datetime.now(timezone.utc).isoformat()

    if body.action == "set_status" and body.statusValue:
        for c in contacts:
            c.status = body.statusValue
            c.updated_at = now
    elif body.action == "add_tag" and body.tagName:
        tn = body.tagName.strip().lower()
        tag_obj = db.query(Tag).filter(Tag.name == tn).first()
        if not tag_obj:
            tag_obj = Tag(name=tn, label=tn.capitalize(), color="#38bdf8", created_at=now)
            db.add(tag_obj)
            db.flush()
        for c in contacts:
            if tag_obj not in c.tags:
                c.tags.append(tag_obj)
                c.updated_at = now
    elif body.action == "remove_tag" and body.tagName:
        tn = body.tagName.strip().lower()
        tag_obj = db.query(Tag).filter(Tag.name == tn).first()
        if tag_obj:
            for c in contacts:
                if tag_obj in c.tags:
                    c.tags.remove(tag_obj)
                    c.updated_at = now
    elif body.action == "blacklist":
        for c in contacts:
            c.is_blacklisted = True
            c.blacklist_reason = body.blacklistReason or "Bulk Blacklist"
            c.blacklisted_at = now
            c.updated_at = now
    elif body.action == "delete":
        for c in contacts:
            c.is_deleted = True
            c.deleted_at = now

    db.commit()
    log_action(db, "contacts_bulk_action", user_id=current_user.id, resource_type="contact", resource_id="bulk", details={"action": body.action, "count": len(contacts)}, ip=request.client.host if request.client else None)
    return {"status": "ok", "affected": len(contacts)}


# ── 9. Importazione CSV (Fase 1: Anteprima, Fase 2: Esecuzione) ─────────────

@router.post("/contacts/import-preview", dependencies=[Depends(verify_csrf)])
async def import_csv_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("editor")),
):
    """Analizza il file CSV e restituisce l'anteprima per la mappatura."""
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File CSV troppo grande (limite 5 MB).")

    raw_bytes = await file.read()
    preview = parse_csv_preview(raw_bytes, max_rows=10)
    return preview


class ImportConfirmRequest(BaseModel):
    csvData: str  # Base64 o testo raw
    columnMapping: dict  # {"email": 0, "first_name": 1, ...}
    duplicateStrategy: str = "update_empty"  # skip | update_empty | overwrite | conflict
    defaultSource: str = "csv_import"


@router.post("/contacts/import-confirm", dependencies=[Depends(verify_csrf)])
async def import_csv_confirm(
    request: Request,
    file: UploadFile = File(...),
    mappingJson: str = Form(...),
    duplicateStrategy: str = Form(default="update_empty"),
    defaultSource: str = Form(default="csv_import"),
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Esegue l'importazione effettiva dei contatti con mappatura e strategia scelta."""
    try:
        column_mapping = json.loads(mappingJson)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato mappatura colonne non valido.")

    raw_bytes = await file.read()
    result = execute_csv_import(
        db=db,
        raw_bytes=raw_bytes,
        column_mapping={k: int(v) for k, v in column_mapping.items()},
        duplicate_strategy=duplicateStrategy,
        default_source=defaultSource,
        admin_user_id=current_user.id,
    )

    log_action(db, "contacts_csv_import", user_id=current_user.id, resource_type="contact", resource_id="import", details=result, ip=request.client.host if request.client else None)
    return result


# ── 10. Esportazione CSV ─────────────────────────────────────────────────────

@router.get("/contacts/export")
async def export_contacts_csv(
    request: Request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    isBlacklisted: Optional[bool] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Esporta i contatti filtrati in formato CSV con codifica UTF-8 BOM."""
    query = db.query(Contact).filter(Contact.is_deleted.is_(False))

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Contact.first_name.ilike(s),
                Contact.last_name.ilike(s),
                Contact.email.ilike(s),
                Contact.phone.ilike(s),
            )
        )

    if status:
        query = query.filter(Contact.status == status)

    if isBlacklisted is not None:
        query = query.filter(Contact.is_blacklisted == isBlacklisted)

    if tag:
        query = query.join(Contact.tags).filter(Tag.name == tag.strip().lower())

    contacts = query.order_by(Contact.created_at.desc()).all()
    csv_bytes = generate_contacts_export_csv(contacts)

    filename = f"contatti_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}.csv"

    log_action(db, "contacts_csv_export", user_id=current_user.id, resource_type="contact", resource_id="export", details={"count": len(contacts), "filename": filename}, ip=request.client.host if request.client else None)

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 11. Gestione Tag ─────────────────────────────────────────────────────────

@router.get("/tags")
async def list_tags(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    tags = db.query(Tag).order_by(Tag.label).all()
    return {"tags": [t.to_dict() for t in tags]}


@router.post("/tags", dependencies=[Depends(verify_csrf)])
async def create_tag(
    request: Request,
    body: TagCreateRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    tn = body.name.strip().lower()
    existing = db.query(Tag).filter(Tag.name == tn).first()
    if existing:
        return existing.to_dict()

    tag = Tag(
        name=tn,
        label=body.label.strip(),
        color=body.color or "#38bdf8",
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag.to_dict()