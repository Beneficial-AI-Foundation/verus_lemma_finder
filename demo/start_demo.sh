#!/bin/bash
# Simple script to start the Verus Lemma Finder demo server

set -e

cd "$(dirname "$0")/.."

echo "🚀 Starting Verus Lemma Finder Demo..."
echo ""
echo "📦 Installing dependencies..."
uv pip install -q fastapi "uvicorn[standard]"

echo ""
echo "🔍 Starting server..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Demo URL: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Health:   http://localhost:8000/api/health"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uv run uvicorn demo.server:app --host 0.0.0.0 --port 8000

