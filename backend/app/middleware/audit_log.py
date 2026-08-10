"""
backend/app/middleware/audit_log.py
Funzioni di supporto per il log di audit.
IMPORTANTE: non loggare mai dati personali (email, nome, password, token).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog


def log_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Registra un'azione nell'audit log.
    I dettagli NON devono contenere: email, nome, cognome, telefono, password, token, dati personali.
    """
    # Sanitizza i dettagli rimuovendo eventuali campi sensibili
    safe_details = _sanitize_details(details or {})

    entry = AuditLog(
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        ip=ip,
        details=json.dumps(safe_details, ensure_ascii=False) if safe_details else None,
    )
    try:
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()  # Il log non deve bloccare l'operazione principale


_SENSITIVE_KEYS = {
    "email", "password", "phone", "telefono", "nome", "cognome",
    "firstName", "lastName", "first_name", "last_name",
    "token", "secret", "key", "smtp", "paypal",
}


def _sanitize_details(details: dict) -> dict:
    """Rimuove chiavi sensibili dai dettagli del log."""
    return {
        k: "[REDACTED]" if k.lower() in _SENSITIVE_KEYS else v
        for k, v in details.items()
    }
