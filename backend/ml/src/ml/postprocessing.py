"""
Postprocessing для финальной hierarchical ML-модели.

Содержит:
- допустимые deficiency_cause в зависимости от anemia;
- constrained selection по вероятностям модели;
- преобразование anemia + deficiency_cause → anemia_class.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


# ==================================================
# Финальный deterministic mapping
# ==================================================

POSTPROCESSING_MAP = {

    # ------------------------------------------------
    # Без анемии
    # ------------------------------------------------
    (0, "none"):
        "no_anemia_no_deficiency",

    (0, "iron_deficiency"):
        "latent_deficiency",

    (0, "B12_deficiency"):
        "B12_deficiency_no_anemia",

    (0, "folate_deficiency"):
        "folate_deficiency_no_anemia",

    (0, "B6_deficiency"):
        "B6_deficiency",

    (0, "copper_deficiency"):
        "copper_deficiency",

    # ------------------------------------------------
    # С анемией
    # ------------------------------------------------
    (1, "iron_deficiency"):
        "iron_deficiency_anemia",

    (1, "B12_deficiency"):
        "B12_deficiency_anemia",

    (1, "folate_deficiency"):
        "folate_deficiency_anemia",

    (1, "B6_deficiency"):
        "B6_deficiency",

    (1, "copper_deficiency"):
        "copper_deficiency",

    (1, "inflammation"):
        "inflammation_anemia",

    (1, "iron_B12"):
        "mixed_deficiency",

    (1, "iron_folate"):
        "mixed_deficiency",

    (1, "B12_folate"):
        "mixed_deficiency",

    (1, "undetermined"):
        "anemia_other",
}


# ==================================================
# Допустимые causes
# ==================================================

VALID_CAUSES_BY_ANEMIA = {

    0: {
        "none",
        "iron_deficiency",
        "B12_deficiency",
        "folate_deficiency",
        "B6_deficiency",
        "copper_deficiency",
    },

    1: {
        "iron_deficiency",
        "B12_deficiency",
        "folate_deficiency",
        "B6_deficiency",
        "copper_deficiency",
        "inflammation",
        "iron_B12",
        "iron_folate",
        "B12_folate",
        "undetermined",
    },
}


# ==================================================
# Проверка констант
# ==================================================

assert len(POSTPROCESSING_MAP) == 16

for anemia_value, causes in VALID_CAUSES_BY_ANEMIA.items():
    for cause in causes:
        assert (
            anemia_value,
            cause,
        ) in POSTPROCESSING_MAP


# ==================================================
# Constrained probabilities
# ==================================================

def constrain_probabilities(
    classes: Iterable[str],
    probabilities: Iterable[float],
    anemia: int,
) -> dict[str, float]:
    """
    Оставляет только клинически допустимые deficiency_cause
    для текущего состояния anemia.

    Вероятности оставшихся классов нормализуются до суммы 1.

    Важно:
    это model scores после ограничения, а не клинически
    откалиброванные вероятности диагноза.
    """

    anemia = int(anemia)

    if anemia not in VALID_CAUSES_BY_ANEMIA:
        raise ValueError(
            "anemia must be 0 or 1"
        )

    allowed = VALID_CAUSES_BY_ANEMIA[
        anemia
    ]

    result = {}

    for cls, probability in zip(
        classes,
        probabilities,
    ):
        cls = str(cls)

        if cls in allowed:
            result[cls] = float(
                probability
            )

    if not result:
        raise RuntimeError(
            "Model returned no clinically valid "
            "deficiency causes."
        )

    total = sum(
        result.values()
    )

    if total <= 0:
        raise RuntimeError(
            "Sum of valid model probabilities "
            "must be greater than zero."
        )

    return {
        cls: probability / total
        for cls, probability
        in result.items()
    }


# ==================================================
# Выбор deficiency_cause
# ==================================================

def select_deficiency_cause(
    classes: Iterable[str],
    probabilities: Iterable[float],
    anemia: int,
) -> tuple[str, dict[str, float]]:
    """
    Выбирает наиболее вероятный допустимый deficiency_cause.

    Returns
    -------
    tuple
        (
            predicted_deficiency_cause,
            constrained_scores
        )
    """

    scores = constrain_probabilities(
        classes=classes,
        probabilities=probabilities,
        anemia=anemia,
    )

    predicted_cause = max(
        scores,
        key=scores.get,
    )

    return (
        predicted_cause,
        scores,
    )


# ==================================================
# Финальный anemia_class
# ==================================================

def get_anemia_class(
    anemia: int,
    deficiency_cause: str,
) -> str:
    """
    Детерминированно формирует итоговый anemia_class.
    """

    key = (
        int(anemia),
        str(deficiency_cause),
    )

    if key not in POSTPROCESSING_MAP:
        raise ValueError(
            "Unsupported combination: "
            f"anemia={key[0]}, "
            f"deficiency_cause={key[1]}"
        )

    return POSTPROCESSING_MAP[key]