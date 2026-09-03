import os
from typing import Dict


DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "operator": {"password": "op123", "role": "Operator"},
    "viewer": {"password": "view123", "role": "Viewer"},
}


def load_users() -> Dict[str, Dict[str, str]]:
    """Load dashboard credentials without enabling demo passwords in production."""
    environment = os.getenv("APP_ENV", "production").strip().lower()
    if environment == "development":
        return DEFAULT_USERS.copy()

    configured = {}
    for username, role in (("admin", "Admin"), ("operator", "Operator"), ("viewer", "Viewer")):
        password = os.getenv(f"{username.upper()}_PASSWORD")
        if password:
            configured[username] = {"password": password, "role": role}
    return configured
