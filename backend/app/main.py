"""Точка входа FastAPI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .engine.predictor import get_predictor
from .routers import auth, meta, screening

DESCRIPTION = """
Сервис скрининга анемий и латентных дефицитных состояний.

**Что сервис делает:** проверяет формат данных и приводит значения к единицам датасета, передаёт их в ML-модуль
(`backend/ml`, модель *Hierarchical Random Forest + panel masking*), который проверяет достаточность данных,
определяет анемию по клиническому правилу (гемоглобин и пол), причину (`deficiency_cause`) и итоговый класс
(`anemia_class`). По ответу модуля сервис формирует два представления результата: для врача и для пациента.

`model_score` и `deficiency_cause_scores` — технические оценки модели, а не вероятности диагноза.

**Чего сервис не делает:** не ставит диагноз и не назначает лечение. Персональные данные не принимаются 
(только псевдонимизированный ID), данные пациентов не сохраняются.
"""

@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_predictor()  # модель загружается при старте: ошибки видны сразу, первый запрос не ждёт загрузки
    yield


app = FastAPI(title="Скрининг анемий: API", version=settings.app_version, description=DESCRIPTION,
              docs_url="/docs", redoc_url=None, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"   # ответы с медицинскими данными не кэшируются
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Единый формат ошибок ввода: {"status": "error", "errors": [{"field", "message"}]}."""
    errors = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", []) if p != "body") or "body"
        kind = err.get("type", "")
        if kind == "missing":
            message = "Обязательное поле не заполнено."
        elif "parsing" in kind or "type" in kind:
            message = "Некорректное значение (ожидается число)."
        else:
            message = "Некорректное значение."
        errors.append({"field": field, "message": message})
    return JSONResponse(status_code=422, content={"status": "error", "errors": errors})


app.include_router(meta.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(screening.router, prefix="/api/v1")
