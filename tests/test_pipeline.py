"""Заключения: какие тексты получает врач и пациент при каждом решении ML-модуля.

Чтобы проверить тексты для всех причин детерминированно, здесь используется заглушка модели,
возвращающая заданный ответ в формате ML-модуля. Работу настоящей модели проверяют
test_ml_integration.py и test_demo_data.py.
"""
import pytest

from app.engine import demo_data
from app.engine import labels as lb
from app.engine.pipeline import screen
from app.engine.validation import validate_case

from .conftest import set_setting

LABS = demo_data.examples()[1]["input"]["laboratory_data"]   # полный набор показателей


class StubPredictor:
    info = {"kind": "ml_model", "is_demo": False, "name": "stub", "version": "0", "architecture": "stub",
            "test_macro_f1": None, "note": None}

    def __init__(self, anemia, cause, anemia_class):
        self.answer = {"patient_id": None, "status": "no_signal_detected" if (anemia, cause) == (0, "none") else "signal_detected",
                       "reason": None, "data_sufficient": True, "anemia": anemia, "deficiency_cause": cause,
                       "anemia_class": anemia_class, "missing_panels": [], "deficiency_cause_scores": {cause: 0.7, "undetermined": 0.2},
                       "model_score": 0.7}

    def predict(self, case):
        return dict(self.answer, patient_id=case.case_id)

    def predict_many(self, cases):
        return [self.predict(c) for c in cases]


def _run(anemia, cause, sex="female", **labs):
    from src.ml.postprocessing import get_anemia_class

    hb = 105 if anemia else 140
    case = validate_case("T1", 45, sex, {**LABS, "hemoglobin": hb, **labs}).case
    return screen(case, StubPredictor(anemia, cause, get_anemia_class(anemia, cause)))


def _titles(view):
    return [s["title"] for s in view["sections"]]


def _items(view):
    return [i for s in view["sections"] for i in s["items"]]


ALL_PAIRS = [(0, c) for c in ("none", "iron_deficiency", "B12_deficiency", "folate_deficiency", "B6_deficiency", "copper_deficiency")] + \
            [(1, c) for c in ("iron_deficiency", "B12_deficiency", "folate_deficiency", "B6_deficiency", "copper_deficiency",
                              "inflammation", "iron_B12", "iron_folate", "B12_folate", "undetermined")]


@pytest.mark.parametrize("anemia,cause", ALL_PAIRS)
def test_every_model_answer_gets_both_reports(anemia, cause):
    result = _run(anemia, cause)
    for view in ("doctor", "patient"):
        report = result["report"][view]
        assert report["headline"] and report["sections"] and report["disclaimer"]
    assert result["anemia_class_label"] == lb.ANEMIA_CLASS_LABELS[result["anemia_class"]]
    assert result["report"]["severity"] == ("attention" if anemia else "watch" if cause != "none" else "ok")
    assert "%" not in " ".join(_items(result["report"]["doctor"]))   # scores — не проценты/вероятности


def test_treatment_hidden_by_default_and_shown_on_flag():
    assert not any("лечение" in t.lower() for t in _titles(_run(1, "iron_deficiency")["report"]["doctor"]))
    set_setting("include_treatment_hints", True)
    try:
        flagged = _run(1, "iron_deficiency")
    finally:
        set_setting("include_treatment_hints", False)
    assert any("лечение" in t.lower() for t in _titles(flagged["report"]["doctor"]))


def test_patient_version_has_no_doctor_only_sections():
    titles = _titles(_run(0, "B12_deficiency", sex="male")["report"]["patient"])
    assert "Уточнить у пациента" not in titles and "Основание результата" not in titles
    assert "Что обнаружено" in titles and "Что делать дальше" in titles


def test_gynecological_exam_only_for_women_with_iron_deficiency():
    assert "Гинекологический осмотр" in _items(_run(1, "iron_deficiency", "female")["report"]["doctor"])
    assert "Гинекологический осмотр" not in _items(_run(1, "iron_deficiency", "male")["report"]["doctor"])


def test_mixed_title_follows_correction_priority():
    title = _run(1, "iron_B12")["report"]["title"]
    assert title == "Сочетанный дефицит B12 и железа с анемией"


def test_undetermined_uses_safe_wording():
    result = _run(1, "undetermined", sex="male")
    assert result["anemia_class"] == "anemia_other" and "иной" not in result["anemia_class_label"]
    assert any("дифференциальная оценка" in n for n in _items(result["report"]["doctor"]))


def test_doctor_basis_explains_rule_and_model_score():
    basis = _run(1, "iron_deficiency")["report"]["doctor"]["sections"][0]
    assert basis["title"] == "Основание результата"
    assert "при пороге 120 г/л" in basis["items"][0]
    assert "не вероятность" in basis["items"][1]
