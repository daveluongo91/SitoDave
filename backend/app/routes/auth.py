"""
backend/app/routes/auth.py
Login a due fasi (Password + OTP Email / Codice Recupero), logout, me, cambio password, sessioni attive.
Sessioni server-side con cookie HttpOnly/Secure/SameSite=Lax.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.config.settings import settings
from backend.app.middleware.auth import get_admin_user
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import generate_csrf_token, verify_csrf
from backend.app.middleware.rate_limit import check_rate_limit
from backend.app.models.user import User
from backend.app.models.session import UserSession
from backend.app.services.auth_service import (
    AuthError,
    authenticate_user,
    create_session,
    get_current_user,
    hash_password,
    invalidate_all_sessions,
    invalidate_session,
    verify_password,
)
from backend.app.services.otp_service import (
    generate_and_send_login_otp,
    verify_login_otp_or_recovery,
    generate_recovery_codes_for_user,
    OTP_EXPIRY_MINUTES,
    OTP_COOLDOWN_SECONDS,
)

router = APIRouter(prefix="/api/admin/auth", tags=["auth"])

SESSION_COOKIE = "admin_session"
CSRF_COOKIE = "csrf_token"

# ── Schemas ──────────────────────────────────────────────────────────────────

class LoginPhase1Request(BaseModel):
    username: str
    password: str

    @field_validator("username", "password")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obbligatorio.")
        return v.strip()


class LoginPhase2Request(BaseModel):
    challengeToken: str
    otpCode: str  # 6-digit OTP oppure codice di recupero

    @field_validator("challengeToken", "otpCode")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obbligatorio.")
        return v.strip()


class ResendOtpRequest(BaseModel):
    challengeToken: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("La nuova password deve avere almeno 12 caratteri.")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login-phase1")
async def login_phase1(
    request: Request,
    body: LoginPhase1Request,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    """
    Fase 1: Verifica username e password.
    Se corretti, genera challenge temporanea e invia codice OTP via email.
    NON crea alcuna sessione né rilascia cookie admin.
    """
    ip = request.client.host if request.client else "unknown"

    try:
        user = authenticate_user(db, body.username, body.password)
    except AuthError:
        # Risposta generica per sicurezza
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
        )

    try:
        challenge_token, masked_email = generate_and_send_login_otp(db, user, ip=ip)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    log_action(db, "login_phase1_success", user_id=user.id, ip=ip)

    return {
        "status": "otp_required",
        "challengeToken": challenge_token,
        "expiresIn": OTP_EXPIRY_MINUTES * 60,
        "cooldownSeconds": OTP_COOLDOWN_SECONDS,
        "emailMasked": masked_email,
        "message": f"Codice di verifica inviato all'indirizzo {masked_email}.",
    }


@router.post("/login-phase2")
async def login_phase2(
    request: Request,
    body: LoginPhase2Request,
    response: Response,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    """
    Fase 2: Verifica codice OTP a 6 cifre o codice di recupero.
    Se valido, crea la sessione, imposta i cookie HttpOnly e ruota il token CSRF.
    """
    ip = request.client.host if request.client else "unknown"

    try:
        user = verify_login_otp_or_recovery(db, body.challengeToken, body.otpCode)
    except ValueError as e:
        log_action(db, "login_phase2_failure", resource_type="otp", details={"error": str(e)}, ip=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Crea nuova sessione amministrativa (Session rotation)
    session_id = create_session(db, user, ip=ip, user_agent=request.headers.get("User-Agent"))
    csrf_token = generate_csrf_token()

    log_action(db, "login_success_2fa", user_id=user.id, ip=ip)

    # Cookie session: HttpOnly, Secure (in produzione), SameSite=Lax
    is_prod = settings.app_env == "production"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.session_lifetime_hours * 3600,
        path="/",
    )
    # Cookie CSRF: leggibile da JS (no HttpOnly), Secure in produzione
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=is_prod,
        samesite="lax",
        max_age=settings.session_lifetime_hours * 3600,
        path="/",
    )

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


@router.post("/resend-otp")
async def resend_otp(
    request: Request,
    body: ResendOtpRequest,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    """Re-invia il codice OTP rispettando il cooldown di 60 secondi."""
    user = db.query(User).filter(User.otp_challenge_token == body.challengeToken).first()
    if not user:
        raise HTTPException(status_code=400, detail="Challenge non valida o scaduta.")

    ip = request.client.host if request.client else "unknown"
    try:
        challenge_token, masked_email = generate_and_send_login_otp(db, user, ip=ip)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    return {
        "status": "ok",
        "challengeToken": challenge_token,
        "expiresIn": OTP_EXPIRY_MINUTES * 60,
        "cooldownSeconds": OTP_COOLDOWN_SECONDS,
        "emailMasked": masked_email,
        "message": "Nuovo codice inviato.",
    }


# Retrocompatibilità per test o chiamate dirette
@router.post("/login")
async def login(
    request: Request,
    body: LoginPhase1Request,
    response: Response,
    db: Session = Depends(get_db),
    _rate: None = Depends(check_rate_limit),
):
    """Login fallback diretto (usato se 2FA non è configurata o in ambienti di test specifici)."""
    return await login_phase1(request, body, db, _rate)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(
    request: Request,
    response: Response,
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    """Logout: invalida la sessione e cancella i cookie."""
    if session_id:
        user = get_current_user(db, session_id)
        if user:
            log_action(db, "logout", user_id=user.id, ip=request.client.host if request.client else None)
        invalidate_session(db, session_id)

    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "ok"}


@router.get("/me")
async def me(current_user: User = Depends(get_admin_user)):
    """Restituisce dati dell'utente corrente (senza password hash)."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "lastLogin": current_user.last_login,
        "hasRecoveryCodes": bool(current_user.recovery_codes_hash),
        "lastPasswordChange": current_user.last_password_change_at,
    }


