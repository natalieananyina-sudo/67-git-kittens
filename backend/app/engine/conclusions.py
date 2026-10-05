"""Заключения для врача и для пациента по результату ML-модуля.

Вход — ответ AnemiaInferenceService (anemia, deficiency_cause, anemia_class, status, reason, ...).
Этот модуль ничего не решает сам: он только подбирает тексты к решению модели.

Тексты (исследования, вопросы пациенту, повторный приём, питание) взяты из документа медицинского эксперта
«Заключения (часть после результатов)». Расхождения между документами команды решены так:
* «Рекомендуемое лечение» есть у эксперта, но концепция MVP запрещает назначать лечение. Блок по умолчанию
  скрыт; включается переменной окружения INCLUDE_TREATMENT_HINTS=true.
* «Предполагаемый диагноз» заменён на «Предварительное заключение»: сервис не ставит диагноз.
* Латентный дефицит железа: у эксперта причина указана как «недостаток трансферрина»; в коде использована
  формулировка «истощение запасов железа». Требует подтверждения медицинским экспертом.
* model_score и deficiency_cause_scores — технические оценки модели, НЕ вероятности диагноза
  (README_ML.md). Поэтому в текстах они не выражаются в процентах и не называются «вероятностью».
"""
from . import analytes as an
from . import labels as lb
from .validation import CaseInput

DISCLAIMER_DOCTOR = (
    "Заключение создано автоматически на основе технологий искусственного интеллекта. "
    "Результат является скрининговой поддержкой принятия решения и не заменяет клинический диагноз."
)
DISCLAIMER_PATIENT = (
    "Заключение создано автоматически на основе технологий искусственного интеллекта. "
    "Не является окончательным диагнозом; интерпретация результатов и тактика определяются лечащим врачом."
)

# deficiency_cause модели -> блоки текстов эксперта. Порядок в сочетаниях — приоритет коррекции
# по заключениям эксперта: B12, затем фолаты, затем железо.
CAUSE_TEXT_KEYS = {
    "iron_deficiency": ["iron"],
    "B12_deficiency": ["b12"],
    "folate_deficiency": ["folate"],
    "B6_deficiency": ["b6"],
    "copper_deficiency": ["copper"],
    "inflammation": ["inflammation"],
    "iron_B12": ["b12", "iron"],
    "iron_folate": ["folate", "iron"],
    "B12_folate": ["b12", "folate"],
    "undetermined": ["unexplained"],
}
_MIXED_NAMES = {"iron": "железа", "b12": "B12", "folate": "фолатов"}
_OTHER_SYSTEMS = "Обследование других систем при наличии жалоб"

