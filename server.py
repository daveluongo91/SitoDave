#!/usr/bin/env python3
"""
Davide Luongo Website — Backend Server v2.0
Includes: PayPal Orders API v2, Webhook verification, Coupon engine,
          Booking lifecycle management, sRGB image processing, AI SEO.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
import re
import hmac
import hashlib
import threading
import urllib.parse
import io
import base64
import csv
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from collections import defaultdict

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import Image, ImageCms, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── Load .env ────────────────────────────────────────────────────────────────
def _load_env(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

ROOT = Path(__file__).parent.resolve()
_load_env(ROOT / ".env")

DATA_FILE        = ROOT / "data" / "content.json"
PARTICIPANTS_FILE = ROOT / "data" / "participants.json"
BOOKINGS_FILE    = ROOT / "data" / "bookings.json"
UPLOAD_DIR       = ROOT / "assets" / "upload"
EXPORTS_DIR      = ROOT / "data" / "exports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

PORT          = 3000
MAX_DIMENSION = 2048
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB

DEPOSIT_CENTS = 5000  # €50.00 caparra fissa

# ─── PayPal Config ────────────────────────────────────────────────────────────
_PAYPAL_ENV = os.environ.get("PAYPAL_ENV", "sandbox").lower()
if _PAYPAL_ENV == "live":
    _PAYPAL_BASE = "https://api-m.paypal.com"
    _PAYPAL_CLIENT_ID     = os.environ.get("PAYPAL_LIVE_CLIENT_ID", "")
    _PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_LIVE_CLIENT_SECRET", "")
else:
    _PAYPAL_BASE = "https://api-m.sandbox.paypal.com"
    _PAYPAL_CLIENT_ID     = os.environ.get("PAYPAL_SANDBOX_CLIENT_ID", "")
    _PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_SANDBOX_CLIENT_SECRET", "")
_PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")

_paypal_token_cache = {"token": None, "expires_at": 0}
_paypal_token_lock  = threading.Lock()

def _paypal_get_token():
    """Fetch (or return cached) PayPal OAuth access token."""
    with _paypal_token_lock:
        now = datetime.now(timezone.utc).timestamp()
        if _paypal_token_cache["token"] and now < _paypal_token_cache["expires_at"] - 60:
            return _paypal_token_cache["token"]
        if not HAS_REQUESTS:
            raise RuntimeError("La libreria 'requests' non è installata. Esegui: pip install requests")
        r = _requests.post(
            f"{_PAYPAL_BASE}/v1/oauth2/token",
            auth=(_PAYPAL_CLIENT_ID, _PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        _paypal_token_cache["token"] = data["access_token"]
        _paypal_token_cache["expires_at"] = now + data.get("expires_in", 3600)
        return _paypal_token_cache["token"]

def _paypal_request(method, path, body=None):
    token = _paypal_get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{_PAYPAL_BASE}{path}"
    r = _requests.request(method, url, headers=headers, json=body, timeout=20)
    r.raise_for_status()
    if r.text:
        return r.json()
    return {}

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
_rate_store     = defaultdict(list)   # ip -> [timestamp, ...]
_rate_store_lock = threading.Lock()

def _rate_check(ip, max_per_minute=10):
    """Return True if request is allowed, False if rate limited."""
    with _rate_store_lock:
        now = datetime.now(timezone.utc).timestamp()
        window = now - 60
        _rate_store[ip] = [t for t in _rate_store[ip] if t > window]
        if len(_rate_store[ip]) >= max_per_minute:
            return False
        _rate_store[ip].append(now)
        return True

# ─── Bookings DB ──────────────────────────────────────────────────────────────
_bookings_lock = threading.Lock()

def load_bookings():
    with _bookings_lock:
        if not BOOKINGS_FILE.exists():
            return []
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_bookings(bookings):
    with _bookings_lock:
        BOOKINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookings, f, ensure_ascii=False, indent=2)

def get_booking_by_order_id(order_id):
    for b in load_bookings():
        if b.get("paypalOrderId") == order_id:
            return b
    return None

def upsert_booking(booking):
    bookings = load_bookings()
    for i, b in enumerate(bookings):
        if b.get("id") == booking["id"]:
            bookings[i] = booking
            save_bookings(bookings)
            return
    bookings.insert(0, booking)
    save_bookings(bookings)



def load_content():
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_content(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_participants():
    if not PARTICIPANTS_FILE.exists():
        return []
    with open(PARTICIPANTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_participants(participants):
    with open(PARTICIPANTS_FILE, "w", encoding="utf-8") as f:
        json.dump(participants, f, ensure_ascii=False, indent=2)

def compute_urgency_seats(available_seats, total_seats=8):
    """
    Computes displayed seats minus 20% for urgency/FOMO bias.
    """
    if available_seats <= 0:
        return 0
    bias = int(total_seats * 0.20) # 8 * 0.20 = 1.6 -> 1 seat bias
    displayed = max(1, available_seats - bias)
    return displayed

def generate_excel_report(workshop_id_or_name=None):
    """
    Generates an Excel-compatible CSV report with UTF-8 BOM for participant lists.
    """
    participants = load_participants()
    if workshop_id_or_name:
        participants = [p for p in participants if workshop_id_or_name.lower() in p.get("workshop", "").lower() or workshop_id_or_name.lower() in p.get("workshopId", "").lower()]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_partecipanti_{workshop_id_or_name or 'tutti'}_{timestamp}.csv"
    filepath = EXPORTS_DIR / filename

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ID Prenotazione", "Data Iscrizione", "Workshop", "Nome", "Cognome", "Email", "Telefono (WhatsApp)", "Formula Pagamento", "Importo Versato", "Stato Cutoff"])
        for p in participants:
            writer.writerow([
                p.get("id", ""),
                p.get("bookingDate", ""),
                p.get("workshop", ""),
                p.get("firstName", ""),
                p.get("lastName", ""),
                p.get("email", ""),
                p.get("phone", ""),
                p.get("paymentFormula", ""),
                p.get("amountPaid", ""),
                p.get("cutoffStatus", "Attivo")
            ])

    return filepath, filename

def send_real_email_aruba(recipient_email, subject, body_text, attachment_path=None):
    """
    Sends real emails via Aruba SMTP (smtps.aruba.it:465 SSL).
    Reads password from environment ARUBA_SMTP_PASS or data/smtp_config.json.
    """
    config_file = ROOT / "data" / "smtp_config.json"
    smtp_pass = os.environ.get("ARUBA_SMTP_PASS", "")
    smtp_user = os.environ.get("ARUBA_SMTP_USER", "info@davideluongo.it")
    smtp_host = os.environ.get("ARUBA_SMTP_HOST", "smtps.aruba.it")
    smtp_port = int(os.environ.get("ARUBA_SMTP_PORT", "465"))

    if not smtp_pass and config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                smtp_pass = cfg.get("smtpPassword", "")
                smtp_user = cfg.get("smtpUser", smtp_user)
                smtp_host = cfg.get("smtpHost", smtp_host)
                smtp_port = cfg.get("smtpPort", smtp_port)
        except Exception:
            pass

    msg = MIMEMultipart()
    msg["From"] = f"Davide Luongo Website <{smtp_user}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    if attachment_path and Path(attachment_path).exists():
        att_path = Path(attachment_path)
        part = MIMEBase("application", "octet-stream")
        part.set_payload(att_path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={att_path.name}")
        msg.attach(part)

    if smtp_pass:
        try:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [recipient_email], msg.as_string())
            server.quit()
            
            log_entry = f"[{datetime.now().isoformat()}] REAL EMAIL SENT via Aruba SMTP to {recipient_email} (Subject: {subject})\n"
            (ROOT / "data" / "sent_emails.log").open("a", encoding="utf-8").write(log_entry)
            return True, f"Email inviata con successo via Aruba SMTP a {recipient_email}"
        except Exception as e:
            log_entry = f"[{datetime.now().isoformat()}] Aruba SMTP error: {str(e)}\n"
            (ROOT / "data" / "sent_emails.log").open("a", encoding="utf-8").write(log_entry)
            return False, f"Errore invio SMTP Aruba: {str(e)}"
    else:
        # Log pending configuration
        log_entry = f"[{datetime.now().isoformat()}] SMTP Password not set. Email logged locally for {recipient_email} (Subject: {subject})\n"
        (ROOT / "data" / "sent_emails.log").open("a", encoding="utf-8").write(log_entry)
        return True, "Email registrata in locale (inserisci la password Aruba in Admin per la spedizione reale)"

def send_excel_email_report(filepath, recipient_email="info@davideluongo.com", workshop_name="Workshop"):
    body = f"""Ciao Davide,

