"""
backend/app/services/email_service.py
Invio email via Aruba SMTP. Nessuna password in chiaro nei log.
"""
from __future__ import annotations

import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from backend.app.config.settings import settings


def send_email(
    recipient_email: str,
    subject: str,
    body_text: str,
    attachment_path: Optional[Path] = None,
) -> tuple[bool, str]:
    """
    Invia una email via Aruba SMTP SSL.
    Restituisce (success: bool, message: str).
    NESSUNA credenziale viene loggata.
    """
    if not settings.aruba_smtp_pass:
        _log(f"SMTP non configurato. Email non inviata per: [REDACTED] (Subject: {subject})")
        return False, "Servizio email temporaneamente non disponibile."

    msg = MIMEMultipart()
    msg["From"] = f"Davide Luongo Website <{settings.aruba_smtp_user}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    if attachment_path and attachment_path.exists():
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{attachment_path.name}"')
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL(
            settings.aruba_smtp_host,
            settings.aruba_smtp_port,
            timeout=15,
        ) as server:
            server.login(settings.aruba_smtp_user, settings.aruba_smtp_pass)
            server.sendmail(settings.aruba_smtp_user, [recipient_email], msg.as_string())

        _log(f"Email inviata via Aruba SMTP a [REDACTED] (Subject: {subject})")
        return True, "Email inviata con successo."

    except Exception as e:
        # NESSUN dato personale nel messaggio di errore
        _log(f"Errore SMTP Aruba (Subject: {subject}): {type(e).__name__}")
        return False, f"Errore invio email: {type(e).__name__}"


def _log(message: str) -> None:
    """Scrive nel log email (senza dati personali)."""
    log_file = settings.logs_dir / "emails.log"
    timestamp = datetime.utcnow().isoformat()
    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Il log non deve mai bloccare il flusso principale


def send_booking_confirmation(booking: dict) -> None:
    """Invia conferma prenotazione al cliente e notifica admin."""
    formula = booking.get("formula", "caparra")
    name = f"{booking.get('firstName', '')} {booking.get('lastName', '')}".strip()
    ws_name = booking.get("workshopName", "Workshop")
    final_eur = (booking.get("finalCents", 0) or 0) / 100
    balance_eur = (booking.get("balanceCents", 0) or 0) / 100
    is_friuli = booking.get("workshopId") == "friuli-2026"
    extra_day_selected = bool(booking.get("extraDay"))
    extra_day_note = "Sì, da venerdì 9 ottobre (+€100)" if extra_day_selected else "No, dal sabato 10 ottobre"
    client_extra_day_line = f"Arrivo anticipato: {extra_day_note}\n" if is_friuli else ""
    admin_extra_day_line = f"Dal venerdì     : {extra_day_note}\n" if is_friuli else ""
    coupon_note = f" (codice: {booking['couponCode']})" if booking.get("couponCode") else ""

    if formula == "caparra":
        client_body = (
            f"Ciao {booking.get('firstName', '')},\n\n"
            f"Abbiamo ricevuto la tua caparra di €50{coupon_note} per il workshop:\n\n"
            f"▸ {ws_name}\n\n"
            f"{client_extra_day_line}"
            f"Prezzo finale: €{final_eur:.2f}\n"
            f"Saldo residuo: €{balance_eur:.2f} (in loco: bonifico, contanti o PayPal)\n\n"
            "Per informazioni rispondi a questa email.\n\n"
            "Davide Luongo\ninfo@davideluongo.it"
        )
    else:
        client_body = (
            f"Ciao {booking.get('firstName', '')},\n\n"
            f"Abbiamo ricevuto il pagamento completo di €{final_eur:.2f}{coupon_note} per:\n\n"
            f"▸ {ws_name}\n\n"
            f"{client_extra_day_line}"
            "Non risultano importi residui.\n\n"
            "Davide Luongo\ninfo@davideluongo.it"
        )

    bk_id = booking.get("id", "N/D")
    admin_body = (
        f"Nuova prenotazione CONFERMATA\n\n"
        f"ID Prenotazione : {bk_id}\n"
        f"Workshop        : {ws_name}\n"
        f"Formula         : {'Caparra €50' if formula == 'caparra' else 'Pagamento completo'}\n"
        f"{admin_extra_day_line}"
        f"Prezzo finale   : €{final_eur:.2f}\n"
        f"Codice sconto   : {booking.get('couponCode') or 'Nessuno'}\n"
    )

    send_email(
        booking.get("email", ""),
        f"✅ Prenotazione confermata — {ws_name}",
        client_body,
    )
    send_email(
        settings.aruba_smtp_user,
        f"🔔 NUOVA PRENOTAZIONE [{bk_id}] — {ws_name}",
        admin_body,
    )
