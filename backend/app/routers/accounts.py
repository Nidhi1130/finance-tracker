from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_current_user_id
from app.repositories import DuplicateResourceError, account_repository
from app.schemas import AccountCreate, AccountListResponse, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=AccountListResponse)
def list_accounts(user_id: UUID = Depends(get_current_user_id)) -> AccountListResponse:
    return AccountListResponse(
        items=[record.to_out() for record in account_repository.list(user_id)],
    )


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> AccountOut:
    try:
        return account_repository.create(user_id, payload).to_out()
    except DuplicateResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account name already exists",
        ) from error


@router.put("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    user_id: UUID = Depends(get_current_user_id),
) -> AccountOut:
    try:
        record = account_repository.update(user_id, account_id, payload)
    except DuplicateResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account name already exists",
        ) from error
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return record.to_out()


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    if not account_repository.delete(user_id, account_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
