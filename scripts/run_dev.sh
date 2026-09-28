#!/usr/bin/env bash
# Start Chicago Ag Connect (Chicago) locally. Stop with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
export KMP_USE_SHM="${KMP_USE_SHM:-0}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
exec .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
