"""
backend/app/middleware/csrf.py
Protezione CSRF per tutte le route admin non-GET.
Pattern: Double-Submit Cookie (token in cookie + header).
"""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Cookie, HTTPException, Request, status

from backend.app.config.settings import settings


class CSRFError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF non valido o mancante.",
        )


def verify_csrf(
    request: Request,
    csrf_token: Optional[str] = Cookie(default=None, alias="csrf_token"),
) -> None:
    """
    FastAPI dependency: verifica il token CSRF per metodi non-idempotenti.
    Il client deve inviare il token anche nell'header X-CSRF-Token.
    Da usare su tutte le route POST/PUT/DELETE admin.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return  # Metodi sicuri: nessuna verifica

    header_token = request.headers.get("X-CSRF-Token", "")

    if not csrf_token or not header_token:
        raise CSRFError()

    if not secrets.compare_digest(csrf_token, header_token):
        raise CSRFError()


def generate_csrf_token() -> str:
    """Genera un token CSRF crittograficamente sicuro."""
    return secrets.token_hex(settings.csrf_token_length)
