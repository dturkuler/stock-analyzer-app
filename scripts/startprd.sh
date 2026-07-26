#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "🐳 Starting Stock Analyzer App (Production Docker Mode)..."
docker-compose up -d --build
