from app.engine import analytes as an
from app.engine.validation import parse_number, validate_case


def test_dataset_column_names_and_decimal_comma():
    res = validate_case("A-1", "42", "Ж", {"Hemoglobin": "108,5", "vitamin_B12": 300, "Ret_He": None, "sTfR": "", "MCV": 75})
    assert res.case is not None and not res.errors
    assert res.case.sex == "female" and res.case.age == 42
    assert res.case.labs == {"hemoglobin": 108.5, "vitamin_b12": 300.0, "mcv": 75.0}


def test_registry_matches_variables_xlsx():
    codes = [a.code for a in an.ANALYTES]
    assert len(codes) == 35
    assert {"RBC", "WBC", "Ret_He", "sTfR", "vitamin_B12", "active_B12", "MMA", "CRP", "ESR", "eGFR", "TSH", "LDH"} <= set(codes)
    assert an.BY_KEY["ceruloplasmin"].unit_code == "g/L" and an.BY_KEY["ferritin"].unit_code == "ug/L"


def test_unit_conversion_to_dataset_units():
    res = validate_case("A1", 40, "female", {"hemoglobin": 10.8, "vitamin_b12": 100, "ceruloplasmin": 25, "folate": 10},
                        units={"hemoglobin": "g/dL", "vitamin_B12": "pmol/L", "ceruloplasmin": "мг/дл", "folate": "nmol/L"})
    assert res.case is not None, res.errors
    assert res.case.labs["hemoglobin"] == 108
    assert res.case.labs["vitamin_b12"] == 135.5
    assert res.case.labs["ceruloplasmin"] == 0.25
    assert abs(res.case.labs["folate"] - 4.413) < 1e-6
    assert len(res.conversions) == 4 and "г/дл" in res.conversions[0]


def test_unknown_unit_is_error():
    res = validate_case("A1", 40, "female", {"hemoglobin": 108}, units={"hemoglobin": "furlongs"})
    assert res.case is None and "не поддерживается" in res.errors[0].message


def test_missing_hemoglobin_and_sex_are_not_format_errors():
    """Достаточность данных решает ML-модуль (insufficient_data), а не проверка формата."""
    res = validate_case("A1", 40, "", {"ferritin": 20})
    assert res.case is not None and res.case.sex is None and "hemoglobin" not in res.case.labs


def test_unrecognized_sex_is_format_error():
    res = validate_case("A1", 40, "Q", {"hemoglobin": 140})
    assert res.case is None and res.errors[0].field == "sex"
    assert validate_case("A1", 40, "Ж", {}).case.sex == "female"
    assert validate_case("A1", 40, "M", {}).case.sex == "male"


def test_out_of_range_value_hints_at_units():
    res = validate_case("A1", 40, "male", {"hemoglobin": 12.5})
    assert res.case is None and "единицы" in res.errors[0].message


def test_case_id_rejects_names_and_spaces():
    for bad in ("Иванов Иван", "ivan ivanov", "", "x" * 65, "a/b"):
        res = validate_case(bad, 40, "male", {"hemoglobin": 140})
        assert any(e.field == "case_id" for e in res.errors), bad


def test_age_limits():
    assert validate_case("A", 17, "male", {"hemoglobin": 140}).case is None
    assert validate_case("A", 18, "male", {"hemoglobin": 140}).case is not None
    assert validate_case("A", 121, "male", {"hemoglobin": 140}).case is None
    assert validate_case("A", "abc", "male", {"hemoglobin": 140}).case is None


def test_unknown_analyte_is_warning_not_error():
    res = validate_case("A", 40, "male", {"hemoglobin": 140, "unobtainium": 1})
    assert res.case is not None and any("unobtainium" in w for w in res.warnings)


def test_parse_number():
    assert parse_number("1 234,5") == 1234.5
    assert parse_number("") is None and parse_number(None) is None
