from __future__ import annotations

from datetime import date as Date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


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
