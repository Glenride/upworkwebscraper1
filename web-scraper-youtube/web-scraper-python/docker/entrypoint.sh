#!/usr/bin/env bash
set -euo pipefail

# Defaults for directories when not provided
export SCRAPER_OUTPUT_ROOT="${SCRAPER_OUTPUT_ROOT:-output}"
export SCRAPER_LOGS_ROOT="${SCRAPER_LOGS_ROOT:-logs}"
export SCRAPER_UI_DB_PATH="${SCRAPER_UI_DB_PATH:-ui_runs.db}"
export SCRAPER_TEMPLATES_ROOT="${SCRAPER_TEMPLATES_ROOT:-templates}"

if [[ -z "${SCRAPER_INPUT_URLS:-}" ]]; then
  echo "ERROR: SCRAPER_INPUT_URLS environment variable is required." >&2
  exit 1
fi

mkdir -p "$SCRAPER_OUTPUT_ROOT" "$SCRAPER_LOGS_ROOT"

# Ensure the run database file exists so SQLite can open it in mounted volumes
if [[ ! -f "$SCRAPER_UI_DB_PATH" ]]; then
  touch "$SCRAPER_UI_DB_PATH"
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

exec uvicorn api.app:create_app --factory --host "$HOST" --port "$PORT"
