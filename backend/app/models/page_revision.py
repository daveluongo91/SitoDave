"""backend/app/models/page_revision.py — Revisioni pagine CMS (cronologia)."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base


class PageRevision(Base):
    __tablename__ = "page_revisions"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    # Snapshot completo dei blocchi in JSON
    blocks_snapshot = Column(Text, nullable=False)
    created_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    label = Column(String(128), nullable=True)   # es. "Pubblicazione 05/08/2026"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pageId": self.page_id,
            "createdAt": self.created_at,
            "createdBy": self.created_by,
            "label": self.label,
        }
