"""Заполненная строка для шаблона файла и проверочные случаи для автотестов (без персональных данных).

Случаи берутся из demo_cases.json, который создаёт scripts/generate_demo_data.py: это слегка зашумлённые копии
строк исходного датасета (значения в единицах датасета). В интерфейсе примеры не показываются: отсюда берётся
только одна строка для шаблона CSV, чтобы было видно формат.
"""
import csv
import io
import json
from functools import lru_cache
from pathlib import Path

from . import analytes as an

_FILE = Path(__file__).with_name("demo_cases.json")


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


def template_csv() -> str:
    """Шаблон: заголовки и одна заполненная строка, чтобы было видно формат значений."""
    case = next((c for c in examples() if "Железодефицитная" in c["title"]), examples()[0])
    row = _row(case)
    row[0] = "CASE-001"
    return _csv([row])
