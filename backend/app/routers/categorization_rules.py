from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_current_user_id
from app.repositories import (
    DuplicateResourceError,
    InvalidReferenceError,
    categorization_rule_repository,
)
from app.schemas import (
    CategorizationRuleCreate,
    CategorizationRuleListResponse,
    CategorizationRuleOut,
    CategorizationRuleUpdate,
)

router = APIRouter(prefix="/categorization-rules", tags=["categorization-rules"])


@router.get("", response_model=CategorizationRuleListResponse)
def list_categorization_rules(
    user_id: UUID = Depends(get_current_user_id),
) -> CategorizationRuleListResponse:
    return CategorizationRuleListResponse(
        items=[record.to_out() for record in categorization_rule_repository.list(user_id)],
    )


@router.post("", response_model=CategorizationRuleOut, status_code=status.HTTP_201_CREATED)
def create_categorization_rule(
    payload: CategorizationRuleCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> CategorizationRuleOut:
    try:
        return categorization_rule_repository.create(user_id, payload).to_out()
    except DuplicateResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rule keyword already exists",
        ) from error
    except InvalidReferenceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{error.field} is not available to the current user",
        ) from error


@router.put("/{rule_id}", response_model=CategorizationRuleOut)
def update_categorization_rule(
    rule_id: UUID,
    payload: CategorizationRuleUpdate,
    user_id: UUID = Depends(get_current_user_id),
) -> CategorizationRuleOut:
    try:
        record = categorization_rule_repository.update(user_id, rule_id, payload)
    except DuplicateResourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rule keyword already exists",
        ) from error
    except InvalidReferenceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{error.field} is not available to the current user",
        ) from error
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categorization rule not found",
        )
    return record.to_out()


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categorization_rule(
    rule_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    if not categorization_rule_repository.delete(user_id, rule_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categorization rule not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
