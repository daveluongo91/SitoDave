"""
backend/app/routes/backup.py
Router amministrativo per la creazione, verifica e download dei backup SQLite.
Solo per amministratori con ruolo admin e CSRF token verificato.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.config.settings import settings
from backend.app.middleware.auth import require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.user import User
from backend.app.services.backup_service import (
    create_database_backup,
    list_database_backups,
    verify_backup_integrity,
)

router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])


@router.get("/")
async def get_backups(current_user: User = Depends(require_role("admin"))):
    """Elenco dei backup disponibili."""
    return {"backups": list_database_backups()}


@router.post("/create", dependencies=[Depends(verify_csrf)])
async def trigger_backup(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Crea un backup atomico immediato del database SQLite."""
    try:
        backup_info = create_database_backup()
        log_action(
            db, "database_backup_create",
            user_id=current_user.id,
            resource_type="backup",
            resource_id=backup_info["filename"],
            details={"hash": backup_info["hashSha256"], "size": backup_info["sizeFormatted"]},
            ip=request.client.host if request.client else None,
        )
        return {"status": "ok", "backup": backup_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore creazione backup: {str(e)}")


@router.get("/{filename}/download")
async def download_backup(
    filename: str,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Download protetto del file di backup SQLite."""
    backup_dir = settings.private_dir / "database" / "backups"
    target = (backup_dir / filename).resolve()

    try:
        target.relative_to(backup_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Accesso non autorizzato al file.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Backup non trovato.")

    log_action(
        db, "database_backup_download",
        user_id=current_user.id,
        resource_type="backup",
        resource_id=filename,
        ip=request.client.host if request.client else None,
    )

    return FileResponse(
        path=target,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )