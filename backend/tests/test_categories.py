from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient


AuthHeaders = Callable[[str], dict[str, str]]


def create_category(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    color: str = "#2563EB",
):
    return client.post(
        "/categories",
        headers=headers,
        json={"name": name, "color": color},
    )


def test_category_crud(client: TestClient, auth_headers: AuthHeaders) -> None:
    created = create_category(
        client,
        auth_headers(),
        name=" Travel ",
        color="#2563eb",
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Travel"
    assert body["color"] == "#2563EB"
    assert body["is_global"] is False
    assert "user_id" not in body

    listed = client.get("/categories", headers=auth_headers())
    assert listed.status_code == 200
    assert body["id"] in {item["id"] for item in listed.json()["items"]}

    updated = client.put(
        f"/categories/{body['id']}",
        headers=auth_headers(),
        json={"name": "Trips", "color": "#7c3aed"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Trips"
    assert updated.json()["color"] == "#7C3AED"

    deleted = client.delete(f"/categories/{body['id']}", headers=auth_headers())
    assert deleted.status_code == 204
    assert client.put(
        f"/categories/{body['id']}",
        headers=auth_headers(),
        json={"name": "Missing", "color": "#111827"},
    ).status_code == 404


def test_categories_include_defaults_but_exclude_other_users_custom_rows(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    own = create_category(client, auth_headers(user_a_id), name="Own").json()
    create_category(client, auth_headers(user_b_id), name="Other user")

    items = client.get(
        "/categories",
        headers=auth_headers(user_a_id),
    ).json()["items"]

    assert own["id"] in {item["id"] for item in items}
    assert "Other user" not in {item["name"] for item in items}
    assert {item["name"] for item in items if item["is_global"]} == {
        "Housing",
        "Groceries",
        "Dining",
        "Transport",
        "Utilities",
        "Health",
        "Entertainment",
        "Shopping",
        "Salary",
        "Other",
    }
    global_count = len([item for item in items if item["is_global"]])
    assert [item["is_global"] for item in items[:global_count]] == [True] * global_count


def test_global_categories_are_read_only(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    global_category = next(
        item
        for item in client.get("/categories", headers=auth_headers()).json()["items"]
        if item["is_global"]
    )
    assert client.put(
        f"/categories/{global_category['id']}",
        headers=auth_headers(),
        json={"name": "Changed", "color": "#111827"},
    ).status_code == 403
    assert client.delete(
        f"/categories/{global_category['id']}",
        headers=auth_headers(),
    ).status_code == 403


def test_category_mutations_are_isolated(
    client: TestClient,
    auth_headers: AuthHeaders,
    user_a_id: str,
    user_b_id: str,
) -> None:
    category = create_category(client, auth_headers(user_a_id), name="Private").json()
    assert client.put(
        f"/categories/{category['id']}",
        headers=auth_headers(user_b_id),
        json={"name": "Stolen", "color": "#111827"},
    ).status_code == 404
    assert client.delete(
        f"/categories/{category['id']}",
        headers=auth_headers(user_b_id),
    ).status_code == 404


def test_category_validation_duplicates_and_bad_ids(
    client: TestClient,
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers()
    assert create_category(client, headers, name="Travel").status_code == 201
    assert create_category(client, headers, name="travel").status_code == 409
    assert create_category(client, headers, name="   ").status_code == 422
    assert create_category(client, headers, name="x" * 81).status_code == 422
    assert create_category(client, headers, name="Valid", color="blue").status_code == 422
    assert client.put(
        "/categories/not-a-uuid",
        headers=headers,
        json={"name": "Valid", "color": "#111827"},
    ).status_code == 422
    assert client.delete(f"/categories/{uuid4()}", headers=headers).status_code == 404
