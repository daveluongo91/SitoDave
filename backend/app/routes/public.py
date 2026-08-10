"""
backend/app/routes/public.py
API pubbliche read-only (senza autenticazione).
Servono il frontend: workshop, contenuti home, validazione coupon, info email.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.rate_limit import check_rate_limit
from backend.app.models.workshop import Workshop
from backend.app.models.coupon import Coupon
from backend.app.models.page import Page
from backend.app.models.block import Block
from backend.app.models.availability_subscriber import AvailabilitySubscriber
from backend.app.services.coupon_service import validate_coupon, CouponError
from backend.app.services.email_service import send_email
from backend.app.config.settings import settings
import json
import re
import secrets
from datetime import datetime, timezone

router = APIRouter(prefix="/api", tags=["public"])


# ── Workshop pubblici ─────────────────────────────────────────────────────────

@router.get("/workshops")
async def list_workshops(db: Session = Depends(get_db)):
    """Lista workshop attivi per il frontend pubblico."""
    workshops = (
        db.query(Workshop)
        .filter(Workshop.status.in_(["active", "soldout"]))
        .order_by(Workshop.start_date)
        .all()
    )
    return {
        "workshops": [
            {
                "id": w.workshop_key,
                "title": w.title,
                "category": w.category,
                "date": f"{w.start_date} - {w.end_date}" if w.end_date else w.start_date,
                "location": w.location,
                "description": w.description,
                "duration": w.duration,
                "price": w.price_label or f"€{w.price_cents // 100}",
                "priceCents": w.price_cents,
                "availableSeats": max(0, w.available_seats),
                # Urgency bias: mostra -20% posti per FOMO (mai meno di 1 se disponibile)
                "urgencySeats": max(1, w.available_seats - max(1, int(w.total_seats * 0.2))) if w.available_seats > 0 else 0,
                "totalSeats": w.total_seats,
                "status": w.status,
                "statusLabel": _status_label(w.status),
                "image": w.image,
                "detailsUrl": w.details_url,
            }
            for w in workshops
        ]
    }


def _status_label(status: str) -> str:
    return {
        "active": "Iscrizioni Aperte",
        "soldout": "Sold Out",
        "cancelled": "Annullato",
        "completed": "Concluso",
        "draft": "In Preparazione",
    }.get(status, status)


@router.get("/workshops/{workshop_id}/seats")
async def get_seats(workshop_id: str, db: Session = Depends(get_db)):
    """Disponibilità posti in tempo reale (solo numero, nessun dato sensibile)."""
    ws = db.query(Workshop).filter(Workshop.workshop_key == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop non trovato.")
    return {
        "availableSeats": max(0, ws.available_seats),
        "status": ws.status,
    }


# ── Contenuto home ────────────────────────────────────────────────────────────

@router.get("/content")
async def get_content(db: Session = Depends(get_db)):
    """
    Endpoint di compatibilità con il frontend esistente.
    Restituisce workshop + home data in formato equivalente al vecchio content.json.
    """
    workshops = (
        db.query(Workshop)
        .filter(Workshop.status.in_(["active", "soldout", "completed"]))
        .order_by(Workshop.start_date)
        .all()
    )

    home_page = db.query(Page).filter(Page.page_key == "home").first()
    home_blocks = []
    if home_page:
        blocks = (
            db.query(Block)
            .filter(Block.page_id == home_page.id, Block.is_visible.is_(True))
            .order_by(Block.order_index)
            .all()
        )
        home_blocks = [json.loads(b.content) for b in blocks]

    return {
        "workshops": [_ws_to_legacy(w) for w in workshops],
        "homeBlocks": home_blocks,
    }


def _ws_to_legacy(w: Workshop) -> dict:
    return {
        "id": w.workshop_key,
        "title": w.title,
        "category": w.category,
        "date": f"{w.start_date} - {w.end_date}" if w.end_date else (w.start_date or ""),
        "location": w.location,
        "description": w.description,
        "duration": w.duration,
        "price": w.price_label or f"€{w.price_cents // 100}",
        "priceCents": w.price_cents,
        "availableSeats": max(0, w.available_seats),
        "totalSeats": w.total_seats,
        "status": w.status,
        "statusLabel": _status_label(w.status),
        "image": w.image,
        "detailsUrl": w.details_url,
    }


# ── Validazione coupon (pubblica, rate-limited) ───────────────────────────────

class CouponValidateRequest(BaseModel):
    code: str
    workshopId: str
    email: str
    originalPriceCents: int

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Codice obbligatorio.")
        return v.strip().upper()

    @field_validator("email")
    @classmethod
    def email_basic_check(cls, v: str) -> str:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Email non valida.")
        return v.strip().lower()


@router.post("/validate-coupon")
async def validate_coupon_endpoint(
    body: CouponValidateRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    """
    Valida un coupon e restituisce l'anteprima del calcolo.
    Rate-limited. NON espone l'elenco coupon.
    """
    try:
        coupon, discount, final = validate_coupon(
            db,
            code=body.code,
            workshop_id=body.workshopId,
            email=body.email,
            original_price_cents=body.originalPriceCents,
        )
    except CouponError as e:
        raise HTTPException(status_code=400, detail=str(e))

    original = body.originalPriceCents / 100
    pct_label = f"{coupon.value_decimal}%" if coupon.type == "percentage" else f"→ €{final:.2f}"

    return {
        "status": "ok",
        "code": body.code,
        "type": coupon.type,
        "discountAmount": str(discount),
        "finalPrice": str(final),
        "message": f"✅ Codice {body.code} applicato! Sconto: {pct_label} (-€{discount:.2f})",
    }


# ── Richiesta informazioni ────────────────────────────────────────────────────

class InfoRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    subject: str = "Informazioni Workshop"
    message: str = ""

    @field_validator("name", "email")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Campo obbligatorio.")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_check(cls, v: str) -> str:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Email non valida.")
        return v.strip().lower()

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        # Limita lunghezza messaggio
        return v[:2000].strip()


@router.post("/send-info-email")
async def send_info_email(
    body: InfoRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    """Invia richiesta informazioni via email. Rate-limited."""
    email_body = (
        f"Nuova Richiesta Informazioni:\n\n"
        f"Nome: {body.name}\n"
        f"Telefono: {body.phone or 'Non specificato'}\n"
        f"Oggetto: {body.subject}\n\n"
        f"Messaggio:\n{body.message}"
    )
    success, msg = send_email(
        settings.aruba_smtp_user,
        f"✉️ Richiesta Info: {body.subject} ({body.name})",
        email_body,
    )
    return {"status": "ok" if success else "error", "message": msg}


# ── Avvisi ultimi posti ───────────────────────────────────────────────────────

class AvailabilityAlertRequest(BaseModel):
    workshopId: str
    name: str
    email: str
    consent: bool

    @field_validator("workshopId")
    @classmethod
    def workshop_id_check(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9-]{3,64}", value):
            raise ValueError("Workshop non valido.")
        return value

    @field_validator("name")
    @classmethod
    def name_check(cls, value: str) -> str:
        value = re.sub(r"[\r\n\t]+", " ", value).strip()
        if not 2 <= len(value) <= 120:
            raise ValueError("Inserisci un nome valido.")
        return value

    @field_validator("email")
    @classmethod
    def alert_email_check(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Email non valida.")
        return value

    @field_validator("consent")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Il consenso è obbligatorio per ricevere gli avvisi.")
        return value


@router.post("/availability-alerts/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_availability_alerts(
    body: AvailabilityAlertRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    workshop = db.query(Workshop).filter(Workshop.workshop_key == body.workshopId).first()
    if not workshop or workshop.status not in ("active", "soldout"):
        raise HTTPException(status_code=404, detail="Workshop non disponibile.")

    now = datetime.now(timezone.utc).isoformat()
    subscriber = (
        db.query(AvailabilitySubscriber)
        .filter(
            AvailabilitySubscriber.workshop_id == body.workshopId,
            AvailabilitySubscriber.email == body.email,
        )
        .first()
    )
    if subscriber:
        subscriber.name = body.name
        subscriber.active = True
        subscriber.consent_at = now
        subscriber.consent_source = "friuli-landing"
        subscriber.unsubscribed_at = None
    else:
        subscriber = AvailabilitySubscriber(
            workshop_id=body.workshopId,
            name=body.name,
            email=body.email,
            consent_at=now,
            consent_source="friuli-landing",
            unsubscribe_token=secrets.token_urlsafe(32),
            active=True,
        )
        db.add(subscriber)
    db.commit()

    return {
        "status": "ok",
        "message": "Iscrizione registrata. Riceverai al massimo due avvisi per questo workshop.",
    }


@router.get("/availability-alerts/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_availability_alerts(token: str, db: Session = Depends(get_db)):
    subscriber = (
        db.query(AvailabilitySubscriber)
        .filter(AvailabilitySubscriber.unsubscribe_token == token)
        .first()
    )
    if not subscriber:
        return HTMLResponse(
            "<main><h1>Link non valido</h1><p>L'iscrizione non è stata trovata.</p></main>",
            status_code=404,
        )

    subscriber.active = False
    subscriber.unsubscribed_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return HTMLResponse(
        "<main><h1>Disiscrizione completata</h1>"
        "<p>Non riceverai altri avvisi sulla disponibilità del Workshop Friuli 2026.</p></main>"
    )


# ── CSP Report ────────────────────────────────────────────────────────────────

@router.post("/csp-report")
async def csp_report(request: Request):
    """Riceve e logga violazioni CSP (per debug, non critico)."""
    try:
        body = await request.json()
        report = body.get("csp-report", {})
        # Log semplice — non loggare URL con dati utente
        print(f"[CSP] Violazione: {report.get('violated-directive')} | {report.get('blocked-uri', '')[:100]}")
    except Exception:
        pass
    return {}
