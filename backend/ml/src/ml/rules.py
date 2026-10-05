"""
Клинические и safety-правила для ML-модуля.

Содержит:
- детерминированное определение анемии;
- проверку достаточности входных данных;
- итоговый статус результата.
"""

from __future__ import annotations

import pandas as pd

from .config import LAB_PANELS


# ==================================================
# Clinical anemia rule
# ==================================================

def apply_anemia_rule(
    sex: str,
    hemoglobin: float,
) -> int:
    """
    Определяет наличие анемии по полу и гемоглобину.

    Правило:
    - F: Hb < 120 г/л
    - M: Hb < 130 г/л

    Returns
    -------
    int
        1 — анемия выявлена
        0 — анемия не выявлена
    """

    if pd.isna(sex):
        raise ValueError(
            "sex is required for anemia rule"
        )

    sex = str(sex).strip().upper()

    if sex not in {"F", "M"}:
        raise ValueError(
            "sex must be 'F' or 'M'"
        )

    if pd.isna(hemoglobin):
        raise ValueError(
            "hemoglobin is required for anemia rule"
        )

    if sex == "F":
        return int(hemoglobin < 120)

    return int(hemoglobin < 130)


# ==================================================
# Missing panels
# ==================================================

def get_fully_missing_panels(
    row: pd.Series,
) -> list[str]:
    """
    Возвращает список лабораторных панелей,
    в которых отсутствуют все показатели.
    """

    missing_panels = []

    for panel_name, columns in LAB_PANELS.items():

        if row[columns].isna().all():
            missing_panels.append(
                panel_name
            )

    return missing_panels


# ==================================================
# Data sufficiency
# ==================================================

def check_data_sufficiency(
    row: pd.Series,
) -> tuple[bool, str | None]:
    """
    Проверяет, достаточно ли данных для безопасного inference.

    Недостаточно данных, если:
    - отсутствует sex;
    - sex имеет недопустимое значение;
    - отсутствует hemoglobin;
    - полностью отсутствует более одной
      лабораторной панели, кроме CBC.

    Returns
    -------
    tuple[bool, str | None]
        (True, None), если данных достаточно.

        Иначе:
        (False, reason)
    """

    if pd.isna(row["sex"]):
        return (
            False,
            "missing_sex",
        )

    sex = str(
        row["sex"]
    ).strip().upper()

    if sex not in {"F", "M"}:
        return (
            False,
            "invalid_sex",
        )

    if pd.isna(
        row["hemoglobin"]
    ):
        return (
            False,
            "missing_hemoglobin",
        )

    missing_panels = (
        get_fully_missing_panels(
            row
        )
    )

    # CBC отдельно не учитываем здесь:
    # отсутствие Hb уже обработано выше.
    non_cbc_missing = [
        panel
        for panel in missing_panels
        if panel != "cbc"
    ]

    if len(
        non_cbc_missing
    ) > 1:

        return (
            False,
            "multiple_fully_missing_panels",
        )

    return (
        True,
        None,
    )


# ==================================================
# Result status
# ==================================================

def determine_result_status(
    anemia: int,
    deficiency_cause: str,
    sufficient_data: bool = True,
) -> str:
    """
    Возвращает один из трёх статусов MVP:

    - signal_detected
    - no_signal_detected
    - insufficient_data
    """

    if not sufficient_data:
        return "insufficient_data"

    if (
        int(anemia) == 0
        and deficiency_cause == "none"
    ):
        return "no_signal_detected"

    return "signal_detected"