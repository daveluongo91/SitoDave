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

    # Tipo di esperienza & Template
    experience_type = Column(String(32), default="workshop", nullable=False)  # workshop | international_trip
    template_version = Column(String(32), default="workshop-v1", nullable=False)

    # Campi specifici per viaggi internazionali & logistica estesa
    country = Column(String(128), nullable=True)
    destination = Column(String(255), nullable=True)
    arrival_airport = Column(String(128), nullable=True)
    currency = Column(String(16), default="EUR", nullable=False)
    flights_included = Column(Boolean, default=False, nullable=False)
    baggage_info = Column(Text, nullable=True)
    documents_required = Column(Text, nullable=True)
    passport_or_id = Column(String(64), nullable=True)
    visa_required = Column(Boolean, default=False, nullable=False)
    insurance_info = Column(Text, nullable=True)
    min_participants = Column(Integer, default=4, nullable=True)
    technical_operator = Column(String(255), nullable=True)
    sales_liability = Column(Text, nullable=True)
    accommodation_type = Column(String(255), nullable=True)
    room_type = Column(String(128), nullable=True)
    single_supplement_cents = Column(Integer, default=0, nullable=False)
    meals_included = Column(Text, nullable=True)
    transfers_info = Column(Text, nullable=True)
    weather_conditions = Column(Text, nullable=True)
    physical_level = Column(String(64), nullable=True)
    day_by_day_itinerary = Column(Text, nullable=True)  # JSON-encoded array of days
    legal_notes = Column(Text, nullable=True)

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
            "experienceType": self.experience_type or "workshop",
            "templateVersion": self.template_version or "workshop-v1",
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
            "country": self.country,
            "destination": self.destination,
            "arrivalAirport": self.arrival_airport,
            "currency": self.currency,
            "flightsIncluded": bool(self.flights_included),
            "baggageInfo": self.baggage_info,
            "documentsRequired": self.documents_required,
            "passportOrId": self.passport_or_id,
            "visaRequired": bool(self.visa_required),
            "insuranceInfo": self.insurance_info,
            "minParticipants": self.min_participants,
            "technicalOperator": self.technical_operator,
            "salesLiability": self.sales_liability,
            "accommodationType": self.accommodation_type,
            "roomType": self.room_type,
            "singleSupplementCents": self.single_supplement_cents,
            "mealsIncluded": self.meals_included,
            "transfersInfo": self.transfers_info,
            "weatherConditions": self.weather_conditions,
            "physicalLevel": self.physical_level,
            "dayByDayItinerary": self.day_by_day_itinerary,
            "legalNotes": self.legal_notes,
            "location": self.location,
            "duration": self.duration,
            "description": self.description,
            "image": self.image,
            "detailsUrl": self.details_url,
        }