In allegato trovi il report Excel ufficiale dei partecipanti per: {workshop_name}.

- Data generazione: {datetime.now().strftime("%d/%m/%Y %H:%M")}
- Destinatario: {recipient_email}

Il file contiene nome, cognome, indirizzo email e numero di telefono per la creazione del gruppo WhatsApp.

Un saluto,
Davide Luongo Website Automated Engine
"""
    return send_real_email_aruba(recipient_email, f"📊 Report Partecipanti Excel Cutoff — {workshop_name}", body, attachment_path=filepath)

def process_image_srgb(input_bytes, original_filename, target_page="general"):
    raw_data = input_bytes.getvalue()
    raw_size = len(raw_data)
    stem = Path(original_filename).stem.replace(" ", "_")
    jpg_filename = f"{stem}_web.jpg"
    jpg_path = UPLOAD_DIR / jpg_filename

    if not HAS_PIL:
        jpg_path.write_bytes(raw_data)
        return {
            "filename": original_filename,
            "fullResPath": f"assets/upload/{jpg_filename}",
            "webpPath": f"assets/upload/{jpg_filename}",
            "jpegPath": f"assets/upload/{jpg_filename}",
            "width": 1920,
            "height": 1080,
            "originalSize": raw_size,
            "wasRescaled": False,
            "srgbPreserved": True,
            "pageTag": target_page,
            "uploadDate": datetime.now().strftime("%Y-%m-%d")
        }

    img = Image.open(io.BytesIO(raw_data))
    img = ImageOps.exif_transpose(img)

    orig_w, orig_h = img.size
    needs_rescale = (raw_size > MAX_FILE_BYTES) or (orig_w > MAX_DIMENSION) or (orig_h > MAX_DIMENSION)

    if needs_rescale:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    icc_profile = img.info.get('icc_profile')
    srgb_cms = ImageCms.createProfile('sRGB')
    srgb_bytes = ImageCms.ImageCmsProfile(srgb_cms).tobytes()
    final_icc = icc_profile or srgb_bytes

    webp_filename = f"{stem}_web.webp"
    webp_path = UPLOAD_DIR / webp_filename
    img.save(webp_path, format="WEBP", quality=90, icc_profile=final_icc)
    img.save(jpg_path, format="JPEG", quality=92, icc_profile=final_icc)

    return {
        "filename": original_filename,
        "fullResPath": f"assets/upload/{jpg_filename}",
        "webpPath": f"assets/upload/{webp_filename}",
        "jpegPath": f"assets/upload/{jpg_filename}",
        "width": img.width,
        "height": img.height,
        "originalSize": raw_size,
        "wasRescaled": needs_rescale,
        "srgbPreserved": True,
        "pageTag": target_page,
        "uploadDate": datetime.now().strftime("%Y-%m-%d")
    }

def run_ai_seo_agent(entity_type, entity):
    title = entity.get("title", "")
    location = entity.get("location", "")
    date_str = entity.get("date", "")
    description = entity.get("description") or entity.get("excerpt") or entity.get("microArticle") or ""
    image = entity.get("image", "assets/hero_milky_way.png")
    
    if entity_type == "workshop":
        seo_title = f"Workshop Fotografico {title} {date_str} • Davide Luongo"
    elif entity_type == "viaggio":
        seo_title = f"Photo Tour {title} {date_str} • Davide Luongo Viaggi"
    elif entity_type == "blog":
        seo_title = f"{title} • Guida & Articolo | Davide Luongo"
    elif entity_type == "gear":
        seo_title = f"{title} • Test & Recensione | Davide Luongo Gear"
    else:
        seo_title = f"{title} • Davide Luongo Landscape & Astrophotography"

    if len(seo_title) > 65:
        seo_title = seo_title[:62] + "..."

    clean_desc = description.replace("\n", " ").strip()
    if entity_type in ["workshop", "viaggio"]:
        seo_desc = f"Partecipa al {title} il {date_str} in {location}. Sessioni di fotografia di paesaggio ed astrofotografia con Davide Luongo. {clean_desc}"
    elif entity_type == "blog":
        seo_desc = f"Leggi l'articolo '{title}' su paesaggio e astrofotografia di Davide Luongo: {clean_desc}"
    elif entity_type == "gear":
        seo_desc = f"Recensione tecnica e test sul campo di {title} di Davide Luongo: {clean_desc}"
    else:
        seo_desc = clean_desc

    if len(seo_desc) > 158:
        seo_desc = seo_desc[:155] + "..."

    json_ld = {
        "@context": "https://schema.org",
        "@type": "EducationEvent" if entity_type in ["workshop", "viaggio"] else "Product" if entity_type == "gear" else "BlogPosting",
        "name": title,
        "description": seo_desc,
        "image": f"https://www.davideluongo.it/{image}"
    }

    return {
        "seoTitle": seo_title,
        "seoDescription": seo_desc,
        "ogTitle": seo_title,
        "ogDescription": seo_desc,
        "jsonLd": json_ld
    }

# ── Email helper for booking confirmations ──────────────────────────────────
def _send_booking_confirmation_emails(booking):
    formula      = booking.get("formula", "caparra")
    name         = f"{booking['firstName']} {booking['lastName']}"
    ws_name      = booking.get("workshopName", "Workshop Fotografico")
    final_eur    = booking.get("finalCents", 35000) / 100
    balance_eur  = booking.get("balanceCents", 30000) / 100
    coupon_note  = f" (codice: {booking['couponCode']})" if booking.get("couponCode") else ""
    order_id     = booking.get("paypalOrderId", "N/D")
    capture_id   = booking.get("paypalCaptureId", "N/D")
    bk_id        = booking.get("id", "")

    if formula == "caparra":
        client_body = f"""Ciao {booking['firstName']},

