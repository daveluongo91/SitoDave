"""Crea o aggiorna la configurazione backend del Workshop Dardagna 2026."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config.database import SessionLocal, init_db
from backend.app.models.workshop import Workshop


WORKSHOP_KEY = "dardagna-2026"


def seed() -> str:
    init_db()
    db = SessionLocal()
    try:
        workshop = db.query(Workshop).filter(Workshop.workshop_key == WORKSHOP_KEY).first()
        created = workshop is None
        if created:
            workshop = Workshop(
                workshop_key=WORKSHOP_KEY,
                slug=WORKSHOP_KEY,
                title="Workshop Dardagna: Cascate dell’Appennino",
                price_cents=35000,
                total_seats=8,
                available_seats=8,
            )
            db.add(workshop)

        workshop.slug = WORKSHOP_KEY
        workshop.title = "Workshop Dardagna: Cascate dell’Appennino"
        workshop.category = "nazionale"
        workshop.start_date = "2026-10-24"
        workshop.end_date = "2026-10-25"
        workshop.timezone = "Europe/Rome"
        workshop.total_seats = 8
        if created:
            workshop.available_seats = 8
        else:
            workshop.available_seats = max(0, min(workshop.available_seats, 8))
        workshop.price_cents = 35000
        workshop.price_label = "€350"
        workshop.status = "active" if workshop.available_seats > 0 else "soldout"
        # Mezzanotte locale all'inizio del 24 ottobre, salvata in UTC.
        workshop.cutoff_at = "2026-10-23T22:00:00+00:00"
        if created or not workshop.cutoff_status:
            workshop.cutoff_status = "pending"
        workshop.operative_notes = (
            "Caparra €50; saldo €300. Politiche di rimborso identiche al Friuli 2026. "
            "Docenti: Davide Luongo e Manuel Linari."
        )
        workshop.location = "Cascate del Dardagna, Parco Regionale del Corno alle Scale"
        workshop.duration = "2 Giorni / 1 Notte"
        workshop.description = (
            "Workshop fotografico dedicato alle cascate, alla faggeta e alle lunghe esposizioni."
        )
        workshop.image = "/Dardagna_2026/assets/dardagna-hero-poster.jpg"
        workshop.details_url = "/Dardagna_2026/"
        db.commit()
        return "created" if created else "updated"
    finally:
        db.close()


if __name__ == "__main__":
    print(f"dardagna-2026: {seed()}")
