"""
backend/app/routes/content.py
CMS a blocchi — gestione pagine, blocchi, revisioni.
Solo admin autenticati con CSRF.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.block import Block, BLOCK_TYPES, BLOCK_VARIANTS
from backend.app.models.page import Page
from backend.app.models.page_revision import PageRevision
from backend.app.models.user import User
from backend.app.services.cms_service import (
    acquire_lock,
    create_revision,
    release_lock,
    restore_revision,
    sanitize_block_content,
)

router = APIRouter(prefix="/api/admin/pages", tags=["admin-cms"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class BlockData(BaseModel):
    blockKey: Optional[str] = None   # None = nuovo blocco
    type: str
    content: dict
    orderIndex: int
    isVisible: bool = True
    variant: Optional[str] = None
    responsiveSettings: Optional[dict] = None

    @field_validator("type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in BLOCK_TYPES:
            raise ValueError(f"Tipo blocco non valido: {v}. Tipi ammessi: {', '.join(sorted(BLOCK_TYPES))}")
        return v

    @field_validator("variant")
    @classmethod
    def valid_variant(cls, v: Optional[str], info) -> Optional[str]:
        if v is None:
            return None
        block_type = info.data.get("type", "")
        allowed = BLOCK_VARIANTS.get(block_type, [])
        if allowed and v not in allowed:
            raise ValueError(f"Variante '{v}' non valida per il blocco '{block_type}'. Ammesse: {', '.join(allowed)}")
        return v


class PageSaveRequest(BaseModel):
    blocks: list[BlockData]
    seoTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    status: Optional[str] = None   # draft | published
    label: Optional[str] = None    # etichetta revisione


# ── Endpoints Pagine ─────────────────────────────────────────────────────────

@router.get("/")
async def list_pages(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    pages = db.query(Page).order_by(Page.admin_title).all()
    return {"pages": [p.to_dict() for p in pages]}


@router.get("/{page_key}")
async def get_page(
    page_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Pagina non trovata.")

    blocks = (
        db.query(Block)
        .filter(Block.page_id == page.id)
        .order_by(Block.order_index)
        .all()
    )

    result = page.to_dict()
    result["blocks"] = [b.to_dict() for b in blocks]
    result["isLockedByOther"] = page.is_locked_by_other(current_user.id)
    return result


@router.post("/{page_key}/lock", dependencies=[Depends(verify_csrf)])
async def acquire_page_lock(
    page_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Pagina non trovata.")

    success = acquire_lock(db, page, current_user.id)
    if not success:
        raise HTTPException(
            status_code=423,
            detail=f"Pagina in modifica da un altro utente. Riprova tra qualche minuto."
        )
    return {"status": "ok", "lockExpires": page.lock_expires}


@router.post("/{page_key}/unlock", dependencies=[Depends(verify_csrf)])
async def release_page_lock(
    page_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if page:
        release_lock(db, page, current_user.id)
    return {"status": "ok"}


@router.put("/{page_key}", dependencies=[Depends(verify_csrf)])
async def save_page(
    request: Request,
    page_key: str,
    body: PageSaveRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """
    Salva blocchi di una pagina con sanitizzazione HTML e snapshot revisione.
    Richiede lock acquisito.
    """
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Pagina non trovata.")

    if page.is_locked_by_other(current_user.id):
        raise HTTPException(
            status_code=423,
            detail="Pagina in modifica da un altro utente."
        )

    # Crea revisione prima di modificare
    create_revision(db, page, current_user.id, label=body.label)

    # Aggiorna metadati pagina
    if body.seoTitle is not None:
        page.seo_title = body.seoTitle[:80]
    if body.metaDescription is not None:
        page.meta_description = body.metaDescription[:165]
    if body.status in ("draft", "published"):
        page.status = body.status
    page.updated_at = datetime.now(timezone.utc).isoformat()
    page.updated_by = current_user.id

    # Elimina blocchi esistenti e ricrea
    db.query(Block).filter(Block.page_id == page.id).delete()
    db.commit()

    for i, bd in enumerate(body.blocks):
        # Sanitizza contenuto in base al tipo
        try:
            sanitized_content = sanitize_block_content(bd.type, bd.content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        block_key = bd.blockKey or uuid.uuid4().hex

        block = Block(
            page_id=page.id,
            block_key=block_key,
            type=bd.type,
            content=json.dumps(sanitized_content, ensure_ascii=False),
            order_index=i,
            is_visible=bd.isVisible,
            variant=bd.variant,
            responsive_settings=json.dumps(bd.responsiveSettings) if bd.responsiveSettings else None,
        )
        db.add(block)

    db.commit()

    log_action(db, "page_save", user_id=current_user.id,
               resource_type="page", resource_id=page_key,
               details={"blockCount": len(body.blocks), "status": body.status},
               ip=request.client.host if request.client else None)

    return {"status": "ok", "message": f"Pagina '{page.admin_title}' salvata."}


@router.post("/{page_key}/publish", dependencies=[Depends(verify_csrf)])
async def publish_page(
    request: Request,
    page_key: str,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Pagina non trovata.")
    page.status = "published"
    page.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_action(db, "page_publish", user_id=current_user.id,
               resource_type="page", resource_id=page_key,
               ip=request.client.host if request.client else None)
    return {"status": "ok"}


# ── Revisioni ────────────────────────────────────────────────────────────────

@router.get("/{page_key}/revisions")
async def list_revisions(
    page_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Pagina non trovata.")
    revisions = (
        db.query(PageRevision)
        .filter(PageRevision.page_id == page.id)
        .order_by(PageRevision.created_at.desc())
        .limit(50)
        .all()
    )
    return {"revisions": [r.to_dict() for r in revisions]}


@router.post("/{page_key}/revisions/{revision_id}/restore", dependencies=[Depends(verify_csrf)])
async def restore_page_revision(
    request: Request,
    page_key: str,
    revision_id: int,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.page_key == page_key).first()
    if not page:
        raise HTTPException(status_code=404, detail="Pagina non trovata.")

    revision = db.query(PageRevision).filter(
        PageRevision.id == revision_id,
        PageRevision.page_id == page.id,
    ).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revisione non trovata.")

    restore_revision(db, page, revision, current_user.id)

    log_action(db, "page_restore_revision", user_id=current_user.id,
               resource_type="page", resource_id=page_key,
               details={"revisionId": revision_id},
               ip=request.client.host if request.client else None)

    return {"status": "ok", "message": f"Revisione {revision_id} ripristinata."}
