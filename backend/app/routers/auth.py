"""Авторизация врача (мок): одна демо-учётная запись, токен JWT."""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import settings
from ..schemas import LoginRequest, TokenResponse, UserInfo
from ..security import check_credentials, create_access_token, get_current_doctor, register_failure, retry_after_seconds

router = APIRouter(tags=["Авторизация"])


@router.post(
    "/auth/login", response_model=TokenResponse, summary="Вход врача (демо-учётная запись)",
    responses={401: {"description": "Неверный логин или пароль"}, 429: {"description": "Слишком много неудачных попыток"}},
)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    client_key = request.client.host if request.client else "unknown"
    wait = retry_after_seconds(client_key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Слишком много неудачных попыток входа. Повторите через {wait} с.",
                            headers={"Retry-After": str(wait)})
    if not check_credentials(body.login, body.password):
        register_failure(client_key)
        # Одно и то же сообщение для неверного логина и неверного пароля: не подсказываем, что из них верно
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль.")
    return TokenResponse(
        access_token=create_access_token(settings.doctor_login),
        expires_in=settings.token_ttl_seconds,
        user=UserInfo(login=settings.doctor_login, display_name=settings.doctor_name, role="doctor"),
    )


@router.get("/auth/me", response_model=UserInfo, summary="Текущий пользователь")
def me(doctor: dict = Depends(get_current_doctor)) -> UserInfo:
    return UserInfo(**doctor)
