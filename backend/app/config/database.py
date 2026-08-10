"""
backend/app/config/database.py
SQLAlchemy engine + sessione. Usa SQLite con WAL mode.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings


def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    """Abilita WAL, foreign keys e busy timeout su ogni connessione SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# Percorso assoluto del DB dalla URL SQLite
_db_url = settings.database_url

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False},  # necessario per FastAPI async
    echo=(settings.app_env == "development"),
)

# Registra pragmas su ogni nuova connessione SQLite
event.listen(engine, "connect", _set_sqlite_pragmas)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base class per tutti i modelli ORM."""
    pass


def get_db():
    """
    FastAPI dependency: fornisce una sessione DB e la chiude alla fine.
    Uso: db: Session = Depends(get_db)
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Crea tutte le tabelle se non esistono.
    Chiamato all'avvio del server (lifespan).
    """
    from backend.app.models import (  # noqa: F401 — importa per registrare i modelli
        user, session, page, block, page_revision,
        workshop, booking, coupon, media, cost, report, audit_log,
        availability_subscriber,
    )
    Base.metadata.create_all(bind=engine)
