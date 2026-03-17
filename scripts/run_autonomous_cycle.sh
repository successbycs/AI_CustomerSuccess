#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cd "$ROOT_DIR"

echo "== Autonomous audit =="
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

if [[ -n "${AUTONOMOUS_AGENT_RUNNER:-}" ]]; then
  echo
  echo "== Executing configured local agent runner =="
  for PROMPT_PATH in \
    "docs/agents/planner_agent.md" \
    "docs/agents/builder_agent.md" \
    "docs/agents/reviewer_agent.md" \
    "docs/agents/qa_agent.md"; do
    echo "Running $PROMPT_PATH for milestone $CURRENT_FOCUS"
    "$AUTONOMOUS_AGENT_RUNNER" "$PROMPT_PATH" "$CURRENT_FOCUS"
  done

  echo
  echo "== Verification =="
  "$PYTHON_BIN" scripts/autonomous_controller.py verify

  echo
  echo "== Review / QA status recording =="
  echo "Record reviewer outcome:"
  echo "  $PYTHON_BIN scripts/autonomous_controller.py review $CURRENT_FOCUS --status pass|fail --note \"...\""
  echo "Record QA outcome:"
  echo "  $PYTHON_BIN scripts/autonomous_controller.py qa $CURRENT_FOCUS --status pass|fail --note \"...\" [--manual-checks-complete]"
  echo "Complete only after verification, review, and QA pass:"
  echo "  $PYTHON_BIN scripts/autonomous_controller.py complete $CURRENT_FOCUS"
else
  echo
  echo "No AUTONOMOUS_AGENT_RUNNER configured."
  echo "Generating repo-native local role packets instead."
  for PROMPT_PATH in \
    "docs/agents/planner_agent.md" \
    "docs/agents/builder_agent.md" \
    "docs/agents/reviewer_agent.md" \
    "docs/agents/qa_agent.md"; do
    "$PYTHON_BIN" scripts/local_agent_runner.py "$PROMPT_PATH" "$CURRENT_FOCUS"
  done
  echo
  echo "You can still execute milestone verification and status transitions manually:"
  echo "  $PYTHON_BIN scripts/autonomous_controller.py verify"
fi
