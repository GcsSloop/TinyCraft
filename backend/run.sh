#!/usr/bin/env sh
set -eu

APP_MODULE="${APP_MODULE:-app.main:app}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

source .venv/bin/activate

exec uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" --reload
