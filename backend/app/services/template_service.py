"""
backend/app/services/template_service.py
Gestione template dichiarativi e versionati (workshop-v1, international-trip-v1),
validazione pre-pubblicazione, controlli di completezza e generazione deterministica.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.workshop import Workshop

# ── 1. Schemi Template Versionati ─────────────────────────────────────────────

TEMPLATES = {
    "workshop-v1": {
        "version": "workshop-v1",
        "name": "Workshop Fotografico Standard",
        "experienceType": "workshop",
        "description": "Template per workshop nazionali sul campo di 1-4 giorni.",
        "mandatoryFields": [
            "title", "slug", "startDate", "endDate", "location", "priceCents", "totalSeats"
        ],
        "mandatoryBlocks": ["seo", "hero", "quick_facts", "presentation", "itinerary", "included_excluded", "faq", "cta_final"],
        "allowedBlocks": [
            "seo", "hero", "quick_facts", "presentation", "highlights", "gallery",
            "itinerary", "included_excluded", "requirements", "equipment", "instructors",
            "logistics", "weather", "pricing_policy", "faq", "cta_final"
        ],
    },
    "international-trip-v1": {
        "version": "international-trip-v1",
        "name": "Viaggio Fotografico Internazionale",
        "experienceType": "international_trip",
        "description": "Template per viaggi e spedizioni fotografiche all'estero con gestione tour operator e logistica voli.",
        "mandatoryFields": [
            "title", "slug", "startDate", "endDate", "country", "destination",
            "priceCents", "totalSeats", "technicalOperator", "documentsRequired"
        ],
        "mandatoryBlocks": ["seo", "hero", "quick_facts", "presentation", "travel_logistics", "itinerary", "included_excluded", "faq", "legal_disclaimer", "cta_final"],
        "allowedBlocks": [
            "seo", "hero", "quick_facts", "presentation", "highlights", "gallery",
            "travel_logistics", "flight_info", "itinerary", "included_excluded",
            "requirements", "equipment", "instructors", "accommodation", "weather",
            "pricing_policy", "faq", "legal_disclaimer", "cta_final"
        ],
    },
}


# ── 2. Controlli Pre-Pubblicazione ───────────────────────────────────────────

_FORBIDDEN_PLACEHOLDERS = [
    r"\[DA COMPILARE\]", r"\[TODO\]", r"\[TBD\]", r"LOREM IPSUM",
    r"PLACEHOLDER", r"XXX", r"TEST TEST", r"INSERISCI QUI"
]

_SECRET_PATTERNS = [
    r"(?i)sk_live_[0-9a-zA-Z]{24,}",
    r"(?i)access_token\$production\$[0-9a-zA-Z]+",
    r"(?i)AKIA[0-9A-Z]{16}",
    r"(?i)password\s*=\s*['\"][^'\"]{6,}['\"]",
]


def validate_experience_for_publication(
    data: Dict[str, Any],
    blocks: Optional[List[Dict[str, Any]]] = None,
    existing_slugs: Optional[List[str]] = None,
    current_id: Optional[int] = None,
) -> Tuple[bool, List[str], List[str]]:
    """
    Esegue tutti i controlli di integrità prima della pubblicazione.
    Restituisce (is_valid, errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []

    exp_type = data.get("experienceType") or "workshop"
    tmpl_ver = data.get("templateVersion") or ("international-trip-v1" if exp_type == "international_trip" else "workshop-v1")
    template = TEMPLATES.get(tmpl_ver, TEMPLATES["workshop-v1"])

    # 1. Controllo Slug
    slug = (data.get("slug") or "").strip().lower()
    if not slug:
        errors.append("Lo slug della pagina è obbligatorio.")
    elif not re.fullmatch(r"[a-z0-9-_]{3,128}", slug):
        errors.append("Lo slug può contenere solo lettere minuscole, numeri, trattini e underscore (3-128 caratteri).")
    elif existing_slugs and slug in existing_slugs:
        errors.append(f"Lo slug '{slug}' è già utilizzato da un'altra pagina.")

    # 2. Controllo Titolo
    title = (data.get("title") or "").strip()
    if not title:
        errors.append("Il titolo dell'esperienza è obbligatorio.")
    elif len(title) < 5:
        errors.append("Il titolo deve contenere almeno 5 caratteri.")

    # 3. Controllo Date
    start_date = data.get("startDate") or ""
    end_date = data.get("endDate") or ""
    if not start_date:
        errors.append("La data di inizio è obbligatoria.")
    if end_date and start_date and end_date < start_date:
        errors.append("La data di fine non può essere precedente alla data di inizio.")

    # 4. Controllo Prezzi e Posti
    price_cents = data.get("priceCents")
    if price_cents is None or price_cents <= 0:
        errors.append("Il prezzo deve essere maggiore di zero.")
    
    total_seats = data.get("totalSeats")
    if total_seats is None or total_seats <= 0:
        errors.append("Il numero di posti totali deve essere maggiore di zero.")

    # 5. Controllo Campi Obbligatori da Template
    for field in template["mandatoryFields"]:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            field_name_it = {
                "location": "Location / Luogo di ritrovo",
                "country": "Paese di destinazione",
                "destination": "Località / Destinazione",
                "technicalOperator": "Tour Operator / Agenzia Tecnica",
                "documentsRequired": "Documenti richiesti per l'espatrio",
            }.get(field, field)
            errors.append(f"Il campo '{field_name_it}' è obbligatorio per il template {template['name']}.")

    # 6. Controllo Note Legali per Viaggi Internazionali
    if exp_type == "international_trip":
        if not data.get("technicalOperator"):
            errors.append("Per i viaggi internazionali è obbligatorio specificare il Tour Operator o l'Agenzia Viaggi autorizzata.")

    # 7. Scansione Testi per Placeholder e Segreti
    all_text_to_scan = json.dumps(data, ensure_ascii=False)
    if blocks:
        all_text_to_scan += " " + json.dumps(blocks, ensure_ascii=False)

    for pattern in _FORBIDDEN_PLACEHOLDERS:
        if re.search(pattern, all_text_to_scan, re.IGNORECASE):
            errors.append(f"Trovato testo placeholder non approvato corrispondente a '{pattern}'. Compila tutti i contenuti prima di pubblicare.")
            break

    for sec_pat in _SECRET_PATTERNS:
        if re.search(sec_pat, all_text_to_scan):
            errors.append("Rilevato possibile segreto o chiave API all'interno dei testi. Rimuovi le credenziali prima di pubblicare.")
            break

    # 8. Warnings su SEO e Media
    if not data.get("image"):
        warnings.append("Nessuna immagine di copertina (Hero/Social) associata all'esperienza.")
    if not data.get("description") or len(data.get("description", "")) < 30:
        warnings.append("La descrizione breve è molto sintetica; una descrizione più ricca migliora l'indicizzazione.")

    is_valid = (len(errors) == 0)
    return is_valid, errors, warnings


# ── 3. Generazione Deterministica HTML ───────────────────────────────────────

def render_deterministic_page_html(
    workshop: Workshop,
    blocks: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Genera l'HTML deterministico e riproducibile per l'anteprima o la build statica."""
    is_trip = (workshop.experience_type == "international_trip")
    category_badge = "🌍 VIAGGIO INTERNAZIONALE" if is_trip else "🏔️ WORKSHOP NAZIONALE"
    price_fmt = workshop.price_label or f"€{workshop.price_cents // 100}"
    date_fmt = f"{workshop.start_date} - {workshop.end_date}" if workshop.end_date else (workshop.start_date or "")

    itinerary_items = []
    if workshop.day_by_day_itinerary:
        try:
            itinerary_items = json.loads(workshop.day_by_day_itinerary)
        except Exception:
            pass

    itinerary_html = ""
    if itinerary_items:
        itinerary_html = '<div class="itinerary-list" style="margin-top: 1.5rem;">'
        for day in itinerary_items:
            day_num = day.get("day", "Giorno")
            day_title = day.get("title", "")
            day_desc = day.get("desc", "")
            itinerary_html += f"""
            <div class="itinerary-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;">
                <div style="color: var(--accent-cyan); font-weight: 700; font-size: 0.9rem;">{day_num}</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; font-size: 1.1rem;">{day_title}</h4>
                <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6;">{day_desc}</p>
            </div>
            """
        itinerary_html += "</div>"

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{workshop.title} • Davide Luongo</title>
  <meta name="description" content="{workshop.description or workshop.title}">
  <meta name="theme-color" content="#0B1929">
  <link rel="stylesheet" href="../style.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
</head>
<body>
  <!-- Header Globale -->
  <header class="navbar">
    <div class="container nav-container">
      <a href="../index.html" class="brand-logo">
        <img src="../assets/pittogramma.png" alt="Davide Luongo" class="logo-img">
        <span>Davide Luongo</span>
      </a>
      <ul class="nav-links">
        <li><a href="../index.html#home">Home</a></li>
        <li><a href="../index.html#workshops">Workshop & Tour</a></li>
        <li><a href="../one-to-one/one-to-one.html">One to One</a></li>
        <li><a href="../gear/gear.html">Gear</a></li>
        <li><a href="../blog/blog.html">Blog</a></li>
      </ul>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="section" style="padding-top: 8rem; background: radial-gradient(circle at 50% 20%, rgba(0, 240, 255, 0.08) 0%, rgba(11, 25, 41, 0.95) 75%), var(--bg-main);">
    <div class="container" style="max-width: 900px; text-align: center;">
      <span class="badge" style="background: rgba(0,240,255,0.1); color: var(--accent-cyan); border: 1px solid rgba(0,240,255,0.2); padding: 0.35rem 0.85rem; border-radius: 99px; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.1em;">{category_badge}</span>
      <h1 style="font-size: clamp(2rem, 4vw, 3.5rem); margin: 1.25rem 0; line-height: 1.2;">{workshop.title}</h1>
      <p style="font-size: 1.15rem; color: var(--text-secondary); line-height: 1.7; margin-bottom: 2rem;">{workshop.description or ''}</p>
      
      <div style="display: flex; gap: 1.5rem; justify-content: center; flex-wrap: wrap; margin-bottom: 2.5rem;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); border-radius: 8px; padding: 0.75rem 1.25rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Date</div>
          <strong style="color: var(--text-primary);">{date_fmt}</strong>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); border-radius: 8px; padding: 0.75rem 1.25rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Luogo</div>
          <strong style="color: var(--text-primary);">{workshop.destination or workshop.location or 'Italia'}</strong>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); border-radius: 8px; padding: 0.75rem 1.25rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Quota</div>
          <strong style="color: var(--accent-cyan); font-size: 1.15rem;">{price_fmt}</strong>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-glass); border-radius: 8px; padding: 0.75rem 1.25rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Disponibilità</div>
          <strong style="color: {'#4ade80' if workshop.available_seats > 0 else '#ef4444'};">{workshop.available_seats} posti rimasti</strong>
        </div>
      </div>
    </div>
  </section>

  <!-- Programma & Itinerario -->
  <section class="section" style="background: var(--bg-secondary);">
    <div class="container" style="max-width: 860px;">
      <div class="section-header">
        <h2 class="section-title">Programma dell'Esperienza</h2>
      </div>
      {itinerary_html}
    </div>
  </section>

  <!-- Footer Globale -->
  <footer class="footer">
    <div class="container">
      <div class="footer-bottom">
        <div>&copy; 2026 Davide Luongo. P.IVA IT03043130737. Tutti i diritti riservati.</div>
        <div>Designed for High Performance & Astrophotography.</div>
      </div>
    </div>
  </footer>
</body>
</html>"""
    return html