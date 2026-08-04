from __future__ import annotations

import re
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_name(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 80:
        raise ValueError("name must contain between 1 and 80 characters")
    return normalized


def normalize_color(value: str) -> str:
    normalized = value.upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", normalized):
        raise ValueError("color must use #RRGGBB format")
    return normalized


class TxType(str, Enum):
    income = "income"
    expense = "expense"


PositiveAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class TransactionCreate(BaseModel):
    amount: PositiveAmount
    type: TxType
    description: str | None = None
    date: Date
    category_id: UUID | None = None
    account_id: UUID | None = None


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    type: TxType | None = None
    description: str | None = None
    date: Date | None = None
    category_id: UUID | None = None
    account_id: UUID | None = None


class TransactionOut(BaseModel):
    id: UUID
    amount: Decimal
    type: TxType
    description: str | None
    date: Date
    category_id: UUID | None
    account_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]


class CategoryCreate(BaseModel):
    name: str
    color: str

    _normalize_name = field_validator("name")(normalize_name)
    _normalize_color = field_validator("color")(normalize_color)


class CategoryUpdate(BaseModel):
    name: str
    color: str

    _normalize_name = field_validator("name")(normalize_name)
    _normalize_color = field_validator("color")(normalize_color)


class CategoryOut(BaseModel):
    id: UUID
    name: str
    color: str
    is_global: bool
    created_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryOut]


class AccountCreate(BaseModel):
    name: str

    _normalize_name = field_validator("name")(normalize_name)


class AccountUpdate(BaseModel):
    name: str

    _normalize_name = field_validator("name")(normalize_name)


class AccountOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class AccountListResponse(BaseModel):
    items: list[AccountOut]


class DashboardBucket(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class DashboardPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date_from: Date = Field(alias="from")
    date_to: Date = Field(alias="to")
    bucket: DashboardBucket


class DashboardSummary(BaseModel):
    income: Decimal
    expense: Decimal
    net: Decimal


class DashboardCategory(BaseModel):
    category_id: UUID | None
    name: str
    color: str
    amount: Decimal
    percentage: Decimal


class DashboardTrendPoint(BaseModel):
    period_start: Date
    label: str
    income: Decimal
    expense: Decimal


class DashboardResponse(BaseModel):
    period: DashboardPeriod
    summary: DashboardSummary
    categories: list[DashboardCategory]
    trend: list[DashboardTrendPoint]
