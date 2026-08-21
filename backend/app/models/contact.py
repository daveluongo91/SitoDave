"""backend/app/models/contact.py — Contatti CRM."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.config.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(128), nullable=False, default="")
    last_name = Column(String(128), nullable=False, default="")
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(64), nullable=True, index=True)
    country = Column(String(64), nullable=True, default="IT")
    language = Column(String(16), nullable=False, default="it")

    first_source = Column(String(64), nullable=True)
    last_source = Column(String(64), nullable=True)

    # Stati commerciali:
    # new_lead | to_contact | contacted | qualified | quote_sent | customer | loyal_customer | lost_lead | inactive
    status = Column(String(32), nullable=False, default="new_lead", index=True)
    priority = Column(String(16), nullable=False, default="medium")  # low | medium | high | urgent
    owner = Column(String(64), nullable=True, default="Davide Luongo")
    notes = Column(Text, nullable=True)

    # Date e follow-up
    created_at = Column(String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat(), onupdate=lambda: datetime.now(timezone.utc).isoformat())
    last_contact_at = Column(String(32), nullable=True)
    next_followup_at = Column(String(32), nullable=True, index=True)
    customer_since = Column(String(32), nullable=True)

    # Valore economico (calcolato SOLO da pagamenti confermati)
    total_spent_cents = Column(Integer, nullable=False, default=0)

    # Blacklist separata (prioritaria su ogni invio o contatto)
    is_blacklisted = Column(Boolean, nullable=False, default=False, index=True)
    blacklist_reason = Column(Text, nullable=True)
    blacklisted_at = Column(String(32), nullable=True)

    # Privacy e Consensi (GDPR compliant)
    privacy_consent = Column(Boolean, nullable=False, default=True)
    privacy_consent_at = Column(String(32), nullable=True)
    marketing_email_consent = Column(Boolean, nullable=False, default=False)
    marketing_email_consent_at = Column(String(32), nullable=True)
    marketing_phone_consent = Column(Boolean, nullable=False, default=False)
    marketing_phone_consent_at = Column(String(32), nullable=True)
    consent_version = Column(String(32), nullable=False, default="1.0")
    consent_source = Column(String(128), nullable=True)
    consent_revoked = Column(Boolean, nullable=False, default=False)
    consent_revoked_at = Column(String(32), nullable=True)

    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(String(32), nullable=True)

    # Relationships
    interactions = relationship("ContactInteraction", back_populates="contact", cascade="all, delete-orphan", order_by="desc(ContactInteraction.created_at)")
    tags = relationship("Tag", secondary="contact_tags", back_populates="contacts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "fullName": f"{self.first_name} {self.last_name}".strip() or self.email,
            "email": self.email,
            "phone": self.phone or "",
            "country": self.country or "IT",
            "language": self.language or "it",
            "firstSource": self.first_source or "",
            "lastSource": self.last_source or "",
            "status": self.status,
            "priority": self.priority,
            "owner": self.owner,
            "notes": self.notes or "",
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "lastContactAt": self.last_contact_at,
            "nextFollowupAt": self.next_followup_at,
            "customerSince": self.customer_since,
            "totalSpentCents": self.total_spent_cents,
            "totalSpentLabel": f"€{self.total_spent_cents / 100:.2f}",
            "isBlacklisted": bool(self.is_blacklisted),
            "blacklistReason": self.blacklist_reason,
            "blacklistedAt": self.blacklisted_at,
            "privacyConsent": bool(self.privacy_consent),
            "privacyConsentAt": self.privacy_consent_at,
            "marketingEmailConsent": bool(self.marketing_email_consent),
            "marketingEmailConsentAt": self.marketing_email_consent_at,
            "marketingPhoneConsent": bool(self.marketing_phone_consent),
            "marketingPhoneConsentAt": self.marketing_phone_consent_at,
            "consentVersion": self.consent_version,
            "consentSource": self.consent_source,
            "consentRevoked": bool(self.consent_revoked),
            "consentRevokedAt": self.consent_revoked_at,
            "tags": [t.to_dict() for t in self.tags] if self.tags else [],
        }