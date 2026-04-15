#!/bin/zsh

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
