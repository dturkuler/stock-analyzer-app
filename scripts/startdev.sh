#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "🚀 Starting Stock Analyzer App (Development Mode)..."
python3 -m uvicorn 3_web_server.main:app --reload --host 0.0.0.0 --port 6031