TEXTS: dict[str, dict] = {
    "iron": {
        "anemia": {
            "title": "Железодефицитная анемия (ЖДА)", "cause": "недостаток железа",
            "exams": ["Эзофагогастродуоденоскопия (ЭГДС)", "Колоноскопия", "Анализ кала на скрытую кровь",
                      "Серология целиакии (анти-tTG IgA)", "Антитела к париетальным клеткам и внутреннему фактору Кастла",
                      "КТ", _OTHER_SYSTEMS],
            "ask": [], "retest": "через 7–10 дней после начала терапии, назначенной врачом",
            "treatment": ["Препараты железа",
                          "Поддерживающая терапия: после нормализации гемоглобина продолжать приём железа 3–6 месяцев для восполнения депо"],
        },
        "latent": {
            "title": "Латентный дефицит железа", "cause": "истощение запасов железа при сохранённом гемоглобине",
            "exams": ["Серология целиакии (анти-tTG IgA): обязательна при неясном дефиците железа; целиакия может проявляться только латентным дефицитом без симптомов со стороны ЖКТ",
                      "Тест на Helicobacter pylori", "ЭГДС / колоноскопия", _OTHER_SYSTEMS],
            "ask": ["питание", "прохождение терапии по поводу другого заболевания", "наличие сопутствующих заболеваний"],
            "retest": "через 8–10 недель после начала терапии, назначенной врачом", "treatment": ["Сульфат железа"],
        },
        "female_extra_exam": "Гинекологический осмотр",
        "diet": "красное мясо (говядина, телятина), печень, язык, рыба, морепродукты",
        "patient_what": "возможной нехватки железа в организме",
    },
    "b12": {
        "anemia": {
            "title": "B12-дефицитная анемия", "cause": "недостаток витамина B12",
            "exams": ["Антитела к париетальным клеткам и внутреннему фактору", "Гастроскопия с биопсией",
                      "Серология целиакии (анти-tTG IgA)", "Копрограмма и эластаза кала", "МРТ спинного мозга", _OTHER_SYSTEMS],
            "ask": [], "retest": "через 7–10 дней после начала терапии, назначенной врачом",
            "treatment": ["Витамин B12", "Пожизненная заместительная терапия B12"],
        },
        "latent": {
            "title": "B12-дефицит без анемии (латентный B12-дефицит)", "cause": "недостаток витамина B12",
            "exams": ["Антитела к париетальным клеткам и внутреннему фактору", "Гастроскопия с биопсией",
                      "Серология целиакии (анти-tTG IgA)", "Копрограмма и эластаза кала",
                      "При отсутствии показателей: гомоцистеин и метилмалоновая кислота (MMA)", _OTHER_SYSTEMS],
            "ask": ["питание (вегетарианство/веганство)", "приём лекарственных препаратов (метформин, ингибиторы протонной помпы)",
                    "наличие аутоиммунных заболеваний в анамнезе"],
            "retest": "через 7–10 дней после начала терапии, назначенной врачом (оценка клинического ответа и ретикулоцитов; без анемии ретикулоцитарный ответ может быть менее выражен)",
            "treatment": ["Витамин B12", "При вегетарианстве: обязательная фортификация или добавки B12"],
        },
        "diet": "мясо, печень, рыба, моллюски, яйца, молочные продукты",
        "patient_what": "возможной нехватки витамина B12, необходимого для образования клеток крови и работы нервной системы",
    },
    "folate": {
        "anemia": {
            "title": "Фолиеводефицитная анемия", "cause": "недостаток фолиевой кислоты",
            "exams": ["Серология целиакии (анти-tTG IgA)", "Гастроскопия с биопсией", "Копрограмма", _OTHER_SYSTEMS],
            "ask": ["питание", "прохождение терапии по поводу другого заболевания"],
            "retest": "через 7–10 дней после начала терапии, назначенной врачом", "treatment": ["Фолиевая кислота"],
        },
        "latent": {
            "title": "Фолат-дефицит без анемии (латентный фолат-дефицит)", "cause": "недостаток фолиевой кислоты",
            "exams": ["Серология целиакии (анти-tTG IgA)", "Гастроскопия с биопсией", "Копрограмма и эластаза кала",
                      "Если нет показателя: гомоцистеин", "Обязательно проверить уровень B12 до начала терапии фолатом", _OTHER_SYSTEMS],
            "ask": ["питание", "приём лекарственных препаратов (метотрексат, триметоприм, противосудорожные средства)",
                    "хронический алкоголизм"],
            "retest": "через 7–10 дней после начала терапии, назначенной врачом", "treatment": ["Фолиевая кислота"],
        },
        "diet": "зелёные листовые овощи (шпинат, брокколи, салат), бобовые (фасоль, чечевица), спаржа, цитрусовые, печень, яйца",
        "patient_what": "возможной нехватки фолиевой кислоты (витамина B9), необходимой для образования клеток крови",
    },
    "copper": {
        "anemia": {
            "title": "Дефицит меди (гематологические проявления)", "cause": "нарушение всасывания меди",
            "exams": ["Сывороточная медь и церулоплазмин (подтверждение)", "Суточная экскреция меди с мочой",
                      "Уровень цинка в сыворотке (исключение цинк-индуцированного дефицита меди)",
                      "Гастроскопия с биопсией (оценка мальабсорбции, целиакия)", _OTHER_SYSTEMS],
            "ask": ["питание", "хирургические вмешательства (бариатрические операции, резекция желудка/кишечника)",
                    "приём цинксодержащих препаратов"],
            "retest": "через 7–10 дней после начала терапии, назначенной врачом", "treatment": ["Сульфат меди"],
        },
        "latent": {"title": "Возможный дефицит меди (без анемии)"},
        "diet": "печень, морепродукты, орехи, семена, цельные злаки, бобовые",
        "patient_what": "возможной нехватки меди, которая участвует в обмене железа и образовании клеток крови",
    },
    "b6": {
        "anemia": {
            "title": "Дефицит витамина B6 (пиридоксина)", "cause": "недостаток витамина B6",
            "exams": ["Оценка уровня пиридоксаль-5-фосфата (PLP) в плазме",
                      "Анализ принимаемых лекарственных препаратов (изониазид, гидралазин, пеницилламин, противосудорожные средства)",
                      "Оценка нутритивного статуса (исключение белково-энергетической недостаточности)",
                      "Гастроскопия с биопсией", _OTHER_SYSTEMS],
            "ask": ["питание", "приём лекарственных препаратов", "наличие диализа в анамнезе"],
            "retest": "через 7–10 дней после начала терапии, назначенной врачом (оценка гематологического ответа)",
            "treatment": ["Витамин B6"],
        },
        "latent": {"title": "Возможный дефицит витамина B6 (без анемии)"},
        "diet": "печень, рыба, цельные злаки, бобовые, яйца",
        "patient_what": "возможной нехватки витамина B6, который участвует в образовании гемоглобина",
    },
    "inflammation": {
        "anemia": {
            "title": "Анемия, ассоциированная с воспалением", "cause": "острая или хроническая инфекция либо воспалительный процесс",
            "exams": ["Гемокультура", "Серология: ВИЧ, гепатиты B и C, ЭБВ, ЦМВ", "Аутоиммунный профиль",
                      "Рентгенография грудной клетки, УЗИ брюшной полости, при необходимости КТ", "ЭКГ и ЭхоКГ",
                      "Анализ кала на скрытую кровь"],
            "ask": [], "retest": "после получения результатов исследований", "treatment": [],
            "note": "Коррекция анемии возможна только при устранении и контроле основного воспалительного процесса.",
        },
        "latent": {"title": "Лабораторные признаки воспаления без анемии"},
        "diet": None,
        "patient_what": "воспалительного процесса в организме, который может влиять на уровень гемоглобина",
    },
    "unexplained": {
        "anemia": {
            "title": "Анемия без выявленного дефицитного паттерна", "cause": "",
            "exams": ["Развёрнутый анализ крови с ретикулоцитами, MCV, MCH, RDW",
                      "Ферритин, сывороточное железо, TIBC, TSAT (исключение ЖДА и латентного дефицита железа)",
                      "Витамин B12, фолат, гомоцистеин, MMA (исключение мегалобластной анемии)",
                      "CRP, СОЭ (исключение анемии хронического воспаления)",
                      "Креатинин, рСКФ (исключение анемии при ХБП)", "ТТГ (исключение гипотиреоза)",
                      "Электрофорез гемоглобина (исключение талассемии)",
                      "Прямой антиглобулиновый тест (проба Кумбса): исключение аутоиммунного гемолиза",
                      "ЛДГ, гаптоглобин, непрямой билирубин (оценка гемолиза)",
                      "Миелограмма и трепанобиопсия (при неясном генезе после исключения перечисленных причин)",
                      _OTHER_SYSTEMS],
            "ask": ["питание", "менструальный статус (для женщин)", "наличие хронических заболеваний",
                    "приём лекарственных препаратов", "семейный анамнез анемий"],
            "retest": "после получения результатов исследований",
            "treatment": ["Симптоматическая терапия не показана до установления причины; после установления этиологии — патогенетическая терапия"],
        },
        "diet": "сбалансированное питание с достаточным содержанием железа, B12, фолата и белка",
        "patient_what": "",
    },
}

