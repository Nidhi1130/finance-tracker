from __future__ import annotations

import json
from collections.abc import Sequence
from os import getenv
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.schemas import TxType
from app.services.categorization import CategoryCandidate


DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TIMEOUT_SECONDS = 8.0


class CategorizationProviderError(Exception):
    """Raised when a categorization provider cannot return a valid result."""


class _ResponsesAPI(Protocol):
    def parse(self, **kwargs: Any) -> object: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesAPI


class _CategorizationResponse(BaseModel):
    category_id: UUID | None


class OpenAICategorizationProvider:
    def __init__(
        self,
        *,
        client: _OpenAIClient | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key if api_key is not None else getenv("OPENAI_API_KEY")
        self._model = model or getenv("OPENAI_CATEGORIZATION_MODEL", DEFAULT_MODEL)
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else float(getenv("OPENAI_CATEGORIZATION_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        )

    def categorize(
        self,
        *,
        description: str,
        tx_type: TxType,
        categories: Sequence[CategoryCandidate],
    ) -> UUID | None:
        try:
            response = self._get_client().responses.parse(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Choose the one meaningful category for the transaction. "
                            "Return null when no listed category is supported."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "description": " ".join(description.split()),
                                "type": tx_type.value,
                                "categories": [
                                    {"id": str(category.id), "name": category.name}
                                    for category in categories
                                ],
                            },
                            separators=(",", ":"),
                        ),
                    },
                ],
                text_format=_CategorizationResponse,
            )
            if _contains_refusal(response):
                raise CategorizationProviderError
            parsed = _CategorizationResponse.model_validate(
                getattr(response, "output_parsed", None),
            )
            if parsed.category_id is not None and parsed.category_id not in {
                category.id for category in categories
            }:
                raise CategorizationProviderError
            return parsed.category_id
        except CategorizationProviderError:
            raise
        except Exception as error:
            raise CategorizationProviderError from error

    def _get_client(self) -> _OpenAIClient:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise CategorizationProviderError
        try:
            from openai import OpenAI
        except ImportError as error:
            raise CategorizationProviderError from error
        self._client = OpenAI(api_key=self._api_key, timeout=self._timeout_seconds)
        return self._client


def _contains_refusal(response: object) -> bool:
    for output in getattr(response, "output", ()):
        if getattr(output, "type", None) != "message":
            continue
        if any(getattr(item, "type", None) == "refusal" for item in output.content):
            return True
    return False
