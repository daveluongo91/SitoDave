"""backend/app/models/session.py — Sessioni server-side con cookie HttpOnly."""
from __future__ import annotations
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from backend.app.config.database import Base


class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)       # UUID v4 hex
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(String(32), nullable=False)
    expires_at = Column(String(32), nullable=False)
    ip = Column(String(45), nullable=True)           # IPv4 o IPv6
    user_agent = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
