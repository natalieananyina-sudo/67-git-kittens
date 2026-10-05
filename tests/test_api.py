import io

from app.engine import demo_data

from .conftest import set_setting

IRON_EXAMPLE = next(e for e in demo_data.examples() if e["title"] == "Железодефицитная анемия")
IRON_REQUEST = IRON_EXAMPLE["input"]
ML_KEYS = {"patient_id", "status", "reason", "data_sufficient", "anemia", "deficiency_cause", "anemia_class",
           "missing_panels", "deficiency_cause_scores", "model_score"}


def test_screening_contract(client, auth_headers):
    response = client.post("/api/v1/screening", json=IRON_REQUEST, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == IRON_REQUEST["case_id"] and body["status"] == "completed"
    assert set(body["ml_result"]) == ML_KEYS                       # ответ ML-модуля передан целиком
    assert body["ml_result"]["anemia_class"] == body["anemia_class"] == "iron_deficiency_anemia"
    assert body["screening_status"] == "signal_detected" and body["anemia"]["detected"] is True
    assert body["deficiency_cause"] == "iron_deficiency" and body["model_scores"][0]["cause"] == "iron_deficiency"
    assert body["model"]["kind"] == "ml_model" and body["model"]["is_demo"] is False
    assert set(body["patient"]) == {"age", "sex"}


def test_units_in_request(client, auth_headers):
    labs = {**IRON_REQUEST["laboratory_data"], "hemoglobin": IRON_REQUEST["laboratory_data"]["hemoglobin"] / 10}
    body = {**IRON_REQUEST, "laboratory_data": labs, "units": {"hemoglobin": "g/dL"}}
    response = client.post("/api/v1/screening", json=body, headers=auth_headers).json()
    assert response["anemia"]["hemoglobin"] == round(IRON_REQUEST["laboratory_data"]["hemoglobin"], 4)
    assert response["unit_conversions"] and response["anemia_class"] == "iron_deficiency_anemia"


def test_missing_hemoglobin_is_insufficient_data_not_error(client, auth_headers):
    labs = {k: v for k, v in IRON_REQUEST["laboratory_data"].items() if k != "hemoglobin"}
    response = client.post("/api/v1/screening", json={**IRON_REQUEST, "laboratory_data": labs}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["screening_status"] == "insufficient_data" and body["ml_result"]["reason"] == "missing_hemoglobin"
    assert body["anemia_class"] is None and body["report"]["severity"] == "insufficient"


def test_format_errors_are_readable(client, auth_headers):
    response = client.post("/api/v1/screening", headers=auth_headers,
                           json={**IRON_REQUEST, "laboratory_data": {"ferritin": "много"}})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "laboratory_data.ferritin"


def test_missing_fields_use_unified_error_format(client, auth_headers):
    response = client.post("/api/v1/screening", json={"case_id": "A1"}, headers=auth_headers)
    assert response.status_code == 422 and response.json()["status"] == "error"
    assert {e["field"] for e in response.json()["errors"]} >= {"age", "laboratory_data"}


def _upload(client, headers, name, content, mime="text/csv"):
    return client.post("/api/v1/screening/batch", headers=headers, files={"file": (name, content, mime)})


def test_batch_demo_file(client, auth_headers):
    body = _upload(client, auth_headers, "demo.csv", demo_data.demo_csv().encode()).json()
    summary = body["summary"]
    assert (summary["total"], summary["completed"], summary["errors"], summary["insufficient_data"]) == (27, 25, 2, 1)
    assert {r["case_id"] for r in body["rows"] if r["status"] == "error"} == {"ERR-01", "ERR-02"}
    assert len({r["anemia_class"] for r in body["rows"] if r["anemia_class"]}) == 12
    first_ok = next(r for r in body["rows"] if r["status"] == "completed")
    reopen = client.post("/api/v1/screening", json=first_ok["input"], headers=auth_headers)
    assert reopen.status_code == 200 and reopen.json()["anemia_class"] == first_ok["anemia_class"]


def test_batch_semicolon_decimal_comma_cp1251_and_units_in_header(client, auth_headers):
    text = "patient_id;sex;age_years;Гемоглобин, г/дл;ferritin (ng/mL)\nP1;ж;40;10,85;9,0\nP2;м;50;15;120\n"
    body = _upload(client, auth_headers, "data.csv", text.encode("cp1251")).json()
    assert body["units_from_header"] == {"hemoglobin": "г/дл", "ferritin": "ng/mL"}
    assert body["rows"][0]["hemoglobin"] == 108.5 and body["rows"][1]["hemoglobin"] == 150
    assert body["rows"][0]["sex"] == "female" and body["rows"][1]["sex"] == "male"


def test_batch_rejects_unknown_header_unit(client, auth_headers):
    text = "patient_id,sex,age_years,hemoglobin (stones)\nP1,male,40,140\n"
    response = _upload(client, auth_headers, "d.csv", text.encode())
    assert response.status_code == 422 and "Единица «stones»" in response.json()["errors"][0]["message"]


def test_batch_rejects_personal_data_columns(client, auth_headers):
    text = "case_id,ФИО,sex,age,hemoglobin\nP1,Иванов И.И.,male,40,140\n"
    response = _upload(client, auth_headers, "d.csv", text.encode())
    assert response.status_code == 422 and "персональн" in response.json()["errors"][0]["message"]


def test_batch_accepts_case_dataset_format_and_ignores_labels(client, auth_headers):
    text = ("patient_id,age_years,sex,hemoglobin,MCV,ferritin,anemia,iron_deficiency,anemia_class,deficiency_cause\n"
            "P1,40,male,125,78,9,0,0,no_anemia_no_deficiency,none\n")
    body = _upload(client, auth_headers, "d.csv", text.encode()).json()
    assert set(body["ignored_columns"]) == {"anemia", "iron_deficiency", "anemia_class", "deficiency_cause"}
    # метки из файла не используются; строка без 2+ панелей -> модель вернула insufficient_data
    assert body["rows"][0]["screening_status"] == "insufficient_data"


def test_batch_xlsx(client, auth_headers):
    from openpyxl import Workbook
    labs = IRON_REQUEST["laboratory_data"]
    wb = Workbook()
    wb.active.append(["case_id", "sex", "age"] + list(labs))
    wb.active.append(["X1", IRON_REQUEST["sex"], IRON_REQUEST["age"]] + list(labs.values()))
    buffer = io.BytesIO()
    wb.save(buffer)
    body = _upload(client, auth_headers, "d.xlsx", buffer.getvalue(), "application/octet-stream").json()
    assert body["rows"][0]["anemia_class"] == "iron_deficiency_anemia"


def test_batch_bad_files(client, auth_headers):
    assert _upload(client, auth_headers, "d.txt", b"a,b").status_code == 422
    assert _upload(client, auth_headers, "d.csv", b"case_id,sex,age\n").status_code == 422
    assert _upload(client, auth_headers, "d.csv", b"case_id,sex,age,foo\nA,male,40,1\n").status_code == 422


def test_batch_limits(client, auth_headers):
    set_setting("max_batch_rows", 2)
    try:
        text = "case_id,sex,age,hemoglobin\n" + "\n".join(f"R{i},male,40,140" for i in range(3))
        assert _upload(client, auth_headers, "d.csv", text.encode()).status_code == 422
    finally:
        set_setting("max_batch_rows", 1000)
    set_setting("max_upload_bytes", 100)
    try:
        assert _upload(client, auth_headers, "d.csv", b"x" * 500).status_code == 413
    finally:
        set_setting("max_upload_bytes", 5 * 1024 * 1024)


def test_batch_performance_300_rows(client, auth_headers):
    """Модель вызывается один раз на файл; поштучно 300 строк заняли бы ~30–50 с."""
    import time
    labs = IRON_REQUEST["laboratory_data"]
    header = "patient_id,sex,age_years," + ",".join(labs) + "\n"
    rows = "\n".join(f"R{i},female,{20 + i % 60}," + ",".join(str(v * (1 + (i % 7) / 100)) for v in labs.values())
                     for i in range(300))
    started = time.perf_counter()
    response = _upload(client, auth_headers, "big.csv", (header + rows).encode())
    assert response.status_code == 200 and response.json()["summary"]["completed"] == 300
    assert time.perf_counter() - started < 20


def test_catalog(client):
    body = client.get("/api/v1/analytes").json()
    assert len(body["analytes"]) == 35
    hb = next(a for a in body["analytes"] if a["key"] == "hemoglobin")
    assert hb["required"] is True and hb["unit"] == "г/л" and hb["alt_units"][0]["code"] == "g/dL"


def test_template_and_examples(client, auth_headers):
    template = client.get("/api/v1/screening/batch/template", headers=auth_headers)
    assert template.text.splitlines()[0].startswith("patient_id,age_years,sex,hemoglobin,RBC")
    assert _upload(client, auth_headers, "t.csv", template.content).status_code == 200
    for example in client.get("/api/v1/screening/examples", headers=auth_headers).json()["examples"]:
        assert client.post("/api/v1/screening", json=example["input"], headers=auth_headers).status_code == 200


def test_openapi_and_security_headers(client):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/screening" in schema["paths"] and "/api/v1/auth/login" in schema["paths"]
    assert client.get("/docs").status_code == 200
    response = client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff" and response.headers["cache-control"] == "no-store"


BROKEN = ("patient_id,sex,age_years,hemoglobin (g/dL),ferritin,MCV,anemia_class,comment\n"
          "A1,F,40,10.5,abc,80,x,hi\n"
          "A1,Q,15,13,20,abc,x,\n"
          "A3,M,50,abc,30,90,x,\n"
          "A4,M,50,14,30,90,x,\n")


def test_file_check_pinpoints_row_and_column(client, auth_headers):
    body = _upload(client, auth_headers, "broken.csv", BROKEN.encode()).json()
    check = body["file_check"]
    assert check["ok"] is False and check["rows"] == 4
    errors = {(i["row"], i["column"]) for i in check["issues"] if i["level"] == "error"}
    assert errors == {(1, "ferritin"), (2, "sex"), (2, "age_years"), (2, "MCV"), (3, "hemoglobin (g/dL)")}
    warnings = [i["message"] for i in check["issues"] if i["level"] == "warning"]
    assert any("comment" in w for w in warnings) and any("anemia_class" in w for w in warnings)
    assert any("«A1» уже встречался" in w for w in warnings) and any("g/dL" in w for w in warnings)
    assert body["summary"]["completed"] == 1 and body["rows"][3]["hemoglobin"] == 140  # 14 г/дл -> 140 г/л


def test_file_check_ok_for_clean_file(client, auth_headers):
    check = _upload(client, auth_headers, "t.csv", client.get("/api/v1/screening/batch/template", headers=auth_headers).content).json()["file_check"]
    assert check["ok"] is True and check["errors"] == 0 and check["recognized_columns"] == 35


def test_fatal_file_errors_are_listed_together(client, auth_headers):
    response = _upload(client, auth_headers, "d.csv", "ФИО,sex\nИванов,M\n".encode())
    assert response.status_code == 422
    messages = [i["message"] for i in response.json()["file_check"]["issues"]]
    assert len(messages) == 4 and "персональными" in messages[0]


def test_duplicate_analyte_columns_rejected(client, auth_headers):
    text = "patient_id,sex,age_years,hemoglobin,Hb\nA,M,40,140,141\n"
    response = _upload(client, auth_headers, "d.csv", text.encode())
    assert response.status_code == 422 and "двух столбцах" in response.json()["errors"][0]["message"]


def _upload_single(client, headers, name, content):
    return client.post("/api/v1/screening/file", headers=headers, files={"file": (name, content, "text/csv")})


def test_single_patient_file(client, auth_headers):
    example = client.get(f"/api/v1/screening/examples/{IRON_EXAMPLE['id']}/file", headers=auth_headers)
    assert example.status_code == 200
    body = _upload_single(client, auth_headers, "one.csv", example.content).json()
    assert body["file_check"]["ok"] is True
    assert body["result"]["case_id"] == IRON_EXAMPLE["id"] and body["result"]["anemia_class"] == "iron_deficiency_anemia"


def test_single_patient_file_with_units_in_header(client, auth_headers):
    text = "patient_id,sex,age_years,hemoglobin (g/dL),vitamin_B12 (pmol/L)\nS1,M,60,10.4,80\n"
    body = _upload_single(client, auth_headers, "one.csv", text.encode()).json()
    assert body["result"]["anemia"]["hemoglobin"] == 104 and len(body["result"]["unit_conversions"]) == 2


def test_single_patient_file_must_have_one_row(client, auth_headers):
    response = _upload_single(client, auth_headers, "many.csv", BROKEN.encode())
    assert response.status_code == 422 and "4 строки" in response.json()["errors"][0]["message"]


def test_single_patient_file_with_bad_cell(client, auth_headers):
    text = "patient_id,sex,age_years,hemoglobin,ferritin\nS1,M,60,104,abc\n"
    response = _upload_single(client, auth_headers, "one.csv", text.encode())
    assert response.status_code == 422
    issue = response.json()["file_check"]["issues"][0]
    assert issue["row"] == 1 and issue["column"] == "ferritin"


def test_unknown_example_file(client, auth_headers):
    assert client.get("/api/v1/screening/examples/NOPE/file", headers=auth_headers).status_code == 404
