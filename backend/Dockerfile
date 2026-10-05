# Python 3.12 — версия, на которой ML-команда сохранила модель (backend/ml/artifacts/models/final/model_manifest.json)
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
COPY ml/requirements-ml.txt ml/
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY ml ./ml
EXPOSE 8000
# start-period: загрузка модели (Random Forest, 24 МБ) занимает несколько секунд
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
# --proxy-headers: за nginx реальный IP клиента берётся из X-Forwarded-For (нужно для ограничения попыток входа)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
