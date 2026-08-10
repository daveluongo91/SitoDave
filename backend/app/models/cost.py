"""backend/app/models/cost.py — Costi workshop con Decimal e link ViaMichelin."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base


class WorkshopCost(Base):
    __tablename__ = "workshop_costs"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(String(64), ForeignKey("workshops.workshop_key"), nullable=False, unique=True)

    # Pernottamento
    nights = Column(Integer, default=0, nullable=False)
    cost_per_night_decimal = Column(String(16), default="0", nullable=False)   # Decimal string
    room_count = Column(Integer, default=1, nullable=False)
    total_accommodation_decimal = Column(String(16), nullable=True)            # calcolato

    # Itinerario
    departure_address = Column(String(512), nullable=True)
    destination = Column(String(512), nullable=True)
    waypoints = Column(Text, nullable=True)                   # JSON array
    vehicle_type = Column(String(64), nullable=True)

    # Costi viaggio (Decimal strings)
    fuel_decimal = Column(String(16), default="0", nullable=False)
    tolls_decimal = Column(String(16), default="0", nullable=False)
    parking_decimal = Column(String(16), default="0", nullable=False)
    ferries_decimal = Column(String(16), default="0", nullable=False)
    other_travel_decimal = Column(String(16), default="0", nullable=False)
    other_org_decimal = Column(String(16), default="0", nullable=False)

    # Note e fonte
    travel_notes = Column(Text, nullable=True)
    verified_at = Column(String(32), nullable=True)          # data verifica stima
    estimate_source = Column(String(255), nullable=True)     # ViaMichelin / altro
    viamichelin_url = Column(Text, nullable=True)            # URL itinerario salvato

    # Totali calcolati (Decimal strings)
    total_travel_decimal = Column(String(16), nullable=True)
    total_costs_decimal = Column(String(16), nullable=True)
    cost_per_participant_decimal = Column(String(16), nullable=True)
    estimated_margin_decimal = Column(String(16), nullable=True)

    created_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "workshopId": self.workshop_id,
            "nights": self.nights,
            "costPerNight": self.cost_per_night_decimal,
            "roomCount": self.room_count,
            "totalAccommodation": self.total_accommodation_decimal,
            "departureAddress": self.departure_address,
            "destination": self.destination,
            "waypoints": self.waypoints,
            "vehicleType": self.vehicle_type,
            "fuel": self.fuel_decimal,
            "tolls": self.tolls_decimal,
            "parking": self.parking_decimal,
            "ferries": self.ferries_decimal,
            "otherTravel": self.other_travel_decimal,
            "otherOrg": self.other_org_decimal,
            "travelNotes": self.travel_notes,
            "verifiedAt": self.verified_at,
            "estimateSource": self.estimate_source,
            "viamichelinUrl": self.viamichelin_url,
            "totalTravel": self.total_travel_decimal,
            "totalCosts": self.total_costs_decimal,
            "costPerParticipant": self.cost_per_participant_decimal,
            "estimatedMargin": self.estimated_margin_decimal,
            "updatedAt": self.updated_at,
        }
