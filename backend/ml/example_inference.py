import json

from src.ml import AnemiaInferenceService


MODEL_PATH = (
    "artifacts/models/final/pipeline.joblib"
)

INPUT_PATH = "example_patient.json"
EXPECTED_OUTPUT_PATH = "example_output.json"


# ==========================================
# Загружаем пример пациента
# ==========================================

with open(
    INPUT_PATH,
    "r",
    encoding="utf-8",
) as file:
    patient_data = json.load(file)


# ==========================================
# Загружаем модель
# ==========================================

service = AnemiaInferenceService(
    MODEL_PATH
)


# ==========================================
# Выполняем inference
# ==========================================

result = service.predict(
    patient_data
)


print("=== ML INFERENCE RESULT ===")

print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
)


# ==========================================
# Проверяем ожидаемый результат
# ==========================================

with open(
    EXPECTED_OUTPUT_PATH,
    "r",
    encoding="utf-8",
) as file:
    expected = json.load(file)


fields_to_check = [
    "status",
    "anemia",
    "deficiency_cause",
    "anemia_class",
]


for field in fields_to_check:

    assert result[field] == expected[field], (
        f"Mismatch in {field}: "
        f"expected={expected[field]}, "
        f"got={result[field]}"
    )


print()
print("SMOKE TEST PASSED")
print("Model integration is working.")