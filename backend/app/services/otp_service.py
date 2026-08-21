"""
backend/app/services/otp_service.py
Gestione 2FA: generazione OTP sicuro, calcolo HMAC, verifica temporalmente sicura,
invio email, gestione cooldown, limitazione tentativi e codici di recupero monouso.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from backend.app.config.settings import settings
from backend.app.models.user import User
from backend.app.services.email_service import send_email


OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 60
NUM_RECOVERY_CODES = 8


def _get_hmac_key() -> bytes:
    """Restituisce la chiave segreta per l'HMAC dell'OTP."""
    key = settings.secret_key or "sito_dave_default_hmac_secret_key_2026"
    return key.encode("utf-8")


def hash_otp(otp_code: str, salt: str) -> str:
    """Calcola l'HMAC-SHA256 dell'OTP con sale (challenge_token)."""
    h = hmac.new(_get_hmac_key(), f"{otp_code}:{salt}".encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def verify_otp_code(stored_hash: str, input_otp: str, salt: str) -> bool:
    """Confronto crittograficamente sicuro a tempo costante per evitare timing attacks."""
    if not stored_hash or not input_otp or not salt:
        return False
    expected_hash = hash_otp(input_otp.strip(), salt)
    return hmac.compare_digest(stored_hash, expected_hash)


def mask_email(email: str) -> str:
    """Maschera l'indirizzo email per la visualizzazione sicura (es. i***@davideluongo.it)."""
    if not email or "@" not in email:
        return "***@***"
    parts = email.split("@")
    name, domain = parts[0], parts[1]
    if len(name) <= 2:
        masked_name = name[0] + "***"
    else:
        masked_name = name[0] + "***" + name[-1]
    return f"{masked_name}@{domain}"


def generate_and_send_login_otp(db: Session, user: User, ip: str = "") -> Tuple[str, str]:
    """
    Genera un OTP a 6 cifre crittograficamente sicuro, salva l'HMAC e invia l'email.
    Restituisce (challenge_token, masked_email).
    """
    now = datetime.now(timezone.utc)
    
    # Verifica cooldown
    if user.otp_cooldown_until:
        try:
            cooldown_dt = datetime.fromisoformat(user.otp_cooldown_until)
            if now < cooldown_dt:
                rem_sec = int((cooldown_dt - now).total_seconds())
                raise ValueError(f"Attendi ancora {rem_sec} secondi prima di richiedere un nuovo codice.")
        except (ValueError, TypeError):
            pass

    # Genera OTP a 6 cifre (da 100000 a 999999)
    raw_otp = f"{secrets.randbelow(900000) + 100000:06d}"
    challenge_token = secrets.token_urlsafe(32)
    expires_at = (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    cooldown_until = (now + timedelta(seconds=OTP_COOLDOWN_SECONDS)).isoformat()

    # Salva HMAC dell'OTP
    user.otp_challenge_token = challenge_token
    user.otp_hash = hash_otp(raw_otp, challenge_token)
    user.otp_expires_at = expires_at
    user.otp_cooldown_until = cooldown_until
    user.otp_failed_attempts = 0
    db.commit()

    # Destinatario OTP (configurato o email admin)
    recipient = getattr(settings, "admin_otp_email", None) or user.email or settings.aruba_smtp_user

    # Invia email con il codice
    email_subject = f"🔐 Codice di Accesso Amministrazione: {raw_otp}"
    email_body = (
        f"Ciao Davide,\n\n"
        f"Ecco il tuo codice di verifica monouso per accedere all'Admin di SitoDave:\n\n"
        f"  CODICE DI ACCESSO: {raw_otp}\n\n"
        f"Questo codice è valido per {OTP_EXPIRY_MINUTES} minuti e può essere usato una sola volta.\n"
        f"Richiesta effettuata il {now.strftime('%d/%m/%Y alle %H:%M UTC')} da IP: {ip or 'Non disponibile'}.\n\n"
        f"Se non hai richiesto tu questo accesso, ignora questa email e controlla la sicurezza del tuo account.\n\n"
        f"Davide Luongo Photography"
    )

    send_email(recipient, email_subject, email_body)

    return challenge_token, mask_email(recipient)


def verify_login_otp_or_recovery(db: Session, challenge_token: str, code_input: str) -> User:
    """
    Verifica il codice OTP o un codice di recupero monouso.
    Se valido, consuma il codice e azzera la challenge.
    """
    if not challenge_token or not code_input:
        raise ValueError("Token challenge o codice mancante.")

    user = db.query(User).filter(User.otp_challenge_token == challenge_token).first()
    if not user:
        raise ValueError("Sessione di verifica non valida o scaduta.")

    now = datetime.now(timezone.utc)

    # 1. Verifica se è un codice di recupero (8-10 caratteri alfanumerici)
    cleaned_input = code_input.strip().upper()
    if len(cleaned_input) >= 8 and user.recovery_codes_hash:
        try:
            hashes = json.loads(user.recovery_codes_hash)
            input_hash = hashlib.sha256(cleaned_input.encode("utf-8")).hexdigest()
            if input_hash in hashes:
                # Codice di recupero valido! Rimuovilo (monouso)
                hashes.remove(input_hash)
                user.recovery_codes_hash = json.dumps(hashes)
                user.otp_challenge_token = None
                user.otp_hash = None
                user.otp_expires_at = None
                user.otp_failed_attempts = 0
                db.commit()
                return user
        except Exception:
            pass

    # 2. Verifica scadenza OTP
    if not user.otp_expires_at:
        raise ValueError("Nessun codice OTP attivo. Richiedi un nuovo codice.")

    try:
        exp_dt = datetime.fromisoformat(user.otp_expires_at)
        if now > exp_dt:
            raise ValueError("Il codice OTP è scaduto. Richiedine uno nuovo.")
    except (ValueError, TypeError):
        raise ValueError("Data di scadenza non valida.")

    # 3. Verifica tentativi falliti
    if user.otp_failed_attempts >= OTP_MAX_ATTEMPTS:
        user.otp_challenge_token = None
        user.otp_hash = None
        user.otp_expires_at = None
        db.commit()
        raise ValueError(f"Troppi tentativi errati ({OTP_MAX_ATTEMPTS}). La richiesta è stata bloccata. Riavvia il login.")

    # 4. Verifica codice OTP
    if not verify_otp_code(user.otp_hash, cleaned_input, challenge_token):
        user.otp_failed_attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - user.otp_failed_attempts
        raise ValueError(f"Codice OTP errato. Tentativi rimasti: {max(0, remaining)}.")

    # Successo: consuma l'OTP
    user.otp_challenge_token = None
    user.otp_hash = None
    user.otp_expires_at = None
    user.otp_failed_attempts = 0
    db.commit()

    return user


def generate_recovery_codes_for_user(db: Session, user: User) -> List[str]:
    """Genera una nuova serie di codici di recupero monouso e ne salva l'hash nel DB."""
    plain_codes = []
    hashed_codes = []
    for _ in range(NUM_RECOVERY_CODES):
        code = secrets.token_hex(4).upper()  # 8 caratteri hex
        plain_codes.append(code)
        hashed_codes.append(hashlib.sha256(code.encode("utf-8")).hexdigest())

    user.recovery_codes_hash = json.dumps(hashed_codes)
    db.commit()
    return plain_codes