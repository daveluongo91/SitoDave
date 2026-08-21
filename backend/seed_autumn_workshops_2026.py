"""Crea o aggiorna Canfaito & Conero e Foreste Casentinesi 2026."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config.database import SessionLocal, init_db
from backend.app.models.workshop import Workshop


WORKSHOPS = (
    {
        "key": "canfaito-2026",
        "title": "Workshop Canfaito & Conero: Faggeta e Costa Adriatica",
        "start_date": "2026-11-07",
        "end_date": "2026-11-08",
        "cutoff_at": "2026-11-06T23:00:00+00:00",
        "location": "Faggeta di Canfaito e Monte Conero, Marche",
        "description": (
            "Workshop fotografico tra la faggeta di Canfaito e gli scorci costieri "
            "del Monte Conero, dedicato al tardo autunno e alla fotografia di paesaggio."
        ),
        "image": "/Canfaito_Conero_2026/assets/placeholder-hero-canfaito-2026.svg",
        "details_url": "/Canfaito_Conero_2026/",
    },
    {
        "key": "foreste-casentinesi-2026",
        "title": "Workshop Foreste Casentinesi: Bosco, Acqua e Tardo Autunno",
        "start_date": "2026-11-28",
        "end_date": "2026-11-29",
        "cutoff_at": "2026-11-27T23:00:00+00:00",
        "location": "Parco Nazionale delle Foreste Casentinesi",
        "description": (
            "Workshop fotografico dedicato ai boschi, ai torrenti e alle atmosfere "
            "di fine novembre nelle Foreste Casentinesi."
        ),
        "image": "/Foreste_Casentinesi_2026/assets/placeholder-hero-foreste-casentinesi-2026.svg",
        "details_url": "/Foreste_Casentinesi_2026/",
    },
)


def _upsert_workshop(db, data: dict[str, str]) -> str:
    workshop = db.query(Workshop).filter(Workshop.workshop_key == data["key"]).first()
    created = workshop is None
    if created:
        workshop = Workshop(
            workshop_key=data["key"],
            slug=data["key"],
            title=data["title"],
            price_cents=35000,
            total_seats=8,
            available_seats=8,
        )
        db.add(workshop)

    workshop.slug = data["key"]
    workshop.title = data["title"]
    workshop.category = "nazionale"
    workshop.start_date = data["start_date"]
    workshop.end_date = data["end_date"]
    workshop.timezone = "Europe/Rome"
    workshop.total_seats = 8
    if created:
        workshop.available_seats = 8
    else:
        workshop.available_seats = max(0, min(workshop.available_seats, 8))
    workshop.price_cents = 35000
    workshop.price_label = "€350"
    workshop.status = "active" if workshop.available_seats > 0 else "soldout"
    workshop.cutoff_at = data["cutoff_at"]
    if created or not workshop.cutoff_status:
        workshop.cutoff_status = "pending"
    workshop.operative_notes = (
        "Caparra €50; saldo €300. Politiche di rimborso identiche al Friuli 2026. "
        "Docenti: Davide Luongo e Manuel Linari."
    )
    workshop.location = data["location"]
    workshop.duration = "2 Giorni / 1 Notte"
    workshop.description = data["description"]
    workshop.image = data["image"]
    workshop.details_url = data["details_url"]
    return "created" if created else "updated"


def seed() -> dict[str, str]:
    init_db()
    db = SessionLocal()
    try:
        results = {data["key"]: _upsert_workshop(db, data) for data in WORKSHOPS}
        db.commit()
        return results
    finally:
        db.close()


if __name__ == "__main__":
    for workshop_key, result in seed().items():
        print(f"{workshop_key}: {result}")
