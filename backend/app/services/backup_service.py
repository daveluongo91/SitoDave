"""
backend/app/services/backup_service.py
Gestione backup SQLite atomico e coerente, calcolo hash SHA-256,
verifica integrità e gestione retention.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config.settings import settings


def create_database_backup(db_path: Optional[Path] = None, backup_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Esegue una copia atomica consistente del database SQLite tramite l'API SQLite Backup.
    Restituisce un dizionario con percorso file, dimensione, hash SHA-256 e timestamp.
    """
    if db_path is None:
        db_path = settings.private_dir / "database" / "sito_dave.db"
    if backup_dir is None:
        backup_dir = settings.private_dir / "database" / "backups"

    backup_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_sito_dave_{timestamp_str}.db"
    dest_path = backup_dir / backup_filename

    if not db_path.exists():
        raise FileNotFoundError(f"Database sorgente non trovato: {db_path}")

    # SQLite Backup API nativa (atomica e consistente anche con transazioni in corso)
    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(dest_path))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    # Calcola hash e dimensione
    file_bytes = dest_path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = dest_path.stat().st_size

    # Verifica integrità
    is_ok = verify_backup_integrity(dest_path)
    if not is_ok:
        dest_path.unlink()
        raise RuntimeError("Il backup generato ha fallito il controllo di integrità SQLite.")

    return {
        "filename": backup_filename,
        "path": str(dest_path),
        "sizeBytes": file_size,
        "sizeFormatted": f"{file_size / 1024:.1f} KB",
        "hashSha256": file_hash,
        "createdAt": now.isoformat(),
        "integrityOk": True,
    }


def verify_backup_integrity(backup_path: Path) -> bool:
    """Verifica che il file di backup sia un database SQLite valido e integro (PRAGMA quick_check)."""
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA quick_check")
        res = cursor.fetchone()
        conn.close()
        return bool(res and res[0] == "ok")
    except Exception:
        return False


def list_database_backups(backup_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Restituisce la lista di tutti i backup disponibili ordinati dal più recente."""
    if backup_dir is None:
        backup_dir = settings.private_dir / "database" / "backups"

    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        st = f.stat()
        backups.append({
            "filename": f.name,
            "path": str(f),
            "sizeBytes": st.st_size,
            "sizeFormatted": f"{st.st_size / 1024:.1f} KB",
            "modifiedAt": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
        })

    return backups