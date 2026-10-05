#!/usr/bin/env bash
# Установка зависимостей для запуска без Docker (Linux, macOS, WSL).
# Требуется: Python 3.11+ (рекомендуется 3.12 — на нём сохранена ML-модель) и Node.js 20.19+ (или 22.12+).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Берём python3.12, если он установлен, иначе python3 (не ниже 3.11)
PYTHON="$(command -v python3.12 || command -v python3)"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || { echo "Нужен Python 3.11 или новее, найден: $("$PYTHON" --version)"; exit 1; }

echo "== Бэкенд и ML-модуль: виртуальное окружение ($("$PYTHON" --version)) и зависимости"
cd "$ROOT/backend"
"$PYTHON" -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements-dev.txt

echo "== ML-модуль: smoke-test из поставки ML-команды"
(cd ml && ../.venv/bin/python example_inference.py | tail -2)

echo "== Фронтенд: зависимости"
cd "$ROOT/frontend"
npm ci

echo "Готово. Запуск: scripts/dev.sh"
