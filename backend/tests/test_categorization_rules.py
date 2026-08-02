from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import categorization_rule_repository


AuthHeaders = Callable[[str], dict[str, str]]
GLOBAL_CATEGORY_ID = "00000000-0000-4000-8000-000000000001"


def create_rule(
    client: TestClient,
    headers: dict[str, str],
    *,
    keyword: str,
    category_id: str = GLOBAL_CATEGORY_ID,
    enabled: bool = True,
):
    return client.post(
        "/categorization-rules",
        headers=headers,
        json={"keyword": keyword, "category_id": category_id, "enabled": enabled},
    )


def test_rule_crud_returns_category_details(client: TestClient, auth_headers: AuthHeaders) -> None:
    created = create_rule(client, auth_headers(), keyword="  coffee   shop  ")
    assert created.status_code == 201
    body = created.json()
    assert body["keyword"] == "coffee shop"
    assert body["category_id"] == GLOBAL_CATEGORY_ID
    assert body["category_name"] == "Housing"
    assert body["category_color"] == "#7C3AED"
    assert body["enabled"] is True
    assert "user_id" not in body

    listed = client.get("/categorization-rules", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json() == {"items": [body]}

    updated = client.put(
        f"/categorization-rules/{body['id']}",
        headers=auth_headers(),
        json={"keyword": "Café", "enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["keyword"] == "Café"
    assert updated.json()["enabled"] is False

    deleted = client.delete(f"/categorization-rules/{body['id']}", headers=auth_headers())
    assert deleted.status_code == 204
    assert client.put(
        f"/categorization-rules/{body['id']}",
        headers=auth_headers(),
        json={"enabled": True},
    ).status_code == 404


def test_rules_are_isolated_by_authenticated_user(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    created = create_rule(client, auth_headers(user_a_id), keyword="spotify")
    assert created.status_code == 201
    rule_id = created.json()["id"]

    other = client.get("/categorization-rules", headers=auth_headers(user_b_id))
    assert other.status_code == 200
    assert other.json() == {"items": []}
    assert client.put(
        f"/categorization-rules/{rule_id}",
        headers=auth_headers(user_b_id),
        json={"enabled": False},
    ).status_code == 404
    assert client.delete(
        f"/categorization-rules/{rule_id}",
        headers=auth_headers(user_b_id),
    ).status_code == 404


def test_rule_keyword_is_case_insensitively_unique(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    assert create_rule(client, auth_headers(), keyword="Spotify").status_code == 201
    assert create_rule(client, auth_headers(), keyword="spotify").status_code == 409


def test_rule_rejects_unavailable_categories(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    private_category = client.post(
        "/categories",
        headers=auth_headers(user_b_id),
        json={"name": "Other user's category", "color": "#123ABC"},
    ).json()

    assert create_rule(
        client,
        auth_headers(user_a_id),
        keyword="private",
        category_id=private_category["id"],
    ).status_code == 422
    assert create_rule(
        client,
        auth_headers(user_a_id),
        keyword="missing",
        category_id=str(uuid4()),
    ).status_code == 422


def test_rule_list_is_keyword_ordered_and_can_filter_enabled_rules(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
) -> None:
    headers = auth_headers(user_a_id)
    disabled = create_rule(client, headers, keyword="zebra", enabled=False).json()
    enabled = create_rule(client, headers, keyword="Alpha").json()

    listed = client.get("/categorization-rules", headers=headers)
    assert [item["id"] for item in listed.json()["items"]] == [enabled["id"], disabled["id"]]
    active = categorization_rule_repository.list(UUID(user_a_id), enabled_only=True)
    assert [item.id for item in active] == [UUID(enabled["id"])]


def test_rule_update_rejects_duplicate_and_unavailable_category(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    headers = auth_headers(user_a_id)
    first = create_rule(client, headers, keyword="Netflix").json()
    second = create_rule(client, headers, keyword="Hulu").json()
    other_category = client.post(
        "/categories",
        headers=auth_headers(user_b_id),
        json={"name": "Hidden", "color": "#123ABC"},
    ).json()

    assert client.put(
        f"/categorization-rules/{second['id']}",
        headers=headers,
        json={"keyword": "netflix"},
    ).status_code == 409
    assert client.put(
        f"/categorization-rules/{first['id']}",
        headers=headers,
        json={"category_id": other_category["id"]},
    ).status_code == 422


def test_rules_for_deleted_categories_are_not_found(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    category = client.post(
        "/categories",
        headers=headers,
        json={"name": "Disposable", "color": "#123ABC"},
    ).json()
    rule = create_rule(client, headers, keyword="Disposable", category_id=category["id"]).json()

    assert client.delete(f"/categories/{category['id']}", headers=headers).status_code == 204
    assert client.put(
        f"/categorization-rules/{rule['id']}",
        headers=headers,
        json={"enabled": False},
    ).status_code == 404
    assert client.delete(f"/categorization-rules/{rule['id']}", headers=headers).status_code == 404


@pytest.mark.parametrize("payload", [{"keyword": None}, {"category_id": None}, {"enabled": None}])
def test_rule_update_rejects_explicit_null_values(
    client: TestClient,
    auth_headers: AuthHeaders,
    payload: dict[str, None],
) -> None:
    created = create_rule(client, auth_headers(), keyword="Null safety").json()

    with TestClient(app, raise_server_exceptions=False) as non_raising_client:
        response = non_raising_client.put(
            f"/categorization-rules/{created['id']}",
            headers=auth_headers(),
            json=payload,
        )

    assert response.status_code == 422
