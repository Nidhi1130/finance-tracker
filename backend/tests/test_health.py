import os

from fastapi.testclient import TestClient

os.environ.pop("DATABASE_URL", None)
os.environ.pop("SUPABASE_JWT_SECRET", None)

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200


def test_phase2_preview_origin_is_allowed() -> None:
    response = client.options(
        "/categories",
        headers={
            "Origin": "http://localhost:3100",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3100"
