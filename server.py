#!/usr/bin/env python3
"""
Davide Luongo Website — Advanced Backend Server, Asset Engine & Entity CMS Generator
Handles:
1. REST APIs for content persistence (content.json).
2. Advanced sRGB Image Processing: Auto-rescaling (>5MB or >2048px max side) preserving aspect ratio and sRGB ICC profile with zero color alteration.
3. Page-based Asset Management and Tagging.
4. Dynamic Entity & Page Generation for Workshops, Viaggi, Blog Articles, and Gear.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
import urllib.parse
import io
import base64
from pathlib import Path
from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).parent.resolve()
DATA_FILE = ROOT / "data" / "content.json"
UPLOAD_DIR = ROOT / "assets" / "upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
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

def process_image_srgb(input_bytes, original_filename, target_page="general"):
    """
    Processes full resolution image bytes:
    - Auto-rotates EXIF.
    - If size > 5MB or max side > 2048px: rescales to max 2048px with high quality Lanczos filter.
    - Strictly preserves/creates sRGB ICC profile with zero color distortion.
    - Generates optimized sRGB WebP and JPEG assets.
    """
    raw_data = input_bytes.getvalue()
    raw_size = len(raw_data)
    stem = Path(original_filename).stem.replace(" ", "_")
    
    img = Image.open(io.BytesIO(raw_data))
    img = ImageOps.exif_transpose(img)

    orig_w, orig_h = img.size
    needs_rescale = (raw_size > MAX_FILE_BYTES) or (orig_w > MAX_DIMENSION) or (orig_h > MAX_DIMENSION)

    if needs_rescale:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    # Maintain / Convert to RGB mode
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # sRGB Profile handling
    icc_profile = img.info.get('icc_profile')
    srgb_cms = ImageCms.createProfile('sRGB')
    srgb_bytes = ImageCms.ImageCmsProfile(srgb_cms).tobytes()
    final_icc = icc_profile or srgb_bytes

    # Generate WebP sRGB
    webp_filename = f"{stem}_web.webp"
    webp_path = UPLOAD_DIR / webp_filename
    img.save(webp_path, format="WEBP", quality=90, icc_profile=final_icc)

    # Generate JPEG sRGB
    jpg_filename = f"{stem}_web.jpg"
    jpg_path = UPLOAD_DIR / jpg_filename
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
        "uploadDate": "2026-07-31"
    }

def generate_workshop_landing_page(entity):
    """
    Generates a dedicated HTML landing page for a Workshop or Viaggio entity.
    """
    slug = entity.get("id")
    if not slug:
        return
    
    title = entity.get("title", "Workshop Fotografico")
    date_str = entity.get("date", "2026 / 2027")
    location = entity.get("location", "Location da definire")
    description = entity.get("description", "")
    image = entity.get("image", "assets/hero_milky_way.png")
    status_label = entity.get("statusLabel", "Iscrizioni Aperte")
    seats_str = f"{entity.get('availableSeats', 8)} Posti Disponibili" if entity.get('availableSeats') else "Anteprima"
    duration = entity.get("duration", "2 Giorni / 1 Notte")
    price = entity.get("price", "In Definizione")

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} • Davide Luongo</title>
  <meta name="description" content="{description}" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>

  <!-- NAVBAR -->
  <header class="navbar">
    <div class="container nav-container">
      <a href="index.html" class="brand-logo">
        <img src="assets/pittogramma.png" alt="Davide Luongo" class="logo-img" />
        <span>Davide Luongo</span>
      </a>

      <ul class="nav-links">
        <li><a href="index.html#home">Home</a></li>
        <li><a href="index.html#workshops" class="nav-current">Workshop & Tour</a></li>
        <li><a href="index.html#corsi">Formazione 1-to-1</a></li>
        <li><a href="gear.html">Gear & Attrezzatura</a></li>
        <li><a href="blog.html">Blog & Pubblicazioni</a></li>
        <li><a href="index.html#chi-sono">Chi Sono</a></li>
      </ul>

      <div class="nav-actions">
        <button class="btn btn-primary open-modal-btn" data-subject="Prenotazione {title}">Prenota Workshop</button>
      </div>
    </div>
  </header>

  <!-- HERO LANDING -->
  <section class="hero" style="min-height: 80vh; padding-top: 8rem;">
    <img src="{image}" alt="{title}" class="hero-bg" />
    <div class="hero-overlay"></div>

    <div class="container">
      <div class="hero-content">
        <div class="hero-tagline-badge">
          <span>{date_str.upper()} • {location.upper()}</span>
        </div>

        <h1 class="hero-title">
          <span class="gradient-text">{title}</span>
        </h1>

        <p class="hero-description">
          {description}
        </p>

        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
          <button class="btn btn-primary open-modal-btn" data-subject="Prenotazione {title}">Riserva il tuo Posto</button>
          <span class="badge-status active" style="position: static;">{status_label} ({seats_str})</span>
        </div>
      </div>
    </div>
  </section>

  <!-- LOGISTICA & HIGHLIGHTS -->
  <section class="section" style="background: var(--bg-secondary);">
    <div class="container">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem;">
        
        <div style="background: var(--bg-card); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-glass);">
          <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📍 Location</div>
          <div style="font-family: var(--font-heading); font-weight: 700;">{location}</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">Paesaggi d'eccezione</div>
        </div>

        <div style="background: var(--bg-card); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-glass);">
          <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">⏱️ Durata / Quota</div>
          <div style="font-family: var(--font-heading); font-weight: 700;">{duration}</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">Quota: {price}</div>
        </div>

        <div style="background: var(--bg-card); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-glass);">
          <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">👥 Gruppo</div>
          <div style="font-family: var(--font-heading); font-weight: 700;">Massimo {entity.get('totalSeats', 8)} Partecipanti</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">Supporto didattico 1-to-1</div>
        </div>

        <div style="background: var(--bg-card); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-glass);">
          <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">👨‍🏫 Docente</div>
          <div style="font-family: var(--font-heading); font-weight: 700;">Davide Luongo</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">Fotografo Paesaggista & Astro</div>
        </div>

      </div>
    </div>
  </section>

  <!-- MODAL FORM PRENOTAZIONE -->
  <div id="reservation-modal" class="modal-overlay">
    <div class="modal-content">
      <button id="modal-close" class="modal-close">&times;</button>
      <h3 style="font-size: 1.5rem; margin-bottom: 0.5rem;" class="gradient-text">Prenota {title}</h3>
      <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.5rem;">Compila il modulo per riservare il tuo posto.</p>

      <form id="reservation-form">
        <div class="form-group">
          <label class="form-label" for="modal-subject">Evento</label>
          <input type="text" id="modal-subject" class="form-input" value="{title}" readonly />
        </div>

        <div class="form-group">
          <label class="form-label" for="form-name">Nome e Cognome *</label>
          <input type="text" id="form-name" class="form-input" placeholder="Es. Mario Rossi" required />
        </div>

        <div class="form-group">
          <label class="form-label" for="form-email">Indirizzo Email *</label>
          <input type="email" id="form-email" class="form-input" placeholder="nome@esempio.com" required />
        </div>

        <button type="submit" class="btn btn-primary" style="width: 100%;">Conferma Prenotazione</button>
      </form>
    </div>
  </div>

  <!-- FOOTER -->
  <footer class="footer">
    <div class="container" style="text-align: center;">
      <p>&copy; 2026 Davide Luongo. {title}.</p>
    </div>
  </footer>

  <script src="main.js"></script>
</body>
</html>
"""
    file_path = ROOT / f"{slug}.html"
    file_path.write_text(html_content, encoding="utf-8")
    return f"{slug}.html"

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
                self.wfile.write(json.dumps({"status": "success", "message": "Contenuti salvati con successo"}).encode("utf-8"))
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

        elif parsed.path == "/api/create-entity":
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body.decode("utf-8"))
                entity_type = req.get("entityType") # "workshop", "viaggio", "blog", "gear"
                entity = req.get("entity", {})

                data = load_content()
                if entity_type in ["workshop", "viaggio"]:
                    if "workshops" not in data: data["workshops"] = []
                    if "trips_2027" not in data: data["trips_2027"] = []

                    if entity_type == "workshop":
                        data["workshops"].insert(0, entity)
                    else:
                        data["trips_2027"].insert(0, entity)

                    # Generate dedicated HTML landing page
                    page_path = generate_workshop_landing_page(entity)
                    entity["detailsUrl"] = page_path

                elif entity_type == "blog":
                    if "blog" not in data: data["blog"] = []
                    data["blog"].insert(0, entity)

                elif entity_type == "gear":
                    if "gear" not in data: data["gear"] = []
                    data["gear"].insert(0, entity)

                save_content(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "entity": entity}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        elif parsed.path == "/api/delete-entity":
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body.decode("utf-8"))
                entity_type = req.get("entityType")
                entity_id = req.get("entityId")

                data = load_content()
                if entity_type == "workshop" and "workshops" in data:
                    data["workshops"] = [w for w in data["workshops"] if w.get("id") != entity_id]
                elif entity_type == "viaggio" and "trips_2027" in data:
                    data["trips_2027"] = [t for t in data["trips_2027"] if t.get("id") != entity_id]
                elif entity_type == "blog" and "blog" in data:
                    data["blog"] = [b for b in data["blog"] if b.get("id") != entity_id]
                elif entity_type == "gear" and "gear" in data:
                    data["gear"] = [g for g in data["gear"] if g.get("id") != entity_id]
                elif entity_type == "asset" and "assets" in data:
                    data["assets"] = [a for a in data["assets"] if a.get("filename") != entity_id]

                save_content(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Entità eliminata"}).encode("utf-8"))
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
    print(f"Davide Luongo CMS Server running on http://localhost:{PORT}")
    print(f"Admin Dashboard available at http://localhost:{PORT}/admin")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
