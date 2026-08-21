from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config.database import get_db
from backend.app.main import app
from backend.app.models.availability_subscriber import AvailabilitySubscriber
from backend.app.models.workshop import Workshop
from backend.app.routes import public
from backend.app.services import availability_alert_service


def test_dardagna_seats_are_served_from_backend():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Workshop.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(
        Workshop(
            workshop_key="dardagna-2026",
            slug="dardagna-2026",
            title="Workshop Dardagna: Cascate dell’Appennino",
            total_seats=8,
            available_seats=8,
            price_cents=35000,
            status="active",
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/workshops/dardagna-2026/seats")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200
    assert response.json() == {"availableSeats": 8, "status": "active"}


def test_info_email_has_dardagna_marker_and_reply_address(monkeypatch):
    captured = {}

    def fake_send_email(recipient, subject, body):
        captured.update(recipient=recipient, subject=subject, body=body)
        return True, "Email inviata con successo."

    monkeypatch.setattr(public, "send_email", fake_send_email)
    with TestClient(app) as client:
        response = client.post(
            "/api/send-info-email",
            json={
                "name": "Mario Rossi",
                "email": "mario@example.com",
                "phone": "+39 333 0000000",
                "source": "dardagna-2026",
                "subject": "Richiesta informazioni",
                "message": "Vorrei alcune informazioni.",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "[DARDAGNA 2026]" in captured["subject"]
    assert "Email: mario@example.com" in captured["body"]
    assert "Provenienza: [DARDAGNA 2026]" in captured["body"]


def test_dardagna_availability_alert_uses_its_own_page(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Workshop.__table__.create(engine)
    AvailabilitySubscriber.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    workshop = Workshop(
        workshop_key="dardagna-2026",
        slug="dardagna-2026",
        title="Workshop Dardagna: Cascate dell’Appennino",
        total_seats=8,
        available_seats=2,
        price_cents=35000,
        details_url="/Dardagna_2026/",
    )
    subscriber = AvailabilitySubscriber(
        workshop_id="dardagna-2026",
        name="Mario",
        email="mario@example.com",
        consent_at="2026-08-19T00:00:00+00:00",
        consent_source="dardagna-2026-landing",
        unsubscribe_token="test-token-dardagna-2026",
        active=True,
    )
    db.add_all([workshop, subscriber])
    db.commit()

    captured = {}

    def fake_send_email(recipient, subject, body):
        captured.update(recipient=recipient, subject=subject, body=body)
        return True, "ok"

    monkeypatch.setattr(availability_alert_service, "send_email", fake_send_email)
    monkeypatch.setattr(availability_alert_service.settings, "aruba_smtp_pass", "test-only")
    sent = availability_alert_service.notify_availability_threshold(db, workshop)

    assert sent == 1
    assert "[DARDAGNA 2026]" in captured["subject"]
    assert "https://www.davideluongo.it/Dardagna_2026/" in captured["body"]
    assert subscriber.notified_two_at is not None
    db.close()
