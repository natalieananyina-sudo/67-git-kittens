"""Общие фикстуры. Тесты лежат в /tests, код сервиса — в /backend: добавляем его в путь импорта."""
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.security import reset_failures  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_login_limiter():
    reset_failures()
    yield
    reset_failures()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth_headers(client):
    response = client.post("/api/v1/auth/login", json={"login": settings.doctor_login, "password": settings.doctor_password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def set_setting(name, value):
    object.__setattr__(settings, name, value)