Abbiamo ricevuto la tua caparra di €50{coupon_note} per il workshop:

▸ {ws_name}

Prezzo finale: €{final_eur:.2f}
Saldo residuo: €{balance_eur:.2f} (da corrispondere in loco tramite bonifico, contanti o PayPal)

Importo rimborsabile in caso di disdetta: €{balance_eur:.2f}
(La caparra di €50 rimane a conferma dell'impegno preso.)

Per qualsiasi informazione rispondi a questa email.

A presto in Friuli!
Davide Luongo
info@davideluongo.it
"""
    else:
        client_body = f"""Ciao {booking['firstName']},

Abbiamo ricevuto il pagamento completo di €{final_eur:.2f}{coupon_note} per il workshop:

▸ {ws_name}

Non risultano importi residui da corrispondere.

Per qualsiasi informazione rispondi a questa email.

A presto in Friuli!
Davide Luongo
info@davideluongo.it
"""

    admin_body = f"""Nuova prenotazione CONFERMATA

ID Prenotazione : {bk_id}
Workshop        : {ws_name}
Cliente         : {name}
Email           : {booking['email']}
Telefono        : {booking.get('phone', 'N/D')}
Formula         : {'Caparra €50' if formula == 'caparra' else 'Pagamento completo'}
Prezzo finale   : €{final_eur:.2f}
Saldo in loco   : €{balance_eur:.2f}
Codice sconto   : {booking.get('couponCode') or 'Nessuno'}
PayPal Order ID : {order_id}
PayPal Capture  : {capture_id}
Ambiente PayPal : {booking.get('paypalEnv', 'sandbox')}
"""

    send_real_email_aruba(
        booking["email"],
        f"✅ Prenotazione confermata — {ws_name}",
        client_body
    )
    send_real_email_aruba(
        "info@davideluongo.it",
        f"🔔 NUOVA PRENOTAZIONE [{bk_id}] — {ws_name}",
        admin_body
    )


class BackendRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ─ Convenience response helpers ───────────────────────────────────────
    def _json_ok(self, data):
        payload = json.dumps({"status": "success", **data}, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def _json_err(self, message, code=400):
        payload = json.dumps({"status": "error", "message": message}, ensure_ascii=False)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-File-Name, X-Page-Tag")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/api/content":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = load_content()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/participants":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            participants = load_participants()
            self.wfile.write(json.dumps(participants, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/bookings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            bookings = load_bookings()
            self.wfile.write(json.dumps(bookings, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path.startswith("/api/download-excel"):
            query_params = urllib.parse.parse_qs(parsed.query)
            ws_id = query_params.get("workshopId", [None])[0]
            filepath, filename = generate_excel_report(ws_id)
            
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename={filename}")
            self.end_headers()
            self.wfile.write(filepath.read_bytes())
            return

        elif any(tag in parsed.path.lower() for tag in ["blog", "pubblicazioni"]):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            blog_file = ROOT / "blog" / "blog.html"
            if blog_file.exists():
                self.wfile.write(blog_file.read_bytes())
            else:
                self.wfile.write(b"Blog page not found")
            return

        elif parsed.path in ["/gear", "/gear/", "/gear.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            gear_file = ROOT / "gear" / "gear.html"
            if gear_file.exists():
                self.wfile.write(gear_file.read_bytes())
            else:
                self.wfile.write(b"Gear page not found")
            return

        elif parsed.path == "/admin":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            admin_file = ROOT / "admin.html"
            if admin_file.exists():
                self.wfile.write(admin_file.read_bytes())
            else:
                self.wfile.write(b"Admin page not found")
            return
        
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))

        if parsed.path == "/api/content":
            body = self.rfile.read(content_length)
            try:
                new_content = json.loads(body.decode("utf-8"))
                save_content(new_content)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Contenuti salvati ed aggiornati"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # ── Create PayPal Order (server-side price calculation) ──────────────
        elif parsed.path == "/api/create-paypal-order":
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body.decode("utf-8"))
                workshop_id   = req.get("workshopId", "").strip()
                formula       = req.get("formula", "caparra")   # caparra | saldo
                coupon_code   = req.get("couponCode", "").strip().upper()
                customer      = {
                    "firstName":    req.get("firstName", "").strip(),
                    "lastName":     req.get("lastName", "").strip(),
                    "email":        req.get("email", "").strip().lower(),
                    "phone":        req.get("phone", "").strip(),
                    "participants": int(req.get("participants", 1)),
                }

                # Basic validation
                if not customer["firstName"] or not customer["email"] or not workshop_id:
                    raise ValueError("Dati obbligatori mancanti (nome, email, workshop).")
                if not re.match(r"[^@]+@[^@]+\.[^@]+", customer["email"]):
                    raise ValueError("Indirizzo email non valido.")

                # Lookup workshop price from DB
                content = load_content()
                workshops_list = content.get("workshops", []) + content.get("trips_2027", [])
                ws = next((w for w in workshops_list if
                           w.get("id") == workshop_id or
                           w.get("title", "").lower() in workshop_id.lower() or
                           workshop_id.lower() in w.get("title", "").lower()), None)

                # Default price 350 if workshop not found (Friuli 2026)
                original_cents = int(ws.get("priceCents", 35000)) if ws else 35000
                original_price = original_cents  # in cents

                # Validate & apply coupon server-side
                discount_cents = 0
                coupon_applied = None
                if coupon_code:
                    coupons = content.get("coupons", [])
                    c = next((x for x in coupons if
                              x.get("code", "").strip().upper() == coupon_code and
                              x.get("active", True)), None)
                    if not c:
                        raise ValueError("Codice sconto non valido o scaduto.")

                    today = datetime.now(timezone.utc).date().isoformat()
                    if c.get("expiryDate") and c["expiryDate"] < today:
                        raise ValueError("Il codice sconto è scaduto.")
                    if c.get("startDate") and c["startDate"] > today:
                        raise ValueError("Il codice sconto non è ancora attivo.")
                    if c.get("maxUsesTotal") is not None and c.get("usedCount", 0) >= c["maxUsesTotal"]:
                        raise ValueError("Il codice sconto ha raggiunto il limite di utilizzi.")
                    if c.get("maxUsesPerEmail"):
                        bookings_all = load_bookings()
                        per_email = sum(1 for b in bookings_all
                                        if b.get("couponCode") == coupon_code
                                        and b.get("email") == customer["email"]
                                        and b.get("status") == "paid")
                        if per_email >= c["maxUsesPerEmail"]:
                            raise ValueError("Hai già utilizzato questo codice con questo indirizzo email.")

                    applicable = c.get("applicableWorkshops", ["all"])
                    if "all" not in applicable and workshop_id not in applicable:
                        raise ValueError("Il codice sconto non è applicabile a questo workshop.")

                    if c.get("type") == "percentage":
                        pct = float(c.get("value", 0))
                        raw_disc = round(original_price * pct / 100)
                        max_disc_cents = int(c["maxDiscount"] * 100) if c.get("maxDiscount") else None
                        discount_cents = min(raw_disc, max_disc_cents) if max_disc_cents else raw_disc
                    else:
                        fixed_cents = int(float(c.get("fixedPrice", 0)) * 100)
                        discount_cents = max(0, original_price - fixed_cents)

                    coupon_applied = c

                final_cents  = max(DEPOSIT_CENTS, original_price - discount_cents)
                balance_cents = max(0, final_cents - DEPOSIT_CENTS)

                amount_due_cents = DEPOSIT_CENTS if formula == "caparra" else final_cents
                amount_due_str   = f"{amount_due_cents / 100:.2f}"

                # Create PayPal order
                ws_name = ws.get("title", "Workshop Fotografico") if ws else "Workshop Fotografico"
                paypal_order = _paypal_request("POST", "/v2/checkout/orders", {
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": workshop_id,
                        "description": f"{ws_name} — {'Caparra' if formula == 'caparra' else 'Saldo Completo'}",
                        "amount": {
                            "currency_code": "EUR",
                            "value": amount_due_str,
                        },
                        "custom_id": f"{formula}|{coupon_code}|{customer['email']}",
                    }],
                    "application_context": {
                        "brand_name": "Davide Luongo Photography",
                        "locale": "it-IT",
                        "user_action": "PAY_NOW",
                        "return_url": f"http://localhost:{PORT}/thank-you.html",
                        "cancel_url": f"http://localhost:{PORT}/index.html",
                    },
                })

                order_id = paypal_order["id"]

                # Save pending booking
                existing_ids = [b["id"] for b in load_bookings()]
                bk_num = len(existing_ids) + 1
                bk_id  = f"BK-{bk_num:04d}"

                booking = {
                    "id":                bk_id,
                    "createdAt":         datetime.now(timezone.utc).isoformat(),
                    "status":            "pending",
                    "workshopId":        workshop_id,
                    "workshopName":      ws_name,
                    "firstName":         customer["firstName"],
                    "lastName":          customer["lastName"],
                    "email":             customer["email"],
                    "phone":             customer["phone"],
                    "participants":      customer["participants"],
                    "formula":           formula,
                    "originalCents":     original_price,
                    "discountCents":     discount_cents,
                    "finalCents":        final_cents,
                    "balanceCents":      balance_cents,
                    "amountDueCents":    amount_due_cents,
                    "couponCode":        coupon_code,
                    "paypalOrderId":     order_id,
                    "paypalCaptureId":   None,
                    "paypalEnv":         _PAYPAL_ENV,
                    "balancePaid":       False,
                    "balancePaidMethod": None,
                    "balancePaidDate":   None,
                }
                upsert_booking(booking)

                self._json_ok({"orderId": order_id, "bookingId": bk_id,
                               "amountDue": amount_due_str,
                               "finalPrice": f"{final_cents/100:.2f}",
                               "discountAmount": f"{discount_cents/100:.2f}",
                               "balanceDue": f"{balance_cents/100:.2f}",
                               "formula": formula,
                               "couponApplied": coupon_applied["code"] if coupon_applied else None,
                               })
            except Exception as e:
                self._json_err(str(e))
            return

        # ── Capture PayPal Order (after user approval) ───────────────────────
        elif parsed.path == "/api/capture-paypal-order":
            body = self.rfile.read(content_length)
            try:
                req      = json.loads(body.decode("utf-8"))
                order_id = req.get("orderId", "").strip()
                if not order_id:
                    raise ValueError("orderId mancante.")

                booking = get_booking_by_order_id(order_id)
                if not booking:
                    raise ValueError("Prenotazione non trovata per questo ordine PayPal.")

                # Idempotency: block double capture
                if booking.get("status") == "paid":
                    self._json_ok({"status": "already_paid",
                                   "bookingId": booking["id"]})
                    return

                capture_result = _paypal_request("POST", f"/v2/checkout/orders/{order_id}/capture")

                capture = capture_result.get("purchase_units", [{}])[0] \
                                        .get("payments", {}) \
                                        .get("captures", [{}])[0]
                capture_id     = capture.get("id")
                capture_status = capture.get("status", "")
                captured_amt   = capture.get("amount", {}).get("value", "0.00")

                booking["paypalCaptureId"] = capture_id
                booking["capturedAmount"]  = captured_amt
                booking["status"]          = "paid" if capture_status == "COMPLETED" else "pending"
                booking["paidAt"]          = datetime.now(timezone.utc).isoformat()
                upsert_booking(booking)

                # Consume coupon counter
                if capture_status == "COMPLETED" and booking.get("couponCode"):
                    content = load_content()
                    for c in content.get("coupons", []):
                        if c.get("code", "").upper() == booking["couponCode"].upper():
                            c["usedCount"] = c.get("usedCount", 0) + 1
                            break
                    save_content(content)

                # Decrement workshop seats
                if capture_status == "COMPLETED":
                    content = load_content()
                    for ws in content.get("workshops", []):
                        if ws.get("id") == booking["workshopId"] or \
                           ws.get("title", "").lower() in booking.get("workshopId", "").lower():
                            avail = max(0, ws.get("availableSeats", 8) - 1)
                            ws["availableSeats"] = avail
                            ws["urgencyDisplayedSeats"] = compute_urgency_seats(avail)
                            if avail == 0:
                                ws["status"] = "soldout"
                                ws["statusLabel"] = "Sold Out"
                            break
                    save_content(content)

                # Send confirmation emails
                if capture_status == "COMPLETED":
                    _send_booking_confirmation_emails(booking)

                self._json_ok({"status": booking["status"],
                               "bookingId": booking["id"],
                               "captureId": capture_id,
                               "captured": captured_amt})
            except Exception as e:
                self._json_err(str(e))
            return

        # ── PayPal Webhook (async events) ────────────────────────────────────
        elif parsed.path == "/api/paypal-webhook":
            raw_body = self.rfile.read(content_length)
            try:
                # Verify signature if WEBHOOK_ID is configured
                if _PAYPAL_WEBHOOK_ID:
                    auth_algo = self.headers.get("PAYPAL-AUTH-ALGO", "")
                    cert_url  = self.headers.get("PAYPAL-CERT-URL", "")
                    transmission_id  = self.headers.get("PAYPAL-TRANSMISSION-ID", "")
                    transmission_sig = self.headers.get("PAYPAL-TRANSMISSION-SIG", "")
                    transmission_time= self.headers.get("PAYPAL-TRANSMISSION-TIME", "")
                    # Use PayPal's verification API
                    token = _paypal_get_token()
                    verify_resp = _requests.post(
                        f"{_PAYPAL_BASE}/v1/notifications/verify-webhook-signature",
                        headers={"Authorization": f"Bearer {token}",
                                 "Content-Type": "application/json"},
                        json={
                            "auth_algo": auth_algo,
                            "cert_url": cert_url,
                            "transmission_id": transmission_id,
                            "transmission_sig": transmission_sig,
                            "transmission_time": transmission_time,
                            "webhook_id": _PAYPAL_WEBHOOK_ID,
                            "webhook_event": json.loads(raw_body),
                        },
                        timeout=15,
                    )
                    vd = verify_resp.json()
                    if vd.get("verification_status") != "SUCCESS":
                        self.send_response(400)
                        self.end_headers()
                        return

                event = json.loads(raw_body)
                event_type = event.get("event_type", "")
                resource   = event.get("resource", {})
                order_id   = resource.get("id") or \
                             resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id", "")

                booking = get_booking_by_order_id(order_id) if order_id else None

                STATUS_MAP = {
                    "CHECKOUT.ORDER.APPROVED":        "approved",
                    "PAYMENT.CAPTURE.COMPLETED":      "paid",
                    "PAYMENT.CAPTURE.PENDING":        "pending",
                    "PAYMENT.CAPTURE.DENIED":         "failed",
                    "PAYMENT.CAPTURE.REFUNDED":       "refunded",
                    "CHECKOUT.ORDER.CANCELLED":       "cancelled",
                    "PAYMENT.REFUND-CANCELLED":       "partially_refunded",
                }

                new_status = STATUS_MAP.get(event_type)
                if booking and new_status and booking.get("status") != "paid":
                    booking["status"] = new_status
                    booking["lastWebhookEvent"] = event_type
                    booking["lastWebhookAt"]    = datetime.now(timezone.utc).isoformat()
                    if new_status == "paid" and not booking.get("paypalCaptureId"):
                        booking["paypalCaptureId"] = resource.get("id")
                    upsert_booking(booking)

                # Always respond 200 to PayPal
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_response(200)  # always 200 to PayPal
                self.end_headers()
            return

        # ── Mark Balance as Paid (Admin) ─────────────────────────────────────
        elif parsed.path == "/api/mark-balance-paid":
            body = self.rfile.read(content_length)
            try:
                req        = json.loads(body.decode("utf-8"))
                booking_id = req.get("bookingId", "").strip()
                method     = req.get("method", "contanti")  # bonifico|contanti|paypal

                bookings = load_bookings()
                updated  = False
                for b in bookings:
                    if b["id"] == booking_id:
                        b["balancePaid"]       = True
                        b["balancePaidMethod"] = method
                        b["balancePaidDate"]   = datetime.now(timezone.utc).isoformat()
                        updated = True
                        break
                if not updated:
                    raise ValueError(f"Prenotazione {booking_id} non trovata.")
                save_bookings(bookings)
                self._json_ok({"message": "Saldo segnato come pagato."})
            except Exception as e:
                self._json_err(str(e))
            return

        # ── Legacy book-workshop (kept for backward compat, redirects to new) 
        elif parsed.path == "/api/book-workshop":
            # Redirect old calls — advise frontend to use new endpoints
            self._json_err("Questo endpoint è deprecato. Usa /api/create-paypal-order.")
            return

        # ── Validate Coupon (rate-limited, server-side preview only) ─────────
        elif parsed.path == "/api/validate-coupon":
            body = self.rfile.read(content_length)
            ip = self.client_address[0]
            if not _rate_check(ip, 10):
                self._json_err("Troppe richieste. Attendi un momento.", 429)
                return
            try:
                req         = json.loads(body.decode("utf-8"))
                input_code  = req.get("code", "").strip().upper()
                original_price = float(req.get("originalPrice", 350))
                formula        = req.get("formula", "saldo")
                email          = req.get("email", "").strip().lower()

                data    = load_content()
                coupons = data.get("coupons", [])
                c = next((x for x in coupons if
                          x.get("code", "").strip().upper() == input_code and
                          x.get("active", True)), None)

                if not c:
                    raise ValueError("Codice sconto non valido o non attivo.")

                today = datetime.now(timezone.utc).date().isoformat()
                if c.get("expiryDate") and c["expiryDate"] < today:
                    raise ValueError("Il codice sconto è scaduto.")
                if c.get("startDate") and c["startDate"] > today:
                    raise ValueError("Il codice sconto non è ancora attivo.")
                if c.get("maxUsesTotal") is not None and c.get("usedCount", 0) >= c["maxUsesTotal"]:
                    raise ValueError("Questo codice ha raggiunto il limite massimo di utilizzi.")

                original_cents = round(original_price * 100)
                if c.get("type") == "percentage":
                    pct       = float(c.get("value", 0))
                    raw_d     = round(original_cents * pct / 100)
                    max_d     = int(c["maxDiscount"] * 100) if c.get("maxDiscount") else None
                    disc_cents= min(raw_d, max_d) if max_d else raw_d
                else:
                    fp_cents  = int(float(c.get("fixedPrice", 0)) * 100)
                    disc_cents= max(0, original_cents - fp_cents)

                final_cents   = max(DEPOSIT_CENTS, original_cents - disc_cents)
                balance_cents = max(0, final_cents - DEPOSIT_CENTS)

                pct_label = f"{c.get('value')}%" if c.get("type") == "percentage" else f"→ €{final_cents/100:.0f}"
                msg = f"✅ Codice {input_code} applicato! Sconto: {pct_label} (-€{disc_cents/100:.2f})"
                if formula == "caparra":
                    msg += " Lo sconto si applica al saldo in loco."

                self._json_ok({
                    "code":            input_code,
                    "type":            c.get("type"),
                    "discountCents":   disc_cents,
                    "discountAmount":  f"{disc_cents/100:.2f}",
                    "finalCents":      final_cents,
                    "finalPrice":      f"{final_cents/100:.2f}",
                    "balanceCents":    balance_cents,
                    "balanceDue":      f"{balance_cents/100:.2f}",
                    "message":         msg,
                })
            except Exception as e:
                self._json_err(str(e))
            return

        # ── Save Coupons (Admin) ──────────────────────────────────────────────
        elif parsed.path == "/api/save-coupons":
            body = self.rfile.read(content_length)
            try:
                req          = json.loads(body.decode("utf-8"))
                coupons_list = req.get("coupons", [])
                data         = load_content()
                data["coupons"] = coupons_list
                save_content(data)
                self._json_ok({"message": "Codici sconto salvati con successo!"})
            except Exception as e:
                self._json_err(str(e))
            return

        elif parsed.path == "/api/send-info-email":
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body.decode("utf-8"))
                name = req.get("name")
                email = req.get("email")
                phone = req.get("phone", "Non specificato")
                subject = req.get("subject", "Informazioni Workshop")
                message = req.get("message", "")

                # Store request in data/info_requests.json
                requests_file = ROOT / "data" / "info_requests.json"
                info_requests = []
                if requests_file.exists():
                    try:
                        with open(requests_file, "r", encoding="utf-8") as f:
                            info_requests = json.load(f)
                    except Exception:
                        info_requests = []

                new_req = {
                    "id": f"INF-{len(info_requests)+1:04d}",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "subject": subject,
                    "message": message,
                    "recipient": "info@davideluongo.it"
                }
                info_requests.insert(0, new_req)
                with open(requests_file, "w", encoding="utf-8") as f:
                    json.dump(info_requests, f, ensure_ascii=False, indent=2)

                # Send REAL EMAIL via Aruba SMTP to info@davideluongo.it
                email_body = f"""Nuova Richiesta Informazioni Ricevuta dal Sito Web:

Nome e Cognome: {name}
Email Mittente: {email}
Telefono (WhatsApp): {phone}
Oggetto / Workshop: {subject}

Messaggio:
{message}

---
Inviato in data {new_req['date']} dal Sito Web Davide Luongo.
"""
                success, send_msg = send_real_email_aruba("info@davideluongo.it", f"✉️ Richiesta Info Sito Web: {subject} ({name})", email_body)

                mailto_url = f"mailto:info@davideluongo.it?subject={urllib.parse.quote('Richiesta Info: ' + subject)}&body={urllib.parse.quote('Nome: ' + name + '\nEmail: ' + email + '\nTelefono: ' + phone + '\n\nMessaggio:\n' + message)}"

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": send_msg,
                    "mailtoUrl": mailto_url
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/save-smtp-config":
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body.decode("utf-8"))
                smtp_config = {
                    "smtpUser": req.get("smtpUser", "info@davideluongo.it"),
                    "smtpPassword": req.get("smtpPassword", ""),
                    "smtpHost": req.get("smtpHost", "smtps.aruba.it"),
                    "smtpPort": int(req.get("smtpPort", 465))
                }
                config_file = ROOT / "data" / "smtp_config.json"
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(smtp_config, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Configurazione Aruba SMTP salvata con successo!"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        elif parsed.path == "/api/upload":
            body = self.rfile.read(content_length)
            try:
                content_type = self.headers.get("Content-Type", "")
                page_tag = self.headers.get("X-Page-Tag", "general")
                if "application/json" in content_type:
                    upload_data = json.loads(body.decode("utf-8"))
                    filename = upload_data.get("filename", "upload.jpg")
                    page_tag = upload_data.get("pageTag", page_tag)
                    raw_bytes = base64.b64decode(upload_data.get("base64Data", ""))
                else:
                    filename = self.headers.get("X-File-Name", "upload.jpg")
                    raw_bytes = body

                asset_meta = process_image_srgb(io.BytesIO(raw_bytes), filename, target_page=page_tag)

                data = load_content()
                if "assets" not in data:
                    data["assets"] = []
                data["assets"].insert(0, asset_meta)
                save_content(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "asset": asset_meta}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def main():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, BackendRequestHandler)
    print(f"Davide Luongo Server & Reservation Engine running on http://localhost:{PORT}")
    print(f"Admin Dashboard available at http://localhost:{PORT}/admin")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
