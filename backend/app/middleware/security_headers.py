"""
backend/app/middleware/security_headers.py
Aggiunge security headers a tutte le risposte FastAPI.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.config.settings import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Aggiunge tutti gli header di sicurezza raccomandati.
    CSP inizialmente in Report-Only; da applicare dopo eliminazione violazioni.
    """

    # CSP Report-Only (liberale per il frontend esistente)
    # Da inasprire progressivamente dopo aver eliminato le violazioni.
    _CSP_REPORT_ONLY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.paypal.com https://www.paypalobjects.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://www.davideluongo.it https://www.universofoto.it; "
        "media-src 'self'; "
        "frame-src https://www.paypal.com https://www.sandbox.paypal.com; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "report-uri /api/csp-report"
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Prevenzione MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Clickjacking (compatibilità browser vecchi + CSP frame-ancestors)
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=(), "
            "accelerometer=(), gyroscope=()"
        )

        # Rimuovi header informativi
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        # CSP Report-Only (non blocca ancora, solo segnala violazioni)
        response.headers["Content-Security-Policy-Report-Only"] = self._CSP_REPORT_ONLY

        # HSTS solo in produzione (da attivare dopo verifica sottodomini)
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
