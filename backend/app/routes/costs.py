"""
backend/app/routes/costs.py
Gestione costi workshop con calcoli Decimal e link ViaMichelin.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.cost import WorkshopCost
from backend.app.models.workshop import Workshop
from backend.app.models.booking import Booking
from backend.app.models.user import User
from backend.app.services.cost_service import update_cost_totals

router = APIRouter(prefix="/api/admin/costs", tags=["admin-costs"])


class CostUpdate(BaseModel):
    nights: int = 0
    costPerNight: str = "0"          # Decimal string
    roomCount: int = 1
    departureAddress: Optional[str] = None
    destination: Optional[str] = None
    waypoints: Optional[list[str]] = None
    vehicleType: Optional[str] = None
    fuel: str = "0"
    tolls: str = "0"
    parking: str = "0"
    ferries: str = "0"
    otherTravel: str = "0"
    otherOrg: str = "0"
    travelNotes: Optional[str] = None
    verifiedAt: Optional[str] = None
    estimateSource: Optional[str] = None
    viamichelinUrl: Optional[str] = None

    @field_validator("nights", "roomCount")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Il valore non può essere negativo.")
        return v

    @field_validator("costPerNight", "fuel", "tolls", "parking", "ferries", "otherTravel", "otherOrg")
    @classmethod
    def valid_decimal(cls, v: str) -> str:
        try:
            d = Decimal(v)
            if d < Decimal("0"):
                raise ValueError()
        except Exception:
            raise ValueError(f"Valore non valido: '{v}'. Usa un numero decimale non negativo.")
        return str(d)

    @field_validator("viamichelinUrl")
    @classmethod
    def safe_url(cls, v: Optional[str]) -> Optional[str]:
        """Verifica che l'URL sia ViaMichelin o None."""
        if v is None:
            return None
        if not v.startswith("https://www.viamichelin.it/"):
            raise ValueError("URL non valido. Usa un link di ViaMichelin.")
        return v[:2048]


@router.get("/{workshop_id}")
async def get_costs(
    workshop_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    cost = db.query(WorkshopCost).filter(WorkshopCost.workshop_id == workshop_id).first()
    if not cost:
        # Restituisce record vuoto se non esiste ancora
        return {
            "workshopId": workshop_id,
            "nights": 0,
            "costPerNight": "0",
            "roomCount": 1,
            "fuel": "0",
            "tolls": "0",
            "parking": "0",
            "ferries": "0",
            "otherTravel": "0",
            "otherOrg": "0",
        }
    return cost.to_dict()


@router.put("/{workshop_id}", dependencies=[Depends(verify_csrf)])
async def update_costs(
    request: Request,
    workshop_id: str,
    body: CostUpdate,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    # Verifica che il workshop esista
    ws = db.query(Workshop).filter(Workshop.workshop_key == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop non trovato.")

    cost = db.query(WorkshopCost).filter(WorkshopCost.workshop_id == workshop_id).first()
    if not cost:
        cost = WorkshopCost(workshop_id=workshop_id)
        db.add(cost)

    import json
    cost.nights = body.nights
    cost.cost_per_night_decimal = body.costPerNight
    cost.room_count = body.roomCount
    cost.departure_address = body.departureAddress
    cost.destination = body.destination
    cost.waypoints = json.dumps(body.waypoints) if body.waypoints else None
    cost.vehicle_type = body.vehicleType
    cost.fuel_decimal = body.fuel
    cost.tolls_decimal = body.tolls
    cost.parking_decimal = body.parking
    cost.ferries_decimal = body.ferries
    cost.other_travel_decimal = body.otherTravel
    cost.other_org_decimal = body.otherOrg
    cost.travel_notes = body.travelNotes
    cost.verified_at = body.verifiedAt
    cost.estimate_source = body.estimateSource
    cost.viamichelin_url = body.viamichelinUrl
    cost.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    # Conta partecipanti paganti per calcolo costo per persona
    participant_count = db.query(Booking).filter(
        Booking.workshop_id == workshop_id,
        Booking.status == "paid",
        Booking.is_deleted.is_(False),
    ).count()

    # Calcola ricavi previsti (priceCents × partecipanti)
    revenue_cents = ws.price_cents * participant_count

    cost = update_cost_totals(db, cost, participant_count, revenue_cents)

    log_action(db, "costs_update", user_id=current_user.id,
               resource_type="cost", resource_id=workshop_id,
               ip=request.client.host if request.client else None)

    return cost.to_dict()
