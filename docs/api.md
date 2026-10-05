# REST API

Интерактивная документация (Swagger): `/docs` на работающем сервисе. Все пути начинаются с `/api/v1`.

## Авторизация

`POST /auth/login` с телом `{"login": "...", "password": "..."}` возвращает `access_token`.
Его нужно передавать во все запросы скрининга: `Authorization: Bearer <token>`. В Swagger — кнопка **Authorize**.
Ошибки: `401` (неверный логин или пароль, одно сообщение для обоих случаев), `429` (5 неудачных попыток за 5 минут).

## Эндпоинты

| Метод и путь | Доступ | Что делает |
| --- | --- | --- |
| `GET /health` | открыт | Проверка работоспособности и текущая модель (`ml_model` или `demo_fallback`, версия, test macro-F1) |
| `GET /analytes` | открыт | Справочник 35 показателей: единицы, альтернативные единицы, референсы |
| `POST /auth/login` | открыт | Вход врача |
| `GET /auth/me` | токен | Текущий пользователь |
| `POST /screening` | токен | Один пациент, JSON |
| `POST /screening/file` | токен | Один пациент, файл CSV/XLSX с одной строкой |
| `POST /screening/batch` | токен | Много пациентов, файл CSV/XLSX |
| `GET /screening/batch/template` | токен | Шаблон файла |
| `GET /screening/batch/demo-file` | токен | Небольшой демо-файл |
| `GET /screening/examples` | токен | Примеры одного пациента (обезличенные копии строк датасета) |
| `GET /screening/examples/{id}/file` | токен | Пример одного пациента в виде файла |

## Один пациент (JSON)

```http
POST /api/v1/screening
Authorization: Bearer <token>
Content-Type: application/json

{
  "case_id": "A7F4C92",
  "age": 42,
  "sex": "female",
  "laboratory_data": {"hemoglobin": 108, "MCV": 74, "MCH": 23, "ferritin": 8, "TSAT": 9, "vitamin_B12": 410,
                      "folate": 9, "copper": 15, "CRP": 2.1, "creatinine": 70, "reticulocytes": 1.1},
  "units": {"hemoglobin": "g/L"}
}
```

`units` необязателен: если значение дано в другой единице (например, `"hemoglobin": "g/dL"`), оно будет переведено.
`sex` можно не указывать: тогда модель вернёт `insufficient_data` с причиной `missing_sex`.

Ответ (сокращён, реальный ответ сервиса):

```json
{
  "case_id": "A7F4C92",
  "status": "completed",
  "ml_result": {
    "patient_id": "A7F4C92", "status": "signal_detected", "reason": null, "data_sufficient": true,
    "anemia": 1, "deficiency_cause": "iron_deficiency", "anemia_class": "iron_deficiency_anemia",
    "missing_panels": [],
    "deficiency_cause_scores": {"iron_deficiency": 0.766, "undetermined": 0.065, "iron_folate": 0.053, "...": "..."},
    "model_score": 0.766
  },
  "screening_status": "signal_detected",
  "screening_status_label": "Выявлен сигнал, требующий внимания",
  "insufficient_reason": null,
  "anemia": {"detected": true, "hemoglobin": 108.0, "threshold": 120.0, "unit": "г/л"},
  "deficiency_cause": "iron_deficiency",
  "deficiency_cause_label": "Дефицит железа",
  "anemia_class": "iron_deficiency_anemia",
  "anemia_class_label": "Железодефицитная анемия",
  "missing_panels": [],
  "model_scores": [{"cause": "iron_deficiency", "label": "Дефицит железа", "score": 0.766}, "..."],
  "labs": [{"key": "hemoglobin", "value": 108.0, "unit": "г/л", "flag": "low", "...": "..."}],
  "report": {"title": "Железодефицитная анемия (ЖДА)", "severity": "attention", "doctor": {}, "patient": {}},
  "model": {"kind": "ml_model", "is_demo": false, "name": "anemia_hierarchical_rf_masked_v1", "version": "1.0.0",
            "architecture": "Hierarchical Random Forest + panel masking", "test_macro_f1": 0.8835, "note": null},
  "warnings": [],
  "unit_conversions": []
}
```

* `ml_result` — ответ ML-модуля **без изменений** (контракт: `backend/ml/README_ML.md`). Остальные поля — подписи
  и представление для интерфейса; решение в них не пересчитывается.
* `model_score` и `deficiency_cause_scores` — технические оценки модели, **не вероятности диагноза**.
* Недостаточно данных — это ответ `200`, а не ошибка: `screening_status = "insufficient_data"`,
  `anemia_class = null`, причина в `ml_result.reason` и по-русски в `insufficient_reason`
  (`missing_sex`, `missing_hemoglobin`, `multiple_fully_missing_panels`).
* `422` возвращается только при ошибках записи данных: не число, неизвестная единица, значение вне
  допустимого диапазона, неверный ID или возраст, нераспознанный пол.

## Файлы и отчёт о проверке формата

`POST /screening/file` и `POST /screening/batch` принимают поле формы `file`. Оба возвращают `file_check`:

```json
{
  "ok": false,
  "rows": 15,
  "recognized_columns": 35,
  "errors": 6,
  "warnings": 2,
  "issues": [
    {"level": "error", "row": 13, "column": "CRP", "message": "С-реактивный белок (СРБ): «<0,5» — не число. ..."},
    {"level": "warning", "row": null, "column": null, "message": "Столбцы не распознаны и не учтены: comment."}
  ],
  "issues_truncated": 0
}
```

* `level: "error"` в строке — строка не обрабатывается, остальные обрабатываются;
* в `POST /screening/batch` каждая строка содержит `status` обработки (`completed` / `error`) и, для обработанных,
  `screening_status`, `anemia`, `deficiency_cause`, `anemia_class`, `model_score`; сводка `summary` считает
  в том числе `insufficient_data`;
* фатальная ошибка файла (нет обязательных столбцов, персональные данные, нераспознанная единица, повтор
  столбца, не CSV/XLSX) — ответ `422` с полным списком проблем в `file_check`;
* `POST /screening/file` требует ровно одну строку данных.

## Формат ошибок

Все ошибки ввода: `{"status": "error", "errors": [{"field": "...", "message": "..."}]}` (+ `file_check` для файлов).
