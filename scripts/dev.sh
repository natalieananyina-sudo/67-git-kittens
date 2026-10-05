#!/usr/bin/env bash
# Запуск бэкенда и фронтенда для разработки одной командой. Остановка: Ctrl+C.
# Перед первым запуском выполните scripts/setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/backend"
.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

cd "$ROOT/frontend"
echo "Откройте http://localhost:5173 (API: http://localhost:5173/docs). Модель загружается несколько секунд."
npm run dev
