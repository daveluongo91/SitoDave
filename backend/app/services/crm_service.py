"""
backend/app/services/crm_service.py
Logica di business per il CRM: acquisizione automatica, deduplicazione,
gestione interazioni, blacklist, calcolo metriche commerciali.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from backend.app.models.contact import Contact
from backend.app.models.contact_interaction import ContactInteraction
from backend.app.models.booking import Booking
from backend.app.models.tag import Tag


def normalize_email(email: str) -> str:
    """Normalizza un indirizzo email (lowercase, stripped)."""
    return (email or "").strip().lower()


def normalize_phone(phone: Optional[str]) -> str:
    """Normalizza un numero di telefono preservando il prefisso internazionale."""
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    return cleaned


def get_or_create_contact_from_interaction(
    db: Session,
    email: str,
    first_name: str = "",
    last_name: str = "",
    phone: Optional[str] = None,
    source: str = "web",
    interaction_type: str = "info_request",
    interaction_subject: str = "",
    interaction_note: str = "",
    workshop_or_trip_key: Optional[str] = None,
    marketing_consent: bool = False,
    privacy_consent: bool = True,
    consent_source: Optional[str] = None,
) -> Tuple[Contact, ContactInteraction]:
    """
    Acquisisce o aggiorna un contatto in modo atomico, registrando l'interazione.
    Non sovrascrive dati esistenti con stringhe vuote.
    """
    norm_email = normalize_email(email)
    norm_phone = normalize_phone(phone)
    now = datetime.now(timezone.utc).isoformat()

    contact = None
    if norm_email:
        contact = db.query(Contact).filter(Contact.email == norm_email, Contact.is_deleted.is_(False)).first()
    if not contact and norm_phone and len(norm_phone) >= 6:
        contact = db.query(Contact).filter(Contact.phone == norm_phone, Contact.is_deleted.is_(False)).first()

    if contact:
        # Aggiorna campi mancanti
        if not contact.first_name and first_name:
            contact.first_name = first_name.strip()
        if not contact.last_name and last_name:
            contact.last_name = last_name.strip()
        if not contact.phone and norm_phone:
            contact.phone = norm_phone
        contact.last_source = source
        contact.last_contact_at = now
        contact.updated_at = now
        if marketing_consent:
            contact.marketing_email_consent = True
            contact.marketing_email_consent_at = now
    else:
        # Nuovo contatto
        contact = Contact(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=norm_email,
            phone=norm_phone,
            first_source=source,
            last_source=source,
            status="new_lead",
            priority="medium",
            created_at=now,
            updated_at=now,
            last_contact_at=now,
            privacy_consent=privacy_consent,
            privacy_consent_at=now if privacy_consent else None,
            marketing_email_consent=marketing_consent,
            marketing_email_consent_at=now if marketing_consent else None,
            consent_source=consent_source or source,
        )
        db.add(contact)
        db.flush()  # Ottiene contact.id

    # Registra interazione
    interaction = ContactInteraction(
        contact_id=contact.id,
        type=interaction_type,
        created_at=now,
        source=source,
        subject=interaction_subject[:255] if interaction_subject else "",
        note=interaction_note[:4000] if interaction_note else "",
        workshop_or_trip_key=workshop_or_trip_key,
    )
    db.add(interaction)
    db.commit()
    db.refresh(contact)
    db.refresh(interaction)

    return contact, interaction


def link_booking_to_contact(db: Session, booking: Booking) -> Contact:
    """Collega una prenotazione al contatto CRM e aggiorna lo stato commerciale e il totale speso."""
    norm_email = normalize_email(booking.email)
    norm_phone = normalize_phone(booking.phone)
    now = datetime.now(timezone.utc).isoformat()

    contact = None
    if norm_email:
        contact = db.query(Contact).filter(Contact.email == norm_email, Contact.is_deleted.is_(False)).first()
    if not contact and norm_phone:
        contact = db.query(Contact).filter(Contact.phone == norm_phone, Contact.is_deleted.is_(False)).first()

    if not contact:
        contact = Contact(
            first_name=booking.first_name,
            last_name=booking.last_name,
            email=norm_email,
            phone=norm_phone,
            first_source=f"booking_{booking.workshop_id or 'direct'}",
            last_source=f"booking_{booking.workshop_id or 'direct'}",
            status="customer",
            created_at=now,
            updated_at=now,
            last_contact_at=now,
            customer_since=now,
            privacy_consent=bool(booking.privacy_accepted),
            privacy_consent_at=now if booking.privacy_accepted else None,
        )
        db.add(contact)
    booking.contact_id = contact.id
    db.flush()

    # Conta quante prenotazioni pagate ha questo contatto
    paid_count = db.query(Booking).filter(
        Booking.contact_id == contact.id,
        Booking.status == "paid",
        Booking.is_deleted.is_(False)
    ).count()

    if paid_count >= 2:
        contact.status = "loyal_customer"
    elif paid_count >= 1:
        contact.status = "customer"
        if not contact.customer_since:
            contact.customer_since = now

    # Calcola il totale speso effettivo
    total_cents = db.query(
        func.coalesce(func.sum(Booking.final_cents), 0)
    ).filter(
        Booking.contact_id == contact.id,
        Booking.status == "paid",
        Booking.is_deleted.is_(False)
    ).scalar() or 0

    contact.total_spent_cents = int(total_cents)
    contact.updated_at = now

    # Aggiungi interazione di prenotazione
    interaction = ContactInteraction(
        contact_id=contact.id,
        type="booking",
        created_at=now,
        source="paypal_checkout",
        subject=f"Prenotazione {booking.id} ({booking.workshop_name or booking.workshop_id})",
        note=f"Formula: {booking.formula} • Importo versato: €{(booking.final_cents or 0)/100:.2f}",
        workshop_or_trip_key=booking.workshop_id,
    )
    db.add(interaction)
    db.commit()
    db.refresh(contact)
    return contact


def get_crm_dashboard_metrics(db: Session) -> dict:
    """Calcola metriche chiave per la dashboard commerciale."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    total_contacts = db.query(Contact).filter(Contact.is_deleted.is_(False)).count()
    new_leads = db.query(Contact).filter(Contact.status == "new_lead", Contact.is_deleted.is_(False)).count()
    to_contact = db.query(Contact).filter(Contact.status == "to_contact", Contact.is_deleted.is_(False)).count()
    customers = db.query(Contact).filter(Contact.status.in_(["customer", "loyal_customer"]), Contact.is_deleted.is_(False)).count()
    loyal_customers = db.query(Contact).filter(Contact.status == "loyal_customer", Contact.is_deleted.is_(False)).count()
    lost_leads = db.query(Contact).filter(Contact.status == "lost_lead", Contact.is_deleted.is_(False)).count()
    blacklisted = db.query(Contact).filter(Contact.is_blacklisted.is_(True), Contact.is_deleted.is_(False)).count()

    # Follow-up
    today_followups = db.query(Contact).filter(
        Contact.next_followup_at.like(f"{today_str}%"),
        Contact.is_deleted.is_(False)
    ).count()

    overdue_followups = db.query(Contact).filter(
        Contact.next_followup_at < today_str,
        Contact.next_followup_at.isnot(None),
        Contact.status.notin_(["customer", "loyal_customer", "lost_lead", "inactive"]),
        Contact.is_deleted.is_(False)
    ).count()

    # Tasso di conversione (Clienti / Totale Lead)
    conversion_rate = (customers / total_contacts * 100) if total_contacts > 0 else 0.0

    # Ricavi confermati per fonte (da Booking pagati)
    revenue_rows = db.query(
        Booking.workshop_id,
        func.coalesce(func.sum(Booking.final_cents), 0)
    ).filter(
        Booking.status == "paid",
        Booking.is_deleted.is_(False)
    ).group_by(Booking.workshop_id).all()

    revenue_by_source = [
        {
            "source": r[0] or "Diretto",
            "totalCents": int(r[1]),
            "totalFormatted": f"€{int(r[1])/100:.2f}"
        }
        for r in revenue_rows
    ]

    # Contatti per fonte
    source_counts = db.query(
        Contact.first_source,
        func.count(Contact.id)
    ).filter(Contact.is_deleted.is_(False)).group_by(Contact.first_source).all()

    contacts_by_source = [
        {"source": s[0] or "Diretto / Non specificato", "count": s[1]}
        for s in source_counts
    ]

    return {
        "totalContacts": total_contacts,
        "newLeads": new_leads,
        "toContact": to_contact,
        "customers": customers,
        "loyalCustomers": loyal_customers,
        "lostLeads": lost_leads,
        "blacklistedCount": blacklisted,
        "todayFollowups": today_followups,
        "overdueFollowups": overdue_followups,
        "conversionRatePct": round(conversion_rate, 1),
        "revenueBySource": revenue_by_source,
        "contactsBySource": contacts_by_source,
    }