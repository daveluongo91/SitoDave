"""
backend/app/services/coupon_service.py
Validazione e calcolo coupon con Decimal. Mai floating point.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.models.coupon import Coupon, COUPON_TYPE_PERCENTAGE, COUPON_TYPE_FINAL_PRICE
from backend.app.models.booking import Booking


class CouponError(ValueError):
    pass


# Arrotondamento monetario italiano (centesimi)
CENT = Decimal("0.01")


def _decimal(value: str | int | float) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise CouponError("Valore non valido nel coupon.")


def validate_coupon(
    db: Session,
    code: str,
    workshop_id: str,
    email: str,
    original_price_cents: int,
) -> Tuple[Coupon, Decimal, Decimal]:
    """
    Valida un coupon e calcola sconto e prezzo finale.
    Restituisce: (coupon, discount_decimal, final_decimal) — in EURO, non centesimi.
    Lancia CouponError se non valido.
    """
    code_upper = code.strip().upper()
    coupon: Optional[Coupon] = (
        db.query(Coupon)
        .filter(Coupon.code == code_upper, Coupon.status == "active")
        .first()
    )

    if coupon is None:
        raise CouponError("Codice sconto non valido o non attivo.")

    today = datetime.now(timezone.utc).date().isoformat()

    if coupon.end_date and coupon.end_date < today:
        raise CouponError("Il codice sconto è scaduto.")

    if coupon.start_date and coupon.start_date > today:
        raise CouponError("Il codice sconto non è ancora attivo.")

    if coupon.max_uses_total is not None and coupon.used_count >= coupon.max_uses_total:
        raise CouponError("Questo codice ha raggiunto il limite massimo di utilizzi.")

    # Verifica applicabilità workshop
    try:
        applicable = json.loads(coupon.applicable_workshops or '["all"]')
    except json.JSONDecodeError:
        applicable = ["all"]

    if "all" not in applicable and workshop_id not in applicable:
        raise CouponError("Il codice sconto non è applicabile a questo workshop.")

    # Verifica per email
    if coupon.max_uses_per_email:
        uses_by_email = (
            db.query(Booking)
            .filter(
                Booking.coupon_code == code_upper,
                Booking.email == email.lower(),
                Booking.status == "paid",
                Booking.is_deleted.is_(False),
            )
            .count()
        )
        if uses_by_email >= coupon.max_uses_per_email:
            raise CouponError("Hai già utilizzato questo codice con questo indirizzo email.")

    # Calcolo con Decimal
    original = _decimal(original_price_cents) / Decimal("100")  # € decimali

    if coupon.type == COUPON_TYPE_PERCENTAGE:
        pct = coupon.value
        if pct <= Decimal("0") or pct > Decimal("100"):
            raise CouponError("Percentuale di sconto non valida nel coupon.")
        discount = (original * pct / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
        final = (original - discount).quantize(CENT, rounding=ROUND_HALF_UP)

    elif coupon.type == COUPON_TYPE_FINAL_PRICE:
        final = coupon.value.quantize(CENT, rounding=ROUND_HALF_UP)
        if final < Decimal("0"):
            raise CouponError("Prezzo finale del coupon non valido.")
        if final > original:
            # Il prezzo finale è maggiore dell'originale → nessuno sconto
            final = original
        discount = (original - final).quantize(CENT, rounding=ROUND_HALF_UP)

    else:
        raise CouponError("Tipo di coupon non riconosciuto.")

    return coupon, discount, final


def consume_coupon(db: Session, coupon_code: str) -> None:
    """Incrementa il contatore utilizzi. Chiamato solo dopo pagamento confermato."""
    code_upper = coupon_code.strip().upper()
    coupon = db.query(Coupon).filter(Coupon.code == code_upper).first()
    if coupon:
        coupon.used_count = (coupon.used_count or 0) + 1
        db.commit()
