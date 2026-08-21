"""backend/app/models/tag.py — Tag contatti personalizzabili."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.config.database import Base

contact_tags = Table(
    "contact_tags",
    Base.metadata,
    Column("contact_id", Integer, ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False, index=True)   # es. 'astrofotografia'
    label = Column(String(64), nullable=False)                          # es. 'Astrofotografia'
    color = Column(String(32), default="#38bdf8", nullable=False)        # hex color code
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    contacts = relationship("Contact", secondary=contact_tags, back_populates="tags")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "color": self.color,
            "createdAt": self.created_at,
        }