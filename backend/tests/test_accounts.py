from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient


AuthHeaders = Callable[[str], dict[str, str]]


def create_account(
    client: TestClient,
    headers: dict[str, str],
    name: str,
):
    return client.post("/accounts", headers=headers, json={"name": name})


def test_account_crud(client: TestClient, auth_headers: AuthHeaders) -> None:
    created = create_account(client, auth_headers(), " Main checking ")
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Main checking"
    assert "user_id" not in body

    listed = client.get("/accounts", headers=auth_headers())
    assert listed.status_code == 200
    assert body["id"] in {item["id"] for item in listed.json()["items"]}

    updated = client.put(
        f"/accounts/{body['id']}",
        headers=auth_headers(),
        json={"name": "Savings"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Savings"

    assert client.delete(
        f"/accounts/{body['id']}",
        headers=auth_headers(),
    ).status_code == 204
    assert client.delete(
        f"/accounts/{body['id']}",
        headers=auth_headers(),
    ).status_code == 404


def test_accounts_are_sorted_and_isolated(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    create_account(client, auth_headers(user_a_id), "Wallet")
    create_account(client, auth_headers(user_a_id), "Bank")
    private = create_account(client, auth_headers(user_b_id), "Private").json()

    items = client.get(
        "/accounts",
        headers=auth_headers(user_a_id),
    ).json()["items"]
    assert [item["name"] for item in items] == ["Bank", "Wallet"]
    assert private["id"] not in {item["id"] for item in items}
    assert client.put(
        f"/accounts/{private['id']}",
        headers=auth_headers(user_a_id),
        json={"name": "Stolen"},
    ).status_code == 404
    assert client.delete(
        f"/accounts/{private['id']}",
        headers=auth_headers(user_a_id),
    ).status_code == 404


def test_account_validation_duplicates_and_bad_ids(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    assert create_account(client, headers, "Checking").status_code == 201
    assert create_account(client, headers, "checking").status_code == 409
    assert create_account(client, headers, "  ").status_code == 422
    assert create_account(client, headers, "x" * 81).status_code == 422
    assert client.put(
        "/accounts/not-a-uuid",
        headers=headers,
        json={"name": "Valid"},
    ).status_code == 422
    assert client.delete(f"/accounts/{uuid4()}", headers=headers).status_code == 404
