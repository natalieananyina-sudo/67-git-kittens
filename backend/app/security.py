"""Мок-авторизация врача: одна фиксированная пара логин/пароль + подписанный токен (JWT)."""
import secrets
import time
from collections import defaultdict, deque

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False, description="Токен из POST /api/v1/auth/login")

# Простейшая защита от перебора пароля: клиент -> моменты неудачных попыток.
_failures: dict[str, deque] = defaultdict(deque)


def check_credentials(login: str, password: str) -> bool:
    """Сравнение в постоянное время: по скорости ответа нельзя угадать, какая часть верна."""
    login_ok = secrets.compare_digest(login.encode("utf-8"), settings.doctor_login.encode("utf-8"))
    password_ok = secrets.compare_digest(password.encode("utf-8"), settings.doctor_password.encode("utf-8"))
    return login_ok and password_ok


def retry_after_seconds(client_key: str) -> int:
    """Если клиент заблокирован, возвращает, сколько секунд осталось ждать; иначе 0."""
    now = time.monotonic()
    attempts = _failures[client_key]
    while attempts and now - attempts[0] > settings.login_window_seconds:
        attempts.popleft()
    if len(attempts) >= settings.login_max_failures:
        return int(settings.login_window_seconds - (now - attempts[0])) + 1
    return 0


def register_failure(client_key: str) -> None:
    _failures[client_key].append(time.monotonic())


def reset_failures() -> None:
    _failures.clear()


def create_access_token(login: str) -> str:
    now = int(time.time())
    payload = {"sub": login, "name": settings.doctor_name, "role": "doctor", "iat": now, "exp": now + settings.token_ttl_seconds}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def get_current_doctor(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Зависимость FastAPI: пропускает запрос только с действующим токеном врача."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется авторизация. Войдите в систему.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise unauthorized from None
    if payload.get("role") != "doctor" or payload.get("sub") != settings.doctor_login:
        raise unauthorized
    return {"login": payload["sub"], "display_name": payload.get("name", ""), "role": "doctor"}
