# EDA: статистика датасета deficiency_anemia

## Общая информация
- Всего пациентов: **840**
- Всего признаков: **48**
- Целевых переменных: **10** (8 бинарных + anemia_class + deficiency_cause)
- Уникальных классов anemia_class: **12**
- Уникальных причин deficiency_cause: **11**

## Демография
- age_years: 18–93, среднее 58.4
- sex: F = 596 (71%), M = 244 (29%) — **дисбаланс 2.4×**

## Пропуски (актуально по CSV, 27 признаков с пропусками)

| Признак | Пропусков | % |
|---|---|---|
| copper | 716 | 85.2% |
| ceruloplasmin | 709 | 84.4% |
| vitamin_B6 | 705 | 83.9% |
| Ret_He | 614 | 73.1% |
| sTfR | 588 | 70.0% |
| active_B12 | 588 | 70.0% |
| MMA | 568 | 67.6% |
| homocysteine | 542 | 64.5% |
| LDH | 515 | 61.3% |
| indirect_bilirubin | 515 | 61.3% |
| haptoglobin | 494 | 58.8% |
| reticulocytes | 439 | 52.3% |
| TSH | 415 | 49.4% |
| folate | 385 | 45.8% |
| ESR | 348 | 41.4% |
| CRP | 344 | 41.0% |
| vitamin_B12 | 327 | 38.9% |
| TIBC, UIBC, TSAT, serum_iron, transferrin | 300 | 35.7% |
| eGFR, creatinine | 299 | 35.6% |
| albumin | 296 | 35.2% |
| ferritin | 246 | 29.3% |
| RDW | 15 | 1.8% |

## Распределение классов anemia_class

| Класс | Кол-во |
|---|---|
| mixed_deficiency | 115 |
| iron_deficiency_anemia | 115 |
| no_anemia_no_deficiency | 110 |
| latent_deficiency | 85 |
| anemia_other | 75 |
| inflammation_anemia | 65 |
| B12_deficiency_anemia | 65 |
| B12_deficiency_no_anemia | 50 |
| folate_deficiency_anemia | 50 |
| folate_deficiency_no_anemia | 40 |
| copper_deficiency | 35 |
| B6_deficiency | 35 |

**Дисбаланс:** макс/мин ≈ 3.3× (умеренный).

## Проблемы
1. **Ферритин пропущен у 29.3%** — ключевой маркер ЖДА.
2. **B12 пропущен у 38.9%** — компенсация через active_B12 (70% пропусков) и MMA (67.6% пропусков) **затруднена**.
3. **TSH пропущен у 49.4%** — сложно исключить гипотиреоз.
4. **copper, ceruloplasmin, vitamin_B6** пропущены у 84–85% — **классы `copper_deficiency` и `B6_deficiency` предсказать сложно**.
5. Все таргеты **заполнены** — можно обучать ML.
6. **Дисбаланс пола:** F=596, M=244 (2.4×). Клинически объяснимо.

## Стратегия
- **XGBoost/LightGBM/CatBoost** — устойчивы к NaN.
- **Флаги пропуска** для ключевых признаков (ferritin, B12, sTfR, Ret_He, MMA, active_B12, homocysteine, copper, B6, TSH).
- **Не импутировать ферритин** глобально — потеря информации о MNAR-природе пропусков.
- **Комбинация правил (clinical_rules) + ML.**
- **Anemia** — детерминированное правило (Hb < 120 Ж, < 130 М). Совпадение с target 100%.
- **Метрика:** Macro-F1 по anemia_class.
- **Контроль shortcut:** missingness-only baseline.

## Важные наблюдения
- **TSAT_calc** не восстановил новых значений — у 300 пациентов пропущены TSAT+serum_iron+TIBC вместе.
- **Выбросы** (CRP до 180, ESR до 113, eGFR до 18) — клинически осмысленные, не удалять.
- **Mixed_deficiency** выводится из комбинации базовых дефицитов правилом.
- **`deficiency_cause`** однозначно определяется из anemia + 6 базовых состояний.
- **`anemia_class`** однозначно определяется из anemia + deficiency_cause.

## Актуальный датасет
- Источник: `data/raw/deficiency_anemia.csv`
- SHA-256 зафиксирован, совпадает с копиями команды.
- Единый источник данных для обучения.
