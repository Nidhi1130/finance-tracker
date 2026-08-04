from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient

AuthHeaders = Callable[[str], dict[str, str]]


def create_category(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post(
        "/categories",
        headers=headers,
        json={"name": name, "color": "#2563EB"},
    )
    assert response.status_code == 201
    return response.json()


def create_account(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post("/accounts", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_transaction(
    client: TestClient,
    headers: dict[str, str],
    *,
    amount: str = "24.50",
    tx_type: str = "expense",
    date: str = "2026-07-13",
    description: str = "Coffee and lunch",
    category_id: str | None = None,
    account_id: str | None = None,
):
    return client.post(
        "/transactions",
        headers=headers,
        json={
            "amount": amount,
            "type": tx_type,
            "date": date,
            "description": description,
            "category_id": category_id,
            "account_id": account_id,
        },
    )


def test_create_list_update_and_delete_transaction(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    category = create_category(client, headers, "Dining out")
    account = create_account(client, headers, "Checking")
    created_response = create_transaction(
        client,
        headers,
        category_id=category["id"],
        account_id=account["id"],
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["amount"] == "24.50"
    assert created["category_id"] == category["id"]
    assert created["account_id"] == account["id"]
    assert "user_id" not in created

    listed = client.get("/transactions", headers=headers).json()["items"]
    assert [item["id"] for item in listed] == [created["id"]]

    updated = client.put(
        f"/transactions/{created['id']}",
        headers=headers,
        json={"description": "Updated", "amount": "30.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"
    assert updated.json()["amount"] == "30.00"

    assert client.delete(
        f"/transactions/{created['id']}", headers=headers
    ).status_code == 204
    assert client.get(
        f"/transactions/{created['id']}", headers=headers
    ).status_code == 404


def test_transaction_list_filters_category_and_account(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    salary = next(
        item
        for item in client.get("/categories", headers=headers).json()["items"]
        if item["name"] == "Salary"
    )
    groceries = create_category(client, headers, "Weekly groceries")
    checking = create_account(client, headers, "Checking")
    savings = create_account(client, headers, "Savings")
    create_transaction(
        client,
        headers,
        amount="100.00",
        tx_type="income",
        date="2026-07-01",
        description="Salary",
        category_id=salary["id"],
        account_id=savings["id"],
    )
    create_transaction(
        client,
        headers,
        amount="45.00",
        date="2026-07-02",
        description="Groceries",
        category_id=groceries["id"],
        account_id=checking["id"],
    )

    filtered = client.get(
        "/transactions",
        headers=headers,
        params={
            "from": "2026-07-02",
            "to": "2026-07-31",
            "type": "expense",
            "category_id": groceries["id"],
            "account_id": checking["id"],
        },
    )
    assert filtered.status_code == 200
    assert [item["description"] for item in filtered.json()["items"]] == ["Groceries"]
    assert client.get(
        "/transactions",
        headers=headers,
        params={"account_id": savings["id"]},
    ).json()["items"][0]["description"] == "Salary"


def test_transaction_reference_ownership_is_enforced(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    category = create_category(client, auth_headers(user_b_id), "Private category")
    account = create_account(client, auth_headers(user_b_id), "Private account")
    assert create_transaction(
        client,
        auth_headers(user_a_id),
        category_id=category["id"],
    ).status_code == 422
    assert create_transaction(
        client,
        auth_headers(user_a_id),
        account_id=account["id"],
    ).status_code == 422
    global_id = client.get(
        "/categories", headers=auth_headers(user_a_id)
    ).json()["items"][0]["id"]
    assert create_transaction(
        client,
        auth_headers(user_a_id),
        category_id=global_id,
    ).status_code == 201


def test_transactions_are_isolated_per_user(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    transaction = create_transaction(
        client,
        auth_headers(user_a_id),
        description="Private transaction",
    ).json()
    assert client.get(
        "/transactions", headers=auth_headers(user_b_id)
    ).json()["items"] == []
    assert client.get(
        f"/transactions/{transaction['id']}", headers=auth_headers(user_b_id)
    ).status_code == 404
    assert client.put(
        f"/transactions/{transaction['id']}",
        headers=auth_headers(user_b_id),
        json={"description": "Stolen"},
    ).status_code == 404
    assert client.delete(
        f"/transactions/{transaction['id']}", headers=auth_headers(user_b_id)
    ).status_code == 404


def test_deleting_resources_nulls_transaction_references(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    category = create_category(client, headers, "Travel")
    account = create_account(client, headers, "Card")
    transaction = create_transaction(
        client,
        headers,
        category_id=category["id"],
        account_id=account["id"],
    ).json()
    assert client.delete(f"/categories/{category['id']}", headers=headers).status_code == 204
    assert client.delete(f"/accounts/{account['id']}", headers=headers).status_code == 204
    fetched = client.get(f"/transactions/{transaction['id']}", headers=headers).json()
    assert fetched["category_id"] is None
    assert fetched["account_id"] is None


def test_transaction_validation_and_bad_ids(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    assert create_transaction(client, headers, amount="-1.00").status_code == 422
    assert create_transaction(client, headers, tx_type="transfer").status_code == 422
    assert create_transaction(
        client,
        headers,
        category_id=str(uuid4()),
    ).status_code == 422
    assert client.get("/transactions/not-a-uuid", headers=headers).status_code == 422
    assert client.get(f"/transactions/{uuid4()}", headers=headers).status_code == 404
