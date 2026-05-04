import os
from pathlib import Path

from fastapi.testclient import TestClient


def _test_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test-learning.db")


def test_health_endpoint(tmp_path):
    os.environ["LEARNING_DB_PATH"] = _test_db_path(tmp_path)
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login_flow(tmp_path):
    os.environ["LEARNING_DB_PATH"] = _test_db_path(tmp_path)
    from app.main import app

    with TestClient(app) as client:
        register_response = client.post(
            "/register",
            data={
                "full_name": "Student One",
                "email": "student1@example.com",
                "password": "strongpass1",
                "role": "student",
            },
            follow_redirects=False,
        )
        assert register_response.status_code == 303

        login_response = client.post(
            "/login",
            data={"email": "student1@example.com", "password": "strongpass1"},
            follow_redirects=False,
        )
        assert login_response.status_code == 303
        assert login_response.headers["location"] == "/dashboard"
