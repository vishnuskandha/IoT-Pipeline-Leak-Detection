import os

from auth_config import load_users


def test_production_does_not_enable_demo_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for name in ("ADMIN_PASSWORD", "OPERATOR_PASSWORD", "VIEWER_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    users = load_users()

    assert users == {}


def test_production_loads_configured_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-admin-secret")
    monkeypatch.delenv("OPERATOR_PASSWORD", raising=False)
    monkeypatch.delenv("VIEWER_PASSWORD", raising=False)

    users = load_users()

    assert users == {"admin": {"password": "strong-admin-secret", "role": "Admin"}}


def test_development_keeps_demo_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    for name in ("ADMIN_PASSWORD", "OPERATOR_PASSWORD", "VIEWER_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    users = load_users()

    assert users["admin"]["password"] == "admin123"
    assert users["operator"]["password"] == "op123"
    assert users["viewer"]["password"] == "view123"