_UNEXPLAINED_SAFE = (
    "Анемия без выявленного поддерживаемой моделью дефицитного паттерна; "
    "требуется дальнейшая клиническая дифференциальная оценка."
)


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _block(text_key: str, anemia: bool) -> dict:
    """Тексты состояния; для латентных B6/меди берём рекомендации анемического варианта."""
    entry = TEXTS[text_key]
    block = dict(entry["anemia"])
    if not anemia and "latent" in entry:
        block.update(entry["latent"])
    return block


def _content(sex: str | None, anemia: bool, cause: str) -> dict:
    """Тексты эксперта для пары «анемия + причина», выбранной моделью."""
    if cause == "none":
        return {"title": "Отклонений в анализах нет", "cause": "", "exams": [], "ask": [], "retest": "через год",
                "diet": None, "treatment": [], "components": [], "note": None}
    comps = CAUSE_TEXT_KEYS[cause]
    blocks = [_block(k, anemia) for k in comps]
    exams: list[str] = []
    ask: list[str] = []
    treatment: list[str] = []
    diets: list[str] = []
    for key, block in zip(comps, blocks):
        exams += block.get("exams", [])
        ask += block.get("ask", [])
        treatment += block.get("treatment", [])
        if TEXTS[key].get("diet"):
            diets.append(TEXTS[key]["diet"])
        if sex == "female" and TEXTS[key].get("female_extra_exam"):
            exams.append(TEXTS[key]["female_extra_exam"])

    if len(comps) > 1:  # сочетанный дефицит (модель выдаёт его только при анемии)
        names = [_MIXED_NAMES[k] for k in comps]
        joined = ", ".join(names[:-1]) + " и " + names[-1]
        title = f"Сочетанный дефицит {joined} с анемией"
        cause_text = f"недостаток {joined}"
        treatment = ["При сочетании дефицитов в приоритете коррекция B12, затем фолатов"] + treatment
    else:
        title = blocks[0]["title"]
        cause_text = blocks[0].get("cause", "")

    exams = _dedupe(exams)
    if _OTHER_SYSTEMS in exams:  # этот пункт всегда последний
        exams = [e for e in exams if e != _OTHER_SYSTEMS] + [_OTHER_SYSTEMS]
    return {
        "title": title, "cause": cause_text, "exams": exams, "ask": _dedupe(ask),
        "retest": blocks[0].get("retest", ""), "diet": "; ".join(_dedupe(diets)) or None,
        "treatment": _dedupe(treatment), "components": comps,
        "note": next((b.get("note") for b in blocks if b.get("note")), None),
    }


