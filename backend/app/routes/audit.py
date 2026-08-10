"""
backend/app/routes/audit.py
Visualizzazione audit log — solo admin.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import require_role
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User

router = APIRouter(prefix="/api/admin/logs", tags=["admin-logs"])


@router.get("/audit")
async def list_audit_log(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Audit log — solo admin. Limitato a 100 voci per richiesta."""
    limit = min(limit, 500)
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.contains(action))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return {"logs": [l.to_dict() for l in logs]}
