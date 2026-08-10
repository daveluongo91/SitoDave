"""
backend/app/services/auth_service.py
Autenticazione con Argon2id, sessioni server-side, protezione brute-force.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.models.user import User
from backend.app.models.session import UserSession

# Argon2id con parametri conformi alle raccomandazioni OWASP 2024
_ph = PasswordHasher(
    time_cost=3,          # iterazioni
    memory_cost=65536,    # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    encoding="utf-8",
)


# ── Hashing ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Genera hash Argon2id di una password."""
    return _ph.hash(password)


def verify_password(password: str, hash_: str) -> bool:
    """Verifica password contro hash Argon2id. Mai esporre il risultato nei log."""
    try:
        _ph.verify(hash_, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hash_: str) -> bool:
    """Ritorna True se l'hash deve essere rigenerato (parametri aggiornati)."""
    return _ph.check_needs_rehash(hash_)


# ── Brute-force protection ────────────────────────────────────────────────────

def _lockout_until(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def record_failed_attempt(db: Session, user: User) -> None:
    """Incrementa contatore tentativi falliti; blocca se supera il limite."""
    user.failed_attempts = (user.failed_attempts or 0) + 1
    if user.failed_attempts >= settings.admin_login_max_attempts:
        user.locked_until = _lockout_until(settings.admin_lockout_minutes)
    db.commit()


def reset_failed_attempts(db: Session, user: User) -> None:
    """Resetta contatore dopo login riuscito."""
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc).isoformat()
    db.commit()


# ── Login ─────────────────────────────────────────────────────────────────────

class AuthError(Exception):
    """Errore di autenticazione generico (mai rivelare dettagli al client)."""


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User:
    """
    Verifica credenziali. Lancia AuthError in caso di fallimento.
    Il messaggio è sempre generico per evitare user enumeration.
    """
    # Usa timing costante anche se l'utente non esiste
    dummy_hash = hash_password("dummy_constant_timing_password_xz9q")

    user: Optional[User] = (
        db.query(User)
        .filter(User.username == username.strip(), User.is_active.is_(True))
        .first()
    )

    if user is None:
        # Timing costante: verifica la password contro un hash dummy
        verify_password(password, dummy_hash)
        raise AuthError("Credenziali non valide.")

    if user.is_locked():
        raise AuthError("Account temporaneamente bloccato. Riprova più tardi.")

    if not verify_password(password, user.password_hash):
        record_failed_attempt(db, user)
        raise AuthError("Credenziali non valide.")

    # Rigenera hash se i parametri sono cambiati
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    reset_failed_attempts(db, user)
    return user


# ── Sessioni ──────────────────────────────────────────────────────────────────

def create_session(
    db: Session,
    user: User,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """
    Crea una nuova sessione e restituisce il token opaco (UUID v4).
    La sessione va messa in un cookie HttpOnly/Secure/SameSite=Lax.
    """
    session_id = uuid.uuid4().hex  # 32 hex chars, crittograficamente sicuro
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=settings.session_lifetime_hours)
    ).isoformat()

    session = UserSession(
        id=session_id,
        user_id=user.id,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=expires_at,
        ip=ip,
        user_agent=user_agent[:512] if user_agent else None,
        is_active=True,
    )
    db.add(session)
    db.commit()
    return session_id


def get_session(db: Session, session_id: str) -> Optional[UserSession]:
    """Restituisce la sessione se valida e non scaduta."""
    if not session_id:
        return None
    sess = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.is_active.is_(True),
        )
        .first()
    )
    if sess is None:
        return None
    if datetime.now(timezone.utc).isoformat() > sess.expires_at:
        sess.is_active = False
        db.commit()
        return None
    return sess


def get_current_user(db: Session, session_id: str) -> Optional[User]:
    """Restituisce l'utente dalla sessione o None."""
    sess = get_session(db, session_id)
    if not sess:
        return None
    return db.query(User).filter(User.id == sess.user_id, User.is_active.is_(True)).first()


def invalidate_session(db: Session, session_id: str) -> None:
    """Invalida una sessione (logout)."""
    sess = db.query(UserSession).filter(UserSession.id == session_id).first()
    if sess:
        sess.is_active = False
        db.commit()


def invalidate_all_sessions(db: Session, user_id: int) -> None:
    """Invalida tutte le sessioni di un utente (cambio password, compromissione)."""
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active.is_(True),
    ).update({"is_active": False})
    db.commit()


# ── CSRF ──────────────────────────────────────────────────────────────────────

def generate_csrf_token() -> str:
    """Genera un token CSRF crittograficamente sicuro."""
    return secrets.token_hex(settings.csrf_token_length)


def verify_csrf_token(token_from_cookie: str, token_from_header: str) -> bool:
    """Confronto a tempo costante dei token CSRF."""
    if not token_from_cookie or not token_from_header:
        return False
    return secrets.compare_digest(token_from_cookie, token_from_header)
