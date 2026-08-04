from __future__ import annotations

from collections.abc import Callable
from threading import Barrier, Thread
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient

from app.routers import transactions as transactions_router
from app.schemas import CategorizationSource, CategorizationStatus

AuthHeaders = Callable[[str], dict[str, str]]
DEFAULT_USER_ID = UUID("10000000-0000-4000-8000-000000000001")


class CategorizationServiceSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, UUID]] = []

    def categorize(self, user_id: UUID, transaction_id: UUID) -> None:
        self.calls.append((user_id, transaction_id))


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


def test_manual_category_creation_does_not_schedule_background_work(
    client: TestClient,
    auth_headers: AuthHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategorizationServiceSpy()
    monkeypatch.setattr(transactions_router, "categorization_service", service, raising=False)
    headers = auth_headers()
    category = create_category(client, headers, "Manual choice")

    response = create_transaction(client, headers, category_id=category["id"])

    assert response.status_code == 201
    assert response.json()["category_source"] == "manual"
    assert response.json()["categorization_status"] == "categorized"
    assert response.json()["categorized_at"] is not None
    assert service.calls == []


def test_explicitly_clearing_category_resets_categorization_metadata(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    category = create_category(client, headers, "Category to clear")
    created = create_transaction(client, headers, category_id=category["id"]).json()

    response = client.put(
        f"/transactions/{created['id']}",
        headers=headers,
        json={"category_id": None},
    )

    assert response.status_code == 200
    cleared = response.json()
    assert cleared["category_id"] is None
    assert cleared["category_source"] is None
    assert cleared["categorization_status"] == "not_requested"
    assert cleared["categorized_at"] is None


def test_uncategorized_creation_returns_pending_and_schedules_work(
    client: TestClient,
    auth_headers: AuthHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategorizationServiceSpy()
    monkeypatch.setattr(transactions_router, "categorization_service", service, raising=False)
    headers = auth_headers()

    response = create_transaction(client, headers, description="Needs a category")

    assert response.status_code == 201
    created = response.json()
    assert created["category_id"] is None
    assert created["category_source"] is None
    assert created["categorization_status"] == "pending"
    assert created["categorized_at"] is None
    assert service.calls == [(DEFAULT_USER_ID, UUID(created["id"]))]


def test_retry_returns_202_once_then_rejects_pending_duplicate_without_extra_task(
    client: TestClient,
    auth_headers: AuthHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategorizationServiceSpy()
    monkeypatch.setattr(transactions_router, "categorization_service", service, raising=False)
    headers = auth_headers()
    automatic = create_transaction(client, headers, description="Retry me").json()
    assert transactions_router.repository.finish_without_category(
        DEFAULT_USER_ID,
        UUID(automatic["id"]),
        CategorizationStatus.failed,
    ) is not None
    service.calls.clear()

    retried = client.post(
        f"/transactions/{automatic['id']}/categorize",
        headers=headers,
    )
    duplicate = client.post(
        f"/transactions/{automatic['id']}/categorize",
        headers=headers,
    )

    assert retried.status_code == 202
    assert retried.json()["categorization_status"] == "pending"
    assert duplicate.status_code == 409
    assert service.calls == [(DEFAULT_USER_ID, UUID(automatic["id"]))]


def test_retry_rejects_manual_transaction_and_hides_missing_transaction(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_b_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategorizationServiceSpy()
    monkeypatch.setattr(transactions_router, "categorization_service", service, raising=False)
    headers = auth_headers()

    category = create_category(client, headers, "Protected manual choice")
    manual = create_transaction(client, headers, category_id=category["id"]).json()
    rejected = client.post(
        f"/transactions/{manual['id']}/categorize",
        headers=headers,
    )
    hidden = client.post(
        f"/transactions/{manual['id']}/categorize",
        headers=auth_headers(user_b_id),
    )
    missing = client.post(f"/transactions/{uuid4()}/categorize", headers=headers)

    assert rejected.status_code == 409
    assert hidden.status_code == 404
    assert missing.status_code == 404
    assert service.calls == []


def test_concurrent_retry_requests_enqueue_exactly_one_background_task(
    client: TestClient,
    auth_headers: AuthHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategorizationServiceSpy()
    monkeypatch.setattr(transactions_router, "categorization_service", service, raising=False)
    created = create_transaction(client, auth_headers(), description="Concurrent retry").json()
    transaction_id = UUID(created["id"])
    assert transactions_router.repository.finish_without_category(
        DEFAULT_USER_ID,
        transaction_id,
        CategorizationStatus.failed,
    ) is not None
    service.calls.clear()
    real_prepare = transactions_router.repository.prepare_categorization
    start = Barrier(3)

    def controlled_prepare(user_id: UUID, requested_id: UUID):
        start.wait(timeout=2)
        return real_prepare(user_id, requested_id)

    monkeypatch.setattr(
        transactions_router.repository,
        "prepare_categorization",
        controlled_prepare,
    )
    outcomes: list[tuple[int, int]] = []

    def retry() -> None:
        background_tasks = BackgroundTasks()
        try:
            transactions_router.retry_categorization(
                transaction_id,
                background_tasks,
                DEFAULT_USER_ID,
            )
            outcomes.append((202, len(background_tasks.tasks)))
        except HTTPException as error:
            outcomes.append((error.status_code, len(background_tasks.tasks)))

    threads = [Thread(target=retry), Thread(target=retry)]
    for thread in threads:
        thread.start()
    start.wait(timeout=2)
    for thread in threads:
        thread.join(timeout=2)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == [(202, 1), (409, 0)]


@pytest.mark.parametrize(
    "source",
    [CategorizationSource.rule, CategorizationSource.openai],
)
def test_retry_repends_automatic_category_and_schedules_work(
    source: CategorizationSource,
    client: TestClient,
    auth_headers: AuthHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CategorizationServiceSpy()
    monkeypatch.setattr(transactions_router, "categorization_service", service)
    headers = auth_headers()
    category = create_category(client, headers, f"Automatic {source.value}")
    created = create_transaction(client, headers, description="Retry automatic").json()
    applied = transactions_router.repository.apply_automatic_category(
        DEFAULT_USER_ID,
        UUID(created["id"]),
        UUID(category["id"]),
        source,
    )
    assert applied is not None
    service.calls.clear()

    response = client.post(
        f"/transactions/{created['id']}/categorize",
        headers=headers,
    )

    assert response.status_code == 202
    retried = response.json()
    assert retried["category_id"] is None
    assert retried["category_source"] is None
    assert retried["categorization_status"] == "pending"
    assert retried["categorized_at"] is None
    assert service.calls == [(DEFAULT_USER_ID, UUID(created["id"]))]
