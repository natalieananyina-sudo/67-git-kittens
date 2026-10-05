"""Русские подписи для значений, которые возвращает ML-модуль.

Здесь только тексты для интерфейса. Сами решения (анемия, причина, итоговый класс, достаточность
данных) принимает ML-модуль в backend/ml/src/ml; бэкенд их не пересчитывает.
"""

# status (src/ml/rules.py: determine_result_status)
STATUS_LABELS = {
    "signal_detected": "Выявлен сигнал, требующий внимания",
    "no_signal_detected": "Сигналов не выявлено",
    "insufficient_data": "Недостаточно данных для заключения",
}

# reason при status = insufficient_data (src/ml/rules.py: check_data_sufficiency)
REASON_LABELS = {
    "missing_sex": "не указан пол пациента",
    "invalid_sex": "пол указан в неизвестном формате",
    "missing_hemoglobin": "не указан гемоглобин",
    "multiple_fully_missing_panels": "полностью отсутствуют две или более панели анализов (кроме общего анализа крови)",
}

# Лабораторные панели (src/ml/config.py: LAB_PANELS)
PANEL_LABELS = {
    "cbc": "общий анализ крови",
    "iron": "обмен железа",
    "b12_folate": "витамин B12 и фолаты",
    "b6_copper": "витамин B6 и медь",
    "inflammation": "маркеры воспаления",
    "renal_thyroid": "функция почек и щитовидной железы",
    "hemolysis_reticulocytes": "гемолиз и ретикулоциты",
}

# deficiency_cause (src/ml/postprocessing.py: VALID_CAUSES_BY_ANEMIA)
CAUSE_LABELS = {
    "none": "Дефицит не выявлен",
    "iron_deficiency": "Дефицит железа",
    "B12_deficiency": "Дефицит витамина B12",
    "folate_deficiency": "Дефицит фолатов",
    "B6_deficiency": "Дефицит витамина B6",
    "copper_deficiency": "Дефицит меди",
    "inflammation": "Воспаление",
    "iron_B12": "Сочетанный дефицит: железо и B12",
    "iron_folate": "Сочетанный дефицит: железо и фолаты",
    "B12_folate": "Сочетанный дефицит: B12 и фолаты",
    "undetermined": "Причина не определена",
}

# anemia_class (src/ml/postprocessing.py: POSTPROCESSING_MAP)
ANEMIA_CLASS_LABELS = {
    "no_anemia_no_deficiency": "Нет анемии и исследуемых дефицитов",
    "latent_deficiency": "Латентный дефицит железа без анемии",
    "iron_deficiency_anemia": "Железодефицитная анемия",
    "B12_deficiency_anemia": "B12-дефицитная анемия",
    "B12_deficiency_no_anemia": "Дефицит B12 без анемии",
    "folate_deficiency_anemia": "Фолиеводефицитная анемия",
    "folate_deficiency_no_anemia": "Дефицит фолатов без анемии",
    "B6_deficiency": "Дефицит витамина B6",
    "copper_deficiency": "Дефицит меди",
    "inflammation_anemia": "Анемия, ассоциированная с воспалением",
    "mixed_deficiency": "Сочетанное дефицитное состояние",
    # По концепции MVP не пишем «анемия иной природы»: используем безопасную формулировку
    "anemia_other": "Анемия без выявленного дефицитного паттерна",
}
INSUFFICIENT_LABEL = "Недостаточно данных для заключения"

# Пороги гемоглобина — ТОЛЬКО для подписи на экране («88 г/л при пороге 120»).
# Решение об анемии принимает src/ml/rules.py: apply_anemia_rule; совпадение порогов проверяет
# тест tests/test_ml_integration.py, чтобы подпись не разошлась с моделью.
HB_DISPLAY_THRESHOLD = {"female": 120.0, "male": 130.0}

# Причины, которые считаются «дефицитом» в сводке по файлу (воспаление и неопределённая причина — нет)
NUTRITIONAL_CAUSES = {
    "iron_deficiency", "B12_deficiency", "folate_deficiency", "B6_deficiency", "copper_deficiency",
    "iron_B12", "iron_folate", "B12_folate",
}
