"""
backend/app/config/settings.py
Configurazione centralizzata tramite Pydantic Settings.
Legge da variabili d'ambiente o da .env nella root del progetto.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# Root del progetto (L:\Sito_Dave)
# settings.py è in backend/app/config/ → parents[3] = L:\Sito_Dave
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Cerca .env nella root del progetto, poi nel backend
        env_file=[str(PROJECT_ROOT / ".env"), str(BACKEND_ROOT / ".env")],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server ──────────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 3000
    site_public_url: str = "https://www.davideluongo.it"

    # ── Segreto sessioni ─────────────────────────────────────────────────────
    secret_key: str = ""  # OBBLIGATORIO in produzione

    # ── Sessioni ─────────────────────────────────────────────────────────────
    session_lifetime_hours: int = 8
    csrf_token_length: int = 32

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'private' / 'database' / 'sito_dave.db'}"

    # ── SMTP ─────────────────────────────────────────────────────────────────
    aruba_smtp_user: str = "info@davideluongo.it"
    aruba_smtp_pass: str = ""
    aruba_smtp_host: str = "smtps.aruba.it"
    aruba_smtp_port: int = 465

    # ── Sicurezza ────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 10
    admin_login_max_attempts: int = 5
    admin_lockout_minutes: int = 15

    # ── Upload / Immagini ─────────────────────────────────────────────────────
    upload_max_bytes: int = 10 * 1024 * 1024   # 10 MB
    image_max_dimension: int = 2048
    image_max_output_bytes: int = 5 * 1024 * 1024  # 5 MB
    image_quality_webp: int = 85
    image_quality_jpeg: int = 88
    image_quality_min: int = 55

    # ── Privacy ──────────────────────────────────────────────────────────────
    report_retention_days: int = 365
    log_retention_days: int = 90

    # ── PayPal [ISOLATO] ──────────────────────────────────────────────────────
    paypal_env: str = "sandbox"
    paypal_sandbox_client_id: str = ""
    paypal_sandbox_client_secret: str = ""
    paypal_live_client_id: str = ""
    paypal_live_client_secret: str = ""
    paypal_webhook_id: str = ""

    # ── Derived paths ─────────────────────────────────────────────────────────
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def private_dir(self) -> Path:
        return PROJECT_ROOT / "private"

    @property
    def exports_dir(self) -> Path:
        d = self.private_dir / "exports"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def originals_dir(self) -> Path:
        d = self.private_dir / "originals"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def logs_dir(self) -> Path:
        d = self.private_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def public_upload_dir(self) -> Path:
        d = PROJECT_ROOT / "assets" / "upload"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.app_env == "production" and not self.secret_key:
            raise ValueError("SECRET_KEY è obbligatoria in produzione.")
        if not self.secret_key:
            import secrets
            self.secret_key = secrets.token_hex(32)
        if self.paypal_env.lower() == "live":
            missing = [
                name for name, value in (
                    ("PAYPAL_LIVE_CLIENT_ID", self.paypal_live_client_id),
                    ("PAYPAL_LIVE_CLIENT_SECRET", self.paypal_live_client_secret),
                    ("PAYPAL_WEBHOOK_ID", self.paypal_webhook_id),
                ) if not value
            ]
            if missing:
                raise ValueError(f"Configurazione PayPal live incompleta: {', '.join(missing)}")
        return self


settings = Settings()
