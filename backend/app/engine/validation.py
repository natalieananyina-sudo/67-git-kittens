"""Проверка ФОРМАТА, нормализация и приведение единиц входных данных одного случая.

Здесь проверяется только то, что данные корректно записаны: ID, числа, единицы измерения, правдоподобные
диапазоны. Достаточно ли данных для заключения (есть ли пол, гемоглобин, нужные панели анализов),
решает ML-модуль (backend/ml/src/ml/rules.py) — бэкенд эту проверку не дублирует.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Any

from . import analytes as an

CASE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
MIN_AGE, MAX_AGE = 18, 120

# Пустые значения и принятые в лабораториях обозначения «нет данных»
_EMPTY_MARKS = {"", "nan", "na", "n/a", "null", "none", "-", "—", "н/д", "нд"}

_SEX_MAP = {
    "female": "female", "f": "female", "ж": "female", "жен": "female", "женский": "female", "женщина": "female", "woman": "female",
    "male": "male", "m": "male", "м": "male", "муж": "male", "мужской": "male", "мужчина": "male", "man": "male",
}


@dataclass
class CaseInput:
    case_id: str
    age: int
    sex: str | None  # "female" | "male" | None (не указан: ML-модуль вернёт insufficient_data)
    labs: dict[str, float]  # все значения в основных единицах (variables.xlsx)


@dataclass
class FieldError:
    field: str
    message: str


@dataclass
class ValidationResult:
    case: CaseInput | None = None
    errors: list[FieldError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conversions: list[str] = field(default_factory=list)
    ignored_keys: list[str] = field(default_factory=list)


def parse_number(value: Any) -> float | None:
    """Число из числа или строки ("12,5" -> 12.5). Пустое значение -> None. Мусор -> ValueError."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("не число")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace(" ", "").replace(" ", "")
        # пустые значения и принятые в лабораториях обозначения «нет данных»
        if text == "" or text.lower() in _EMPTY_MARKS:
            return None
        number = float(text.replace(",", "."))
    if not math.isfinite(number):
        raise ValueError("не число")
    return number


def normalize_sex(value: Any) -> str | None:
    return _SEX_MAP.get(str(value).strip().lower()) if value is not None else None


def _fmt(x: float) -> str:
    return f"{round(x, 3):g}".replace(".", ",")


def validate_case(
    case_id: Any,
    age: Any,
    sex: Any,
    laboratory_data: dict[str, Any] | None,
    units: dict[str, str] | None = None,
) -> ValidationResult:
    """`units`: необязательные единицы ввода по ключам показателей ({"hemoglobin": "g/dL"}).
    Значения переводятся в основные единицы датасета; перевод фиксируется в `conversions`."""
    result = ValidationResult()
    errors = result.errors

    cid = str(case_id).strip() if case_id is not None else ""
    if not CASE_ID_RE.match(cid):
        errors.append(FieldError(
            "case_id",
            "ID случая: латиница, цифры и символы . _ - (до 64 знаков). Используйте псевдонимизированный ID, не ФИО.",
        ))

    # Пустой пол допустим (решение о достаточности данных принимает модель), нераспознанное значение — ошибка записи
    sex_text = "" if sex is None else str(sex).strip()
    if sex_text.lower() in _EMPTY_MARKS:
        sex_text = ""
    sex_norm = normalize_sex(sex_text) if sex_text else None
    if sex_text and sex_norm is None:
        errors.append(FieldError("sex", f"Пол «{sex_text}» не распознан. Укажите female/male (или F/M, Ж/М)."))

    age_value: int | None = None
    try:
        parsed_age = parse_number(age)
        if parsed_age is None:
            errors.append(FieldError("age", "Укажите возраст."))
        elif parsed_age < MIN_AGE:
            errors.append(FieldError("age", f"Скрининг рассчитан на взрослых: возраст не менее {MIN_AGE} лет."))
        elif parsed_age > MAX_AGE:
            errors.append(FieldError("age", f"Возраст вне допустимого диапазона ({MIN_AGE}–{MAX_AGE} лет)."))
        else:
            age_value = int(round(parsed_age))
    except ValueError:
        errors.append(FieldError("age", "Возраст должен быть числом."))

    unit_by_key: dict[str, str] = {}
    for raw_key, unit in (units or {}).items():
        key = an.resolve_key(raw_key)
        if key and unit:
            unit_by_key[key] = unit

    labs: dict[str, float] = {}
    for raw_key, raw_value in (laboratory_data or {}).items():
        key = an.resolve_key(raw_key)
        if key is None:
            result.ignored_keys.append(str(raw_key))
            continue
        analyte = an.BY_KEY[key]
        field_name = f"laboratory_data.{key}"
        try:
            number = parse_number(raw_value)
        except ValueError:
            shown = str(raw_value).strip()
            hint = " Значения вида «<0,5» или «>100» укажите числом." if shown[:1] in "<>≤≥" else ""
            errors.append(FieldError(field_name, f"{analyte.label}: «{shown}» — не число.{hint}"))
            continue
        if number is None:
            continue
        unit = unit_by_key.get(key)
        factor = an.unit_factor(analyte, unit)
        if factor is None:
            errors.append(FieldError(field_name, f"{analyte.label}: единица «{unit}» не поддерживается. Основная единица: {analyte.unit}."))
            continue
        if factor != 1.0:
            converted = round(number * factor, 4)
            result.conversions.append(
                f"{analyte.label}: {_fmt(number)} {an.unit_label(analyte, unit)} → {_fmt(converted)} {analyte.unit}")
            number = converted
        if not (analyte.valid_min <= number <= analyte.valid_max):
            errors.append(FieldError(
                field_name,
                f"{analyte.label}: значение {_fmt(number)} {analyte.unit} вне допустимого диапазона "
                f"{_fmt(analyte.valid_min)}–{_fmt(analyte.valid_max)} {analyte.unit}. Проверьте единицы измерения.",
            ))
            continue
        labs[key] = number

    for ignored in result.ignored_keys:
        result.warnings.append(f"Показатель «{ignored}» не поддерживается и не учтён в расчёте.")

    if not errors and age_value is not None:
        result.case = CaseInput(case_id=cid, age=age_value, sex=sex_norm, labs=labs)
    return result
