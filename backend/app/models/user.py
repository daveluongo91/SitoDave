"""backend/app/models/user.py — Utenti admin con Argon2id."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from backend.app.config.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Argon2id
    role = Column(String(20), default="editor")           # admin | editor | viewer
    totp_secret = Column(String(64), nullable=True)       # 2FA opzionale
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    last_login = Column(String(32), nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(String(32), nullable=True)

    def is_locked(self) -> bool:
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc).isoformat() < self.locked_until
