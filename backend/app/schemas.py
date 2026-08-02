from __future__ import annotations

from datetime import date as Date, datetime
from decimal import Decimal
from enum import Enum
import re
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


class CategorizationSource(str, Enum):
    manual = "manual"
    rule = "rule"
    openai = "openai"


class CategorizationStatus(str, Enum):
    not_requested = "not_requested"
    pending = "pending"
    categorized = "categorized"
    failed = "failed"


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
    category_source: CategorizationSource | None
    categorization_status: CategorizationStatus
    categorized_at: datetime | None
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


def normalize_keyword(value: str) -> str:
    normalized = " ".join(value.split())
    if not 1 <= len(normalized) <= 120:
        raise ValueError("keyword must contain between 1 and 120 characters")
    return normalized


def normalize_optional_keyword(value: str | None) -> str | None:
    return normalize_keyword(value) if value is not None else None


class CategorizationRuleCreate(BaseModel):
    keyword: str
    category_id: UUID
    enabled: bool = True

    _normalize_keyword = field_validator("keyword")(normalize_keyword)


class CategorizationRuleUpdate(BaseModel):
    keyword: str | None = None
    category_id: UUID | None = None
    enabled: bool | None = None

    _normalize_keyword = field_validator("keyword")(normalize_optional_keyword)


class CategorizationRuleOut(BaseModel):
    id: UUID
    keyword: str
    category_id: UUID
    category_name: str
    category_color: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CategorizationRuleListResponse(BaseModel):
    items: list[CategorizationRuleOut]


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
