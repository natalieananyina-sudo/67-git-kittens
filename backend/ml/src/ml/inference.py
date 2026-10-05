"""
Inference-сервис для финальной модели скрининга анемий
и дефицитных состояний.

Публичный интерфейс:

    service = AnemiaInferenceService(model_path)
    result = service.predict(patient_data)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import FEATURE_COLS
from .postprocessing import (
    get_anemia_class,
    select_deficiency_cause,
)
from .rules import (
    apply_anemia_rule,
    check_data_sufficiency,
    determine_result_status,
    get_fully_missing_panels,
)


class AnemiaInferenceService:
    """
    Обёртка над финальным sklearn Pipeline.

    Модель предсказывает deficiency_cause.
    Наличие анемии определяется клиническим правилом.
    Итоговый anemia_class формируется детерминированно.
    """

    def __init__(
        self,
        model_path: str | Path,
    ) -> None:

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}"
            )

        self.pipeline = joblib.load(
            self.model_path
        )

        # Нужны для constrained postprocessing
        try:
            self.model_classes = np.asarray(
                self.pipeline
                .named_steps["model"]
                .classes_
            )

        except (AttributeError, KeyError) as exc:
            raise RuntimeError(
                "Loaded model does not have expected "
                "Pipeline structure."
            ) from exc


    # ==================================================
    # Подготовка одного пациента
    # ==================================================

    @staticmethod
    def _prepare_input(
        patient_data: dict[str, Any],
    ) -> pd.DataFrame:
        """
        Приводит входной dict к контракту модели.

        - отсутствующие признаки -> NaN;
        - лишние поля игнорируются;
        - sex нормализуется в F/M;
        - остальные признаки приводятся к numeric.
        """

        prepared = {
            feature: patient_data.get(
                feature,
                np.nan,
            )
            for feature in FEATURE_COLS
        }

        data = pd.DataFrame(
            [prepared],
            columns=FEATURE_COLS,
        )

        # ----------------------------------------------
        # sex
        # ----------------------------------------------

        if pd.notna(
            data.loc[0, "sex"]
        ):
            data.loc[0, "sex"] = (
                str(
                    data.loc[0, "sex"]
                )
                .strip()
                .upper()
            )

        # ----------------------------------------------
        # numeric features
        # ----------------------------------------------

        numeric_cols = [
            feature
            for feature in FEATURE_COLS
            if feature != "sex"
        ]

        for column in numeric_cols:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

        return data


    # ==================================================
    # Prediction
    # ==================================================

    def predict(
        self,
        patient_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Выполняет inference для одного пациента.

        Returns
        -------
        dict
            Структурированный результат,
            пригодный для передачи backend/frontend.
        """

        X = self._prepare_input(
            patient_data
        )

        row = X.iloc[0]

        patient_id = patient_data.get(
            "patient_id"
        )

        missing_panels = (
            get_fully_missing_panels(
                row
            )
        )

        sufficient_data, reason = (
            check_data_sufficiency(
                row
            )
        )


        # ==================================================
        # Недостаточно данных
        # ==================================================

        if not sufficient_data:

            return {
                "patient_id":
                    patient_id,

                "status":
                    "insufficient_data",

                "reason":
                    reason,

                "data_sufficient":
                    False,

                "anemia":
                    None,

                "deficiency_cause":
                    None,

                "anemia_class":
                    None,

                "missing_panels":
                    missing_panels,

                "deficiency_cause_scores":
                    None,

                "model_score":
                    None,
            }


        # ==================================================
        # Clinical anemia rule
        # ==================================================

        anemia = apply_anemia_rule(
            sex=row["sex"],
            hemoglobin=row["hemoglobin"],
        )


        # ==================================================
        # ML: deficiency_cause
        # ==================================================

        probabilities = (
            self.pipeline
            .predict_proba(X)[0]
        )

        (
            deficiency_cause,
            constrained_scores,
        ) = select_deficiency_cause(
            classes=self.model_classes,
            probabilities=probabilities,
            anemia=anemia,
        )


        # ==================================================
        # Deterministic final class
        # ==================================================

        anemia_class = get_anemia_class(
            anemia=anemia,
            deficiency_cause=deficiency_cause,
        )


        status = determine_result_status(
            anemia=anemia,
            deficiency_cause=deficiency_cause,
            sufficient_data=True,
        )


        # ==================================================
        # Response
        # ==================================================

        return {
            "patient_id":
                patient_id,

            "status":
                status,

            "reason":
                None,

            "data_sufficient":
                True,

            "anemia":
                int(anemia),

            "deficiency_cause":
                deficiency_cause,

            "anemia_class":
                anemia_class,

            "missing_panels":
                missing_panels,

            "deficiency_cause_scores":
                constrained_scores,

            # Это технический score модели,
            # НЕ клинически откалиброванная вероятность.
            "model_score":
                float(
                    max(
                        constrained_scores.values()
                    )
                ),
        }