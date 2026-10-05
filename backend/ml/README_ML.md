```markdown
# Anemia ML v1

Финальная ML-модель для скрининга анемий и дефицитных состояний.

## Что внутри

Модель использует:

- клиническое правило определения анемии по полу и гемоглобину;
- ML-модель для определения `deficiency_cause`;
- constrained postprocessing;
- детерминированное формирование итогового `anemia_class`.

Финальная модель:

`Hierarchical Random Forest + panel masking`

## Установка зависимостей

```bash
pip install -r requirements-ml.txt
```

Рекомендуемая версия Python:

```text
Python 3.12
```

Версии основных библиотек зафиксированы в:

```text
requirements-ml.txt
```

и в:

```text
artifacts/models/final/model_manifest.json
```

## Быстрый тест

После распаковки архива из его корневой папки выполнить:

```bash
python example_inference.py
```

Ожидаемый результат в конце:

```text
SMOKE TEST PASSED
Model integration is working.
```

`example_inference.py`:

1. загружает пример входных данных из `example_patient.json`;
2. загружает финальную модель;
3. выполняет inference;
4. сравнивает основные поля результата с `example_output.json`.

Для smoke-test не требуется исходный датасет или Jupyter Notebook.

## Использование в backend

Импорт:

```python
from src.ml import AnemiaInferenceService
```

Инициализация модели:

```python
service = AnemiaInferenceService(
    "artifacts/models/final/pipeline.joblib"
)
```

Пример вызова:

```python
result = service.predict({
    "patient_id": "P001",
    "age_years": 42,
    "sex": "F",
    "hemoglobin": 112,
    "MCV": 74.5,
    "ferritin": 8.2,
})
```

Отсутствующие лабораторные показатели можно не передавать.

ML-модуль самостоятельно приведёт отсутствующие входные признаки к `NaN`.

Лишние поля во входном словаре не используются моделью.

## Формат входных данных

Вход в `service.predict()` — обычный Python `dict`.

Основные демографические признаки:

```text
age_years
sex
```

`sex` должен иметь значение:

```text
F
```

или:

```text
M
```

Модель также использует лабораторные показатели, перечисленные в:

```text
src/ml/config.py
```

Полный контракт содержит 37 входных признаков:

- 2 демографических;
- 35 лабораторных.

## Формат результата

Метод:

```python
service.predict(patient_data)
```

возвращает Python `dict`.

Пример:

```json
{
  "patient_id": "P001",
  "status": "signal_detected",
  "reason": null,
  "data_sufficient": true,
  "anemia": 1,
  "deficiency_cause": "iron_deficiency",
  "anemia_class": "iron_deficiency_anemia",
  "missing_panels": [],
  "deficiency_cause_scores": {
    "iron_deficiency": 0.85
  },
  "model_score": 0.85
}
```

## Поле `status`

Возможны три значения.

### `signal_detected`

Модель и/или клиническое правило выявили сигнал, требующий внимания.

### `no_signal_detected`

Анемия не выявлена и модель не выявила дефицитное состояние.

### `insufficient_data`

Данных недостаточно для безопасного формирования результата.

Например:

- отсутствует пол;
- отсутствует гемоглобин;
- полностью отсутствует более одной лабораторной панели.

Причина указывается в поле:

```text
reason
```

## Поле `anemia`

```text
1
```

означает наличие анемии по используемому клиническому правилу.

```text
0
```

означает отсутствие анемии по используемому клиническому правилу.

Анемия определяется отдельно от ML-модели по полу и уровню гемоглобина.

## Поле `deficiency_cause`

Это результат ML-модели после constrained postprocessing.

Возможные значения включают:

```text
none
iron_deficiency
B12_deficiency
folate_deficiency
B6_deficiency
copper_deficiency
inflammation
iron_B12
iron_folate
B12_folate
undetermined
```

Допустимые значения зависят от наличия или отсутствия анемии.

Эта логика уже реализована внутри `src/ml/` и не должна отдельно дублироваться в backend.

## Поле `anemia_class`

Финальный класс формируется детерминированно на основании:

```text
anemia + deficiency_cause
```

Например:

```text
anemia = 1
deficiency_cause = iron_deficiency
```

даёт:

```text
iron_deficiency_anemia
```

Backend не должен самостоятельно пересчитывать `anemia_class`.

Необходимо использовать результат, который возвращает `AnemiaInferenceService`.

## Поля `deficiency_cause_scores` и `model_score`

`deficiency_cause_scores` содержит технические scores модели для допустимых классов.

`model_score` содержит максимальный score выбранного класса.

Важно:

эти значения не являются клинически откалиброванными вероятностями диагноза.

Их нельзя интерпретировать как, например:

> вероятность железодефицитной анемии составляет 85%

без отдельной процедуры калибровки и клинической валидации.

## Обработка неполных данных

Модель обучалась с использованием panel masking и поддерживает работу с частично отсутствующими лабораторными данными.

Проверка достаточности данных уже реализована в:

```text
src/ml/rules.py
```

Backend не должен самостоятельно воспроизводить эту логику.

Если данных недостаточно, сервис вернёт:

```json
{
  "status": "insufficient_data",
  "data_sufficient": false
}
```

и укажет причину в поле `reason`.

## Основные файлы

### `src/ml/`

Runtime-логика модели.

Содержит:

```text
__init__.py
config.py
rules.py
postprocessing.py
inference.py
```

### `artifacts/models/final/pipeline.joblib`

Финальная frozen-модель версии v1.

Именно этот файл должен использоваться для inference.

### `artifacts/models/final/model_manifest.json`

Паспорт модели.

Содержит:

- название и версию модели;
- архитектуру;
- итоговые test-метрики;
- версии Python и библиотек;
- SHA-256 модели.

### `requirements-ml.txt`

Зависимости, необходимые для загрузки и запуска модели.

### `example_patient.json`

Пример входных данных одного пациента.

### `example_output.json`

Пример ожидаемого ответа модели.

### `example_inference.py`

Автономный smoke-test интеграции.

## Важно для интеграции

Backend должен использовать готовый класс:

```python
AnemiaInferenceService
```

Не требуется отдельно реализовывать:

- правило определения анемии;
- preprocessing;
- заполнение пропущенных значений внутри ML pipeline;
- constrained postprocessing;
- выбор `deficiency_cause`;
- формирование `anemia_class`;
- проверку достаточности данных.

Вся эта логика уже входит в передаваемый ML-модуль.

## Финальная модель

Версия:

```text
1.0.0
```

Название:

```text
anemia_hierarchical_rf_masked_v1
```

Архитектура:

```text
Hierarchical Random Forest + panel masking
```

Итоговые показатели на отложенной test-выборке:

```text
Macro-F1:          0.8835
Balanced accuracy: 0.8768
Macro precision:   0.9096
Macro recall:      0.8768
```

Модель является прототипом скрининговой системы и не должна интерпретироваться как самостоятельно валидированная диагностическая медицинская система.
```