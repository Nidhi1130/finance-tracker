from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol
from uuid import UUID

from app.repositories.categories import CategoryRepository
from app.repositories.transactions import TransactionRepository
from app.schemas import DashboardBucket, TxType


@dataclass(frozen=True)
class DashboardCategoryRecord:
    category_id: UUID | None
    name: str
    color: str
    amount: Decimal
    percentage: Decimal


@dataclass(frozen=True)
class DashboardTrendRecord:
    period_start: date
    income: Decimal
    expense: Decimal


@dataclass(frozen=True)
class DashboardRecord:
    income: Decimal
    expense: Decimal
    categories: list[DashboardCategoryRecord]
    trend: list[DashboardTrendRecord]


class DashboardRepository(Protocol):
    def get(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        bucket: DashboardBucket,
    ) -> DashboardRecord: ...


@dataclass
class InMemoryDashboardRepository:
    transaction_repository: TransactionRepository
    category_repository: CategoryRepository

    def get(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        bucket: DashboardBucket,
    ) -> DashboardRecord:
        records = self.transaction_repository.list(
            user_id,
            date_from=date_from,
            date_to=date_to,
        )
        income = sum(
            (record.amount for record in records if record.type is TxType.income),
            Decimal("0.00"),
        )
        expense = sum(
            (record.amount for record in records if record.type is TxType.expense),
            Decimal("0.00"),
        )
        category_amounts: dict[UUID | None, Decimal] = {}
        trend: dict[date, list[Decimal]] = {}

        for record in records:
            period_start = self._period_start(record.date, bucket)
            period_totals = trend.setdefault(period_start, [Decimal("0.00"), Decimal("0.00")])
            if record.type is TxType.income:
                period_totals[0] += record.amount
            else:
                period_totals[1] += record.amount
                category_amounts[record.category_id] = (
                    category_amounts.get(record.category_id, Decimal("0.00")) + record.amount
                )

        categories = [
            self._category_record(user_id, category_id, amount, expense)
            for category_id, amount in category_amounts.items()
        ]
        categories.sort(key=lambda item: (-item.amount, item.name.casefold()))
        return DashboardRecord(
            income=income,
            expense=expense,
            categories=categories,
            trend=[
                DashboardTrendRecord(period_start=period_start, income=totals[0], expense=totals[1])
                for period_start, totals in sorted(trend.items())
            ],
        )

    @staticmethod
    def _period_start(record_date: date, bucket: DashboardBucket) -> date:
        if bucket is DashboardBucket.daily:
            return record_date
        if bucket is DashboardBucket.weekly:
            return record_date - timedelta(days=record_date.weekday())
        return record_date.replace(day=1)

    def _category_record(
        self,
        user_id: UUID,
        category_id: UUID | None,
        amount: Decimal,
        total_expense: Decimal,
    ) -> DashboardCategoryRecord:
        category = self.category_repository.get(user_id, category_id) if category_id else None
        percentage = (amount / total_expense * Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if category is None:
            return DashboardCategoryRecord(
                category_id=None,
                name="Uncategorized",
                color="#6B7280",
                amount=amount,
                percentage=percentage,
            )
        return DashboardCategoryRecord(
            category_id=category.id,
            name=category.name,
            color=category.color,
            amount=amount,
            percentage=percentage,
        )
