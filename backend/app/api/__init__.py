"""API routers package."""

from app.api import medicines, dispensing, alerts, dashboard, clock, import_batch, outbox, auth

__all__ = [
    "medicines",
    "dispensing",
    "alerts",
    "dashboard",
    "clock",
    "import_batch",
    "outbox",
    "auth",
]