def _section(title: str, text: str | None = None, items: list[str] | None = None) -> dict:
    return {"title": title, "text": text, "items": items or []}


def _fmt(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _flagged_groups(lab_flags: list[dict]) -> str:
    """Группы показателей, вышедших за ориентировочный диапазон (факт, а не «вклад в решение модели»)."""
    groups: list[str] = []
    for lab in lab_flags:
        if lab["flag"] != "normal" and an.GROUPS[lab["group"]] not in groups:
            groups.append(an.GROUPS[lab["group"]])
    return "; ".join(groups)


def _insufficient_report(case: CaseInput, ml: dict) -> dict:
    reason = lb.REASON_LABELS.get(ml.get("reason") or "", ml.get("reason") or "причина не указана")
    todo: list[str] = []
    if ml.get("reason") == "missing_sex":
        todo.append("Укажите пол пациента.")
    elif ml.get("reason") == "invalid_sex":
        todo.append("Укажите пол в формате female/male (F/M, Ж/М).")
    elif ml.get("reason") == "missing_hemoglobin":
        todo.append("Добавьте значение гемоглобина.")
    else:
        missing = [lb.PANEL_LABELS.get(p, p) for p in ml.get("missing_panels") or [] if p != "cbc"]
        todo.append("Нет ни одного показателя в панелях: " + "; ".join(missing) + ".")
        todo.append("Добавьте результаты хотя бы части этих панелей — модель допускает отсутствие не более одной панели.")
    doctor_sections = [
        _section("Основание результата", items=[f"ML-модуль не сформировал заключение: {reason}."]),
        _section("Что нужно для заключения", items=todo),
    ]
    patient_sections = [
        _section("Что произошло", "Для автоматического скрининга не хватило результатов анализов."),
        _section("Что делать дальше", items=["Обсудите с лечащим врачом, какие анализы нужно сдать дополнительно."]),
    ]
    return {
        "title": lb.INSUFFICIENT_LABEL, "severity": "insufficient",
        "doctor": {"headline": lb.INSUFFICIENT_LABEL, "summary": f"Заключение не сформировано: {reason}.",
                   "sections": doctor_sections, "disclaimer": DISCLAIMER_DOCTOR},
        "patient": {"headline": "Данных недостаточно для результата", "summary": "",
                    "sections": patient_sections, "disclaimer": DISCLAIMER_PATIENT},
    }


def build_report(case: CaseInput, ml: dict, lab_flags: list[dict], include_treatment: bool) -> dict:
    """ml — ответ AnemiaInferenceService.predict(); lab_flags — показатели с отметками «ниже/выше нормы»."""
    if ml["status"] == "insufficient_data":
        return _insufficient_report(case, ml)

    anemia = bool(ml["anemia"])
    cause = ml["deficiency_cause"]
    content = _content(case.sex, anemia, cause)
    healthy = cause == "none" and not anemia
    hb = case.labs["hemoglobin"]
    threshold = lb.HB_DISPLAY_THRESHOLD[case.sex]
    sex_word = "женщин" if case.sex == "female" else "мужчин"

    # ---------- основания результата (для врача) ----------
    scores = ml.get("deficiency_cause_scores") or {}
    basis = [f"Гемоглобин {hb:g} г/л при пороге {threshold:g} г/л для {sex_word}: анемия "
             f"{'выявлена' if anemia else 'не выявлена'} (клиническое правило ML-модуля, не обучаемая часть)."]
    basis.append(f"Причина по модели: {lb.CAUSE_LABELS[cause].lower()} "
                 f"(технический score {_fmt(ml['model_score'])}; это не вероятность диагноза).")
    alternatives = [f"{lb.CAUSE_LABELS[c].lower()} — {_fmt(v)}"
                    for c, v in sorted(scores.items(), key=lambda kv: -kv[1]) if c != cause and v >= 0.1]
    if alternatives:
        basis.append("Другие варианты модели со score ≥ 0,10: " + "; ".join(alternatives) + ".")
    missing = [lb.PANEL_LABELS.get(p, p) for p in ml.get("missing_panels") or []]
    if missing:
        basis.append("Нет данных панели: " + "; ".join(missing) + ". Модель обучена работать с такими пропусками, "
                     "но уверенность вывода ниже.")

    notes: list[str] = []
    if content["note"]:
        notes.append(content["note"])
    if cause == "undetermined":
        notes.append(_UNEXPLAINED_SAFE)

    # ---------- версия для врача ----------
    doctor_sections = [_section("Основание результата", items=basis)]
    if healthy:
        doctor_summary = "Заключение: отклонений в анализах нет."
        doctor_sections.append(_section("Рекомендация", "Повторное обследование через год."))
    else:
        doctor_summary = f"Причина (предположительно): {content['cause']}." if content["cause"] else _UNEXPLAINED_SAFE
        if content["exams"]:
            doctor_sections.append(_section("Рекомендуемые исследования", items=content["exams"]))
        if content["ask"]:
            doctor_sections.append(_section("Уточнить у пациента", items=content["ask"]))
        if content["retest"]:
            doctor_sections.append(_section("Повторный приём", content["retest"][0].upper() + content["retest"][1:] + "."))
        if content["diet"]:
            doctor_sections.append(_section("Питание", "Добавить в рацион продукты: " + content["diet"] + "."))
        if include_treatment and content["treatment"]:
            doctor_sections.append(_section("Рекомендуемое лечение (по заключению эксперта)", items=content["treatment"]))
    if notes:
        doctor_sections.append(_section("Примечания", items=notes))

    # ---------- версия для пациента ----------
    if healthy:
        patient_headline = "Отклонений в анализах не выявлено"
        patient_sections = [
            _section("Что обнаружено", "По имеющимся данным признаков анемии и скрытого дефицита не обнаружено."),
            _section("Что делать дальше", "Повторное обследование рекомендуется через год."),
        ]
    else:
        comps = content["components"]
        whats = [TEXTS[k]["patient_what"] for k in comps if TEXTS[k]["patient_what"]]
        if len(whats) > 1:
            what_part = "нехватки нескольких веществ: " + "; ".join(w.replace("возможной нехватки ", "") for w in whats)
        else:
            what_part = whats[0] if whats else ""

        if anemia:
            patient_headline = "Выявлены признаки анемии"
            what = f"Гемоглобин снижен ({hb:g} г/л): есть признаки анемии."
            what += (f" Дополнительно есть признаки {what_part}." if what_part
                     else " По имеющимся данным причину определить не удалось; её нужно выяснить вместе с врачом.")
            why = ("Низкий гемоглобин может сопровождаться слабостью, быстрой утомляемостью, одышкой, головокружением. "
                   "Важно выяснить причину этого состояния.")
        else:
            patient_headline = "Выявлены признаки возможного скрытого дефицита"
            what = f"Гемоглобин в пределах нормы ({hb:g} г/л), но есть признаки {what_part}."
            why = ("Скрытое состояние может долго никак не проявляться, но со временем способно привести к анемии. "
                   "Поэтому его важно подтвердить и выяснить причину.")
        next_steps = ["Обсудите результат с лечащим врачом: окончательное решение принимает он."]
        if content["retest"]:
            next_steps.append("Повторный приём: " + content["retest"] + ".")
        patient_sections = [_section("Что обнаружено", what), _section("Почему это важно", why)]
        groups = _flagged_groups(lab_flags)
        if groups:
            patient_sections.append(_section("Какие показатели вне нормы", groups + "."))
        patient_sections.append(_section("Что делать дальше", items=next_steps))
        if content["exams"]:
            patient_sections.append(_section("Рекомендуется выполнить (по согласованию с врачом)", items=content["exams"]))
        if content["diet"]:
            patient_sections.append(_section("Питание", "Добавьте в рацион продукты: " + content["diet"] + "."))
        if include_treatment and content["treatment"]:
            patient_sections.append(_section("Возможная тактика (обсудите с врачом)", items=content["treatment"]))

    severity = "attention" if anemia else ("watch" if cause != "none" else "ok")
    return {
        "title": content["title"],
        "severity": severity,
        "doctor": {"headline": content["title"], "summary": doctor_summary, "sections": doctor_sections, "disclaimer": DISCLAIMER_DOCTOR},
        "patient": {"headline": patient_headline, "summary": "", "sections": patient_sections, "disclaimer": DISCLAIMER_PATIENT},
    }
