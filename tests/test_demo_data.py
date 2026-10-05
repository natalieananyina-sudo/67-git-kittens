"""Демо-наборы из data/demo обрабатываются так, как записано в их ключах ответов.

Если тест падает после замены модели — пересоберите витрину:
    backend/.venv/bin/python scripts/generate_demo_data.py
"""
from pathlib import Path

import pandas as pd
import pytest

DEMO = Path(__file__).resolve().parent.parent / "data" / "demo"
pytestmark = pytest.mark.skipif(not DEMO.exists(), reason="нет папки data/demo")


def _upload(client, headers, path: Path, endpoint="batch"):
    return client.post(f"/api/v1/screening/{endpoint}", headers=headers,
                       files={"file": (path.name, path.read_bytes(), "application/octet-stream")})


@pytest.mark.parametrize("name,answers", [("01_showcase_all_classes.csv", "01_answers.csv"),
                                          ("05_other_units.csv", "05_answers.csv")])
def test_showcase_files_match_answer_keys(client, auth_headers, name, answers):
    body = _upload(client, auth_headers, DEMO / name).json()
    assert body["file_check"]["ok"] is True
    got = {r["case_id"]: r["anemia_class"] for r in body["rows"]}
    expected = pd.read_csv(DEMO / "answers" / answers)
    mismatched = [pid for pid, cls in zip(expected.patient_id, expected.true_class) if got[pid] != cls]
    assert not mismatched, f"Витрина устарела, пересоберите демо-наборы: {mismatched}"


def test_showcase_covers_all_12_classes(client, auth_headers):
    body = _upload(client, auth_headers, DEMO / "01_showcase_all_classes.csv").json()
    assert len({r["anemia_class"] for r in body["rows"]}) == 12


def test_error_file_reports_every_planted_problem(client, auth_headers):
    body = _upload(client, auth_headers, DEMO / "04_with_format_errors.csv").json()
    planted = pd.read_csv(DEMO / "answers" / "04_expected_problems.csv")
    rows_with_issues = {i["row"] for i in body["file_check"]["issues"] if i["row"]}
    # 7 заложенных проблем: 5 ошибок формата, повтор ID (предупреждение) и пустой гемоглобин,
    # который не ошибка формата: такую строку ML-модуль возвращает со статусом insufficient_data
    assert body["summary"]["errors"] == 5 and body["summary"]["insufficient_data"] >= 1
    assert len(rows_with_issues) == len(planted) - 1


def test_single_patient_files(client, auth_headers):
    answers = pd.read_csv(DEMO / "answers" / "single_answers.csv")
    for path in sorted((DEMO / "single").glob("0[1-7]_*.csv")):
        result = _upload(client, auth_headers, path, "file").json()["result"]
        assert result["anemia_class"] == answers.set_index("patient_id").loc[result["case_id"], "true_class"], path.name
    assert _upload(client, auth_headers, DEMO / "single" / "08_with_errors.csv", "file").status_code == 422
    insufficient = _upload(client, auth_headers, DEMO / "single" / "09_insufficient_data.csv", "file").json()["result"]
    assert insufficient["screening_status"] == "insufficient_data"


def test_unselected_sets_show_honest_share_of_insufficient_data(client, auth_headers):
    """В наборах без отбора, как и в исходных данных, около трети строк — insufficient_data."""
    body = _upload(client, auth_headers, DEMO / "02_clinic_day_representative.csv").json()
    share = body["summary"]["insufficient_data"] / body["summary"]["total"]
    assert 0.15 < share < 0.5
