"""
backend/app/routes/paypal.py
[ISOLATO — NON MODIFICARE senza autorizzazione esplicita]

Questo modulo contiene le route PayPal dal server.py originale.
Supporta Workshop fisici e Percorsi Formativi One to One.
NON considerare un pagamento confermato sulla base di dati inviati dal frontend.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone

import requests as _requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from backend.app.config.settings import settings
from backend.app.config.database import get_db, SessionLocal
from backend.app.models.booking import Booking
from backend.app.models.workshop import Workshop
from backend.app.models.coupon import Coupon
from backend.app.services.coupon_service import validate_coupon, consume_coupon, CouponError
from backend.app.services.email_service import send_booking_confirmation
from backend.app.services.availability_alert_service import notify_availability_threshold
from backend.app.middleware.rate_limit import check_rate_limit

router = APIRouter(prefix="/api", tags=["paypal-isolated"])

# ── PayPal Config [INVARIATO] ────────────────────────────────────────────────
_PAYPAL_ENV = settings.paypal_env.lower()
if _PAYPAL_ENV == "live":
    _PAYPAL_BASE = "https://api-m.paypal.com"
    _CLIENT_ID = settings.paypal_live_client_id
    _CLIENT_SECRET = settings.paypal_live_client_secret
else:
    _PAYPAL_BASE = "https://api-m.sandbox.paypal.com"
    _CLIENT_ID = settings.paypal_sandbox_client_id
    _CLIENT_SECRET = settings.paypal_sandbox_client_secret

_WEBHOOK_ID = settings.paypal_webhook_id
_token_cache: dict = {"token": None, "expires_at": 0}
_token_lock = threading.Lock()
DEPOSIT_CENTS = 5000  # €50.00 caparra fissa
FRIULI_WORKSHOP_ID = "friuli-2026"
EXTRA_DAY_CENTS = 10000  # €100.00 per venerdì 9 ottobre


def _get_token():
    with _token_lock:
        now = datetime.now(timezone.utc).timestamp()
        if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
            return _token_cache["token"]
        r = _requests.post(
            f"{_PAYPAL_BASE}/v1/oauth2/token",
            auth=(_CLIENT_ID, _CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        return _token_cache["token"]


def _paypal_request(method: str, path: str, body=None):
    token = _get_token()
    r = _requests.request(
        method,
        f"{_PAYPAL_BASE}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=20,
    )
    r.raise_for_status()
    return r.json() if r.text else {}


class CreateOrderRequest(BaseModel):
    workshopId: str
    formula: str = "caparra"
    hours: int = 1
    extraDay: bool = False
    couponCode: str = ""
    firstName: str
    lastName: str
    email: str
    phone: str = ""
    participants: int = 1

    @field_validator("formula")
    @classmethod
    def valid_formula(cls, value: str) -> str:
        if value not in {"caparra", "saldo", "one-to-one"}:
            raise ValueError("Formula di pagamento non valida.")
        return value

    @field_validator("hours")
    @classmethod
    def valid_hours(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("Le ore devono essere comprese tra 1 e 5.")
        return value

    @field_validator("participants")
    @classmethod
    def valid_participants(cls, value: int) -> int:
        if not 1 <= value <= 8:
            raise ValueError("Numero partecipanti non valido.")
        return value

    @field_validator("firstName", "lastName")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = re.sub(r"[\r\n\t]+", " ", value).strip()
        if not 2 <= len(value) <= 100:
            raise ValueError("Nome non valido.")
        return value


def calculate_one_to_one_price_cents(hours: int) -> tuple[int, int, int]:
    """Calcola (list_price_cents, discount_percent, final_price_cents) per One to One."""
    if not 1 <= hours <= 5:
        raise ValueError("Le ore devono essere comprese tra 1 e 5.")
    base_rate_cents = 8000  # 80.00 EUR / ora
    list_price_cents = base_rate_cents * hours
    discounts = {1: 0, 2: 10, 3: 20, 4: 30, 5: 40}
    discount_pct = discounts[hours]
    final_price_cents = list_price_cents * (100 - discount_pct) // 100
    return list_price_cents, discount_pct, final_price_cents


@router.post("/create-paypal-order")
async def create_paypal_order(
    body: CreateOrderRequest,
    request: Request,
    _rate: None = Depends(check_rate_limit),
):
    """[ISOLATO] Crea ordine PayPal server-side con validazione importi sicura."""
    db = SessionLocal()
    try:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", body.email):
            raise HTTPException(status_code=400, detail="Email non valida.")

        if body.workshopId == "one-to-one" or body.formula == "one-to-one":
            hours = body.hours or body.participants
            if not 1 <= hours <= 5:
                raise HTTPException(status_code=400, detail="Le ore devono essere comprese tra 1 e 5.")
            original_cents, discount_pct, final_cents = calculate_one_to_one_price_cents(hours)
            discount_cents = original_cents - final_cents
            amount_due_cents = final_cents
            amount_due_str = f"{amount_due_cents / 100:.2f}"
            ws_name = f"Corso One to One ({hours} {'ora' if hours == 1 else 'ore'})"
            extra_day_selected = False
            extra_day_cents = 0
            balance_cents = 0
            coupon_code = ""

            paypal_order = _paypal_request("POST", "/v2/checkout/orders", {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": "one-to-one",
                    "description": ws_name,
                    "amount": {"currency_code": "EUR", "value": amount_due_str},
                    "custom_id": f"one-to-one|hours={hours}|{body.email}",
                }],
                "application_context": {
                    "brand_name": "Davide Luongo Photography",
                    "locale": "it-IT",
                    "user_action": "PAY_NOW",
                    "return_url": f"{settings.site_public_url.rstrip('/')}/thank-you.html",
                    "cancel_url": f"{settings.site_public_url.rstrip('/')}/one-to-one/one-to-one.html",
                },
            })
        else:
            ws = db.query(Workshop).filter(Workshop.workshop_key == body.workshopId).first()
            if not ws or ws.status != "active":
                raise HTTPException(status_code=404, detail="Workshop non disponibile.")
            if ws.available_seats < body.participants:
                raise HTTPException(status_code=409, detail="Posti disponibili insufficienti.")
            extra_day_selected = bool(body.extraDay and body.workshopId == FRIULI_WORKSHOP_ID)
            extra_day_cents = EXTRA_DAY_CENTS if extra_day_selected else 0
            original_cents = ws.price_cents + extra_day_cents
            ws_name = ws.title

            discount_cents = 0
            coupon_code = body.couponCode.strip().upper()
            if coupon_code:
                try:
                    coupon, discount, final = validate_coupon(db, coupon_code, body.workshopId, body.email, original_cents)
                    discount_cents = int(discount * 100)
                except CouponError as e:
                    raise HTTPException(status_code=400, detail=str(e))

            final_cents = max(DEPOSIT_CENTS, original_cents - discount_cents)
            balance_cents = max(0, final_cents - DEPOSIT_CENTS)
            amount_due_cents = DEPOSIT_CENTS if body.formula == "caparra" else final_cents
            amount_due_str = f"{amount_due_cents / 100:.2f}"

            paypal_order = _paypal_request("POST", "/v2/checkout/orders", {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": body.workshopId,
                    "description": (
                        f"{ws_name} — {'Caparra' if body.formula == 'caparra' else 'Saldo Completo'}"
                        f"{' — con venerdì 9 ottobre' if extra_day_selected else ''}"
                    ),
                    "amount": {"currency_code": "EUR", "value": amount_due_str},
                    "custom_id": f"{body.formula}|{coupon_code}|{body.email}|extra_day={int(extra_day_selected)}",
                }],
                "application_context": {
                    "brand_name": "Davide Luongo Photography",
                    "locale": "it-IT",
                    "user_action": "PAY_NOW",
                    "return_url": f"{settings.site_public_url.rstrip('/')}/thank-you.html",
                    "cancel_url": f"{settings.site_public_url.rstrip('/')}/index.html",
                },
            })

        order_id = paypal_order["id"]
        approve_url = next(
            (link.get("href") for link in paypal_order.get("links", []) if link.get("rel") == "approve"),
            None,
        )
        if not approve_url:
            raise HTTPException(status_code=502, detail="PayPal non ha restituito il link di approvazione.")
        bk_id = f"BK-{uuid.uuid4().hex[:12].upper()}"

        booking = Booking(
            id=bk_id,
            status="pending",
            workshop_id=body.workshopId,
            workshop_name=ws_name,
            first_name=body.firstName,
            last_name=body.lastName,
            email=body.email.lower(),
            phone=body.phone,
            participants=body.hours if body.workshopId == "one-to-one" else body.participants,
            formula=body.formula,
            extra_day_selected=extra_day_selected,
            extra_day_cents=extra_day_cents,
            original_cents=original_cents,
            discount_cents=discount_cents,
            final_cents=final_cents,
            balance_cents=balance_cents,
            amount_due_cents=amount_due_cents,
            coupon_code=coupon_code or None,
            paypal_order_id=order_id,
            paypal_env=_PAYPAL_ENV,
        )
        db.add(booking)
        db.commit()

        return {
            "status": "success",
            "orderId": order_id,
            "approveUrl": approve_url,
            "bookingId": bk_id,
            "amountDue": amount_due_str,
            "finalPrice": f"{final_cents / 100:.2f}",
            "discountAmount": f"{discount_cents / 100:.2f}",
            "balanceDue": f"{balance_cents / 100:.2f}",
            "formula": body.formula,
            "extraDay": extra_day_selected,
            "extraDayAmount": f"{extra_day_cents / 100:.2f}",
        }
    finally:
        db.close()


@router.post("/capture-paypal-order")
async def capture_paypal_order(
    request: Request,
    _rate: None = Depends(check_rate_limit),
):
    """[ISOLATO] Cattura ordine PayPal dopo approvazione utente."""
    body = await request.json()
    order_id = body.get("orderId", "").strip()
    if not order_id:
        raise HTTPException(status_code=400, detail="orderId mancante.")

    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.paypal_order_id == order_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Prenotazione non trovata.")
        if booking.status == "paid":
            return {
                "status": "already_paid", "bookingId": booking.id,
                "formula": booking.formula, "amount": f"{booking.amount_due_cents / 100:.2f}",
                "extraDay": bool(booking.extra_day_selected),
            }

        capture = _paypal_request("POST", f"/v2/checkout/orders/{order_id}/capture")
        capture_data = capture.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [{}])[0]
        capture_id = capture_data.get("id")
        capture_status = capture_data.get("status", "")
        captured_amt = capture_data.get("amount", {}).get("value", "0.00")
        captured_currency = capture_data.get("amount", {}).get("currency_code", "")
        try:
            captured_cents = int(round(float(captured_amt) * 100))
        except (TypeError, ValueError):
            captured_cents = -1

        if captured_currency != "EUR" or captured_cents != booking.amount_due_cents:
            raise HTTPException(status_code=409, detail="Importo PayPal non coerente con la prenotazione.")

        booking.paypal_capture_id = capture_id
        booking.status = "paid" if capture_status == "COMPLETED" else "pending"
        db.commit()

        if capture_status == "COMPLETED":
            if booking.coupon_code:
                consume_coupon(db, booking.coupon_code)
            # Decrementa posti solo per workshop fisici
            if booking.workshop_id and booking.workshop_id != "one-to-one":
                ws = db.query(Workshop).filter(Workshop.workshop_key == booking.workshop_id).first()
                if ws and ws.available_seats > 0:
                    ws.available_seats = max(0, ws.available_seats - booking.participants)
                    if ws.available_seats == 0:
                        ws.status = "soldout"
            
            # Collega e sincronizza con CRM
            from backend.app.services.crm_service import link_booking_to_contact
            link_booking_to_contact(db, booking)
            db.commit()
            
            if booking.workshop_id and booking.workshop_id != "one-to-one":
                ws = db.query(Workshop).filter(Workshop.workshop_key == booking.workshop_id).first()
                if ws:
                    notify_availability_threshold(db, ws)
            send_booking_confirmation(booking.to_dict())

        return {
            "status": booking.status, "bookingId": booking.id, "captureId": capture_id,
            "formula": booking.formula, "amount": f"{booking.amount_due_cents / 100:.2f}",
            "extraDay": bool(booking.extra_day_selected),
        }
    finally:
        db.close()


@router.post("/paypal-webhook")
async def paypal_webhook(request: Request):
    """Accetta soltanto webhook la cui firma è verificata da PayPal."""
    if not _WEBHOOK_ID:
        raise HTTPException(status_code=503, detail="Webhook PayPal non configurato.")
    raw_body = await request.body()
    try:
        event = json.loads(raw_body)
        verification = _paypal_request("POST", "/v1/notifications/verify-webhook-signature", {
            "auth_algo": request.headers.get("paypal-auth-algo", ""),
            "cert_url": request.headers.get("paypal-cert-url", ""),
            "transmission_id": request.headers.get("paypal-transmission-id", ""),
            "transmission_sig": request.headers.get("paypal-transmission-sig", ""),
            "transmission_time": request.headers.get("paypal-transmission-time", ""),
            "webhook_id": _WEBHOOK_ID,
            "webhook_event": event,
        })
    except (ValueError, json.JSONDecodeError, _requests.RequestException):
        raise HTTPException(status_code=400, detail="Webhook PayPal non valido.")
    if verification.get("verification_status") != "SUCCESS":
        raise HTTPException(status_code=400, detail="Firma webhook PayPal non valida.")
    return {"status": "ok"}