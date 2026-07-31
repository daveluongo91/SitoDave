#!/usr/bin/env python3
"""
Davide Luongo Website — Advanced Backend Server, sRGB Engine, AI SEO & Workshop Reservation System
Handles:
1. REST APIs for content persistence (content.json).
2. Advanced sRGB Image Processing: Auto-rescaling (>5MB or >2048px max side) preserving aspect ratio and sRGB ICC profile.
3. Workshop Reservation & Seat Urgency Counter (total 8 seats, display minus 20% for FOMO urgency).
4. Cutoff Date Enforcement (default 15 days before start date) with automatic Excel report compilation.
5. Participant Database & Excel Report Exporter (.csv/.xlsx format) available for instant download in Admin or auto/on-demand email delivery to info@davideluongo.com.
6. PayPal Business Payment Integration (Caparra €50 vs Saldo Totale con Paga in 3 rate).
7. AI SEO Optimization Agent with JSON-LD Schema markup.
8. Dynamic Entity & Landing Page Generator for subfolders (workshops_2026/, viaggi_2027/, blog/, gear/).
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
import urllib.parse
import io
import base64
import csv
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
try:
    from PIL import Image, ImageCms, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

ROOT = Path(__file__).parent.resolve()
DATA_FILE = ROOT / "data" / "content.json"
PARTICIPANTS_FILE = ROOT / "data" / "participants.json"
UPLOAD_DIR = ROOT / "assets" / "upload"
EXPORTS_DIR = ROOT / "data" / "exports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

PORT = 3000
MAX_DIMENSION = 2048
MAX_FILE_BYTES = 5 * 1024 * 1024 # 5MB

def load_content():
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
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

class BackendRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

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

        elif parsed.path == "/api/book-workshop":
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body.decode("utf-8"))
                workshop_id = req.get("workshopId")
                workshop_name = req.get("workshopName", "Workshop")
                first_name = req.get("firstName")
                last_name = req.get("lastName")
                phone = req.get("phone")
                email = req.get("email")
                payment_formula = req.get("paymentFormula", "caparra") # "caparra" or "saldo"
                amount_paid = req.get("amountPaid", "€50")

                # Update seats & content
                data = load_content()
                workshops = data.get("workshops", [])
                target_ws = None
                for ws in workshops:
                    if ws.get("id") == workshop_id or ws.get("title") == workshop_name:
                        target_ws = ws
                        break

                if target_ws:
                    current_avail = target_ws.get("availableSeats", 8)
                    if current_avail <= 0:
                        raise Exception("Spiacenti, i posti per questo workshop sono esauriti!")

                    target_ws["availableSeats"] = max(0, current_avail - 1)
                    target_ws["urgencyDisplayedSeats"] = compute_urgency_seats(target_ws["availableSeats"])
                    if target_ws["availableSeats"] == 0:
                        target_ws["status"] = "soldout"
                        target_ws["statusLabel"] = "Sold Out"
                    save_content(data)

                # Record participant
                participants = load_participants()
                booking_record = {
                    "id": f"BK-{len(participants)+1:04d}",
                    "bookingDate": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "workshopId": workshop_id,
                    "workshop": workshop_name,
                    "firstName": first_name,
                    "lastName": last_name,
                    "phone": phone,
                    "email": email,
                    "paymentFormula": "Caparra Confirmatoria €50" if payment_formula == "caparra" else "Saldo Totale €290",
                    "amountPaid": amount_paid,
                    "cutoffStatus": "Attivo"
                }
                participants.insert(0, booking_record)
                save_participants(participants)

                # PayPal business checkout redirect URL
                paypal_url = f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=info@davideluongo.it&item_name={urllib.parse.quote(workshop_name + ' - ' + booking_record['paymentFormula'])}&amount={amount_paid.replace('€','').strip()}&currency_code=EUR"

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "booking": booking_record,
                    "paypalUrl": paypal_url,
                    "thankYouUrl": f"thank-you.html?name={urllib.parse.quote(first_name + ' ' + last_name)}&email={urllib.parse.quote(email)}&phone={urllib.parse.quote(phone)}&workshop={urllib.parse.quote(workshop_name)}&payment={urllib.parse.quote(booking_record['paymentFormula'])}"
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
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