@router.post("/generate-recovery-codes", dependencies=[Depends(verify_csrf)])
async def generate_recovery_codes(
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Genera 8 codici di recupero monouso. Mostrati solo una volta."""
    codes = generate_recovery_codes_for_user(db, current_user)
    log_action(db, "recovery_codes_generated", user_id=current_user.id, ip=request.client.host if request.client else None)
    return {
        "status": "ok",
        "codes": codes,
        "message": "Salva questi codici in un luogo sicuro offline. Ciascun codice può essere usato una sola volta.",
    }


@router.get("/sessions")
async def list_active_sessions(
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Elenco sessioni attive dell'utente autenticato (senza token)."""
    now = datetime.now(timezone.utc).isoformat()
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.expires_at > now,
    ).order_by(desc(UserSession.created_at)).all()

    return {
        "sessions": [
            {
                "id": s.id[:8] + "...",
                "isCurrent": (s.id == session_id),
                "ip": s.ip or "N/A",
                "userAgent": s.user_agent or "N/A",
                "createdAt": s.created_at,
                "lastActivity": s.created_at,
                "expiresAt": s.expires_at,
            }
            for s in sessions
        ]
    }


@router.delete("/sessions", dependencies=[Depends(verify_csrf)])
async def revoke_other_sessions(
    request: Request,
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Revoca tutte le altre sessioni attive ad eccezione di quella corrente."""
    if session_id:
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.id != session_id,
        ).delete()
        db.commit()
        log_action(db, "revoke_other_sessions", user_id=current_user.id, ip=request.client.host if request.client else None)

    return {"status": "ok", "message": "Tutte le altre sessioni sono state revocate."}


@router.post("/change-password", dependencies=[Depends(verify_csrf)])
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
):
    """Cambio password: invalida tutte le sessioni esistenti."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Password corrente non valida.")

    now = datetime.now(timezone.utc).isoformat()
    current_user.password_hash = hash_password(body.new_password)
    current_user.last_password_change_at = now
    db.commit()

    # Invalida tutte le sessioni (forza re-login)
    invalidate_all_sessions(db, current_user.id)

    log_action(
        db, "password_changed",
        user_id=current_user.id,
        ip=request.client.host if request.client else None,
    )

    return {"status": "ok", "message": "Password aggiornata. Effettua nuovamente il login."}