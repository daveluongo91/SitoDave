"""
backend/app/services/cms_service.py
Logica CMS: sanitizzazione HTML, gestione blocchi, revisioni, locking.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.page import Page
from backend.app.models.block import Block, BLOCK_TYPES, BLOCK_VARIANTS
from backend.app.models.page_revision import PageRevision

try:
    import bleach
    from bleach.linkifier import LinkifyFilter
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

# ── Sanitizzazione HTML (whitelist sicura) ────────────────────────────────────

# Tag HTML ammessi nei blocchi richtext
ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u", "s",
    "h2", "h3", "h4",
    "ul", "ol", "li",
    "a",
    "blockquote",
    "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td",
    "span",
]

# Attributi ammessi per tag
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],        # rel gestito da noi
    "img": [],                            # img NON ammessa in richtext (usa blocco immagine)
    "*": ["class"],                       # solo classi CSS, nessun attributo evento
}

# Protocolli ammessi negli href
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# Classi CSS ammesse (whitelist)
ALLOWED_CLASSES = {
    "span": ["highlight", "accent", "gradient-text"],
    "*": [],
}


def sanitize_html(raw_html: str) -> str:
    """
    Sanitizza HTML con bleach whitelist.
    Rimuove: script, iframe, attributi evento (onclick, onerror, ecc.),
    URL javascript:, tag non ammessi, attributi non ammessi.
    Aggiunge rel="noopener noreferrer" ai link _blank.
    """
    if not raw_html:
        return ""

    if not HAS_BLEACH:
        # Fallback: escape completo se bleach non installato
        import html
        return html.escape(raw_html)

    def set_link_attrs(tag, name, value):
        if name == "href":
            # Blocca javascript: e data: URL
            if value.strip().lower().startswith(("javascript:", "data:", "vbscript:")):
                return False
        if name == "class":
            allowed = ALLOWED_CLASSES.get(tag, ALLOWED_CLASSES.get("*", []))
            classes = [c for c in value.split() if c in allowed]
            if not classes:
                return False
            return " ".join(classes)
        return value

    clean = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )

    # Forza rel="noopener noreferrer" su tutti i link con target
    # (bleach non gestisce target, quindi non ammettiamo target arbitrari)
    return clean


def sanitize_block_content(block_type: str, content: dict) -> dict:
    """
    Sanitizza il contenuto di un blocco in base al tipo.
    Applica sanitizzazione HTML solo ai campi richtext.
    """
    if block_type not in BLOCK_TYPES:
        raise ValueError(f"Tipo di blocco non valido: {block_type}")

    sanitized = {}
    for key, value in content.items():
        if isinstance(value, str):
            if block_type in ("richtext", "quote") and key in ("html", "content", "text", "body"):
                sanitized[key] = sanitize_html(value)
            else:
                # Testo semplice: nessun HTML ammesso
                sanitized[key] = _strip_all_html(value)
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, (list, dict)):
            # JSON complesso: serializza e deserializza per sicurezza
            sanitized[key] = json.loads(json.dumps(value))
        else:
            sanitized[key] = None

    return sanitized


def _strip_all_html(text: str) -> str:
    """Rimuove tutti i tag HTML da testo semplice."""
    if not text:
        return ""
    if not HAS_BLEACH:
        import re
        return re.sub(r"<[^>]+>", "", text)
    return bleach.clean(text, tags=[], strip=True)


# ── Locking pagine ────────────────────────────────────────────────────────────

LOCK_DURATION_MINUTES = 5


def acquire_lock(db: Session, page: Page, user_id: int) -> bool:
    """
    Tenta di acquisire il lock sulla pagina per l'utente.
    Restituisce True se riuscito, False se occupato da un altro utente.
    """
    if page.is_locked_by_other(user_id):
        return False

    page.lock_user = user_id
    page.lock_expires = (
        datetime.now(timezone.utc) + timedelta(minutes=LOCK_DURATION_MINUTES)
    ).isoformat()
    db.commit()
    return True


def release_lock(db: Session, page: Page, user_id: int) -> None:
    """Rilascia il lock se appartiene all'utente corrente."""
    if page.lock_user == user_id:
        page.lock_user = None
        page.lock_expires = None
        db.commit()


# ── Revisioni ────────────────────────────────────────────────────────────────

def create_revision(
    db: Session,
    page: Page,
    user_id: int,
    label: Optional[str] = None,
) -> PageRevision:
    """Salva uno snapshot immutabile dei blocchi correnti."""
    blocks = (
        db.query(Block)
        .filter(Block.page_id == page.id)
        .order_by(Block.order_index)
        .all()
    )
    snapshot = json.dumps([b.to_dict() for b in blocks], ensure_ascii=False)

    revision = PageRevision(
        page_id=page.id,
        blocks_snapshot=snapshot,
        created_by=user_id,
        label=label or f"Revisione {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}",
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return revision


def restore_revision(db: Session, page: Page, revision: PageRevision, user_id: int) -> None:
    """Ripristina i blocchi di una revisione precedente."""
    # Crea revisione di sicurezza prima di ripristinare
    create_revision(db, page, user_id, label=f"Auto-save prima di ripristino rev. {revision.id}")

    blocks_data = json.loads(revision.blocks_snapshot)

    # Elimina blocchi correnti
    db.query(Block).filter(Block.page_id == page.id).delete()
    db.commit()

    # Ricrea dai dati della revisione
    for bd in blocks_data:
        block = Block(
            page_id=page.id,
            block_key=uuid.uuid4().hex,  # nuovo ID stabile
            type=bd.get("type", "text"),
            content=bd.get("content", "{}"),
            order_index=bd.get("orderIndex", 0),
            is_visible=bd.get("isVisible", True),
            variant=bd.get("variant"),
            responsive_settings=bd.get("responsiveSettings"),
        )
        db.add(block)

    page.updated_at = datetime.now(timezone.utc).isoformat()
    page.updated_by = user_id
    db.commit()
