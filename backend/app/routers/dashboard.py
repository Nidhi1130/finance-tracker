from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_current_user_id
from app.repositories import dashboard_repository
from app.schemas import DashboardResponse
from app.services.dashboard import get_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
repository = dashboard_repository


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def current_utc_month() -> tuple[date, date]:
    today = utc_today()
    return date(today.year, today.month, 1), date(
        today.year,
        today.month,
        calendar.monthrange(today.year, today.month)[1],
    )


@router.get("", response_model=DashboardResponse)
def dashboard(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    user_id: UUID = Depends(get_current_user_id),
) -> DashboardResponse:
    default_from, default_to = current_utc_month()
    resolved_from = date_from or default_from
    resolved_to = date_to or default_to
    if resolved_from > resolved_to:
        raise HTTPException(status_code=422, detail="from must be on or before to")
    return get_dashboard(repository, user_id, resolved_from, resolved_to)
