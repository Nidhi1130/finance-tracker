import os

from fastapi.testclient import TestClient

os.environ.pop("DATABASE_URL", None)
os.environ.pop("SUPABASE_JWT_SECRET", None)

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
