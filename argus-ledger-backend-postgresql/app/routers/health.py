"""Liveness / readiness and service metadata."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "unavailable"
    return HealthResponse(
        status="ok",
        service="argus-api",
        version=settings.version,
        database=database,
    )
