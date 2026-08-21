"""
backend/app/routes/experiences.py
Router amministrativo per la gestione unificata di Workshop e Viaggi Internazionali.
Include template versionati, validazione pre-pubblicazione, anteprima e generazione locale.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.workshop import Workshop
from backend.app.models.user import User
from backend.app.services.template_service import (
    TEMPLATES,
    validate_experience_for_publication,
    render_deterministic_page_html,
)

router = APIRouter(prefix="/api/admin/experiences", tags=["admin-experiences"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ExperiencePayload(BaseModel):
    title: str
    slug: str
    experienceType: str = "workshop"  # workshop | international_trip
    templateVersion: Optional[str] = "workshop-v1"
    category: Optional[str] = "nazionale"
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    timezone: Optional[str] = "Europe/Rome"
    totalSeats: int = 8
    availableSeats: Optional[int] = None
    priceCents: int = 0
    priceLabel: Optional[str] = None
    status: str = "draft"  # draft | active | soldout | completed | cancelled

    # Viaggi & Logistica
    country: Optional[str] = None
    destination: Optional[str] = None
    arrivalAirport: Optional[str] = None
    currency: Optional[str] = "EUR"
    flightsIncluded: bool = False
    baggageInfo: Optional[str] = None
    documentsRequired: Optional[str] = None
    passportOrId: Optional[str] = None
    visaRequired: bool = False
    insuranceInfo: Optional[str] = None
    minParticipants: Optional[int] = 4
    technicalOperator: Optional[str] = None
    salesLiability: Optional[str] = None
    accommodationType: Optional[str] = None
    roomType: Optional[str] = None
    singleSupplementCents: Optional[int] = 0
    mealsIncluded: Optional[str] = None
    transfersInfo: Optional[str] = None
    weatherConditions: Optional[str] = None
    physicalLevel: Optional[str] = None
    dayByDayItinerary: Optional[str] = None  # JSON string
    legalNotes: Optional[str] = None

    # Meta
    location: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    detailsUrl: Optional[str] = None
    operativeNotes: Optional[str] = None

    blocks: Optional[List[Dict[str, Any]]] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(current_user: User = Depends(get_admin_user)):
    """Restituisce l'elenco dei template dichiarativi disponibili."""
    return {"templates": list(TEMPLATES.values())}


