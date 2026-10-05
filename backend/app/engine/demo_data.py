"""Демонстрационные случаи для интерфейса и API (без персональных данных).

Случаи берутся из demo_cases.json, который создаёт scripts/generate_demo_data.py: это слегка зашумлённые копии
строк исходного датасета (значения в единицах датасета), отобранные так, чтобы ML-модель их верно
классифицировала. Отдельно есть пример с нехваткой данных (модель вернёт insufficient_data).
"""
import csv
import io
import json
from functools import lru_cache
from pathlib import Path

from . import analytes as an

_FILE = Path(__file__).with_name("demo_cases.json")

# Две строки с ошибками формата: показывают, как сервис сообщает о проблемах в файле
_BROKEN_ROWS = [
    ["ERR-01", 47, "female", {"hemoglobin": "11,2 г/дл", "ferritin": 20}],   # текст вместо числа
    ["ERR-02", 16, "male", {"hemoglobin": 141}],                             # возраст младше 18 лет
]


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(_FILE.read_text(encoding="utf-8"))


def examples() -> list[dict]:
    return _load()["examples"]


def _header() -> list[str]:
    # Те же названия столбцов, что в исходных данных: их выгрузку можно загрузить без переделки
    return ["patient_id", "age_years", "sex"] + [a.code for a in an.ANALYTES]


def _row(case: dict) -> list:
    data = case["input"]
    labs = data["laboratory_data"]
    return [data["case_id"], data["age"], data["sex"]] + [labs.get(a.key, "") for a in an.ANALYTES]


def _csv(rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_header())
    writer.writerows(rows)
    return buffer.getvalue()


def demo_csv() -> str:
    """Несколько пациентов: витрина всех 12 классов, пример нехватки данных и две строки с ошибками."""
    rows = [_row(c) for c in _load()["batch"]]
    rows.append(_row(examples()[-1]))
    for cid, age, sex, labs in _BROKEN_ROWS:
        rows.append([cid, age, sex] + [labs.get(a.key, "") for a in an.ANALYTES])
    return _csv(rows)


def example_csv(example_id: str) -> str | None:
    """Один пример в виде файла (для режима «Один пациент»)."""
    for case in examples():
        if case["id"] == example_id:
            return _csv([_row(case)])
    return None


def template_csv() -> str:
    """Шаблон: заголовки и одна заполненная строка (пример железодефицитной анемии)."""
    case = next((c for c in examples() if "Железодефицитная" in c["title"]), examples()[0])
    return _csv([_row(case)])
