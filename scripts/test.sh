#!/usr/bin/env bash
# Все проверки: smoke-test ML-модуля, тесты бэкенда, линтер и сборка фронтенда.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Smoke-test ML-модуля (как в README_ML.md: python example_inference.py)"
cd "$ROOT/backend/ml"
../.venv/bin/python example_inference.py | tail -2

echo "== Тесты бэкенда"
cd "$ROOT"
backend/.venv/bin/python -m pytest -q tests

echo "== Линтер и сборка фронтенда"
cd "$ROOT/frontend"
npm run lint
npm run build
