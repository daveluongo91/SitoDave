"""Iscritti agli avvisi di disponibilità dei workshop."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint

from backend.app.config.database import Base


class AvailabilitySubscriber(Base):
    __tablename__ = "availability_subscribers"
    __table_args__ = (
        UniqueConstraint("workshop_id", "email", name="uq_availability_workshop_email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(String(64), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    consent_at = Column(String(32), nullable=False)
    consent_source = Column(String(64), nullable=False, default="landing")
    unsubscribe_token = Column(String(96), unique=True, nullable=False, index=True)
    active = Column(Boolean, nullable=False, default=True)
    notified_two_at = Column(String(32), nullable=True)
    notified_one_at = Column(String(32), nullable=True)
    unsubscribed_at = Column(String(32), nullable=True)
    created_at = Column(
        String(32),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

