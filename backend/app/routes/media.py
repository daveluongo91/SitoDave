"""
backend/app/routes/media.py
Upload e gestione libreria immagini — solo admin.
Pipeline completa backend-side.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.config.settings import settings
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.media import Media
from backend.app.models.user import User
from backend.app.services.image_service import process_image, detect_mime, ALLOWED_MIME_TYPES

router = APIRouter(prefix="/api/admin/media", tags=["admin-media"])


@router.post("/upload", dependencies=[Depends(verify_csrf)])
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    altText: Optional[str] = Form(default=None),
    caption: Optional[str] = Form(default=None),
    pageTag: Optional[str] = Form(default="general"),
    tags: Optional[str] = Form(default=None),   # JSON array string
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Upload immagine con pipeline completa backend.
    Verifica MIME reale, limiti, orientamento EXIF, sRGB, varianti responsive.
    """
    # Limite upload grezzo prima di leggere il file
    if file.size and file.size > settings.upload_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File troppo grande. Limite: {settings.upload_max_bytes // 1024 // 1024} MB"
        )

    raw_bytes = await file.read()

    # Verifica MIME reale (non basarsi sull'estensione o Content-Type del client)
    real_mime = detect_mime(raw_bytes)
    if real_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Formato immagine non supportato.")

    # Verifica deduplicazione per hash
    import hashlib
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    existing = db.query(Media).filter(Media.hash_sha256 == file_hash, Media.is_deleted.is_(False)).first()
    if existing:
        return {
            "status": "duplicate",
            "message": "Immagine già presente nella libreria.",
            "media": existing.to_dict(),
        }

    # Pipeline immagini
    try:
        result = process_image(
            raw_bytes=raw_bytes,
            original_filename=file.filename or "upload.jpg",
            output_dir=settings.public_upload_dir,
            originals_dir=settings.originals_dir / "upload",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Salva nel DB
    media = Media(
        original_filename=file.filename or "upload",
        stored_filename=result["storedFilename"],
        mime_type=real_mime,
        width=result["width"],
        height=result["height"],
        file_size_bytes=result["fileSizeBytes"],
        hash_sha256=result["hashSha256"],
        alt_text=altText,
        caption=caption,
        tags=tags,
        page_tag=pageTag,
        webp_path=result["webpPath"],
        jpeg_path=result["jpegPath"],
        variants=result["variants"],
        uploaded_by=current_user.id,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    log_action(db, "media_upload", user_id=current_user.id,
               resource_type="media", resource_id=str(media.id),
               details={"filename": file.filename, "wasRescaled": result["wasRescaled"]},
               ip=request.client.host if request.client else None)

    return {"status": "ok", "media": media.to_dict()}


@router.get("/")
async def list_media(
    page_tag: Optional[str] = None,
    tags: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(Media).filter(Media.is_deleted.is_(False))
    if page_tag:
        query = query.filter(Media.page_tag == page_tag)
    media_list = query.order_by(Media.uploaded_at.desc()).all()
    return {"media": [m.to_dict() for m in media_list]}


@router.get("/{media_id}")
async def get_media(
    media_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    m = db.query(Media).filter(Media.id == media_id, Media.is_deleted.is_(False)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Media non trovato.")
    return m.to_dict()


class MediaUpdate(BaseModel):
    altText: Optional[str] = None
    caption: Optional[str] = None
    focalPointX: Optional[float] = None
    focalPointY: Optional[float] = None
    tags: Optional[str] = None

    from pydantic import field_validator
    @field_validator("focalPointX", "focalPointY")
    @classmethod
    def focal_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Il punto focale deve essere tra 0.0 e 1.0.")
        return v


from pydantic import BaseModel


@router.put("/{media_id}", dependencies=[Depends(verify_csrf)])
async def update_media(
    request: Request,
    media_id: int,
    body: MediaUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    m = db.query(Media).filter(Media.id == media_id, Media.is_deleted.is_(False)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Media non trovato.")

    if body.altText is not None:
        m.alt_text = body.altText[:512]
    if body.caption is not None:
        m.caption = body.caption[:512]
    if body.focalPointX is not None:
        m.focal_point_x = body.focalPointX
    if body.focalPointY is not None:
        m.focal_point_y = body.focalPointY
    if body.tags is not None:
        m.tags = body.tags

    db.commit()
    return m.to_dict()


@router.delete("/{media_id}", dependencies=[Depends(verify_csrf)])
async def delete_media(
    request: Request,
    media_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Elimina immagine — protetta se ancora in uso nei blocchi CMS."""
    m = db.query(Media).filter(Media.id == media_id, Media.is_deleted.is_(False)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Media non trovato.")

    # Verifica utilizzo nei blocchi CMS
    from backend.app.models.block import Block
    usage = db.query(Block).filter(
        Block.content.contains(m.stored_filename),
        Block.is_visible.is_(True),
    ).count()
    if usage > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Immagine in uso in {usage} blocchi CMS. Sostituiscila prima di eliminarla."
        )

    m.is_deleted = True
    db.commit()

    log_action(db, "media_delete", user_id=current_user.id,
               resource_type="media", resource_id=str(media_id),
               ip=request.client.host if request.client else None)
    return {"status": "ok"}
