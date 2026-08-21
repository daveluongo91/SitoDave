"""Aggiunge in modo idempotente i campi dell'opzione venerdì alle prenotazioni."""
from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "private" / "database" / "sito_dave.db"


def migrate() -> list[str]:
    connection = sqlite3.connect(DB_PATH)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(bookings)")}
        added = []
        if "extra_day_selected" not in columns:
            connection.execute(
                "ALTER TABLE bookings ADD COLUMN extra_day_selected BOOLEAN NOT NULL DEFAULT 0"
            )
            added.append("extra_day_selected")
        if "extra_day_cents" not in columns:
            connection.execute(
                "ALTER TABLE bookings ADD COLUMN extra_day_cents INTEGER NOT NULL DEFAULT 0"
            )
            added.append("extra_day_cents")
        connection.commit()
        return added
    finally:
        connection.close()


if __name__ == "__main__":
    fields = migrate()
    print("booking extra-day migration:", ", ".join(fields) if fields else "already applied")
