"""Реестр лабораторных показателей, единиц измерения и правил их приведения.

Единицы измерения (canonical) соответствуют справочнику переменных исходных данных: к ним сервис приводит
все входные значения, в них же считаются правила и подаются данные в ML-модель.
`code` совпадает с названием столбца в исходных данных (deficiency_anemia.csv), `key` — тот же код
в нижнем регистре (используется в JSON API).

Референсные интервалы ориентировочные (для подсветки на экране); медицинскому эксперту стоит их сверить.
"""
from dataclasses import dataclass

Range = tuple[float | None, float | None]

GROUPS: dict[str, str] = {
    "cbc": "Общий анализ крови",
    "iron": "Метаболизм железа",
    "vitamins": "Витамины и метаболиты",
    "trace": "Микроэлементы",
    "inflammation": "Воспалительный и соматический профиль",
    "hemolysis": "Маркеры гемолиза и тканевого распада",
}


@dataclass(frozen=True)
class AltUnit:
    code: str     # как пишут в лабораториях (латиница)
    label: str    # как показываем пользователю
    factor: float # значение_в_этой_единице * factor = значение_в_основной_единице


@dataclass(frozen=True)
class Analyte:
    code: str                 # название столбца в исходных данных
    label: str
    unit_code: str            # единица из variables.xlsx
    unit: str                 # та же единица по-русски
    group: str
    ref_all: Range | None = None
    ref_female: Range | None = None
    ref_male: Range | None = None
    valid_min: float = 0.0    # границы правдоподобности (в основной единице)
    valid_max: float = 1e9
    required: bool = False
    alt_units: tuple[AltUnit, ...] = ()

    @property
    def key(self) -> str:
        return self.code.lower()

    def reference(self, sex: str | None) -> Range:
        if sex == "female" and self.ref_female:
            return self.ref_female
        if sex == "male" and self.ref_male:
            return self.ref_male
        return self.ref_all or self.ref_female or self.ref_male or (None, None)


def _a(code, label, unit_code, unit, group, *, all=None, f=None, m=None, vmin=0.0, vmax=1e9, required=False, alt=()):
    return Analyte(code, label, unit_code, unit, group, all, f, m, vmin, vmax, required, tuple(AltUnit(*u) for u in alt))


_UGDL_FE = ("ug/dL", "мкг/дл", 0.1791)  # железо: 1 мкг/дл = 0,1791 мкмоль/л

