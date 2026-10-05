"""
Конфигурация ML-модуля для скрининга анемий
и дефицитных состояний.

Содержит фиксированный контракт входных признаков
финальной модели и группы лабораторных показателей.
"""


# ==================================================
# Входные признаки
# ==================================================

DEMOGRAPHIC_COLS = [
    "age_years",
    "sex",
]


LAB_COLS = [
    "hemoglobin",
    "RBC",
    "hematocrit",
    "MCV",
    "MCH",
    "MCHC",
    "RDW",
    "platelets",
    "WBC",
    "reticulocytes",
    "ferritin",
    "serum_iron",
    "transferrin",
    "TIBC",
    "UIBC",
    "TSAT",
    "sTfR",
    "Ret_He",
    "vitamin_B12",
    "active_B12",
    "MMA",
    "homocysteine",
    "folate",
    "vitamin_B6",
    "copper",
    "ceruloplasmin",
    "CRP",
    "ESR",
    "creatinine",
    "eGFR",
    "TSH",
    "albumin",
    "LDH",
    "indirect_bilirubin",
    "haptoglobin",
]


FEATURE_COLS = (
    DEMOGRAPHIC_COLS
    + LAB_COLS
)


# ==================================================
# Лабораторные панели
#
# Используются для:
# - проверки достаточности данных;
# - определения полностью отсутствующих панелей;
# - robustness / masking логики.
# ==================================================

LAB_PANELS = {

    "cbc": [
        "hemoglobin",
        "RBC",
        "hematocrit",
        "MCV",
        "MCH",
        "MCHC",
        "RDW",
        "platelets",
        "WBC",
    ],

    "iron": [
        "ferritin",
        "serum_iron",
        "transferrin",
        "TIBC",
        "UIBC",
        "TSAT",
        "sTfR",
        "Ret_He",
    ],

    "b12_folate": [
        "vitamin_B12",
        "active_B12",
        "MMA",
        "homocysteine",
        "folate",
    ],

    "b6_copper": [
        "vitamin_B6",
        "copper",
        "ceruloplasmin",
    ],

    "inflammation": [
        "CRP",
        "ESR",
        "albumin",
    ],

    "renal_thyroid": [
        "creatinine",
        "eGFR",
        "TSH",
    ],

    "hemolysis_reticulocytes": [
        "reticulocytes",
        "LDH",
        "indirect_bilirubin",
        "haptoglobin",
    ],
}


# ==================================================
# Контроль структуры
# ==================================================

assert len(FEATURE_COLS) == 37

assert len(LAB_COLS) == 35

assert len(
    [
        feature
        for panel in LAB_PANELS.values()
        for feature in panel
    ]
) == 35