@router.get("/")
async def list_experiences(
    experienceType: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Lista esperienze (workshop e viaggi internazionali)."""
    query = db.query(Workshop)

    if experienceType:
        query = query.filter(Workshop.experience_type == experienceType)
    if status:
        query = query.filter(Workshop.status == status)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(Workshop.title.ilike(s) | Workshop.location.ilike(s) | Workshop.destination.ilike(s))

    experiences = query.order_by(Workshop.start_date.desc().nullslast()).all()
    return {"experiences": [e.to_dict() for e in experiences]}


@router.get("/{id_or_key}")
async def get_experience(
    id_or_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Recupera il dettaglio di un workshop o viaggio."""
    if id_or_key.isdigit():
        exp = db.query(Workshop).filter(Workshop.id == int(id_or_key)).first()
    else:
        exp = db.query(Workshop).filter(Workshop.workshop_key == id_or_key).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Esperienza non trovata.")
    return exp.to_dict()


@router.post("/", dependencies=[Depends(verify_csrf)])
async def create_experience(
    request: Request,
    body: ExperiencePayload,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Crea una nuova esperienza in bozza o attiva."""
    slug_clean = body.slug.strip().lower()
    existing = db.query(Workshop).filter(Workshop.slug == slug_clean).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Lo slug '{slug_clean}' è già utilizzato.")

    ws_key = slug_clean
    existing_key = db.query(Workshop).filter(Workshop.workshop_key == ws_key).first()
    if existing_key:
        ws_key = f"{slug_clean}-{int(datetime.now(timezone.utc).timestamp())}"

    now = datetime.now(timezone.utc).isoformat()
    avail_seats = body.availableSeats if body.availableSeats is not None else body.totalSeats

    exp = Workshop(
        workshop_key=ws_key,
        slug=slug_clean,
        title=body.title.strip(),
        experience_type=body.experienceType,
        template_version=body.templateVersion or ("international-trip-v1" if body.experienceType == "international_trip" else "workshop-v1"),
        category=body.category or ("internazionale" if body.experienceType == "international_trip" else "nazionale"),
        start_date=body.startDate,
        end_date=body.endDate,
        timezone=body.timezone or "Europe/Rome",
        total_seats=body.totalSeats,
        available_seats=avail_seats,
        price_cents=body.priceCents,
        price_label=body.priceLabel or f"€{body.priceCents // 100}",
        status=body.status,
        country=body.country,
        destination=body.destination,
        arrival_airport=body.arrivalAirport,
        currency=body.currency or "EUR",
        flights_included=body.flightsIncluded,
        baggage_info=body.baggageInfo,
        documents_required=body.documentsRequired,
        passport_or_id=body.passportOrId,
        visa_required=body.visaRequired,
        insurance_info=body.insuranceInfo,
        min_participants=body.minParticipants,
        technical_operator=body.technicalOperator,
        sales_liability=body.salesLiability,
        accommodation_type=body.accommodationType,
        room_type=body.roomType,
        single_supplement_cents=body.singleSupplementCents or 0,
        meals_included=body.mealsIncluded,
        transfers_info=body.transfersInfo,
        weather_conditions=body.weatherConditions,
        physical_level=body.physicalLevel,
        day_by_day_itinerary=body.dayByDayItinerary,
        legal_notes=body.legalNotes,
        location=body.location or body.destination,
        duration=body.duration,
        description=body.description,
        image=body.image,
        details_url=body.detailsUrl or f"/workshops_2026/{slug_clean}.html",
        operative_notes=body.operativeNotes,
        created_at=now,
        updated_at=now,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    log_action(db, "experience_create", user_id=current_user.id, resource_type="workshop", resource_id=exp.workshop_key, ip=request.client.host if request.client else None)
    return exp.to_dict()


@router.put("/{id_or_key}", dependencies=[Depends(verify_csrf)])
async def update_experience(
    request: Request,
    id_or_key: str,
    body: ExperiencePayload,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Aggiorna i campi di un'esperienza esistente."""
    if id_or_key.isdigit():
        exp = db.query(Workshop).filter(Workshop.id == int(id_or_key)).first()
    else:
        exp = db.query(Workshop).filter(Workshop.workshop_key == id_or_key).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Esperienza non trovata.")

    slug_clean = body.slug.strip().lower()
    if slug_clean != exp.slug:
        existing = db.query(Workshop).filter(Workshop.slug == slug_clean, Workshop.id != exp.id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Lo slug '{slug_clean}' è già utilizzato.")
        exp.slug = slug_clean

    now = datetime.now(timezone.utc).isoformat()
    exp.title = body.title.strip()
    exp.experience_type = body.experienceType
    exp.template_version = body.templateVersion or exp.template_version
    exp.category = body.category or exp.category
    exp.start_date = body.startDate
    exp.end_date = body.endDate
    exp.timezone = body.timezone or exp.timezone
    exp.total_seats = body.totalSeats
    if body.availableSeats is not None:
        exp.available_seats = body.availableSeats
    exp.price_cents = body.priceCents
    exp.price_label = body.priceLabel or f"€{body.priceCents // 100}"
    exp.status = body.status

    exp.country = body.country
    exp.destination = body.destination
    exp.arrival_airport = body.arrivalAirport
    exp.currency = body.currency or "EUR"
    exp.flights_included = body.flightsIncluded
    exp.baggage_info = body.baggageInfo
    exp.documents_required = body.documentsRequired
    exp.passport_or_id = body.passportOrId
    exp.visa_required = body.visaRequired
    exp.insurance_info = body.insuranceInfo
    exp.min_participants = body.minParticipants
    exp.technical_operator = body.technicalOperator
    exp.sales_liability = body.salesLiability
    exp.accommodation_type = body.accommodationType
    exp.room_type = body.roomType
    exp.single_supplement_cents = body.singleSupplementCents or 0
    exp.meals_included = body.mealsIncluded
    exp.transfers_info = body.transfersInfo
    exp.weather_conditions = body.weatherConditions
    exp.physical_level = body.physicalLevel
    exp.day_by_day_itinerary = body.dayByDayItinerary
    exp.legal_notes = body.legalNotes

    exp.location = body.location or body.destination or exp.location
    exp.duration = body.duration
    exp.description = body.description
    exp.image = body.image
    exp.details_url = body.detailsUrl or exp.details_url
    exp.operative_notes = body.operativeNotes
    exp.updated_at = now

    db.commit()
    db.refresh(exp)

    log_action(db, "experience_update", user_id=current_user.id, resource_type="workshop", resource_id=exp.workshop_key, ip=request.client.host if request.client else None)
    return exp.to_dict()


@router.post("/{id_or_key}/validate", dependencies=[Depends(verify_csrf)])
async def validate_experience(
    id_or_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Esegue controlli di completezza e sicurezza pre-pubblicazione."""
    if id_or_key.isdigit():
        exp = db.query(Workshop).filter(Workshop.id == int(id_or_key)).first()
    else:
        exp = db.query(Workshop).filter(Workshop.workshop_key == id_or_key).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Esperienza non trovata.")

    existing_slugs = [w.slug for w in db.query(Workshop.slug).filter(Workshop.id != exp.id).all()]
    is_valid, errors, warnings = validate_experience_for_publication(
        data=exp.to_dict(),
        existing_slugs=existing_slugs,
        current_id=exp.id,
    )

    return {
        "isValid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "experience": exp.to_dict(),
    }


@router.post("/{id_or_key}/publish", dependencies=[Depends(verify_csrf)])
async def publish_experience(
    request: Request,
    id_or_key: str,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Pubblica localmente l'esperienza verificando che tutti i controlli siano soddisfatti."""
    if id_or_key.isdigit():
        exp = db.query(Workshop).filter(Workshop.id == int(id_or_key)).first()
    else:
        exp = db.query(Workshop).filter(Workshop.workshop_key == id_or_key).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Esperienza non trovata.")

    existing_slugs = [w.slug for w in db.query(Workshop.slug).filter(Workshop.id != exp.id).all()]
    is_valid, errors, warnings = validate_experience_for_publication(
        data=exp.to_dict(),
        existing_slugs=existing_slugs,
        current_id=exp.id,
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Impossibile pubblicare: elementi obbligatori mancanti.", "errors": errors}
        )

    exp.status = "active"
    exp.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    log_action(db, "experience_publish_local", user_id=current_user.id, resource_type="workshop", resource_id=exp.workshop_key, ip=request.client.host if request.client else None)
    return {"status": "published", "experience": exp.to_dict(), "warnings": warnings}


@router.get("/{id_or_key}/preview", response_class=HTMLResponse)
async def preview_experience(
    id_or_key: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Genera e visualizza l'anteprima HTML deterministica dell'esperienza."""
    if id_or_key.isdigit():
        exp = db.query(Workshop).filter(Workshop.id == int(id_or_key)).first()
    else:
        exp = db.query(Workshop).filter(Workshop.workshop_key == id_or_key).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Esperienza non trovata.")

    html = render_deterministic_page_html(exp)
    return HTMLResponse(content=html)