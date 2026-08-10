"""
backend/app/routes/reports.py
Gestione report XLSX: lista, download protetto, generazione manuale.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.report import Report
from backend.app.models.user import User
from backend.app.models.workshop import Workshop
from backend.app.services.cutoff_service import run_cutoff

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])


@router.get("/")
async def list_reports(
    workshopId: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(Report)
    if workshopId:
        query = query.filter(Report.workshop_id == workshopId)
    reports = query.order_by(Report.generated_at.desc()).all()
    return {"reports": [r.to_dict() for r in reports]}


class GenerateRequest(BaseModel):
    force: bool = False
    notes: Optional[str] = None


@router.post("/{workshop_id}/generate", dependencies=[Depends(verify_csrf)])
async def generate_report(
    request: Request,
    workshop_id: str,
    body: GenerateRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Genera manualmente un report XLSX per un workshop."""
    result = run_cutoff(
        workshop_id=workshop_id,
        db=db,
        triggered_by_user_id=current_user.id,
        force=body.force,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Download del report XLSX.
    Solo admin autenticati. File servito da directory privata, non pubblica.
    Registra il download nell'audit log.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report non trovato.")

    filepath = Path(report.file_path)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File report non trovato sul disco.")

    # Verifica che il file sia dentro la directory privata (path traversal protection)
    from backend.app.config.settings import settings
    try:
        filepath.resolve().relative_to(settings.exports_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Accesso non autorizzato al file.")

    log_action(
        db,
        action="report_download",
        user_id=current_user.id,
        resource_type="report",
        resource_id=str(report_id),
        details={"workshopId": report.workshop_id, "version": report.version},
        ip=request.client.host if request.client else None,
    )

    return FileResponse(
        path=str(filepath),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filepath.name,
        headers={
            "Content-Disposition": f'attachment; filename="{filepath.name}"',
            "Cache-Control": "no-store",
        },
    )
