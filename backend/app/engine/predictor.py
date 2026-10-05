"""Подключение ML-модуля команды Data Science (папка backend/ml, пакет `src.ml`).

Разделение ответственности (по README_ML.md, который пришёл вместе с моделью):
* ML-модуль сам делает ВСЁ, что относится к расчёту: проверку достаточности данных, клиническое правило
  анемии (пол + гемоглобин), preprocessing, модель deficiency_cause, constrained postprocessing
  и итоговый anemia_class. Бэкенд эту логику НЕ дублирует и результат НЕ пересчитывает.
* Бэкенд отвечает за то, что вокруг: чтение и проверку формата файлов, приведение единиц к единицам
  датасета, передачу данных в модуль и превращение ответа модуля в понятный врачу и пациенту текст.

Режимы (переменная ML_MODE, см. config/backend.env):
* model — только финальная модель; если её не удалось загрузить, бэкенд не запускается;
* auto  — финальная модель, а если она не загрузилась — демо-резерв с предупреждением в интерфейсе;
* demo  — всегда демо-резерв (для разработки интерфейса без модели).

Демо-резерв подменяет ТОЛЬКО классификатор (Random Forest) простыми лабораторными критериями.
Правило анемии, проверка данных и postprocessing и в этом режиме выполняются кодом ML-модуля.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from . import analytes as an
from .validation import CaseInput

log = logging.getLogger("screening.ml")

# Ключи ответа ML-модуля (контракт из README_ML.md)
RESULT_KEYS = (
    "patient_id", "status", "reason", "data_sufficient", "anemia", "deficiency_cause", "anemia_class",
    "missing_panels", "deficiency_cause_scores", "model_score",
)


class Predictor(Protocol):
    """Всё, что нужно бэкенду от модели: один метод predict и описание версии."""

    info: dict

    def predict(self, case: CaseInput) -> dict[str, Any]: ...

    def predict_many(self, cases: list[CaseInput]) -> list[dict[str, Any]]: ...


def model_info(predictor: Predictor) -> dict:
    return predictor.info


def _import_ml_package(package_dir: Path):
    """Делает импортируемым пакет `src.ml` из backend/ml (так его подключает README_ML.md)."""
    path = str(package_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
    import src.ml  # noqa: F401  — проверяем, что пакет и его зависимости доступны
    from src.ml import AnemiaInferenceService

    return AnemiaInferenceService


def to_model_input(case: CaseInput) -> dict[str, Any]:
    """Случай после проверки -> словарь в формате входа модели.

    Ключи — названия столбцов исходного датасета (hemoglobin, MCV, vitamin_B12, ...), значения уже
    переведены в единицы датасета (variables.xlsx). Отсутствующие показатели просто не передаются:
    модуль сам превратит их в NaN. Пол: F / M, как в датасете.
    """
    data: dict[str, Any] = {
        "patient_id": case.case_id,
        "age_years": case.age,
        "sex": {"female": "F", "male": "M"}.get(case.sex or ""),
    }
    for key, value in case.labs.items():
        data[an.BY_KEY[key].code] = value
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
#  1. Финальная модель
# ---------------------------------------------------------------------------
class MlModulePredictor:
    """Обёртка над AnemiaInferenceService: перед загрузкой сверяет SHA-256 файла с паспортом модели."""

    def __init__(self, package_dir: Path, model_path: Path, manifest_path: Path):
        service_class = _import_ml_package(package_dir)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest.get("model_sha256")
        actual = _sha256(model_path)
        if expected and actual != expected:
            raise RuntimeError(
                f"Файл модели {model_path} не совпадает с паспортом (SHA-256 {actual[:12]}… вместо {expected[:12]}…). "
                "Модель заморожена: используйте файл из поставки ML-команды."
            )
        self.service = service_class(model_path)
        metrics = manifest.get("test_metrics", {})
        self.info = {
            "kind": "ml_model",
            "is_demo": False,
            "name": manifest.get("model_name", "unknown"),
            "version": str(manifest.get("version", "unknown")),
            "architecture": "Hierarchical Random Forest + panel masking",
            "test_macro_f1": metrics.get("macro_f1"),
            "note": None,
        }

    def predict(self, case: CaseInput) -> dict[str, Any]:
        return self.service.predict(to_model_input(case))

    def predict_many(self, cases: list[CaseInput]) -> list[dict[str, Any]]:
        """Много пациентов: лес из 500 деревьев вызывается один раз на весь файл, а не на каждую строку.

        Логику модуля не повторяем: сначала одним вызовом predict_proba считаем вероятности для всех строк
        (вход готовит тот же _prepare_input модуля), затем для каждой строки вызываем обычный
        AnemiaInferenceService.predict, у которого классификатор заменён на таблицу уже посчитанных ответов.
        Результат совпадает с поштучным вызовом — это проверяет тест test_batch_equals_single.
        """
        if not cases:
            return []
        import pandas as pd

        inputs = [to_model_input(c) for c in cases]
        frame = pd.concat([self.service._prepare_input(d) for d in inputs], ignore_index=True)
        table = _PrecomputedProbabilities(self.service.pipeline.predict_proba(frame))

        batch_service = object.__new__(type(self.service))  # отдельный экземпляр: потокобезопасно
        batch_service.model_path = self.service.model_path
        batch_service.model_classes = self.service.model_classes
        batch_service.pipeline = table
        results = []
        for index, data in enumerate(inputs):
            table.current = index   # predict() вызывает predict_proba не больше одного раза
            results.append(batch_service.predict(data))
        return results


class _PrecomputedProbabilities:
    """Вместо классификатора: отдаёт заранее посчитанные вероятности для текущей строки."""

    def __init__(self, probabilities):
        self.probabilities = probabilities
        self.current = 0

    def predict_proba(self, _frame):
        return [self.probabilities[self.current]]


# ---------------------------------------------------------------------------
#  2. Демо-резерв: заменяет только классификатор
# ---------------------------------------------------------------------------
DEMO_NOTE = (
    "Финальная ML-модель не загружена: причину дефицита оценивает упрощённая схема по лабораторным "
    "критериям. Правило анемии и проверка данных — из ML-модуля. Результат не валидирован."
)

# Классы deficiency_cause, которые умеет выдавать модель (src/ml/postprocessing.py)
CAUSE_CLASSES = (
    "none", "iron_deficiency", "B12_deficiency", "folate_deficiency", "B6_deficiency", "copper_deficiency",
    "inflammation", "iron_B12", "iron_folate", "B12_folate", "undetermined",
)


def _points_score(points: float) -> float:
    """Логистическое сжатие баллов в 0..1 (2 балла ≈ 0,5)."""
    return 1 / (1 + math.exp(-(points - 2.0) * 1.2))


def _demo_state_scores(labs: dict[str, float], sex: str) -> dict[str, float]:
    """Баллы по лабораторным критериям для шести базовых состояний. Пороги — общепринятые ориентиры,
    подробности в docs/ml_integration.md. Ключи labs: коды показателей в нижнем регистре."""
    g = labs.get
    inflamed = g("crp", 0) > 5 or g("esr", 0) > (20 if sex == "F" else 15) * 1.5
    pts = dict.fromkeys(("iron", "b12", "folate", "b6", "copper", "inflammation"), 0.0)

    ferritin, tsat = g("ferritin"), g("tsat")
    if ferritin is not None:
        if inflamed:  # при воспалении ферритин ложно повышен — нужен низкий TSAT
            pts["iron"] += 2.5 if ferritin < 100 and tsat is not None and tsat < 20 else 0
        else:
            pts["iron"] += 3.5 if ferritin < 15 else 2.0 if ferritin < 30 else 0
    if tsat is not None:
        pts["iron"] += 1.5 if tsat < 16 else 0.8 if tsat < 20 else 0
    pts["iron"] += 1.5 * (g("stfr", 0) > 4.4) + 1.5 * (g("ret_he", 99) < 28) + 0.8 * (g("mcv", 99) < 80)

    b12, holo = g("vitamin_b12"), g("active_b12")
    if b12 is not None:
        pts["b12"] += 3.0 if b12 < 200 else 1.2 if b12 < 300 else 0
    if holo is not None:
        pts["b12"] += 2.5 if holo < 25 else 1.2 if holo < 50 else 0
    pts["b12"] += 2.0 * (g("mma", 0) > 0.4) + 1.0 * (g("homocysteine", 0) > 15) + 1.0 * (g("mcv", 0) > 100)

    folate = g("folate")
    if folate is not None:
        pts["folate"] += 3.0 if folate < 4 else 1.2 if folate < 6 else 0
    pts["folate"] += 0.8 * (g("homocysteine", 0) > 15) + 1.0 * (g("mcv", 0) > 100)

    b6 = g("vitamin_b6")
    if b6 is not None:
        pts["b6"] += 3.0 if b6 < 20 else 1.0 if b6 < 30 else 0
    pts["b6"] += 1.0 * (g("mcv", 99) < 80 and g("ferritin", 0) >= 100)

    copper = g("copper")
    if copper is not None:
        pts["copper"] += 3.0 if copper < 9 else 2.5 if copper < 11 else 0
    pts["copper"] += 2.5 * (g("ceruloplasmin", 99) < 0.2) + 0.7 * (g("wbc", 99) < 4.0)

    crp, esr = g("crp"), g("esr")
    if crp is not None:
        pts["inflammation"] += 3.0 if crp > 20 else 2.0 if crp > 5 else 0
    if esr is not None:
        pts["inflammation"] += 1.5 if esr > 40 else 1.0 if esr > (20 if sex == "F" else 15) else 0
    pts["inflammation"] += 1.0 * (g("ferritin", 0) > 200 and g("tsat", 99) < 20) + 0.5 * (g("albumin", 99) < 35)

    return {k: _points_score(v) for k, v in pts.items()}


class _DemoClassifier:
    """Повторяет интерфейс sklearn-классификатора, который ожидает AnemiaInferenceService:
    predict_proba(X) и classes_."""

    classes_ = CAUSE_CLASSES

    def predict_proba(self, frame) -> list[list[float]]:
        rows = []
        for _, row in frame.iterrows():
            labs = {col.lower(): float(v) for col, v in row.items() if col not in ("sex", "age_years") and v == v}
            s = _demo_state_scores(labs, str(row["sex"]))
            no = {k: 1 - v for k, v in s.items()}
            core_free = no["iron"] * no["b12"] * no["folate"]
            healthy = core_free * no["b6"] * no["copper"] * no["inflammation"]
            weights = {
                "none": healthy,
                "undetermined": healthy,  # допустим только при анемии; «none» тогда исключит постобработка
                "iron_deficiency": s["iron"] * no["b12"] * no["folate"],
                "B12_deficiency": s["b12"] * no["iron"] * no["folate"],
                "folate_deficiency": s["folate"] * no["iron"] * no["b12"],
                "B6_deficiency": s["b6"] * core_free,
                "copper_deficiency": s["copper"] * core_free,
                "inflammation": s["inflammation"] * core_free,
                "iron_B12": s["iron"] * s["b12"],
                "iron_folate": s["iron"] * s["folate"],
                "B12_folate": s["b12"] * s["folate"],
            }
            total = sum(weights.values())
            rows.append([weights[c] / total for c in CAUSE_CLASSES])
        return rows


class DemoPredictor:
    """Код ML-модуля (AnemiaInferenceService.predict) с подменённым классификатором."""

    def __init__(self, package_dir: Path, reason: str | None = None):
        service_class = _import_ml_package(package_dir)

        class _DemoService(service_class):
            def __init__(self):  # файл модели не загружаем
                self.model_path = None
                self.pipeline = _DemoClassifier()
                self.model_classes = list(CAUSE_CLASSES)

        self.service = _DemoService()
        note = DEMO_NOTE + (f" Причина: {reason}" if reason else "")
        self.info = {"kind": "demo_fallback", "is_demo": True, "name": "demo_lab_criteria", "version": "demo-0.3",
                     "architecture": "Лабораторные критерии (без обучения)", "test_macro_f1": None, "note": note}

    def predict(self, case: CaseInput) -> dict[str, Any]:
        return self.service.predict(to_model_input(case))

    def predict_many(self, cases: list[CaseInput]) -> list[dict[str, Any]]:
        return [self.predict(c) for c in cases]


# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MlPaths:
    package_dir: Path
    model_path: Path
    manifest_path: Path


def build_predictor(mode: str, paths: MlPaths) -> Predictor:
    if mode == "demo":
        return DemoPredictor(paths.package_dir)
    try:
        return MlModulePredictor(paths.package_dir, paths.model_path, paths.manifest_path)
    except Exception as exc:  # noqa: BLE001 — в режиме auto любая ошибка загрузки ведёт к демо-резерву
        if mode == "model":
            raise
        log.error("ML-модель не загружена, включён демо-резерв: %s", exc)
        return DemoPredictor(paths.package_dir, reason=f"{type(exc).__name__}: {exc}")


_predictor: Predictor | None = None


def get_predictor() -> Predictor:
    """Модель загружается один раз (≈1 с) и переиспользуется всеми запросами."""
    global _predictor
    if _predictor is None:
        from ..config import settings

        _predictor = build_predictor(settings.ml_mode, settings.ml_paths)
    return _predictor


def set_predictor(predictor: Predictor | None) -> None:
    """Для тестов: подмена модели."""
    global _predictor
    _predictor = predictor
