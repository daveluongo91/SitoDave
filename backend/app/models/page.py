"""backend/app/models/page.py — Pagine CMS con locking e stato bozza/pubblicata."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(64), unique=True, nullable=False, index=True)  # 'home', 'gear', ...
    slug = Column(String(128), unique=True, nullable=False)
    admin_title = Column(String(255), nullable=False)
    seo_title = Column(String(80), nullable=True)
    meta_description = Column(String(165), nullable=True)
    status = Column(String(16), default="draft", nullable=False)  # draft | published

    updated_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Locking concorrente
    lock_user = Column(Integer, ForeignKey("users.id"), nullable=True)
    lock_expires = Column(String(32), nullable=True)    # ISO8601

    def is_locked_by_other(self, user_id: int) -> bool:
        if not self.lock_user or self.lock_user == user_id:
            return False
        now = datetime.now(timezone.utc).isoformat()
        return bool(self.lock_expires and self.lock_expires > now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pageKey": self.page_key,
            "slug": self.slug,
            "adminTitle": self.admin_title,
            "seoTitle": self.seo_title,
            "metaDescription": self.meta_description,
            "status": self.status,
            "updatedAt": self.updated_at,
            "lockUser": self.lock_user,
            "lockExpires": self.lock_expires,
        }
