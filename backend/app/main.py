"""
PharmaFlow — Expiry-Aware Pharmacy Inventory

FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import (
    medicines,
    dispensing,
    alerts,
    dashboard,
    clock,
    import_batch,
    outbox,
    auth,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pharmaflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize database on startup."""
    logger.info("Starting PharmaFlow %s", settings.APP_VERSION)
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down PharmaFlow")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Expiry-Aware Pharmacy Inventory — FEFO dispensing, "
        "sellable stock tracking, batch traceability, and automated daily controls."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow configured origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(medicines.router)
app.include_router(dispensing.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(clock.router)
app.include_router(import_batch.router)
app.include_router(outbox.router)
app.include_router(auth.router)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint welcoming visitors and providing API documentation links."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "message": "Welcome to PharmaFlow — Expiry-Aware Pharmacy Inventory API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/api/health",
        "authentication": {
            "register": "/api/auth/register",
            "login": "/api/auth/login",
            "profile": "/api/auth/me",
        },
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
