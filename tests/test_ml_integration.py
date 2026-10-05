"""Интеграция ML-модуля (backend/ml) с бэкендом.

Проверяем, что бэкенд:
* вызывает модуль так, как описано в README_ML.md, и получает тот же ответ, что и smoke-test модуля;
* не меняет решение модуля и умеет показывать по-русски все его значения;
* загружает только «замороженный» файл модели (SHA-256 из паспорта);
* при сбое загрузки в режиме auto переходит на демо-резерв, а в режиме model — останавливается.
"""
import json
import shutil
from pathlib import Path

import pytest

from app.config import settings
from app.engine import labels as lb
from app.engine.pipeline import screen
from app.engine.predictor import DemoPredictor, MlModulePredictor, MlPaths, build_predictor, get_predictor
from app.engine.validation import validate_case

ML_DIR = Path(settings.ml_package_dir)
EXAMPLE_IN = json.loads((ML_DIR / "example_patient.json").read_text(encoding="utf-8"))
EXAMPLE_OUT = json.loads((ML_DIR / "example_output.json").read_text(encoding="utf-8"))


def _example_case():
    """example_patient.json модуля -> через проверку формата бэкенда (как пришло бы из файла)."""
    labs = {k: v for k, v in EXAMPLE_IN.items() if k not in ("patient_id", "age_years", "sex")}
    check = validate_case(EXAMPLE_IN["patient_id"], EXAMPLE_IN["age_years"], EXAMPLE_IN["sex"], labs)
    assert check.case is not None, check.errors
    return check.case


def test_backend_reproduces_ml_smoke_test():
    """То же, что `python example_inference.py`, но через бэкенд."""
    ml = get_predictor().predict(_example_case())
    for field in ("status", "anemia", "deficiency_cause", "anemia_class"):
        assert ml[field] == EXAMPLE_OUT[field], field
    assert ml["model_score"] == pytest.approx(EXAMPLE_OUT["model_score"])


def test_pipeline_passes_ml_result_unchanged():
    result = screen(_example_case())
    ml = result["ml_result"]
    assert ml["anemia_class"] == result["anemia_class"] == EXAMPLE_OUT["anemia_class"]
    assert ml["deficiency_cause_scores"] == pytest.approx(EXAMPLE_OUT["deficiency_cause_scores"])
    assert result["anemia"]["detected"] is bool(EXAMPLE_OUT["anemia"])
    assert result["model"]["name"] == "anemia_hierarchical_rf_masked_v1" and result["model"]["is_demo"] is False


def test_batch_equals_single():
    """predict_many (один вызов леса на файл) даёт ровно то же, что поштучный predict."""
    predictor = get_predictor()
    base = _example_case()
    cases = [base]
    for factor in (0.85, 1.1, 1.2):
        labs = {k: v * factor for k, v in base.labs.items()}
        cases.append(validate_case(f"B{factor}", 40, "male", labs).case)
    assert all(cases), "масштабированные значения вышли за допустимые диапазоны"
    cases.append(validate_case("NOHB", 40, "female", {"ferritin": 10}).case)   # insufficient_data в середине
    cases.append(validate_case("LAST", 60, "female", base.labs).case)
    assert predictor.predict_many(cases) == [predictor.predict(c) for c in cases]


def test_display_threshold_matches_ml_rule():
    """Порог в подписи «… при пороге 120 г/л» совпадает с правилом внутри ML-модуля."""
    from src.ml.rules import apply_anemia_rule

    for sex, code in (("female", "F"), ("male", "M")):
        threshold = lb.HB_DISPLAY_THRESHOLD[sex]
        assert apply_anemia_rule(code, threshold - 0.1) == 1
        assert apply_anemia_rule(code, threshold) == 0


def test_every_ml_value_has_russian_label():
    from src.ml.config import LAB_PANELS
    from src.ml.postprocessing import POSTPROCESSING_MAP, VALID_CAUSES_BY_ANEMIA

    assert set(POSTPROCESSING_MAP.values()) == set(lb.ANEMIA_CLASS_LABELS)
    assert set().union(*VALID_CAUSES_BY_ANEMIA.values()) == set(lb.CAUSE_LABELS)
    assert set(LAB_PANELS) == set(lb.PANEL_LABELS)
    assert len(lb.ANEMIA_CLASS_LABELS) == 12


@pytest.mark.parametrize("sex,labs,reason", [
    ("female", {"ferritin": 10, "vitamin_b12": 300}, "missing_hemoglobin"),
    (None, {"hemoglobin": 110}, "missing_sex"),
    ("male", {"hemoglobin": 110, "ferritin": 10}, "multiple_fully_missing_panels"),
])
def test_insufficient_data_comes_from_ml_module(sex, labs, reason):
    result = screen(validate_case("IN1", 40, sex, labs).case)
    assert result["screening_status"] == "insufficient_data" and result["ml_result"]["reason"] == reason
    assert result["anemia_class"] is None and result["anemia_class_label"] == lb.INSUFFICIENT_LABEL
    assert result["report"]["severity"] == "insufficient"
    assert result["insufficient_reason"] == lb.REASON_LABELS[reason]


def test_tampered_model_file_is_rejected(tmp_path):
    shutil.copytree(ML_DIR / "artifacts", tmp_path / "artifacts")
    model = tmp_path / "artifacts" / "models" / "final" / "pipeline.joblib"
    with model.open("ab") as file:
        file.write(b"tampered")
    paths = MlPaths(ML_DIR, model, model.parent / "model_manifest.json")
    with pytest.raises(RuntimeError, match="SHA-256"):
        MlModulePredictor(paths.package_dir, paths.model_path, paths.manifest_path)
    with pytest.raises(RuntimeError):
        build_predictor("model", paths)
    fallback = build_predictor("auto", paths)
    assert isinstance(fallback, DemoPredictor) and fallback.info["is_demo"] is True and "SHA-256" in fallback.info["note"]


def test_missing_model_falls_back_to_demo_in_auto_mode(tmp_path):
    paths = MlPaths(ML_DIR, tmp_path / "nope.joblib", tmp_path / "model_manifest.json")
    predictor = build_predictor("auto", paths)
    assert isinstance(predictor, DemoPredictor)
    result = screen(_example_case(), predictor)
    # в демо-режиме правило анемии и постобработка — всё равно код ML-модуля
    assert result["ml_result"]["anemia"] == 1 and result["anemia_class"] in lb.ANEMIA_CLASS_LABELS
    assert result["model"]["kind"] == "demo_fallback"


def test_health_reports_model(client):
    model = client.get("/api/v1/health").json()["model"]
    assert model["kind"] == "ml_model" and model["version"] == "1.0.0" and model["test_macro_f1"] == pytest.approx(0.8835)
