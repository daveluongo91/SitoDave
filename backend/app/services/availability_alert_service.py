"""Invio idempotente degli avvisi quando restano due o un posto."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.models.availability_subscriber import AvailabilitySubscriber
from backend.app.models.workshop import Workshop
from backend.app.services.email_service import send_email


def notify_availability_threshold(db: Session, workshop: Workshop) -> int:
    """Invia una sola volta per iscritto alle soglie esatte 2 e 1."""
    seats = max(0, workshop.available_seats)
    if seats not in (1, 2) or not settings.aruba_smtp_pass:
        return 0

    notified_field = "notified_two_at" if seats == 2 else "notified_one_at"
    subscribers = (
        db.query(AvailabilitySubscriber)
        .filter(
            AvailabilitySubscriber.workshop_id == workshop.workshop_key,
            AvailabilitySubscriber.active.is_(True),
            getattr(AvailabilitySubscriber, notified_field).is_(None),
        )
        .all()
    )

    sent = 0
    now = datetime.now(timezone.utc).isoformat()
    landing_url = f"{settings.site_public_url.rstrip('/')}/Friuli_2026/"

    for subscriber in subscribers:
        unsubscribe_url = (
            f"{settings.site_public_url.rstrip('/')}/api/availability-alerts/unsubscribe"
            f"?token={subscriber.unsubscribe_token}"
        )
        seat_label = "1 solo posto" if seats == 1 else "soltanto 2 posti"
        body = (
            f"Ciao {subscriber.name},\n\n"
            f"per il workshop {workshop.title} restano {seat_label}.\n\n"
            "Se vuoi partecipare, puoi consultare i dettagli e riservare il posto qui:\n"
            f"{landing_url}\n\n"
            "La disponibilità è aggiornata in base ai pagamenti effettivamente confermati.\n\n"
            "Davide Luongo\n"
            "info@davideluongo.it\n\n"
            f"Non vuoi più ricevere questi avvisi? {unsubscribe_url}"
        )
        success, _ = send_email(
            subscriber.email,
            f"📷 Workshop Friuli 2026 — restano {seat_label}",
            body,
        )
        if success:
            setattr(subscriber, notified_field, now)
            sent += 1

    db.commit()
    return sent