ANALYTES: tuple[Analyte, ...] = (
    # --- Общий анализ крови ---
    _a("hemoglobin", "Гемоглобин", "g/L", "г/л", "cbc", f=(120, 150), m=(130, 170), vmin=20, vmax=250, required=True,
       alt=[("g/dL", "г/дл", 10)]),
    _a("RBC", "Эритроциты", "10^12/L", "×10¹²/л", "cbc", f=(3.8, 5.1), m=(4.3, 5.7), vmin=0.5, vmax=9,
       alt=[("10^6/uL", "млн/мкл", 1)]),
    _a("hematocrit", "Гематокрит", "%", "%", "cbc", f=(36, 46), m=(40, 52), vmin=5, vmax=75,
       alt=[("L/L", "л/л", 100)]),
    _a("MCV", "Средний объём эритроцита (MCV)", "fL", "фл", "cbc", all=(80, 100), vmin=40, vmax=160),
    _a("MCH", "Среднее содержание Hb в эритроците (MCH)", "pg", "пг", "cbc", all=(27, 34), vmin=10, vmax=60),
    _a("MCHC", "Средняя концентрация Hb в эритроците (MCHC)", "g/L", "г/л", "cbc", all=(320, 360), vmin=200, vmax=450,
       alt=[("g/dL", "г/дл", 10)]),
    _a("RDW", "Ширина распределения эритроцитов (RDW)", "%", "%", "cbc", all=(11.5, 14.5), vmin=8, vmax=40),
    _a("platelets", "Тромбоциты", "10^9/L", "×10⁹/л", "cbc", all=(150, 400), vmin=5, vmax=2000,
       alt=[("10^3/uL", "тыс/мкл", 1)]),
    _a("WBC", "Лейкоциты", "10^9/L", "×10⁹/л", "cbc", all=(4.0, 10.0), vmin=0.3, vmax=300,
       alt=[("10^3/uL", "тыс/мкл", 1)]),
    _a("reticulocytes", "Ретикулоциты", "%", "%", "cbc", all=(0.5, 2.0), vmin=0, vmax=40,
       alt=[("permille", "‰", 0.1)]),
    # --- Метаболизм железа ---
    _a("ferritin", "Ферритин", "ug/L", "мкг/л", "iron", f=(15, 150), m=(30, 400), vmin=0.5, vmax=20000,
       alt=[("ng/mL", "нг/мл", 1)]),
    _a("serum_iron", "Сывороточное железо", "umol/L", "мкмоль/л", "iron", f=(9, 30), m=(11, 31), vmin=0.5, vmax=100,
       alt=[_UGDL_FE]),
    _a("transferrin", "Трансферрин", "g/L", "г/л", "iron", all=(2.0, 3.6), vmin=0.3, vmax=10,
       alt=[("mg/dL", "мг/дл", 0.01)]),
    _a("TIBC", "Общая железосвязывающая способность (ОЖСС)", "umol/L", "мкмоль/л", "iron", all=(45, 72), vmin=5, vmax=200,
       alt=[_UGDL_FE]),
    _a("UIBC", "Ненасыщенная железосвязывающая способность (ЛЖСС)", "umol/L", "мкмоль/л", "iron", all=(20, 62), vmin=0.5, vmax=200,
       alt=[_UGDL_FE]),
    _a("TSAT", "Насыщение трансферрина железом (TSAT)", "%", "%", "iron", all=(20, 50), vmin=0, vmax=100),
    _a("sTfR", "Растворимый рецептор трансферрина (sTfR)", "mg/L", "мг/л", "iron", all=(1.9, 4.4), vmin=0.2, vmax=60),
    _a("Ret_He", "Гемоглобин ретикулоцитов (Ret-He)", "pg", "пг", "iron", all=(28, 35), vmin=5, vmax=60),
    # --- Витамины и метаболиты ---
    _a("vitamin_B12", "Витамин B12 (общий)", "pg/mL", "пг/мл", "vitamins", all=(200, 900), vmin=10, vmax=10000,
       alt=[("pmol/L", "пмоль/л", 1.355), ("ng/L", "нг/л", 1)]),
    _a("active_B12", "Активный B12 (холотранскобаламин)", "pmol/L", "пмоль/л", "vitamins", all=(25, 165), vmin=1, vmax=1500),
    _a("MMA", "Метилмалоновая кислота (MMA)", "umol/L", "мкмоль/л", "vitamins", all=(None, 0.4), vmin=0, vmax=50,
       alt=[("nmol/L", "нмоль/л", 0.001)]),
    _a("homocysteine", "Гомоцистеин", "umol/L", "мкмоль/л", "vitamins", all=(5, 15), vmin=0.5, vmax=300),
    _a("folate", "Фолат сыворотки", "ng/mL", "нг/мл", "vitamins", all=(4.0, 20.0), vmin=0.1, vmax=200,
       alt=[("nmol/L", "нмоль/л", 0.4413), ("ug/L", "мкг/л", 1)]),
    _a("vitamin_B6", "Витамин B6 (пиридоксаль-5-фосфат)", "nmol/L", "нмоль/л", "vitamins", all=(20, 125), vmin=0.5, vmax=2000,
       alt=[("ug/L", "мкг/л", 4.046), ("ng/mL", "нг/мл", 4.046)]),
    # --- Микроэлементы ---
    _a("copper", "Медь сыворотки", "umol/L", "мкмоль/л", "trace", all=(11, 22), vmin=0.5, vmax=80,
       alt=[("ug/dL", "мкг/дл", 0.1574)]),
    _a("ceruloplasmin", "Церулоплазмин", "g/L", "г/л", "trace", all=(0.2, 0.6), vmin=0.01, vmax=2,
       alt=[("mg/dL", "мг/дл", 0.01)]),
    # --- Воспалительный и соматический профиль ---
    _a("CRP", "С-реактивный белок (СРБ)", "mg/L", "мг/л", "inflammation", all=(None, 5), vmin=0, vmax=600,
       alt=[("mg/dL", "мг/дл", 10)]),
    _a("ESR", "Скорость оседания эритроцитов (СОЭ)", "mm/h", "мм/ч", "inflammation", f=(2, 20), m=(2, 15), vmin=0, vmax=150),
    _a("creatinine", "Креатинин", "umol/L", "мкмоль/л", "inflammation", f=(44, 97), m=(62, 106), vmin=10, vmax=2500,
       alt=[("mg/dL", "мг/дл", 88.42)]),
    _a("eGFR", "Расчётная СКФ (рСКФ)", "mL/min/1.73m2", "мл/мин/1,73 м²", "inflammation", all=(60, 140), vmin=1, vmax=200),
    _a("TSH", "Тиреотропный гормон (ТТГ)", "mIU/L", "мМЕ/л", "inflammation", all=(0.4, 4.0), vmin=0.001, vmax=300,
       alt=[("uIU/mL", "мкМЕ/мл", 1)]),
    _a("albumin", "Альбумин", "g/L", "г/л", "inflammation", all=(35, 50), vmin=5, vmax=80,
       alt=[("g/dL", "г/дл", 10)]),
    # --- Маркеры гемолиза ---
    _a("LDH", "Лактатдегидрогеназа (ЛДГ)", "U/L", "Ед/л", "hemolysis", all=(120, 250), vmin=20, vmax=10000,
       alt=[("ukat/L", "мккат/л", 60)]),
    _a("indirect_bilirubin", "Непрямой билирубин", "umol/L", "мкмоль/л", "hemolysis", all=(None, 17), vmin=0, vmax=400,
       alt=[("mg/dL", "мг/дл", 17.1)]),
    _a("haptoglobin", "Гаптоглобин", "g/L", "г/л", "hemolysis", all=(0.3, 2.0), vmin=0, vmax=10,
       alt=[("mg/dL", "мг/дл", 0.01)]),
)

