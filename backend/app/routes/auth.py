"""
backend/app/routes/auth.py
Login, logout, me, cambio password.
Sessioni server-side con cookie HttpOnly/Secure/SameSite=Lax.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.config.settings import settings
from backend.app.middleware.auth import get_admin_user
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import generate_csrf_token
from backend.app.models.user import User
from backend.app.services.auth_service import (
    AuthError,
    authenticate_user,
    create_session,
    get_current_user,
    hash_password,
    invalidate_all_sessions,
    invalidate_session,
)

router = APIRouter(prefix="/api/admin/auth", tags=["auth"])

SESSION_COOKIE = "admin_session"
CSRF_COOKIE = "csrf_token"

# ── Schemas ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username", "password")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obbligatorio.")
        return v.strip()


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

@router.post("/login")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Login admin. Imposta cookie HttpOnly session + cookie CSRF.
    """
    ip = request.client.host if request.client else "unknown"

    try:
        user = authenticate_user(db, body.username, body.password)
    except AuthError:
        # Risposta generica — non rivelare se l'utente esiste
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
        )

    # Crea nuova sessione (session rotation al login)
    session_id = create_session(db, user, ip=ip, user_agent=request.headers.get("User-Agent"))
    csrf_token = generate_csrf_token()

    log_action(db, "login", user_id=user.id, ip=ip)

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


@router.post("/logout")
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
    }


@router.post("/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
):
    """Cambio password: invalida tutte le sessioni esistenti."""
    from backend.app.services.auth_service import verify_password
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Password corrente non valida.")

    current_user.password_hash = hash_password(body.new_password)
    db.commit()

    # Invalida tutte le sessioni (forza re-login)
    invalidate_all_sessions(db, current_user.id)

    log_action(
        db, "password_changed",
        user_id=current_user.id,
        ip=request.client.host if request.client else None,
    )

    return {"status": "ok", "message": "Password aggiornata. Effettua nuovamente il login."}
