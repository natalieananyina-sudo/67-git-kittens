"""Эндпоинты скрининга: один случай (JSON или файл), много случаев (файл), шаблоны и примеры."""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse, Response

from ..config import settings
from ..engine import demo_data
from ..engine.batch import BatchFileError, process_batch, process_single, read_table
from ..engine.pipeline import screen
from ..engine.predictor import get_predictor
from ..engine.validation import validate_case
from ..schemas import (
    BatchResponse, ErrorResponse, FileErrorResponse, ScreeningRequest, ScreeningResponse, SingleFileResponse,
)
from ..security import get_current_doctor

router = APIRouter(prefix="/screening", tags=["Скрининг"], dependencies=[Depends(get_current_doctor)])
_AUTH = {401: {"description": "Нет действующего токена"}}
_FILE_ERRORS = {413: {"model": FileErrorResponse, "description": "Файл слишком большой"},
                422: {"model": FileErrorResponse, "description": "Ошибки формата файла или данных"}}


def _error(errors: list[dict], status_code: int = 422, file_check: dict | None = None) -> JSONResponse:
    body = {"status": "error", "errors": errors}
    if file_check is not None:
        body["file_check"] = file_check
    return JSONResponse(status_code=status_code, content=body)


def _file_fatal(exc: BatchFileError) -> JSONResponse:
    """Фатальная ошибка файла: отдаём и краткое сообщение, и полный список проблем."""
    check = {"ok": False, "rows": 0, "recognized_columns": 0, "errors": len(exc.issues), "warnings": 0,
             "issues": exc.issues, "issues_truncated": 0}
    return _error([{"field": "file", "message": str(exc)}], file_check=check)


async def _read_upload(file: UploadFile) -> bytes | JSONResponse:
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        return _error([{"field": "file", "message": f"Файл больше {settings.max_upload_bytes // (1024 * 1024)} МБ."}], 413)
    return content


@router.post(
    "", response_model=ScreeningResponse, summary="Скрининг одного случая (JSON)",
    description="Данные проверяются, приводятся к единицам датасета и передаются в ML-модуль. В ответе: "
                "`ml_result` — ответ модуля без изменений, подписи по-русски и два представления (для врача и для пациента). "
                "Если данных недостаточно, ответ 200 со `screening_status = insufficient_data` и причиной.",
    responses={**_AUTH, 422: {"model": ErrorResponse, "description": "Ошибки во входных данных"}},
)
def screening(body: ScreeningRequest):
    check = validate_case(body.case_id, body.age, body.sex, body.laboratory_data, body.units)
    if check.case is None:
        return _error([{"field": e.field, "message": e.message} for e in check.errors])
    result = screen(check.case)
    result["warnings"] = check.warnings + result["warnings"]
    result["unit_conversions"] = check.conversions
    return result


@router.post(
    "/file", response_model=SingleFileResponse, summary="Скрининг одного случая из файла (CSV/XLSX, одна строка)",
    description="Формат файла тот же, что для нескольких пациентов, но строка с данными ровно одна. "
                "В ответе результат и отчёт о проверке формата файла.",
    responses={**_AUTH, **_FILE_ERRORS},
)
async def screening_file(file: UploadFile = File(..., description="CSV или XLSX с одной строкой данных")):
    content = await _read_upload(file)
    if isinstance(content, JSONResponse):
        return content
    try:
        result, check, _case = process_single(read_table(file.filename or "", content), get_predictor())
    except BatchFileError as exc:
        return _file_fatal(exc)
    if result is None:
        first = next(i for i in check["issues"] if i["level"] == "error")
        return _error([{"field": "file", "message": first["message"]}], file_check=check)
    return {"result": result, "file_check": check}


@router.post(
    "/batch", response_model=BatchResponse, summary="Скрининг многих случаев из файла (CSV/XLSX)",
    description="Столбцы: patient_id, age_years, sex и показатели (hemoglobin, RBC, MCV, ferritin, ...). "
                "Единицу можно указать в заголовке: «ferritin (ng/mL)» — значения будут приведены к стандартным единицам. "
                "Строки с ошибками формата получают статус error, остальные обрабатываются ML-модулем; "
                "все проблемы перечислены в file_check. "
                "Файлы со столбцами персональных данных (ФИО, телефон и т.п.) отклоняются.",
    responses={**_AUTH, **_FILE_ERRORS},
)
async def screening_batch(file: UploadFile = File(..., description="CSV или XLSX")):
    content = await _read_upload(file)
    if isinstance(content, JSONResponse):
        return content
    try:
        return process_batch(read_table(file.filename or "", content), get_predictor(), settings.max_batch_rows)
    except BatchFileError as exc:
        return _file_fatal(exc)


def _csv_response(text: str, filename: str) -> Response:
    return Response(text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/batch/template", summary="Шаблон CSV (подходит для обоих режимов)", responses=_AUTH)
def batch_template():
    return _csv_response(demo_data.template_csv(), "screening_template.csv")


@router.get("/batch/demo-file", summary="Демо-файл с несколькими пациентами", responses=_AUTH)
def batch_demo_file():
    return _csv_response(demo_data.demo_csv(), "demo_batch.csv")


@router.get("/examples", summary="Вымышленные примеры для режима «Один пациент»", responses=_AUTH)
def screening_examples():
    return {"examples": demo_data.examples()}


@router.get("/examples/{example_id}/file", summary="Пример одного пациента в виде файла CSV",
            responses={**_AUTH, 404: {"description": "Пример не найден"}})
def screening_example_file(example_id: str):
    text = demo_data.example_csv(example_id)
    if text is None:
        return JSONResponse(status_code=404, content={"detail": "Пример не найден."})
    return _csv_response(text, f"example_{example_id}.csv")
