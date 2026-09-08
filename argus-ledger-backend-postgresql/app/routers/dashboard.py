"""Aggregate metrics for the frontend dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..schemas import DashboardResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return DashboardResponse(**services.dashboard_stats(db))
