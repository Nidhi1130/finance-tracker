from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.providers.openai_categorization import (
    CategorizationProviderError,
    OpenAICategorizationProvider,
)
from app.schemas import TxType
from app.services.categorization import CategoryCandidate


DINING_ID = UUID("10000000-0000-4000-8000-000000000001")
GROCERIES_ID = UUID("10000000-0000-4000-8000-000000000002")
FOREIGN_ID = UUID("20000000-0000-4000-8000-000000000001")


class FakeResponses:
    def __init__(self, *, response: object | None = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.response = response
        self.error = error

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def candidates() -> list[CategoryCandidate]:
    return [
        CategoryCandidate(id=DINING_ID, name="Dining"),
        CategoryCandidate(id=GROCERIES_ID, name="Groceries"),
    ]


def response(category_id: UUID | None) -> SimpleNamespace:
    return SimpleNamespace(output=[], output_parsed={"category_id": category_id})


def provider_with(response_value: object | None = None, error: Exception | None = None):
    responses = FakeResponses(response=response_value, error=error)
    provider = OpenAICategorizationProvider(
        client=FakeClient(responses),
        model="test-model",
        timeout_seconds=2,
    )
    return provider, responses


def test_provider_returns_allowed_category_and_minimizes_the_request_data() -> None:
    provider, responses = provider_with(response(DINING_ID))

    selected = provider.categorize(
        description="  Coffee shop  ",
        tx_type=TxType.expense,
        categories=candidates(),
    )

    assert selected == DINING_ID
    call = responses.calls[0]
    assert call["model"] == "test-model"
    assert call["store"] is False
    payload = json.loads(call["input"][1]["content"])
    assert payload == {
        "categories": [
            {"id": str(DINING_ID), "name": "Dining"},
            {"id": str(GROCERIES_ID), "name": "Groceries"},
        ],
        "description": "Coffee shop",
        "type": "expense",
    }
    serialized = json.dumps(call, default=str)
    for excluded_field in ("amount", "account", "user_id", "secret", "api_key"):
        assert excluded_field not in serialized


def test_provider_allows_a_null_category() -> None:
    provider, _ = provider_with(response(None))

    assert provider.categorize(
        description="Unknown merchant",
        tx_type=TxType.expense,
        categories=candidates(),
    ) is None


def test_provider_translates_a_refusal_to_a_provider_error() -> None:
    refused = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="refusal", refusal="Cannot help")],
            ),
        ],
        output_parsed=None,
    )
    provider, _ = provider_with(refused)

    with pytest.raises(CategorizationProviderError):
        provider.categorize(
            description="Unknown merchant",
            tx_type=TxType.expense,
            categories=candidates(),
        )


@pytest.mark.parametrize(
    "response_value",
    [
        SimpleNamespace(output=[], output_parsed=None),
        SimpleNamespace(output=[], output_parsed={"unexpected": "value"}),
        SimpleNamespace(output=[], output_parsed={"category_id": "not-a-uuid"}),
    ],
)
def test_provider_translates_malformed_structured_output_to_a_provider_error(
    response_value: object,
) -> None:
    provider, _ = provider_with(response_value)

    with pytest.raises(CategorizationProviderError):
        provider.categorize(
            description="Unknown merchant",
            tx_type=TxType.expense,
            categories=candidates(),
        )


def test_provider_rejects_a_category_not_in_the_candidates() -> None:
    provider, _ = provider_with(response(FOREIGN_ID))

    with pytest.raises(CategorizationProviderError):
        provider.categorize(
            description="Unknown merchant",
            tx_type=TxType.expense,
            categories=candidates(),
        )


@pytest.mark.parametrize("error", [TimeoutError(), RuntimeError("sdk failure")])
def test_provider_translates_sdk_errors_to_a_provider_error(error: Exception) -> None:
    provider, _ = provider_with(error=error)

    with pytest.raises(CategorizationProviderError):
        provider.categorize(
            description="Unknown merchant",
            tx_type=TxType.expense,
            categories=candidates(),
        )
