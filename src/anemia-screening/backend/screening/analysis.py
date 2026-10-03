"""Inference from exported coefficients; no training data or patient storage."""

import json
import math
import os
from functools import lru_cache
from pathlib import Path

ETIOLOGIC = (
    "ferritin", "serum_iron", "TSAT", "sTfR", "Ret_He", "vitamin_B12",
    "active_B12", "MMA", "homocysteine", "folate", "vitamin_B6", "copper",
    "ceruloplasmin", "CRP",
)
LABELS = {
    "no_anemia_no_deficiency": "Признаков анемии и исследуемых дефицитов не выявлено",
    "latent_deficiency": "Возможный скрытый дефицит",
    "iron_deficiency_anemia": "Возможная железодефицитная анемия",
    "B12_deficiency_anemia": "Возможная B12-дефицитная анемия",
    "B12_deficiency_no_anemia": "Возможный дефицит B12 без анемии",
    "folate_deficiency_anemia": "Возможная фолиеводефицитная анемия",
    "folate_deficiency_no_anemia": "Возможный дефицит фолатов без анемии",
    "B6_deficiency": "Возможный дефицит B6",
    "copper_deficiency": "Возможный дефицит меди",
    "inflammation_anemia": "Возможная анемия, связанная с воспалением",
    "mixed_deficiency": "Возможное сочетание дефицитов",
    "anemia_other": "Анемия иной или неуточнённой природы",
}
NO_ANEMIA_CLASSES = {
    "no_anemia_no_deficiency", "latent_deficiency", "B12_deficiency_no_anemia",
    "folate_deficiency_no_anemia",
}
ANEMIA_CLASSES = {
    "iron_deficiency_anemia", "B12_deficiency_anemia", "folate_deficiency_anemia",
    "inflammation_anemia", "anemia_other",
}


@lru_cache(maxsize=1)
def get_model():
    default_path = Path(__file__).resolve().parents[2] / "lib" / "model.json"
    with open(os.environ.get("MODEL_PATH", default_path), encoding="utf-8") as file:
        return json.load(file)


def read_number(value, field):
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{field}: требуется число")
    try:
        number = float(value.strip().replace(",", ".") if isinstance(value, str) else value)
    except ValueError as exc:
        raise ValueError(f"{field}: неверное значение") from exc
    if not math.isfinite(number) or number < 0 or number > 100_000:
        raise ValueError(f"{field}: неверное значение")
    return number


def analyze(record):
    sex = record.get("sex")
    if sex not in ("F", "M"):
        raise ValueError("Укажите пол: F или M")
    hb = read_number(record.get("hemoglobin"), "hemoglobin")
    if hb is None or hb < 20 or hb > 250:
        raise ValueError("Укажите гемоглобин в г/л (20–250)")
    age = read_number(record.get("age_years"), "age_years")
    if age is None or age < 18 or age > 120:
        raise ValueError("Укажите возраст взрослого пациента (18–120)")

    model = get_model()
    numbers = [(1.0 if sex == "M" else 0.0) if field == "sex" else read_number(record.get(field), field)
               for field in model["features"]]
    measured = [field for field in ETIOLOGIC if record.get(field) not in (None, "")]
    threshold = 120 if sex == "F" else 130
    result = {"anemia": hb < threshold, "threshold": threshold, "hemoglobin": hb,
              "measuredMarkers": measured}
    if len(measured) < 2:
        return {**result, "status": "insufficient_data", "classCode": None, "className": None,
                "note": "Для предположения о причине нужно как минимум два дополнительных профильных показателя. Результат по анемии рассчитан только по гемоглобину."}

    features = [model["medians"][i] if value is None else value for i, value in enumerate(numbers)]
    features.extend(1 if value is None else 0 for value in numbers)
    standardized = [(value - model["mean"][i]) / model["scale"][i]
                    for i, value in enumerate(features)]
    scores = [sum(weight * value for weight, value in zip(row, standardized)) + model["intercept"][j]
              for j, row in enumerate(model["coef"])]
    class_code = model["classes"][max(range(len(scores)), key=scores.__getitem__)]
    if (result["anemia"] and class_code in NO_ANEMIA_CLASSES) or (
            not result["anemia"] and class_code in ANEMIA_CLASSES):
        return {**result, "status": "discordant", "classCode": None, "className": None,
                "note": "Правило по гемоглобину и прогноз класса расходятся. Причину по этим данным не указываем; требуется проверка анализов и врачебная оценка."}
    return {**result, "status": "predicted", "classCode": class_code,
            "className": LABELS.get(class_code, class_code),
            "note": "Предварительная оценка по учебной модели. Пропущенные анализы и единицы измерения влияют на надёжность; медицинский вывод требует проверки врачом."}
