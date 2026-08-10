"""
backend/admin_init.py
Script per la creazione del primo utente admin.
Eseguire UNA SOLA VOLTA dopo la prima installazione:
  python backend/admin_init.py

La password viene mostrata UNA SOLA VOLTA e non salvata in chiaro.
"""
import sys
import os
from pathlib import Path

# Aggiungi la root al PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Carica .env
_env = PROJECT_ROOT / ".env"
if _env.exists():
    with open(_env, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from backend.app.config.database import SessionLocal, init_db
from backend.app.models.user import User
from backend.app.services.auth_service import hash_password
import secrets

def main():
    print("\n" + "="*60)
    print("  Davide Luongo CMS v3.0 — Creazione Admin")
    print("="*60 + "\n")

    init_db()
    db = SessionLocal()

    try:
        existing = db.query(User).filter(User.role == "admin").first()
        if existing:
            print(f"✅ Esiste già un admin: '{existing.username}'")
            print("   Per creare un secondo admin, modifica questo script.")
            return

        # Dati admin
        username = input("Username admin [admin]: ").strip() or "admin"
        email = input("Email admin [info@davideluongo.it]: ").strip() or "info@davideluongo.it"

        # Genera password sicura
        password = secrets.token_urlsafe(16)

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()

        print("\n" + "="*60)
        print("✅ UTENTE ADMIN CREATO")
        print(f"   Username : {username}")
        print(f"   Email    : {email}")
        print(f"   Password : {password}")
        print("\n⚠️  SALVA QUESTA PASSWORD ORA — non verrà più mostrata!")
        print("   Cambiarla al primo accesso tramite Admin > Sicurezza.")
        print("="*60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
