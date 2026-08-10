"""
backend/app/middleware/auth.py
Dependency FastAPI per autenticazione admin via sessione cookie.
"""
from __future__ import annotations

from typing import Optional
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.models.user import User
from backend.app.services.auth_service import get_current_user


def get_admin_user(
    session_id: Optional[str] = Cookie(default=None, alias="admin_session"),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: verifica che esista una sessione admin valida.
    Lancia 401 se non autenticato.
    Uso: current_user: User = Depends(get_admin_user)
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta.",
        )
    user = get_current_user(db, session_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessione scaduta o non valida.",
        )
    return user


def require_role(required_role: str):
    """
    FastAPI dependency factory per controllo ruolo.
    Uso: current_user: User = Depends(require_role("admin"))
    """
    def _check(user: User = Depends(get_admin_user)) -> User:
        role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 2)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permessi insufficienti per questa operazione.",
            )
        return user
    return _check
