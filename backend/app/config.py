"""Настройки сервиса. Все значения можно переопределить переменными окружения."""
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ======================================================================
#  ДЕМО-УЧЁТНАЯ ЗАПИСЬ ВРАЧА (мок-авторизация)
# ----------------------------------------------------------------------
#  Работает ТОЛЬКО эта пара логин/пароль. Любая другая комбинация даёт 401.
#  Значения записаны в коде осознанно: это демонстрационный контур
#  хакатона, реальных пользователей и реальных данных здесь нет.
#  Для другого стенда их можно переопределить переменными окружения
#  DEMO_DOCTOR_LOGIN / DEMO_DOCTOR_PASSWORD, не меняя код.
#  Не используйте этот пароль нигде, кроме демо.
# ======================================================================
DEMO_DOCTOR_LOGIN = "doctor_demo"
DEMO_DOCTOR_PASSWORD = "y7pr-gHXm-Pb9w"
DEMO_DOCTOR_NAME = "Врач"   # имя в шапке интерфейса

# Ключ подписи токенов. В реальной системе он берётся только из окружения.
_DEV_JWT_SECRET = "84a53c4850f63d18b033d3c3c91329b30d58730ac8e3f1bbc009a6df223d7e10"


def _load_config_file() -> None:
    """Подхватывает config/backend.env (строки KEY=VALUE). Уже заданные переменные окружения важнее файла."""
    path = Path(os.getenv("CONFIG_FILE", str(BASE_DIR.parent / "config" / "backend.env")))
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value.strip():
            os.environ.setdefault(key.strip(), value.strip())


_load_config_file()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_version: str = "1.0.0"

    # Авторизация
    doctor_login: str = field(default_factory=lambda: os.getenv("DEMO_DOCTOR_LOGIN", DEMO_DOCTOR_LOGIN))
    doctor_password: str = field(default_factory=lambda: os.getenv("DEMO_DOCTOR_PASSWORD", DEMO_DOCTOR_PASSWORD))
    doctor_name: str = DEMO_DOCTOR_NAME
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET") or _DEV_JWT_SECRET)
    token_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("TOKEN_TTL_SECONDS", str(8 * 3600))))
    login_max_failures: int = 5          # неудачных попыток ...
    login_window_seconds: int = 300      # ... за это окно, после чего вход блокируется

    # CORS (нужен только при запуске фронтенда на другом порту без прокси)
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
            ).split(",")
            if o.strip()
        )
    )

    # ML-модуль команды Data Science лежит в backend/ml без изменений (см. backend/ml/README_ML.md).
    # ML_MODE: auto (модель, при сбое загрузки — демо-резерв) | model (только модель) | demo
    ml_mode: str = field(default_factory=lambda: os.getenv("ML_MODE", "auto").lower())
    ml_package_dir: Path = field(default_factory=lambda: Path(os.getenv("ML_PACKAGE_DIR", str(BASE_DIR / "ml"))))
    ml_model_path: Path = field(
        default_factory=lambda: Path(os.getenv("ML_MODEL_PATH", str(BASE_DIR / "ml" / "artifacts" / "models" / "final" / "pipeline.joblib")))
    )

    @property
    def ml_paths(self):
        from .engine.predictor import MlPaths

        return MlPaths(self.ml_package_dir, self.ml_model_path, self.ml_model_path.parent / "model_manifest.json")

    # Пакетная загрузка
    max_upload_bytes: int = 5 * 1024 * 1024
    max_batch_rows: int = 1000           # ML-модуль обрабатывает ~10–20 мс на строку: 1000 строк ≈ 10–20 с

    # Показ блоков «Рекомендуемое лечение» из заключений медицинского эксперта.
    # По умолчанию ВЫКЛЮЧЕНО: концепция MVP запрещает назначать лечение.
    include_treatment_hints: bool = field(default_factory=lambda: _env_bool("INCLUDE_TREATMENT_HINTS", False))


settings = Settings()
