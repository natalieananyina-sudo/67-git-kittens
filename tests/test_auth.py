import jwt

from app.config import settings


def _login(client, login, password):
    return client.post("/api/v1/auth/login", json={"login": login, "password": password})


def test_only_the_demo_pair_works(client):
    assert _login(client, settings.doctor_login, settings.doctor_password).status_code == 200
    for login, password in [
        (settings.doctor_login, "wrong"), ("wrong", settings.doctor_password), ("admin", "admin"),
        (settings.doctor_login.upper(), settings.doctor_password), (settings.doctor_login, settings.doctor_password + " "),
    ]:
        assert _login(client, login, password).status_code == 401, (login, password)
    assert _login(client, "", "x").status_code == 422


def test_same_message_for_wrong_login_and_wrong_password(client):
    a = _login(client, "nobody", settings.doctor_password).json()
    b = _login(client, settings.doctor_login, "nope").json()
    assert a == b == {"detail": "Неверный логин или пароль."}


def test_protected_endpoints_need_token(client):
    for method, path in [("get", "/api/v1/auth/me"), ("post", "/api/v1/screening"), ("post", "/api/v1/screening/file"),
                         ("post", "/api/v1/screening/batch"),
                         ("get", "/api/v1/screening/batch/template")]:
        assert getattr(client, method)(path).status_code == 401, path
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_organizations_endpoint_removed(client, auth_headers):
    assert client.get("/api/v1/organizations", headers=auth_headers).status_code == 404


def test_me_with_valid_token(client, auth_headers):
    body = client.get("/api/v1/auth/me", headers=auth_headers).json()
    assert body["login"] == settings.doctor_login and body["role"] == "doctor"


def test_expired_and_foreign_tokens_rejected(client):
    expired = jwt.encode({"sub": settings.doctor_login, "role": "doctor", "exp": 1}, settings.jwt_secret, algorithm="HS256")
    foreign = jwt.encode({"sub": settings.doctor_login, "role": "doctor", "exp": 9999999999}, "x" * 40, algorithm="HS256")
    for token in (expired, foreign):
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_brute_force_is_throttled(client):
    for _ in range(settings.login_max_failures):
        assert _login(client, settings.doctor_login, "bad").status_code == 401
    blocked = _login(client, settings.doctor_login, settings.doctor_password)
    assert blocked.status_code == 429 and "Retry-After" in blocked.headers
