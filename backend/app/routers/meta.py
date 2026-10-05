from fastapi import APIRouter

from ..config import settings
from ..engine import analytes as an
from ..engine.predictor import get_predictor, model_info

router = APIRouter(tags=["Служебные"])


@router.get("/health", summary="Проверка работоспособности и текущая модель")
def health():
    return {"status": "ok", "version": settings.app_version, "model": model_info(get_predictor())}


@router.get("/analytes", summary="Справочник показателей: названия, единицы датасета, альтернативные единицы, референсы")
def analytes_catalog():
    return an.public_catalog()
