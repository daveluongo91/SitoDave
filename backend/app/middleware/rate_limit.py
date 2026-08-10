"""
backend/app/middleware/rate_limit.py
Rate limiting per IP su endpoint pubblici sensibili.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request, status

from backend.app.config.settings import settings

_store: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


def _get_ip(request: Request) -> str:
    """Estrae l'IP reale (gestisce proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    request: Request,
    max_per_minute: Optional[int] = None,
) -> None:
    """
    FastAPI dependency: verifica rate limit per IP.
    Lancia 429 se superato.
    Uso: Depends(check_rate_limit)
    """
    limit = max_per_minute or settings.rate_limit_per_minute
    ip = _get_ip(request)

    with _lock:
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - 60.0
        _store[ip] = [t for t in _store[ip] if t > window_start]

        if len(_store[ip]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Troppe richieste. Attendi un momento e riprova.",
                headers={"Retry-After": "60"},
            )

        _store[ip].append(now)
