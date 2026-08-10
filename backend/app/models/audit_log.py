"""backend/app/models/audit_log.py — Log immutabile delle operazioni admin."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(32), nullable=False, index=True,
                       default=lambda: datetime.now(timezone.utc).isoformat())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    # es. login, logout, page_save, coupon_create, report_download, cutoff_trigger

    resource_type = Column(String(32), nullable=True)   # page | workshop | coupon | media | report
    resource_id = Column(String(64), nullable=True)
    ip = Column(String(45), nullable=True)
    # NESSUN dato personale (email, nome, password, token) nei dettagli
    details = Column(Text, nullable=True)               # JSON senza dati personali

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "userId": self.user_id,
            "action": self.action,
            "resourceType": self.resource_type,
            "resourceId": self.resource_id,
            "ip": self.ip,
            "details": self.details,
        }
