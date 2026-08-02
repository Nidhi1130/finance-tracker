from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status

from app.dependencies import get_current_user_id
from app.repositories import InvalidReferenceError, transaction_repository
from app.schemas import TransactionCreate, TransactionListResponse, TransactionOut, TxType, TransactionUpdate
from app.services import categorization_service

router = APIRouter(prefix="/transactions", tags=["transactions"])
repository = transaction_repository


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    tx_type: TxType | None = Query(default=None, alias="type"),
    category_id: UUID | None = None,
    account_id: UUID | None = None,
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionListResponse:
    items = repository.list(
        user_id,
        tx_type=tx_type,
        category_id=category_id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
    )
    return TransactionListResponse(items=[item.to_out() for item in items])


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionOut:
    try:
        record = repository.create(user_id, payload)
    except InvalidReferenceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{error.field} is not available to the current user",
        ) from error
    if payload.category_id is None:
        background_tasks.add_task(categorization_service.categorize, user_id, record.id)
    return record.to_out()


@router.post(
    "/{transaction_id}/categorize",
    response_model=TransactionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_categorization(
    transaction_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionOut:
    record = repository.prepare_categorization(user_id, transaction_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if record.category_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction is already categorized",
        )
    background_tasks.add_task(categorization_service.categorize, user_id, record.id)
    return record.to_out()


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionOut:
    record = repository.get(user_id, transaction_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return record.to_out()


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionOut:
    try:
        record = repository.update(user_id, transaction_id, payload)
    except InvalidReferenceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{error.field} is not available to the current user",
        ) from error
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return record.to_out()


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    deleted = repository.delete(user_id, transaction_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
