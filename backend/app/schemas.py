"""Pydantic-схемы API: по ним FastAPI строит Swagger/OpenAPI (/docs)."""
from typing import Literal

from pydantic import BaseModel, Field

_EXAMPLE_REQUEST = {
    "case_id": "A7F4C92", "age": 42, "sex": "female",
    "laboratory_data": {"hemoglobin": 108, "mcv": 74, "mch": 23, "ferritin": 8, "tsat": 9, "vitamin_b12": 410,
                        "folate": 9, "copper": 15, "crp": 2.1, "creatinine": 70, "reticulocytes": 1.1},
}


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class UserInfo(BaseModel):
    login: str
    display_name: str
    role: Literal["doctor"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Срок жизни токена, секунды")
    user: UserInfo


class ScreeningRequest(BaseModel):
    case_id: str = Field(description="Псевдонимизированный ID случая (не ФИО)")
    age: float = Field(description="Возраст, лет (от 18)")
    sex: str | None = Field(default=None, description="Пол: female / male (F/M, Ж/М)")
    laboratory_data: dict[str, float | None] = Field(
        description="Показатели по ключам из GET /api/v1/analytes (регистр не важен: MCV = mcv). Пропуски можно опускать."
    )
    units: dict[str, str] | None = Field(
        default=None,
        description="Необязательно: единицы ввода, если они отличаются от стандартных единиц, например {\"hemoglobin\": \"g/dL\"}. "
                    "Значения будут приведены к стандартным единицам.",
    )
    model_config = {"json_schema_extra": {"examples": [_EXAMPLE_REQUEST]}}


class PatientInfo(BaseModel):
    age: int
    sex: Literal["female", "male"] | None = Field(description="null: пол не указан (модель вернёт insufficient_data)")


class MlResult(BaseModel):
    """Ответ ML-модуля без изменений (контракт из backend/ml/README_ML.md)."""
    patient_id: str | None
    status: Literal["signal_detected", "no_signal_detected", "insufficient_data"]
    reason: str | None = Field(description="Причина insufficient_data: missing_sex | invalid_sex | missing_hemoglobin | "
                                           "multiple_fully_missing_panels")
    data_sufficient: bool
    anemia: int | None = Field(description="1/0 по клиническому правилу (Hb < 120 г/л у женщин, < 130 г/л у мужчин)")
    deficiency_cause: str | None
    anemia_class: str | None
    missing_panels: list[str]
    deficiency_cause_scores: dict[str, float] | None = Field(
        description="Технические scores модели для допустимых причин. НЕ откалиброванные вероятности диагноза")
    model_score: float | None = Field(description="Максимальный score (выбранная причина). НЕ вероятность диагноза")


class AnemiaInfo(BaseModel):
    detected: bool | None = Field(description="Из ml_result.anemia; null при insufficient_data")
    hemoglobin: float | None
    threshold: float | None = Field(description="Порог для подписи на экране (решение принимает ML-модуль)")
    unit: str = "г/л"


class CauseScore(BaseModel):
    cause: str
    label: str
    score: float


class LabFlag(BaseModel):
    key: str
    code: str
    label: str
    group: str
    value: float
    unit: str
    ref_low: float | None
    ref_high: float | None
    flag: Literal["low", "normal", "high"]


class ReportSection(BaseModel):
    title: str
    text: str | None = None
    items: list[str] = []


class ReportView(BaseModel):
    headline: str
    summary: str
    sections: list[ReportSection]
    disclaimer: str


class Report(BaseModel):
    title: str
    severity: Literal["ok", "watch", "attention", "insufficient"]
    doctor: ReportView
    patient: ReportView


class ModelInfo(BaseModel):
    kind: Literal["ml_model", "demo_fallback"]
    is_demo: bool = Field(description="true: финальная модель не загружена, работает демо-резерв")
    name: str
    version: str
    architecture: str
    test_macro_f1: float | None = Field(description="Macro-F1 на отложенной выборке (из паспорта модели)")
    note: str | None = None


class ScreeningResponse(BaseModel):
    case_id: str
    status: Literal["completed"] = Field(default="completed", description="Запрос обработан (ошибки ввода дают 422)")
    patient: PatientInfo
    ml_result: MlResult
    screening_status: Literal["signal_detected", "no_signal_detected", "insufficient_data"]
    screening_status_label: str
    insufficient_reason: str | None
    anemia: AnemiaInfo
    deficiency_cause: str | None
    deficiency_cause_label: str | None
    anemia_class: str | None = Field(description="Итоговый класс из ML-модуля (один из 12); null при insufficient_data")
    anemia_class_label: str
    missing_panels: list[str] = Field(description="Полностью отсутствующие панели анализов (по-русски)")
    model_scores: list[CauseScore] = Field(description="Scores модели по убыванию (не вероятности)")
    labs: list[LabFlag]
    report: Report
    model: ModelInfo
    warnings: list[str]
    unit_conversions: list[str] = Field(description="Какие значения и как были приведены к стандартным единицам")


class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    errors: list[FieldError]


class BatchRow(BaseModel):
    row: int = Field(description="Номер строки данных (с 1)")
    case_id: str | None
    status: Literal["completed", "error"]
    sex: str | None = None
    age: int | None = None
    screening_status: Literal["signal_detected", "no_signal_detected", "insufficient_data"] | None = None
    anemia: bool | None = None
    hemoglobin: float | None = None
    deficiency_cause: str | None = None
    deficiency_cause_label: str | None = None
    anemia_class: str | None = None
    anemia_class_label: str | None = None
    model_score: float | None = None
    title: str | None = None
    severity: Literal["ok", "watch", "attention", "insufficient"] | None = None
    errors: list[str] = []
    warnings: list[str] = []
    input: ScreeningRequest | None = Field(default=None, description="Нормализованный вход: по нему открывается полный результат")


class FileIssue(BaseModel):
    level: Literal["error", "warning"]
    row: int | None = Field(default=None, description="Номер строки данных (с 1); null — проблема всего файла")
    column: str | None = Field(default=None, description="Заголовок столбца в файле")
    message: str


class FileCheck(BaseModel):
    ok: bool = Field(description="true, если ошибок формата нет (предупреждения допустимы)")
    rows: int
    recognized_columns: int = Field(description="Сколько столбцов распознано как лабораторные показатели")
    errors: int
    warnings: int
    issues: list[FileIssue]
    issues_truncated: int = Field(description="Сколько проблем не поместилось в список")


class FileErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    errors: list[FieldError]
    file_check: FileCheck | None = None


class BatchSummary(BaseModel):
    total: int
    completed: int
    errors: int
    anemia_detected: int
    with_deficiency: int
    insufficient_data: int


class BatchResponse(BaseModel):
    summary: BatchSummary
    rows: list[BatchRow]
    ignored_columns: list[str]
    units_from_header: dict[str, str]
    file_check: FileCheck
    model: ModelInfo


class SingleFileResponse(BaseModel):
    result: ScreeningResponse
    file_check: FileCheck