BY_KEY: dict[str, Analyte] = {a.key: a for a in ANALYTES}

# Синонимы названий столбцов (после нормализации: нижний регистр, пробелы и дефисы -> "_").
_ALIASES: dict[str, str] = {
    "hb": "hemoglobin", "hgb": "hemoglobin", "гемоглобин": "hemoglobin",
    "hct": "hematocrit", "erythrocytes": "rbc", "эритроциты": "rbc", "plt": "platelets",
    "leukocytes": "wbc", "лейкоциты": "wbc", "retic": "reticulocytes", "rdw_cv": "rdw",
    "serum_ferritin": "ferritin", "ферритин": "ferritin", "iron": "serum_iron", "fe": "serum_iron",
    "transferrin_saturation": "tsat", "кнт": "tsat", "ожсс": "tibc", "лжсс": "uibc",
    "str": "stfr", "ret_hb": "ret_he", "reth": "ret_he",
    "b12": "vitamin_b12", "total_b12": "vitamin_b12", "cobalamin": "vitamin_b12",
    "holotc": "active_b12", "holotranscobalamin": "active_b12",
    "hcy": "homocysteine", "folic_acid": "folate", "b9": "folate",
    "plp": "vitamin_b6", "b6": "vitamin_b6", "pyridoxal_5_phosphate": "vitamin_b6",
    "cu": "copper", "срб": "crp", "c_reactive_protein": "crp", "соэ": "esr",
    "gfr": "egfr", "скф": "egfr", "ттг": "tsh", "лдг": "ldh",
    "bilirubin_indirect": "indirect_bilirubin", "unconjugated_bilirubin": "indirect_bilirubin",
}


def normalize_key(name: str) -> str:
    key = str(name).strip().lower()
    for ch in (" ", "-", ".", "/"):
        key = key.replace(ch, "_")
    key = key.replace("(", "").replace(")", "")
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_")


def resolve_key(name: str) -> str | None:
    """Приводит произвольное название столбца/поля к ключу показателя или возвращает None."""
    key = normalize_key(name)
    if key in BY_KEY:
        return key
    return _ALIASES.get(key)


def _norm_unit(unit: str) -> str:
    text = str(unit).strip().lower().replace(" ", "").replace("µ", "u").replace("μ", "u").replace("мк", "u")
    return text.replace("²", "2").replace(",", ".")


def unit_factor(analyte: Analyte, unit: str | None) -> float | None:
    """Коэффициент перевода в основную единицу; None, если единица не распознана."""
    if unit is None or str(unit).strip() == "":
        return 1.0
    wanted = _norm_unit(unit)
    if wanted in (_norm_unit(analyte.unit_code), _norm_unit(analyte.unit)):
        return 1.0
    for alt in analyte.alt_units:
        if wanted in (_norm_unit(alt.code), _norm_unit(alt.label)):
            return alt.factor
    return None


def unit_label(analyte: Analyte, unit: str) -> str:
    """Русская подпись единицы (для сообщений о переводе)."""
    wanted = _norm_unit(unit)
    for alt in analyte.alt_units:
        if wanted in (_norm_unit(alt.code), _norm_unit(alt.label)):
            return alt.label
    return unit


def public_catalog() -> dict:
    """Описание показателей для фронтенда (форма ввода строится из него)."""
    return {
        "groups": [{"key": k, "label": v} for k, v in GROUPS.items()],
        "analytes": [
            {
                "key": a.key, "code": a.code, "label": a.label, "group": a.group, "required": a.required,
                "unit": a.unit, "unit_code": a.unit_code,
                "alt_units": [{"code": u.code, "label": u.label, "factor": u.factor} for u in a.alt_units],
                "ref_female": list(a.reference("female")), "ref_male": list(a.reference("male")),
                "valid_min": a.valid_min, "valid_max": a.valid_max,
            }
            for a in ANALYTES
        ],
        "note": "Все значения переводятся в стандартные единицы."
                "Референсные интервалы ориентировочные; ориентируйтесь на интервалы вашей лаборатории.",
    }
