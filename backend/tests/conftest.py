from __future__ import annotations

import base64
import json
import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient


os.environ.pop("DATABASE_URL", None)
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_JWT_SECRET", None)

from app.main import app
from app.repositories import category_repository, transaction_repository


USER_A_ID = "10000000-0000-4000-8000-000000000001"
USER_B_ID = "20000000-0000-4000-8000-000000000002"


def build_bearer_token(user_id: str) -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode(),
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id}).encode(),
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.signature"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    def build(user_id: str = USER_A_ID) -> dict[str, str]:
        return {"Authorization": f"Bearer {build_bearer_token(user_id)}"}

    return build


@pytest.fixture
def user_a_id() -> str:
    return USER_A_ID


@pytest.fixture
def user_b_id() -> str:
    return USER_B_ID


@pytest.fixture(autouse=True)
def clear_repositories() -> None:
    transaction_repository.clear()
    category_repository.clear()
