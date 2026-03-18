#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cd "$ROOT_DIR"

if [[ -z "${AUTONOMOUS_CYCLE_ID:-}" ]]; then
  AUTONOMOUS_CYCLE_ID="cycle-$(date -u +%Y%m%dT%H%M%SZ)"
  export AUTONOMOUS_CYCLE_ID
fi

echo "== Autonomous audit =="
echo "Cycle ID: $AUTONOMOUS_CYCLE_ID"
"$PYTHON_BIN" scripts/autonomous_audit.py

echo
echo "== Controller status =="
"$PYTHON_BIN" scripts/autonomous_controller.py status

echo
echo "== Next milestone =="
"$PYTHON_BIN" scripts/autonomous_controller.py next

echo
echo "== Prompt sequence =="
"$PYTHON_BIN" scripts/autonomous_controller.py run-cycle

CURRENT_FOCUS="$("$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("project_state.json").read_text(encoding="utf-8"))
print(payload.get("current_focus") or "")
PY
)"

if [[ -z "$CURRENT_FOCUS" ]]; then
  echo
  echo "No current_focus is set in project_state.json."
  exit 1
fi

get_next_action_json() {
  "$PYTHON_BIN" scripts/autonomous_controller.py next-action "$CURRENT_FOCUS" --json
}

extract_json_field() {
  local JSON_INPUT="$1"
  local FIELD_NAME="$2"
  printf '%s' "$JSON_INPUT" | "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin).get('$FIELD_NAME', ''))"
}

echo
echo "== Controller-owned iteration =="
"$PYTHON_BIN" scripts/autonomous_controller.py auto-iterate "$CURRENT_FOCUS"
