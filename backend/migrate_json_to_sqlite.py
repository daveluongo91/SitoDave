"""
backend/migrate_json_to_sqlite.py
Migra i dati dal sistema JSON flat-file (vecchio) al database SQLite (nuovo).
Idempotente: non duplica dati già migrati.
Eseguire DOPO admin_init.py:
  python backend/migrate_json_to_sqlite.py
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_env = PROJECT_ROOT / ".env"
if _env.exists():
    with open(_env, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from backend.app.config.database import SessionLocal, init_db
from backend.app.models.workshop import Workshop
from backend.app.models.booking import Booking
from backend.app.models.coupon import Coupon
from backend.app.models.page import Page
from backend.app.models.block import Block
import uuid

DATA_DIR = PROJECT_ROOT / "data"
CONTENT_FILE = DATA_DIR / "content.json"
BOOKINGS_FILE = DATA_DIR / "bookings.json"

NOW = datetime.now(timezone.utc).isoformat()


def migrate_workshops(db, content: dict) -> int:
    """Migra workshop da content.json → tabella workshops."""
    count = 0
    for ws_data in content.get("workshops", []) + content.get("trips_2027", []):
        ws_id = ws_data.get("id", "")
        if not ws_id:
            continue
        existing = db.query(Workshop).filter(Workshop.workshop_key == ws_id).first()
        if existing:
            print(f"  SKIP workshop già esistente: {ws_id}")
            continue

        ws = Workshop(
            workshop_key=ws_id,
            slug=ws_id,
            title=ws_data.get("title", ""),
            category=ws_data.get("category"),
            start_date=ws_data.get("date", "").split(" - ")[0] if ws_data.get("date") else None,
            end_date=ws_data.get("date", "").split(" - ")[-1] if " - " in ws_data.get("date", "") else None,
            total_seats=ws_data.get("totalSeats", 8),
            available_seats=ws_data.get("availableSeats", 8),
            price_cents=ws_data.get("priceCents", 35000),
            price_label=ws_data.get("price"),
            status=ws_data.get("status", "active"),
            location=ws_data.get("location"),
            duration=ws_data.get("duration"),
            description=ws_data.get("description"),
            image=ws_data.get("image"),
            details_url=ws_data.get("detailsUrl"),
        )
        db.add(ws)
        count += 1
        print(f"  OK workshop: {ws_id}")
    db.commit()
    return count


def migrate_bookings(db) -> int:
    """Migra prenotazioni da bookings.json → tabella bookings."""
    if not BOOKINGS_FILE.exists():
        print("  bookings.json non trovato. Nessuna prenotazione da migrare.")
        return 0

    with open(BOOKINGS_FILE, "r", encoding="utf-8-sig") as f:
        bookings_data = json.load(f)

    count = 0
    for bd in bookings_data:
        bk_id = bd.get("id", "")
        if not bk_id:
            continue
        existing = db.query(Booking).filter(Booking.id == bk_id).first()
        if existing:
            print(f"  SKIP prenotazione già esistente: {bk_id}")
            continue

        b = Booking(
            id=bk_id,
            created_at=bd.get("createdAt", NOW),
            status=bd.get("status", "pending"),
            workshop_id=bd.get("workshopId"),
            workshop_name=bd.get("workshopName"),
            first_name=bd.get("firstName", ""),
            last_name=bd.get("lastName", ""),
            email=bd.get("email", "").lower(),
            phone=bd.get("phone"),
            participants=bd.get("participants", 1),
            formula=bd.get("formula"),
            extra_day_selected=bd.get("extraDay", False),
            extra_day_cents=bd.get("extraDayCents", 0),
            original_cents=bd.get("originalCents"),
            discount_cents=bd.get("discountCents", 0),
            final_cents=bd.get("finalCents"),
            balance_cents=bd.get("balanceCents", 0),
            amount_due_cents=bd.get("amountDueCents"),
            coupon_code=bd.get("couponCode") or None,
            paypal_order_id=bd.get("paypalOrderId"),
            paypal_capture_id=bd.get("paypalCaptureId"),
            paypal_env=bd.get("paypalEnv"),
            balance_paid=bd.get("balancePaid", False),
            balance_paid_method=bd.get("balancePaidMethod"),
            balance_paid_date=bd.get("balancePaidDate"),
        )
        db.add(b)
        count += 1
        print(f"  OK prenotazione: {bk_id}")
    db.commit()
    return count


def migrate_coupons(db, content: dict) -> int:
    """Migra coupon da content.json → tabella coupons."""
    count = 0
    for c_data in content.get("coupons", []):
        code = c_data.get("code", "").strip().upper()
        if not code:
            continue
        existing = db.query(Coupon).filter(Coupon.code == code).first()
        if existing:
            print(f"  SKIP coupon già esistente: {code}")
            continue

        # Normalizza tipo (il vecchio sistema usava "fixed_price" come "final_price")
        c_type = c_data.get("type", "percentage")
        if c_type not in ("percentage", "final_price"):
            c_type = "final_price" if c_data.get("fixedPrice") else "percentage"

        # Valore: per percentage usa 'percentage' o 'value', per final_price usa 'fixedPrice' o 'value'
        if c_type == "percentage":
            value = str(c_data.get("percentage") or c_data.get("value") or "0")
        else:
            value = str(c_data.get("fixedPrice") or c_data.get("value") or "0")

        import json
        coupon = Coupon(
            code=code,
            description=c_data.get("description"),
            status="active" if c_data.get("active", True) else "inactive",
            type=c_type,
            value_decimal=value,
            applicable_workshops=json.dumps(c_data.get("applicableWorkshops", ["all"])),
            max_uses_total=c_data.get("usageLimit") or c_data.get("maxUsesTotal"),
            used_count=c_data.get("usedCount", 0),
        )
        db.add(coupon)
        count += 1
        print(f"  OK coupon: {code}")
    db.commit()
    return count


def migrate_home_page(db, content: dict) -> None:
    """Crea la pagina Home con i dati base."""
    existing = db.query(Page).filter(Page.page_key == "home").first()
    if existing:
        print("  SKIP pagina home già esistente.")
        return

    page = Page(
        page_key="home",
        slug="home",
        admin_title="Home Page (index.html)",
        seo_title="Davide Luongo — Landscape & Astrophotography",
        meta_description="Workshop fotografici, viaggi guidati e formazione One-to-One con Davide Luongo.",
        status="published",
    )
    db.add(page)
    db.commit()
    db.refresh(page)

    # Crea blocco hero con i dati esistenti
    home_data = content.get("home", {})
    hero_content = {
        "badge": home_data.get("badge", "HIKE • SHOOT • PRINT • REPEAT"),
        "title": home_data.get("title", ""),
        "description": home_data.get("description", ""),
    }
    hero_block = Block(
        page_id=page.id,
        block_key=uuid.uuid4().hex,
        type="hero",
        content=json.dumps(hero_content, ensure_ascii=False),
        order_index=0,
        is_visible=True,
        variant="full",
    )
    db.add(hero_block)

    # Blocco bio
    bio_data = home_data.get("bio", {})
    if bio_data:
        bio_content = {
            "title": bio_data.get("title", ""),
            "subtitle": bio_data.get("subtitle", ""),
            "paragraphs": bio_data.get("paragraphs", []),
        }
        bio_block = Block(
            page_id=page.id,
            block_key=uuid.uuid4().hex,
            type="text",
            content=json.dumps(bio_content, ensure_ascii=False),
            order_index=1,
            is_visible=True,
        )
        db.add(bio_block)

    db.commit()
    print("  OK pagina home creata con blocchi hero e bio.")


def main():
    print("\n" + "="*60)
    print("  Migrazione JSON → SQLite")
    print("="*60 + "\n")

    if not CONTENT_FILE.exists():
        print(f"❌ content.json non trovato in {DATA_DIR}")
        sys.exit(1)

    with open(CONTENT_FILE, "r", encoding="utf-8-sig") as f:
        content = json.load(f)

    init_db()
    db = SessionLocal()

    try:
        print("\n[1/4] Workshop...")
        n_ws = migrate_workshops(db, content)
        print(f"      Migrati {n_ws} workshop.")

        print("\n[2/4] Prenotazioni...")
        n_bk = migrate_bookings(db)
        print(f"      Migrate {n_bk} prenotazioni.")

        print("\n[3/4] Coupon...")
        n_cp = migrate_coupons(db, content)
        print(f"      Migrati {n_cp} coupon.")

        print("\n[4/4] Pagina Home CMS...")
        migrate_home_page(db, content)

        print("\n" + "="*60)
        print("✅ MIGRAZIONE COMPLETATA")
        print(f"   Workshop  : {n_ws}")
        print(f"   Booking   : {n_bk}")
        print(f"   Coupon    : {n_cp}")
        print("="*60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
