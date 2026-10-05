"""Единая точка расчёта: проверенный случай -> ML-модуль -> ответ API.

Порядок:
1. ML-модуль (AnemiaInferenceService) получает данные в единицах датасета и сам принимает все решения:
   достаточно ли данных, есть ли анемия, какая причина, какой итоговый класс.
2. Бэкенд добавляет то, что нужно человеку: подписи по-русски, отметки «ниже/выше нормы» у показателей,
   заключения для врача и для пациента. Решение модели при этом не меняется.
"""
from ..config import settings
from . import analytes as an
from . import conclusions
from . import labels as lb
from .predictor import Predictor, get_predictor, model_info
from .validation import CaseInput


def _lab_flags(case: CaseInput) -> list[dict]:
    """Показатели с ориентировочными референсами. Только для подсветки на экране: в модель не передаются."""
    flags = []
    for analyte in an.ANALYTES:
        if analyte.key not in case.labs:
            continue
        value = case.labs[analyte.key]
        low, high = analyte.reference(case.sex)
        flag = "low" if low is not None and value < low else "high" if high is not None and value > high else "normal"
        flags.append({"key": analyte.key, "code": analyte.code, "label": analyte.label, "group": analyte.group,
                      "value": value, "unit": analyte.unit, "ref_low": low, "ref_high": high, "flag": flag})
    return flags


def _json_safe(ml: dict) -> dict:
    """Ответ модуля как есть, но с обычными float вместо numpy-чисел."""
    out = dict(ml)
    if out.get("deficiency_cause_scores"):
        out["deficiency_cause_scores"] = {k: float(v) for k, v in out["deficiency_cause_scores"].items()}
    if out.get("model_score") is not None:
        out["model_score"] = float(out["model_score"])
    out["missing_panels"] = list(out.get("missing_panels") or [])
    return out


def screen(case: CaseInput, predictor: Predictor | None = None, ml_raw: dict | None = None) -> dict:
    """ml_raw: уже готовый ответ модуля (для файлов, где модель вызывается сразу для всех строк)."""
    predictor = predictor or get_predictor()
    ml = _json_safe(ml_raw if ml_raw is not None else predictor.predict(case))   # всё решение — здесь
    labs = _lab_flags(case)
    report = conclusions.build_report(case, ml, labs, settings.include_treatment_hints)

    sufficient = ml["status"] != "insufficient_data"
    hb = case.labs.get("hemoglobin")
    scores = sorted((ml.get("deficiency_cause_scores") or {}).items(), key=lambda kv: -kv[1])
    warnings = []
    if sufficient and ml["missing_panels"]:
        warnings.append("Нет данных панели: " + "; ".join(lb.PANEL_LABELS.get(p, p) for p in ml["missing_panels"])
                        + ". Модель работала без неё.")

    return {
        "case_id": case.case_id,
        "status": "completed",
        "patient": {"age": case.age, "sex": case.sex},
        "ml_result": ml,
        "screening_status": ml["status"],
        "screening_status_label": lb.STATUS_LABELS[ml["status"]],
        "insufficient_reason": lb.REASON_LABELS.get(ml["reason"], ml["reason"]) if ml.get("reason") else None,
        "anemia": {
            "detected": None if ml["anemia"] is None else bool(ml["anemia"]),
            "hemoglobin": hb,
            "threshold": lb.HB_DISPLAY_THRESHOLD.get(case.sex or ""),
            "unit": "г/л",
        },
        "deficiency_cause": ml["deficiency_cause"],
        "deficiency_cause_label": lb.CAUSE_LABELS.get(ml["deficiency_cause"]) if ml["deficiency_cause"] else None,
        "anemia_class": ml["anemia_class"],
        "anemia_class_label": lb.ANEMIA_CLASS_LABELS.get(ml["anemia_class"], lb.INSUFFICIENT_LABEL)
        if ml["anemia_class"] else lb.INSUFFICIENT_LABEL,
        "missing_panels": [lb.PANEL_LABELS.get(p, p) for p in ml["missing_panels"]],
        "model_scores": [{"cause": c, "label": lb.CAUSE_LABELS.get(c, c), "score": round(v, 3)} for c, v in scores],
        "labs": labs,
        "report": report,
        "model": model_info(predictor),
        "warnings": warnings,
        "unit_conversions": [],
    }
