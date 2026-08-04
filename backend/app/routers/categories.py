from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_current_user_id
from app.repositories import (
    DuplicateResourceError,
    ForbiddenResourceError,
    category_repository,
)
from app.schemas import (
    CategoryCreate,
    CategoryListResponse,
    CategoryOut,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
def list_categories(
    user_id: UUID = Depends(get_current_user_id),
) -> CategoryListResponse:
    return CategoryListResponse(
        items=[record.to_out() for record in category_repository.list(user_id)],
    )


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> CategoryOut:
    try:
        return category_repository.create(user_id, payload).to_out()
    except DuplicateResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        ) from error


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    user_id: UUID = Depends(get_current_user_id),
) -> CategoryOut:
    try:
        record = category_repository.update(user_id, category_id, payload)
    except ForbiddenResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global categories are read-only",
        ) from error
    except DuplicateResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        ) from error
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return record.to_out()


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    try:
        deleted = category_repository.delete(user_id, category_id)
    except ForbiddenResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global categories are read-only",
        ) from error
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
