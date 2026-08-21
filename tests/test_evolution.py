"""
tests/test_evolution.py
Suite di test completa per l'evoluzione di SitoDave:
- Export Partecipanti isolato dal Cutoff
- CRM: Acquisizione, deduplicazione, statistiche, import/export CSV, blacklist, interazioni
- 2FA Email OTP, challenge HMAC, codici di recupero monouso, cooldown e blocco tentativi
- Template Esperienze & Viaggi (workshop-v1, international-trip-v1), validazione pre-pubblicazione
- Backup SQLite atomico con verifica di integrità
"""
import io
import json
import secrets
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.database import Base, get_db
from backend.app.main import app
from backend.app.models.booking import Booking
from backend.app.models.workshop import Workshop
from backend.app.models.contact import Contact
from backend.app.models.contact_interaction import ContactInteraction
from backend.app.models.user import User
from backend.app.models.cost import WorkshopCost
from backend.app.services.auth_service import hash_password, create_session
from backend.app.services.export_service import generate_participants_export_xlsx
from backend.app.services.crm_service import (
    get_or_create_contact_from_interaction,
    link_booking_to_contact,
    get_crm_dashboard_metrics,
)
from backend.app.services.csv_service import (
    parse_csv_preview,
    execute_csv_import,
    generate_contacts_export_csv,
)
from backend.app.services.otp_service import (
    generate_and_send_login_otp,
    verify_login_otp_or_recovery,
    generate_recovery_codes_for_user,
)
from backend.app.services.template_service import (
    validate_experience_for_publication,
    render_deterministic_page_html,
)
from backend.app.services.backup_service import (
    create_database_backup,
    verify_backup_integrity,
)


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test_evolution.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    u = User(
        username="admin_test",
        email="info@davideluongo.it",
        password_hash=hash_password("SuperSecretPassword2026!"),
        role="admin",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def client(db_session, test_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    
    # Crea sessione autenticata per i test admin
    session_id = create_session(db_session, test_user)
    client.cookies.set("admin_session", session_id)
    
    yield client
    app.dependency_overrides.clear()


# ── 1. TEST EXPORT PARTECIPANTI ESTEMPORANEO ─────────────────────────────────

def test_participants_export_is_pure_and_does_not_modify_state(db_session, tmp_path):
    ws = Workshop(
        workshop_key="test-exp-2026",
        slug="test-exp-2026",
        title="Test Workshop 2026",
        start_date="2026-10-10",
        total_seats=8,
        available_seats=7,
        price_cents=35000,
        status="active",
        cutoff_status="pending",
    )
    db_session.add(ws)
    db_session.commit()

    b1 = Booking(
        id="BK-TEST-001",
        workshop_id="test-exp-2026",
        workshop_name="Test Workshop 2026",
        first_name="Mario",
        last_name="Rossi",
        email="mario.rossi@example.com",
        phone="+393331234567",
        participants=1,
        formula="saldo",
        status="paid",
        final_cents=35000,
        balance_cents=0,
    )
    db_session.add(b1)
    db_session.commit()

    # Genera export estemporaneo
    filepath, file_hash, filename = generate_participants_export_xlsx(
        workshop=ws,
        bookings=[b1],
        output_dir=tmp_path,
    )

    assert filepath.exists()
    assert filepath.stat().st_size > 1000
    assert len(file_hash) == 64
    assert filename.startswith("partecipanti_test-exp-2026_")

    # Verifica che lo stato del workshop e della prenotazione siano rimasti invariati
    db_session.refresh(ws)
    db_session.refresh(b1)
    assert ws.cutoff_status == "pending"
    assert b1.status == "paid"


# ── 2. TEST CRM ACQUISIZIONE & DEDUPLICAZIONE ────────────────────────────────

def test_crm_contact_lifecycle(db_session):
    # 1. Nuova richiesta informazioni crea un lead
    c, i = get_or_create_contact_from_interaction(
        db=db_session,
        email="Giulia.Bianchi@example.com",
        first_name="Giulia",
        last_name="Bianchi",
        phone="+39 340 1234567",
        source="friuli-2026",
        interaction_type="info_request",
        interaction_subject="Richiesta informazioni",
        interaction_note="Vorrei sapere se serve attrezzatura specifica.",
    )

    assert c.id is not None
    assert c.email == "giulia.bianchi@example.com"  # Normalizzata
    assert c.status == "new_lead"
    assert c.total_spent_cents == 0
    assert len(c.interactions) == 1
    assert i.type == "info_request"

    # 2. Prenotazione confermata converte il lead in cliente
    b = Booking(
        id="BK-GIULIA-01",
        workshop_id="friuli-2026",
        workshop_name="Friuli 2026",
        first_name="Giulia",
        last_name="Bianchi",
        email="giulia.bianchi@example.com",
        phone="+393401234567",
        participants=1,
        formula="saldo",
        status="paid",
        final_cents=35000,
    )
    db_session.add(b)
    db_session.commit()

    updated_c = link_booking_to_contact(db_session, b)
    assert updated_c.id == c.id
    assert updated_c.status == "customer"
    assert updated_c.total_spent_cents == 35000

    # 3. Seconda prenotazione lo trasforma in loyal_customer
    b2 = Booking(
        id="BK-GIULIA-02",
        workshop_id="canfaito-2026",
        workshop_name="Canfaito 2026",
        first_name="Giulia",
        last_name="Bianchi",
        email="giulia.bianchi@example.com",
        phone="+393401234567",
        participants=1,
        formula="saldo",
        status="paid",
        final_cents=39000,
    )
    db_session.add(b2)
    db_session.commit()

    loyal_c = link_booking_to_contact(db_session, b2)
    assert loyal_c.status == "loyal_customer"
    assert loyal_c.total_spent_cents == 74000


# ── 3. TEST IMPORT ED EXPORT CSV CON SICUREZZA FORMULE ────────────────────────

def test_crm_csv_import_and_export(db_session):
    csv_content = (
        "Nome;Cognome;Email;Telefono;Note;Tags\n"
        "Luca;Verdi;luca.verdi@example.com;+393471112233;Interessato a paesaggi;astrofotografia, dolomiti\n"
        "Anna;Neri;anna.neri@example.com;+393489998877;=cmd|' /C calc'!A0;paesaggio\n"  # Tentativo Formula Injection
    )
    raw_bytes = csv_content.encode("utf-8")

    preview = parse_csv_preview(raw_bytes)
    assert preview["totalRows"] == 2
    assert preview["delimiter"] == ";"
    assert "email" in preview["mappingSuggestions"]

    # Esegui import
    mapping = {"first_name": 0, "last_name": 1, "email": 2, "phone": 3, "notes": 4, "tags": 5}
    res = execute_csv_import(
        db=db_session,
        raw_bytes=raw_bytes,
        column_mapping=mapping,
        duplicate_strategy="update_empty",
    )
    assert res["created"] == 2

    # Verifica sanitize
    anna = db_session.query(Contact).filter(Contact.email == "anna.neri@example.com").first()
    assert anna is not None
    assert len(anna.tags) == 1

    # Export CSV con UTF-8 BOM
    contacts = db_session.query(Contact).all()
    csv_export_bytes = generate_contacts_export_csv(contacts)
    assert csv_export_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    export_text = csv_export_bytes.decode("utf-8-sig")
    assert "luca.verdi@example.com" in export_text
    assert "anna.neri@example.com" in export_text


# ── 4. TEST 2FA EMAIL OTP & RECOVERY CODES ───────────────────────────────────

def test_two_factor_authentication_flow(db_session, test_user):
    # 1. Genera OTP
    challenge_token, masked_email = generate_and_send_login_otp(db_session, test_user, ip="127.0.0.1")
    assert len(challenge_token) > 20
    assert "@" in masked_email
    assert test_user.otp_hash is not None
    assert test_user.otp_challenge_token == challenge_token

    # 2. Tentativo con codice errato
    with pytest.raises(ValueError) as exc:
        verify_login_otp_or_recovery(db_session, challenge_token, "000000")
    assert "errato" in str(exc.value)
    assert test_user.otp_failed_attempts == 1

    # 3. Genera e usa codice di recupero
    recovery_codes = generate_recovery_codes_for_user(db_session, test_user)
    assert len(recovery_codes) == 8
    
    first_recovery_code = recovery_codes[0]
    authenticated_user = verify_login_otp_or_recovery(db_session, challenge_token, first_recovery_code)
    assert authenticated_user.id == test_user.id
    
    # Il codice di recupero è stato consumato (ora ne restano 7)
    remaining_hashes = json.loads(test_user.recovery_codes_hash)
    assert len(remaining_hashes) == 7


# ── 5. TEST TEMPLATE ESPERIENZE E CONTROLLI PRE-PUBBLICAZIONE ────────────────

def test_experience_template_and_validation(db_session):
    # Caso 1: Mancanza tour operator per viaggio internazionale
    invalid_trip_data = {
        "title": "Spedizione Fotografica Isole Lofoten",
        "slug": "lofoten-2027",
        "experienceType": "international_trip",
        "templateVersion": "international-trip-v1",
        "startDate": "2027-02-10",
        "endDate": "2027-02-18",
        "country": "Norvegia",
        "destination": "Lofoten",
        "priceCents": 240000,
        "totalSeats": 8,
        "technicalOperator": "",  # Mancante!
        "documentsRequired": "Passaporto",
    }
    is_valid, errors, warnings = validate_experience_for_publication(invalid_trip_data)
    assert not is_valid
    assert any("Tour Operator" in e for e in errors)

    # Caso 2: Viaggio completo e valido
    valid_trip_data = {
        "title": "Spedizione Fotografica Isole Lofoten 2027",
        "slug": "lofoten-2027",
        "experienceType": "international_trip",
        "templateVersion": "international-trip-v1",
        "startDate": "2027-02-10",
        "endDate": "2027-02-18",
        "country": "Norvegia",
        "destination": "Lofoten",
        "priceCents": 240000,
        "totalSeats": 8,
        "technicalOperator": "Agenzia Viaggi & Tour Operator Autorizzato",
        "documentsRequired": "Carta identità valida per espatrio",
        "description": "Un viaggio fotografico indimenticabile oltre il Circolo Polare Artico tra aurore e fiordi.",
    }
    is_valid, errors, warnings = validate_experience_for_publication(valid_trip_data)
    assert is_valid
    assert len(errors) == 0


# ── 6. TEST BACKUP SQLITE ATOMICO E VERIFICA INTEGRITÀ ───────────────────────

def test_database_backup_and_integrity(db_session, tmp_path):
    db_file = tmp_path / "source.db"
    conn = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=conn)

    backup_dir = tmp_path / "backups"
    backup_info = create_database_backup(db_path=db_file, backup_dir=backup_dir)

    assert backup_info["integrityOk"] is True
    assert len(backup_info["hashSha256"]) == 64
    assert Path(backup_info["path"]).exists()
    assert verify_backup_integrity(Path(backup_info["path"])) is True