"""Генерация демонстрационных наборов данных, похожих на исходный датасет.

Как это работает:
* для каждой строки берётся реальная строка исходного датасета того же итогового класса (anemia_class);
* «первичные» значения слегка зашумляются (±1,5–3 %), а производные индексы пересчитываются по формулам,
  чтобы данные оставались внутренне согласованными: MCV = Hct·10/RBC, MCH = Hb/RBC, MCHC = Hb·100/Hct,
  TIBC = Fe + UIBC, TSAT = Fe/TIBC·100;
* набор пропусков (какие анализы не сданы) сохраняется как в исходной строке;
* гемоглобин зашумляется так, чтобы наличие анемии (порог ВОЗ) не изменилось;
* ID, возраст (±2 года) новые, персональных данных нет.

Запуск (из корня репозитория, исходный CSV в репозиторий не входит):
    backend/.venv/bin/python scripts/generate_demo_data.py
По умолчанию исходный CSV берётся из data/raw/deficiency_anemia.csv (туда же его кладут для ноутбуков;
в git он не хранится). Другой путь: --source путь/к/deficiency_anemia.csv

Витринный набор (01_*) и одиночные файлы отбираются так, чтобы ML-модель классифицировала их верно —
это удобно для живой демонстрации. Наборы 02_* и 03_* не отбираются: в них, как и в исходных данных,
около трети строк получают от модели статус insufficient_data (не хватает двух и более панелей анализов).
Важно: модель обучалась на этом же датасете, поэтому совпадение на демо-наборах выше, чем на новых данных
(честная оценка — test-метрики в backend/ml/artifacts/models/final/model_manifest.json).

Скрипт также записывает backend/app/engine/demo_cases.json — примеры для интерфейса и демо-файл API.
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.engine import analytes as an  # noqa: E402
from app.engine import labels as lb  # noqa: E402
from app.engine.pipeline import screen  # noqa: E402
from app.engine.predictor import get_predictor  # noqa: E402
from app.engine.validation import validate_case  # noqa: E402

LAB_CODES = [a.code for a in an.ANALYTES]
HEADER = ["patient_id", "age_years", "sex"] + LAB_CODES
DERIVED = {"MCV", "MCH", "MCHC", "TIBC", "TSAT"}
NOISE = {"hemoglobin": 0.015, "RBC": 0.015, "hematocrit": 0.015}  # остальные: 3 %
CLASS_TITLES = lb.ANEMIA_CLASS_LABELS


def decimals(series: pd.Series) -> int:
    """Сколько знаков после запятой в исходных значениях столбца."""
    values = series.dropna()
    for k in range(4):
        if ((values * 10**k).round(6) % 1 == 0).all():
            return k
    return 3


def jitter_row(src: pd.Series, rng: random.Random, prec: dict[str, int]) -> dict | None:
    out: dict = {}
    for code in LAB_CODES:
        value = src[code]
        if pd.isna(value) or code in DERIVED:
            continue
        out[code] = float(value) * (1 + rng.gauss(0, NOISE.get(code, 0.03)))

    # Пересчёт производных индексов (только там, где исходно были значения)
    if "hemoglobin" in out and "RBC" in out and "hematocrit" in out:
        hb, rbc, hct = out["hemoglobin"], out["RBC"], out["hematocrit"]
        for code, val in (("MCV", hct * 10 / rbc), ("MCH", hb / rbc), ("MCHC", hb * 100 / hct)):
            if not pd.isna(src[code]):
                out[code] = val
    if "serum_iron" in out and "UIBC" in out:
        tibc = out["serum_iron"] + out["UIBC"]
        if not pd.isna(src["TIBC"]):
            out["TIBC"] = tibc
        if not pd.isna(src["TSAT"]):
            out["TSAT"] = out["serum_iron"] / tibc * 100

    # Наличие анемии не должно измениться от шума
    threshold = lb.HB_DISPLAY_THRESHOLD["female" if src["sex"] == "F" else "male"]
    if (out["hemoglobin"] < threshold) != bool(src["anemia"]):
        return None
    for code in out:
        out[code] = round(out[code], prec[code]) if prec[code] else int(round(out[code]))
        a = an.BY_KEY[code.lower()]
        out[code] = min(max(out[code], a.valid_min), a.valid_max)
    out["age_years"] = min(93, max(18, int(src["age_years"]) + rng.randint(-2, 2)))
    out["sex"] = src["sex"]
    return out


def service_result(row: dict, case_id: str) -> tuple[str | None, str | None]:
    """(anemia_class, status) от ML-модели; (None, None), если строка не прошла проверку формата."""
    labs = {k: v for k, v in row.items() if k in LAB_CODES}
    check = validate_case(case_id, row["age_years"], row["sex"], labs)
    if check.case is None:
        return None, None
    result = screen(check.case, get_predictor())
    return result["anemia_class"], result["screening_status"]


def make_rows(df, classes, rng, prec, prefix, only_correct=False, start=1):
    """classes: список классов (повторы = несколько строк). Возвращает строки и ключ ответов."""
    rows, answers = [], []
    for i, cls in enumerate(classes, start=start):
        pool = df[df.anemia_class == cls]
        for _attempt in range(400):
            src = pool.iloc[rng.randrange(len(pool))]
            row = jitter_row(src, rng, prec)
            if row is None:
                continue
            pid = f"{prefix}-{i:04d}"
            got, status = service_result(row, pid)
            if only_correct and got != cls:
                continue
            row["patient_id"] = pid
            rows.append(row)
            answers.append({"patient_id": pid, "true_class": cls, "true_class_ru": CLASS_TITLES[cls],
                            "service_status": status, "service_class": got, "match": int(got == cls)})
            break
        else:
            raise RuntimeError(f"Не удалось подобрать строку класса {cls}")
    return rows, answers


def make_insufficient(df, rng, prec, pid: str) -> dict:
    """Строка, для которой ML-модуль вернёт insufficient_data (две и более панели отсутствуют целиком)."""
    for _attempt in range(400):
        src = df.iloc[rng.randrange(len(df))]
        row = jitter_row(src, rng, prec)
        if row is None:
            continue
        _cls, status = service_result(row, pid)
        if status == "insufficient_data":
            row["patient_id"] = pid
            return row
    raise RuntimeError("Не найдена строка с insufficient_data")


def case_json(row, case_id: str, title: str) -> dict:
    """Пример в формате запроса POST /api/v1/screening."""
    labs = {}
    for code in LAB_CODES:
        value = row.get(code)
        if value is not None and value == value and value != "":
            labs[code.lower()] = float(value)
    return {"id": case_id, "title": title, "input": {"case_id": case_id, "age": int(row["age_years"]),
            "sex": "female" if row["sex"] == "F" else "male", "laboratory_data": labs}}


def write_csv(path: Path, rows: list[dict], header: list[str] = HEADER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in header})


def write_answers(path: Path, answers: list[dict]) -> tuple[float, float, float]:
    """Возвращает (доля верных среди всех, доля insufficient_data, доля верных среди достаточных)."""
    pd.DataFrame(answers).to_csv(path, index=False, encoding="utf-8")
    sufficient = [a for a in answers if a["service_status"] != "insufficient_data"]
    return (sum(a["match"] for a in answers) / len(answers), 1 - len(sufficient) / len(answers),
            sum(a["match"] for a in sufficient) / max(1, len(sufficient)))


def proportional(df, n, rng):
    """Классы пропорционально исходному распределению (стратифицированная выборка)."""
    shares = df.anemia_class.value_counts(normalize=True)
    counts = (shares * n).round().astype(int)
    classes = [c for c, k in counts.items() for _ in range(k)][:n]
    while len(classes) < n:  # округление могло дать на 1–2 строки меньше
        classes.append(shares.index[0])
    rng.shuffle(classes)
    return classes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=str(ROOT / "data" / "raw" / "deficiency_anemia.csv"),
                        help="исходный CSV (по умолчанию data/raw/deficiency_anemia.csv)")
    parser.add_argument("--out", default=str(ROOT / "data" / "demo"))
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    if not Path(args.source).is_file():
        sys.exit(f"Нет исходного CSV: {args.source}. Положите deficiency_anemia.csv в data/raw/ или укажите --source.")
    df = pd.read_csv(args.source)
    prec = {c: decimals(df[c]) for c in LAB_CODES}
    out = Path(args.out)
    answers_dir = out / "answers"
    answers_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    classes_all = sorted(df.anemia_class.unique())
    report = []

    # 01. Витрина: по 2 пациента каждого из 12 классов, классифицируются сервисом верно
    rows, ans = make_rows(df, [c for c in classes_all for _ in range(2)], rng, prec, "SC", only_correct=True)
    write_csv(out / "01_showcase_all_classes.csv", rows)
    report.append(("01_showcase_all_classes.csv", len(rows), write_answers(answers_dir / "01_answers.csv", ans)))

    # 02. Обычный приём: 60 пациентов, распределение классов как в исходных данных, без отбора
    rows, ans = make_rows(df, proportional(df, 60, rng), rng, prec, "CD")
    write_csv(out / "02_clinic_day_representative.csv", rows)
    report.append(("02_clinic_day_representative.csv", len(rows), write_answers(answers_dir / "02_answers.csv", ans)))

    # 03. Большой скрининг в XLSX: 600 пациентов, без отбора (производительность и формат XLSX)
    rows, ans = make_rows(df, proportional(df, 600, rng), rng, prec, "LG")
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "screening"
    ws.append(HEADER)
    for row in rows:
        ws.append([row.get(k) for k in HEADER])
    wb.save(out / "03_screening_large.xlsx")
    report.append(("03_screening_large.xlsx", len(rows), write_answers(answers_dir / "03_answers.csv", ans)))

    # 04. Файл с ошибками формата: 8 корректных строк и 7 строк с типичными проблемами
    rows, _ = make_rows(df, rng.sample(classes_all, 8), rng, prec, "ER", only_correct=True)
    broken_src, _ = make_rows(df, ["iron_deficiency_anemia"] * 7, rng, prec, "ER", only_correct=True, start=9)
    problems = [
        ("hemoglobin", None, "нет гемоглобина: не ошибка формата, модель вернёт insufficient_data"),
        ("hemoglobin", 11.2, "гемоглобин в г/дл вместо г/л"),
        ("age_years", 16, "возраст младше 18 лет"),
        ("sex", "X", "неизвестный пол"),
        ("CRP", "<0,5", "значение с символом «<»"),
        ("ferritin", "высокий", "текст вместо числа"),
        ("patient_id", rows[0]["patient_id"], "повтор ID (предупреждение, строка обработается)"),
    ]
    expected = []
    for row, (col, value, what) in zip(broken_src, problems):
        row[col] = value
        expected.append({"patient_id": row["patient_id"], "problem_column": col, "problem": what})
    all_rows = rows + broken_src
    header = HEADER + ["comment"]
    for row in all_rows:
        row.setdefault("comment", "")
    all_rows[0]["comment"] = "столбец comment не распознаётся и будет проигнорирован"
    write_csv(out / "04_with_format_errors.csv", all_rows, header)
    pd.DataFrame(expected).to_csv(answers_dir / "04_expected_problems.csv", index=False, encoding="utf-8")
    report.append(("04_with_format_errors.csv", len(all_rows), None))

    # 05. Другие единицы измерения в заголовках: сервис переведёт их в стандартные
    unit_cols = {"hemoglobin": ("g/dL", 10), "ferritin": ("ng/mL", 1), "vitamin_B12": ("pmol/L", 1.355),
                 "folate": ("nmol/L", 0.4413), "creatinine": ("mg/dL", 88.42), "CRP": ("mg/dL", 10)}
    rows, ans = make_rows(df, rng.sample(classes_all, 10), rng, prec, "UN", only_correct=True)
    header = ["patient_id", "age_years", "sex"] + [
        f"{c} ({unit_cols[c][0]})" if c in unit_cols else c for c in LAB_CODES]
    converted = []
    for row in rows:
        new = {k: row.get(k) for k in ("patient_id", "age_years", "sex")}
        for c in LAB_CODES:
            v = row.get(c)
            name = f"{c} ({unit_cols[c][0]})" if c in unit_cols else c
            new[name] = None if v is None else (round(v / unit_cols[c][1], 3) if c in unit_cols else v)
        converted.append(new)
    write_csv(out / "05_other_units.csv", converted, header)
    report.append(("05_other_units.csv", len(rows), write_answers(answers_dir / "05_answers.csv", ans)))

    # Одиночные файлы для режима «Один пациент»
    singles = [("normal", "no_anemia_no_deficiency"), ("iron_deficiency_anemia", "iron_deficiency_anemia"),
               ("latent_iron_deficiency", "latent_deficiency"), ("b12_no_anemia", "B12_deficiency_no_anemia"),
               ("mixed_deficiency", "mixed_deficiency"), ("inflammation_anemia", "inflammation_anemia"),
               ("copper_deficiency", "copper_deficiency")]
    single_answers = []
    for n, (name, cls) in enumerate(singles, start=1):
        rows, ans = make_rows(df, [cls], rng, prec, f"ONE{n:02d}", only_correct=True)
        write_csv(out / "single" / f"{n:02d}_{name}.csv", rows)
        single_answers += ans
    rows, _ = make_rows(df, ["iron_deficiency_anemia"], rng, prec, "ONE08", only_correct=True)
    rows[0]["ferritin"] = "нет"
    rows[0]["CRP"] = "<0,5"
    write_csv(out / "single" / "08_with_errors.csv", rows)
    # реальная строка, где модель сообщит о нехватке данных (нет двух и более панелей)
    insufficient = make_insufficient(df, rng, prec, "ONE09")
    write_csv(out / "single" / "09_insufficient_data.csv", [insufficient])
    write_answers(answers_dir / "single_answers.csv", single_answers)

    # Примеры для интерфейса и демо-файл API (backend/app/engine/demo_cases.json)
    titles = {"no_anemia_no_deficiency": "Без отклонений"}
    examples = []
    for n, (name, cls) in enumerate(singles, start=1):
        row = pd.read_csv(out / "single" / f"{n:02d}_{name}.csv").iloc[0]
        examples.append(case_json(row, f"EX-{n:02d}", titles.get(cls, CLASS_TITLES[cls])))
    examples.append(case_json(pd.Series(insufficient), "EX-09", "Недостаточно данных"))
    showcase = pd.read_csv(out / "01_showcase_all_classes.csv")
    demo_rows = [case_json(r, r["patient_id"], CLASS_TITLES[a["true_class"]])
                 for (_, r), a in zip(showcase.iterrows(), pd.read_csv(answers_dir / "01_answers.csv").to_dict("records"))]
    (ROOT / "backend" / "app" / "engine" / "demo_cases.json").write_text(
        json.dumps({"examples": examples, "batch": demo_rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    print("Готово:", out)
    for name, n, acc in report:
        line = f"  {name:38s} {n:4d} строк"
        if acc is not None:
            line += f": верно {acc[0]:.0%}, insufficient_data {acc[1]:.0%}, верно среди достаточных {acc[2]:.0%}"
        print(line)


if __name__ == "__main__":
    main()
