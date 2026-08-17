"""
backend/app/main.py
Applicazione FastAPI principale.
Registra middleware, router, lifespan, static files.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config.database import init_db
from backend.app.config.settings import settings
from backend.app.middleware.security_headers import SecurityHeadersMiddleware

# Import router
from backend.app.routes import (
    auth,
    public,
    workshops,
    participants,
    coupons,
    media,
    costs,
    content,
    reports,
    audit,
    paypal,
)

PROJECT_ROOT = settings.project_root


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Avvio e spegnimento dell'applicazione."""
    # Inizializza DB (crea tabelle se non esistono)
    init_db()
    print(f"[DB] Database inizializzato: {settings.database_url}")

    # Avvia scheduler cutoff
    from backend.app.services.cutoff_service import setup_scheduler
    scheduler = setup_scheduler()

    print(f"[Server] Davide Luongo CMS v3.0 avviato su {settings.app_host}:{settings.app_port}")
    print(f"[Admin] http://{settings.app_host}:{settings.app_port}/admin/")

    yield

    # Spegnimento
    if scheduler:
        scheduler.shutdown(wait=False)
        print("[Scheduler] APScheduler fermato.")


app = FastAPI(
    title="Davide Luongo Photography — CMS API v3.0",
    version="3.0.0",
    docs_url="/api/docs" if settings.app_env == "development" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.app_env == "development" else None,
    lifespan=lifespan,
)

# ── CORS (limitato agli origin configurati) ───────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
    expose_headers=["Content-Disposition"],
)

# ── Security Headers (tutte le risposte) ─────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── Router ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(workshops.router)
app.include_router(participants.router)
app.include_router(coupons.router)
app.include_router(media.router)
app.include_router(costs.router)
app.include_router(content.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(paypal.router)  # [ISOLATO]

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0", "environment": settings.app_env}


# ── Frontend pubblico con allowlist ──────────────────────────────────────────
# Non montare mai PROJECT_ROOT: contiene .env, backend/, data/ e private/.
def _public_file(filename: str) -> FileResponse:
    path = PROJECT_ROOT / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Risorsa non trovata.")
    return FileResponse(path)


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def home():
    return _public_file("index.html")


@app.get("/thank-you.html", include_in_schema=False)
async def thank_you():
    return _public_file("thank-you.html")


@app.get("/style.css", include_in_schema=False)
async def stylesheet():
    return _public_file("style.css")


@app.get("/main.js", include_in_schema=False)
async def main_script():
    return _public_file("main.js")


@app.get("/blog.js", include_in_schema=False)
async def blog_script():
    return _public_file("blog.js")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return _public_file("robots.txt")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    return _public_file("sitemap.xml")


for route, folder in (
    ("/assets", "assets"),
    ("/blog", "blog"),
    ("/gear", "gear"),
    ("/workshops_2026", "workshops_2026"),
    ("/viaggi_2027", "viaggi_2027"),
    ("/prelancio", "prelancio"),
):
    directory = PROJECT_ROOT / folder
    if directory.exists():
        app.mount(route, StaticFiles(directory=str(directory), html=True), name=folder)


@app.get("/data/articles.json", include_in_schema=False)
async def public_articles():
    return FileResponse(PROJECT_ROOT / "data" / "articles.json", media_type="application/json")

# Admin SPA
_admin = PROJECT_ROOT / "admin"
if _admin.exists():
    app.mount("/admin", StaticFiles(directory=str(_admin), html=True), name="admin")
