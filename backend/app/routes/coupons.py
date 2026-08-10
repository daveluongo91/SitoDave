"""
backend/app/routes/coupons.py
CRUD coupon admin — solo admin autenticati.
Calcoli sempre con Decimal, validazione rigorosa tipo.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.coupon import Coupon, COUPON_TYPE_PERCENTAGE, COUPON_TYPE_FINAL_PRICE
from backend.app.models.user import User

router = APIRouter(prefix="/api/admin/coupons", tags=["admin-coupons"])

VALID_TYPES = {COUPON_TYPE_PERCENTAGE, COUPON_TYPE_FINAL_PRICE}


class CouponCreate(BaseModel):
    code: str
    description: Optional[str] = None
    type: str
    valueDecimal: str           # Decimal string: es. "10" (10%) o "300.00" (€300)
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    applicableWorkshops: Optional[list[str]] = None  # None = ["all"]
    maxUsesTotal: Optional[int] = None
    maxUsesPerEmail: Optional[int] = None

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Il codice non può essere vuoto.")
        # Solo caratteri alfanumerici e trattini
        import re
        if not re.match(r"^[A-Z0-9\-_]+$", v.strip().upper()):
            raise ValueError("Il codice può contenere solo lettere, numeri, trattini e underscore.")
        return v.strip().upper()

    @field_validator("type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in VALID_TYPES:
            raise ValueError(f"Tipo non valido. Ammessi: {', '.join(VALID_TYPES)}")
        return v

    @field_validator("valueDecimal")
    @classmethod
    def valid_decimal(cls, v: str) -> str:
        try:
            d = Decimal(v)
        except InvalidOperation:
            raise ValueError("Valore non è un numero decimale valido.")
        if d < Decimal("0"):
            raise ValueError("Il valore non può essere negativo.")
        return str(d)

    @model_validator(mode="after")
    def validate_type_constraints(self) -> "CouponCreate":
        value = Decimal(self.valueDecimal)
        if self.type == COUPON_TYPE_PERCENTAGE:
            if value <= Decimal("0") or value > Decimal("100"):
                raise ValueError("La percentuale deve essere tra 0 (escluso) e 100.")
        elif self.type == COUPON_TYPE_FINAL_PRICE:
            if value < Decimal("0"):
                raise ValueError("Il prezzo finale non può essere negativo.")
        return self


@router.get("/")
async def list_coupons(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return {"coupons": [c.to_dict(include_sensitive=True) for c in coupons]}


@router.post("/", dependencies=[Depends(verify_csrf)])
async def create_coupon(
    request: Request,
    body: CouponCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(Coupon).filter(Coupon.code == body.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Codice già esistente.")

    workshops_json = json.dumps(body.applicableWorkshops or ["all"])

    coupon = Coupon(
        code=body.code,
        description=body.description,
        type=body.type,
        value_decimal=body.valueDecimal,
        start_date=body.startDate,
        end_date=body.endDate,
        applicable_workshops=workshops_json,
        max_uses_total=body.maxUsesTotal,
        max_uses_per_email=body.maxUsesPerEmail,
        created_by=current_user.id,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    log_action(db, "coupon_create", user_id=current_user.id,
               resource_type="coupon", resource_id=body.code,
               ip=request.client.host if request.client else None)

    return coupon.to_dict(include_sensitive=True)


@router.put("/{coupon_id}", dependencies=[Depends(verify_csrf)])
async def update_coupon(
    request: Request,
    coupon_id: int,
    body: CouponCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon non trovato.")

    coupon.description = body.description
    coupon.type = body.type
    coupon.value_decimal = body.valueDecimal
    coupon.start_date = body.startDate
    coupon.end_date = body.endDate
    coupon.applicable_workshops = json.dumps(body.applicableWorkshops or ["all"])
    coupon.max_uses_total = body.maxUsesTotal
    coupon.max_uses_per_email = body.maxUsesPerEmail
    coupon.updated_at = datetime.now(timezone.utc).isoformat()
    coupon.updated_by = current_user.id
    db.commit()

    log_action(db, "coupon_update", user_id=current_user.id,
               resource_type="coupon", resource_id=str(coupon_id),
               ip=request.client.host if request.client else None)

    return coupon.to_dict(include_sensitive=True)


class CouponStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in {"active", "inactive"}:
            raise ValueError("Stato non valido. Ammessi: active, inactive")
        return v


@router.put("/{coupon_id}/status", dependencies=[Depends(verify_csrf)])
async def toggle_coupon_status(
    request: Request,
    coupon_id: int,
    body: CouponStatusUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon non trovato.")
    coupon.status = body.status
    coupon.updated_at = datetime.now(timezone.utc).isoformat()
    coupon.updated_by = current_user.id
    db.commit()
    return {"status": "ok", "couponStatus": coupon.status}


@router.delete("/{coupon_id}", dependencies=[Depends(verify_csrf)])
async def delete_coupon(
    request: Request,
    coupon_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon non trovato.")
    # Verifica che non sia in uso (prenotazioni paid)
    from backend.app.models.booking import Booking
    in_use = db.query(Booking).filter(
        Booking.coupon_code == coupon.code,
        Booking.status == "paid",
        Booking.is_deleted.is_(False),
    ).count()
    if in_use > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Il coupon è già stato utilizzato in {in_use} prenotazioni confermate. Disattivalo invece di eliminarlo."
        )
    db.delete(coupon)
    db.commit()
    log_action(db, "coupon_delete", user_id=current_user.id,
               resource_type="coupon", resource_id=str(coupon_id),
               ip=request.client.host if request.client else None)
    return {"status": "ok"}
