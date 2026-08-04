from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol
from uuid import UUID

from app.repositories.base import database_session
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
        categories.sort(key=lambda item: (-item.amount, item.name.casefold(), str(item.category_id)))
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
        percentage = (amount / total_expense * Decimal(100)).quantize(
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


@dataclass
class PostgresDashboardRepository:
    database_url: str

    def get(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        bucket: DashboardBucket,
    ) -> DashboardRecord:
        bucket_sql = {
            DashboardBucket.daily: "t.date",
            DashboardBucket.weekly: "date_trunc('week', t.date)::date",
            DashboardBucket.monthly: "date_trunc('month', t.date)::date",
        }[bucket]

        summary_query = """
            select
              coalesce(sum(amount) filter (where type = 'income'), 0.00) as income,
              coalesce(sum(amount) filter (where type = 'expense'), 0.00) as expense
            from transactions t
            where t.user_id = current_setting('app.user_id')::uuid
              and t.date between %s and %s
        """
        categories_query = """
            with expense_totals as (
              select
                t.category_id,
                coalesce(c.name, 'Uncategorized') as name,
                coalesce(c.color, '#6B7280') as color,
                sum(t.amount) as amount
              from transactions t
              left join categories c on c.id = t.category_id
              where t.user_id = current_setting('app.user_id')::uuid
                and t.type = 'expense'
                and t.date between %s and %s
              group by t.category_id, coalesce(c.name, 'Uncategorized'), coalesce(c.color, '#6B7280')
            ),
            total_expense as (
              select sum(amount) as amount
              from expense_totals
            )
            select category_id, name, color, expense_totals.amount as amount,
                   round(expense_totals.amount * 100 / total_expense.amount, 2) as percentage
            from expense_totals
            cross join total_expense
            where total_expense.amount > 0
            order by expense_totals.amount desc, lower(name), category_id
        """
        trend_query = f"""
            select
              {bucket_sql} as period_start,
              coalesce(sum(t.amount) filter (where t.type = 'income'), 0.00) as income,
              coalesce(sum(t.amount) filter (where t.type = 'expense'), 0.00) as expense
            from transactions t
            where t.user_id = current_setting('app.user_id')::uuid
              and t.date between %s and %s
            group by {bucket_sql}
            order by period_start
        """

        with database_session(self.database_url, user_id, repeatable_read=True) as connection:
            summary = connection.execute(summary_query, (date_from, date_to)).fetchone()
            category_rows = connection.execute(categories_query, (date_from, date_to)).fetchall()
            trend_rows = connection.execute(trend_query, (date_from, date_to)).fetchall()

        assert summary is not None
        return DashboardRecord(
            income=summary["income"],
            expense=summary["expense"],
            categories=[
                DashboardCategoryRecord(
                    category_id=UUID(str(row["category_id"])) if row["category_id"] else None,
                    name=row["name"],
                    color=row["color"],
                    amount=row["amount"],
                    percentage=row["percentage"],
                )
                for row in category_rows
            ],
            trend=[
                DashboardTrendRecord(
                    period_start=row["period_start"],
                    income=row["income"],
                    expense=row["expense"],
                )
                for row in trend_rows
            ],
        )
