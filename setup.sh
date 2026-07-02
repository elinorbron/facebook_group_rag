#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> facebook_group_rag setup"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is required. Install from https://www.python.org/downloads/"
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(echo "$PY_VERSION" | cut -d. -f1)"
PY_MINOR="$(echo "$PY_VERSION" | cut -d. -f2)"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "ERROR: Python 3.10+ required (found $PY_VERSION)"
  exit 1
fi

echo "==> Creating virtual environment"
python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Checking Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  echo ""
  echo "Ollama is not installed. Install it with:"
  echo "  brew install ollama"
  echo ""
  echo "Then re-run: ./setup.sh"
  exit 1
fi

if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama (background)..."
  ollama serve >/dev/null 2>&1 &
  sleep 2
fi

CHAT_MODEL="${CHAT_MODEL:-llama3.1:8b}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

echo "==> Pulling models (this may take a few minutes)"
ollama pull "$CHAT_MODEL"
ollama pull "$EMBED_MODEL"

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Copy your Facebook export into: $ROOT/data/"
echo "  2. Run: make ingest"
echo "  3. Run: make run"
echo ""
