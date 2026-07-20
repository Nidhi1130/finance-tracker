from __future__ import annotations

import base64
import os
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.pop("DATABASE_URL", None)
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_JWT_SECRET", None)

from app.main import app
from app.routers.transactions import repository

client = TestClient(app)


def build_bearer_token(user_id: str) -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"),
    ).rstrip(b"=").decode("utf-8")
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id}).encode("utf-8"),
    ).rstrip(b"=").decode("utf-8")
    return f"{header}.{payload}.signature"


def auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    return {"Authorization": f"Bearer {build_bearer_token(user_id)}"}


@pytest.fixture(autouse=True)
def clear_repository() -> None:
    repository.clear()


def test_create_list_and_delete_transaction() -> None:
    user_headers = auth_headers()
    category_id = str(uuid4())
    account_id = str(uuid4())

    create_response = client.post(
        "/transactions",
        headers=user_headers,
        json={
            "amount": "24.50",
            "type": "expense",
            "date": "2026-07-13",
            "description": "Coffee and lunch",
            "category_id": category_id,
            "account_id": account_id,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["amount"] == "24.50"
    assert created["type"] == "expense"
    assert created["category_id"] == category_id
    assert created["account_id"] == account_id
    assert "user_id" not in created

    transaction_id = created["id"]

    list_response = client.get("/transactions", headers=user_headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == transaction_id

    delete_response = client.delete(f"/transactions/{transaction_id}", headers=user_headers)
    assert delete_response.status_code == 204
    assert client.get(f"/transactions/{transaction_id}", headers=user_headers).status_code == 404


def test_transaction_list_filters() -> None:
    user_headers = auth_headers()
    category_id = str(uuid4())

    client.post(
        "/transactions",
        headers=user_headers,
        json={
            "amount": "100.00",
            "type": "income",
            "date": "2026-07-01",
            "description": "Salary",
            "category_id": category_id,
        },
    )
    client.post(
        "/transactions",
        headers=user_headers,
        json={
            "amount": "45.00",
            "type": "expense",
            "date": "2026-07-02",
            "description": "Groceries",
            "category_id": str(uuid4()),
        },
    )

    filtered = client.get(
        "/transactions",
        headers=user_headers,
        params={
            "from": "2026-07-02",
            "to": "2026-07-31",
            "type": "expense",
            "category_id": category_id,
        },
    )

    assert filtered.status_code == 200
    assert filtered.json()["items"] == []

    by_type = client.get(
        "/transactions",
        headers=user_headers,
        params={"type": "expense"},
    )
    assert by_type.status_code == 200
    assert len(by_type.json()["items"]) == 1
    assert by_type.json()["items"][0]["description"] == "Groceries"


def test_transaction_validation_rejects_negative_amount_and_bad_type() -> None:
    user_headers = auth_headers()

    negative_amount = client.post(
        "/transactions",
        headers=user_headers,
        json={
            "amount": "-1.00",
            "type": "expense",
            "date": "2026-07-13",
            "description": "Invalid",
        },
    )
    assert negative_amount.status_code == 422

    bad_type = client.post(
        "/transactions",
        headers=user_headers,
        json={
            "amount": "10.00",
            "type": "transfer",
            "date": "2026-07-13",
            "description": "Invalid",
        },
    )
    assert bad_type.status_code == 422
