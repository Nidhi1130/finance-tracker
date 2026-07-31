from __future__ import annotations

from datetime import date
from uuid import UUID

from app.repositories.dashboard import DashboardRepository
from app.schemas import (
    DashboardBucket,
    DashboardCategory,
    DashboardPeriod,
    DashboardResponse,
    DashboardSummary,
    DashboardTrendPoint,
)

MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def select_bucket(date_from: date, date_to: date) -> DashboardBucket:
    inclusive_days = (date_to - date_from).days + 1
    if inclusive_days <= 31:
        return DashboardBucket.daily
    if inclusive_days <= 90:
        return DashboardBucket.weekly
    return DashboardBucket.monthly


def format_period_label(period_start: date, bucket: DashboardBucket) -> str:
    month = MONTH_LABELS[period_start.month - 1]
    return f"{period_start.day} {month}" if bucket is not DashboardBucket.monthly else f"{month} {period_start.year}"


def get_dashboard(
    repository: DashboardRepository,
    user_id: UUID,
    date_from: date,
    date_to: date,
) -> DashboardResponse:
    if date_from > date_to:
        raise ValueError("from must be on or before to")
    bucket = select_bucket(date_from, date_to)
    record = repository.get(user_id, date_from, date_to, bucket)
    return DashboardResponse(
        period=DashboardPeriod(date_from=date_from, date_to=date_to, bucket=bucket),
        summary=DashboardSummary(
            income=record.income,
            expense=record.expense,
            net=record.income - record.expense,
        ),
        categories=[
            DashboardCategory(
                category_id=category.category_id,
                name=category.name,
                color=category.color,
                amount=category.amount,
                percentage=category.percentage,
            )
            for category in record.categories
        ],
        trend=[
            DashboardTrendPoint(
                period_start=trend.period_start,
                label=format_period_label(trend.period_start, bucket),
                income=trend.income,
                expense=trend.expense,
            )
            for trend in record.trend
        ],
    )
