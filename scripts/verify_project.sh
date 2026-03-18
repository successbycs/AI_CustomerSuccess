#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cd "$ROOT_DIR"

echo "Running repo readiness audit"
"$PYTHON_BIN" scripts/autonomous_audit.py

echo "Running controller smoke checks"
"$PYTHON_BIN" scripts/autonomous_controller.py status >/dev/null
"$PYTHON_BIN" scripts/autonomous_controller.py next >/dev/null
"$PYTHON_BIN" scripts/autonomous_controller.py next-action >/dev/null
"$PYTHON_BIN" scripts/autonomous_controller.py assert-artifacts >/dev/null

echo "Running test suite"
"$PYTHON_BIN" -m pytest
