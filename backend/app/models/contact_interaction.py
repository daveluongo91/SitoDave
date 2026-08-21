"""backend/app/models/contact_interaction.py — Cronologia e interazioni contatti."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.config.database import Base


class ContactInteraction(Base):
    __tablename__ = "contact_interactions"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Tipi di interazione:
    # info_request | phone_call | email | whatsapp | quote | booking | payment | refund | internal_note | import | status_change
    type = Column(String(32), nullable=False, default="internal_note", index=True)
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    source = Column(String(64), nullable=True)
    subject = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    workshop_or_trip_key = Column(String(64), nullable=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    contact = relationship("Contact", back_populates="interactions")
    admin_user = relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contactId": self.contact_id,
            "type": self.type,
            "createdAt": self.created_at,
            "source": self.source or "",
            "subject": self.subject or "",
            "note": self.note or "",
            "workshopOrTripKey": self.workshop_or_trip_key or "",
            "adminUserId": self.admin_user_id,
            "adminUserName": self.admin_user.username if self.admin_user else "Sistema",
        }