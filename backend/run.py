"""
backend/run.py
Avvia il server FastAPI con Uvicorn.
Uso: python run.py
"""
import sys
import os
from pathlib import Path

# Aggiungi la root del progetto al PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Carica .env dalla root del progetto
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

import uvicorn
from backend.app.config.settings import settings

if __name__ == "__main__":
    print(f"Avvio Davide Luongo CMS v3.0...")
    print(f"Ambiente: {settings.app_env}")
    print(f"URL: http://{settings.app_host}:{settings.app_port}")

    uvicorn.run(
        "backend.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=(settings.app_env == "development"),
        log_level="info" if settings.app_env == "development" else "warning",
        access_log=True,
        server_header=False,    # Non espone versione Uvicorn
        date_header=False,
    )
