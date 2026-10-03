import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .analysis import analyze


def response(payload, status=200):
    result = JsonResponse(payload, status=status)
    result["Cache-Control"] = "no-store"
    return result


@csrf_exempt  # Stateless internal API: no accounts, cookies, or session authentication.
@require_POST
def analyze_view(request):
    try:
        if len(request.body) > 750_000:
            raise ValueError("Запрос слишком большой")
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("Неверный формат запроса")
        if "records" in payload:
            records = payload["records"]
            if not isinstance(records, list) or not 1 <= len(records) <= 1000:
                raise ValueError("Передайте от 1 до 1000 строк")
            results = []
            for index, item in enumerate(records, start=1):
                try:
                    if not isinstance(item, dict):
                        raise ValueError("Неверная строка")
                    results.append({"row": index, "result": analyze(item)})
                except ValueError as exc:
                    results.append({"row": index, "error": str(exc)})
            return response({"results": results})
        return response({"result": analyze(payload)})
    except json.JSONDecodeError:
        return response({"error": "Неверный формат JSON"}, status=400)
    except ValueError as exc:
        return response({"error": str(exc)}, status=400)
