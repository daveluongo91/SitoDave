from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config.settings import Settings
from backend.app.routes.paypal import CreateOrderRequest
from pydantic import ValidationError
import pytest


def test_public_site_and_health_are_available():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        home = client.get("/")
        assert home.status_code == 200
        assert "Davide Luongo" in home.text
        assert client.get("/style.css").status_code == 200
        assert client.get("/data/articles.json").status_code == 200
        assert client.get("/admin/").status_code == 200


def test_sensitive_project_paths_are_not_public():
    with TestClient(app) as client:
        for path in (
            "/.env",
            "/server.py",
            "/backend/app/main.py",
            "/data/info_requests.json",
            "/private/database/sito_dave.db",
            "/admin.html",
        ):
            assert client.get(path).status_code == 404, path


def test_technical_pages_have_indexing_controls():
    with TestClient(app) as client:
        assert "Disallow: /admin/" in client.get("/robots.txt").text
        assert 'name="robots" content="noindex,nofollow"' in client.get("/thank-you.html").text


def test_production_requires_persistent_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", secret_key="")


def test_paypal_order_input_is_constrained():
    valid = dict(
        workshopId="friuli-2026", formula="caparra", firstName="Mario",
        lastName="Rossi", email="mario@example.com", participants=1,
    )
    assert CreateOrderRequest(**valid).participants == 1
    with pytest.raises(ValidationError):
        CreateOrderRequest(**{**valid, "formula": "gratis"})
    with pytest.raises(ValidationError):
        CreateOrderRequest(**{**valid, "participants": 0})
