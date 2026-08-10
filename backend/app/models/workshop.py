"""backend/app/models/workshop.py — Workshop con cutoff e disponibilità."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text
from backend.app.config.database import Base


class Workshop(Base):
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True, index=True)
    workshop_key = Column(String(64), unique=True, nullable=False, index=True)  # es. 'friuli-2026'
    slug = Column(String(128), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=True)           # nazionale | internazionale
    start_date = Column(String(32), nullable=True)          # ISO date string
    end_date = Column(String(32), nullable=True)
    timezone = Column(String(64), default="Europe/Rome", nullable=False)
    total_seats = Column(Integer, nullable=False, default=8)
    available_seats = Column(Integer, nullable=False, default=8)
    price_cents = Column(Integer, nullable=False)
    price_label = Column(String(32), nullable=True)        # es. '€290'
    status = Column(String(32), default="active", nullable=False)
    # active | soldout | cancelled | draft | completed

    # Cutoff
    cutoff_at = Column(String(32), nullable=True)           # ISO8601 con tz
    cutoff_status = Column(String(32), default="pending")  # pending | triggered | done | error
    report_generated_at = Column(String(32), nullable=True)
    report_version = Column(Integer, default=0)
    operative_notes = Column(Text, nullable=True)

    # Meta
    location = Column(String(255), nullable=True)
    duration = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    image = Column(String(512), nullable=True)
    details_url = Column(String(512), nullable=True)

    created_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat(),
                        onupdate=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workshopKey": self.workshop_key,
            "slug": self.slug,
            "title": self.title,
            "category": self.category,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "timezone": self.timezone,
            "totalSeats": self.total_seats,
            "availableSeats": self.available_seats,
            "priceCents": self.price_cents,
            "priceLabel": self.price_label,
            "status": self.status,
            "cutoffAt": self.cutoff_at,
            "cutoffStatus": self.cutoff_status,
            "reportGeneratedAt": self.report_generated_at,
            "reportVersion": self.report_version,
            "operativeNotes": self.operative_notes,
            "location": self.location,
            "duration": self.duration,
            "description": self.description,
            "image": self.image,
            "detailsUrl": self.details_url,
        }
