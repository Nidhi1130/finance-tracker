from __future__ import annotations

from collections.abc import Callable
from datetime import date

from fastapi.testclient import TestClient

from app.schemas import DashboardBucket
from app.services.dashboard import select_bucket


AuthHeaders = Callable[[str], dict[str, str]]


def create_transaction(
    client: TestClient,
    headers: dict[str, str],
    payload: dict[str, str],
) -> None:
    response = client.post("/transactions", headers=headers, json=payload)
    assert response.status_code == 201


def test_dashboard_summary_categories_and_trend(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    groceries = next(
        item
        for item in client.get("/categories", headers=headers).json()["items"]
        if item["name"] == "Groceries"
    )
    for payload in (
        {"amount": "1200.00", "type": "income", "date": "2026-07-01", "description": "Salary"},
        {
            "amount": "300.00",
            "type": "expense",
            "date": "2026-07-02",
            "description": "Food",
            "category_id": groceries["id"],
        },
        {"amount": "100.00", "type": "expense", "date": "2026-07-02", "description": "Unknown"},
        {"amount": "999.00", "type": "expense", "date": "2026-06-30", "description": "Outside"},
    ):
        create_transaction(client, headers, payload)

    response = client.get(
        "/dashboard",
        headers=headers,
        params={"from": "2026-07-01", "to": "2026-07-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == {"from": "2026-07-01", "to": "2026-07-31", "bucket": "daily"}
    assert body["summary"] == {"income": "1200.00", "expense": "400.00", "net": "800.00"}
    assert [(item["name"], item["amount"], item["percentage"]) for item in body["categories"]] == [
        ("Groceries", "300.00", "75.00"),
        ("Uncategorized", "100.00", "25.00"),
    ]
    assert body["trend"] == [
        {"period_start": "2026-07-01", "label": "1 Jul", "income": "1200.00", "expense": "0.00"},
        {"period_start": "2026-07-02", "label": "2 Jul", "income": "0.00", "expense": "400.00"},
    ]


def test_bucket_thresholds() -> None:
    assert select_bucket(date(2026, 1, 1), date(2026, 1, 31)) is DashboardBucket.daily
    assert select_bucket(date(2026, 1, 1), date(2026, 2, 1)) is DashboardBucket.weekly
    assert select_bucket(date(2026, 1, 1), date(2026, 3, 31)) is DashboardBucket.weekly
    assert select_bucket(date(2026, 1, 1), date(2026, 4, 1)) is DashboardBucket.monthly


def test_dashboard_empty_period_has_zero_summary_and_no_breakdowns(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    response = client.get(
        "/dashboard",
        headers=auth_headers(),
        params={"from": "2026-05-01", "to": "2026-05-31"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "period": {"from": "2026-05-01", "to": "2026-05-31", "bucket": "daily"},
        "summary": {"income": "0.00", "expense": "0.00", "net": "0.00"},
        "categories": [],
        "trend": [],
    }


def test_dashboard_rejects_reversed_and_malformed_dates(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    assert client.get(
        "/dashboard", headers=headers, params={"from": "2026-07-02", "to": "2026-07-01"}
    ).status_code == 422
    assert client.get(
        "/dashboard", headers=headers, params={"from": "not-a-date"}
    ).status_code == 422


def test_dashboard_defaults_to_the_current_utc_month(
    client: TestClient,
    auth_headers: AuthHeaders,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.routers.dashboard.utc_today", lambda: date(2026, 2, 12))

    response = client.get("/dashboard", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["period"] == {
        "from": "2026-02-01",
        "to": "2026-02-28",
        "bucket": "daily",
    }


def test_dashboard_does_not_include_another_users_transactions(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    create_transaction(
        client,
        auth_headers(user_b_id),
        {"amount": "50.00", "type": "income", "date": "2026-07-10", "description": "Private"},
    )

    response = client.get(
        "/dashboard",
        headers=auth_headers(user_a_id),
        params={"from": "2026-07-01", "to": "2026-07-31"},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == {"income": "0.00", "expense": "0.00", "net": "0.00"}
