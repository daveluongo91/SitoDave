"""
backend/app/routes/workshops.py
CRUD workshop — solo admin autenticati.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.user import User
from backend.app.models.workshop import Workshop
from backend.app.services.availability_alert_service import notify_availability_threshold

router = APIRouter(prefix="/api/admin/workshops", tags=["admin-workshops"])


class WorkshopCreate(BaseModel):
    workshopKey: str
    slug: str
    title: str
    category: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    totalSeats: int = 8
    availableSeats: int = 8
    priceCents: int
    priceLabel: Optional[str] = None
    status: str = "draft"
    cutoffAt: Optional[str] = None
    operativeNotes: Optional[str] = None
    location: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    detailsUrl: Optional[str] = None

    @field_validator("priceCents")
    @classmethod
    def price_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Il prezzo non può essere negativo.")
        return v

    @field_validator("totalSeats", "availableSeats")
    @classmethod
    def seats_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("I posti non possono essere negativi.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        allowed = {"active", "soldout", "cancelled", "draft", "completed"}
        if v not in allowed:
            raise ValueError(f"Stato non valido. Ammessi: {', '.join(allowed)}")
        return v


@router.get("/")
async def list_workshops(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    workshops = db.query(Workshop).order_by(Workshop.start_date).all()
    return {"workshops": [w.to_dict() for w in workshops]}


@router.get("/{workshop_id}")
async def get_workshop(
    workshop_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    ws = db.query(Workshop).filter(Workshop.workshop_key == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop non trovato.")
    return ws.to_dict()


@router.post("/", dependencies=[Depends(verify_csrf)])
async def create_workshop(
    request: Request,
    body: WorkshopCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(Workshop).filter(Workshop.workshop_key == body.workshopKey).first()
    if existing:
        raise HTTPException(status_code=409, detail="Workshop key già esistente.")

    ws = Workshop(
        workshop_key=body.workshopKey,
        slug=body.slug,
        title=body.title,
        category=body.category,
        start_date=body.startDate,
        end_date=body.endDate,
        total_seats=body.totalSeats,
        available_seats=body.availableSeats,
        price_cents=body.priceCents,
        price_label=body.priceLabel,
        status=body.status,
        cutoff_at=body.cutoffAt,
        operative_notes=body.operativeNotes,
        location=body.location,
        duration=body.duration,
        description=body.description,
        image=body.image,
        details_url=body.detailsUrl,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    log_action(db, "workshop_create", user_id=current_user.id,
               resource_type="workshop", resource_id=body.workshopKey,
               ip=request.client.host if request.client else None)

    return ws.to_dict()


@router.put("/{workshop_id}", dependencies=[Depends(verify_csrf)])
async def update_workshop(
    request: Request,
    workshop_id: str,
    body: WorkshopCreate,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    ws = db.query(Workshop).filter(Workshop.workshop_key == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop non trovato.")

    ws.title = body.title
    ws.category = body.category
    ws.start_date = body.startDate
    ws.end_date = body.endDate
    ws.total_seats = body.totalSeats
    ws.available_seats = body.availableSeats
    ws.price_cents = body.priceCents
    ws.price_label = body.priceLabel
    ws.status = body.status
    ws.cutoff_at = body.cutoffAt
    ws.operative_notes = body.operativeNotes
    ws.location = body.location
    ws.duration = body.duration
    ws.description = body.description
    ws.image = body.image
    ws.details_url = body.detailsUrl
    ws.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    notify_availability_threshold(db, ws)

    log_action(db, "workshop_update", user_id=current_user.id,
               resource_type="workshop", resource_id=workshop_id,
               ip=request.client.host if request.client else None)

    return ws.to_dict()
