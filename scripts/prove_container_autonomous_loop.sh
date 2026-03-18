#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${1:-ai-customer-success-autonomous}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to prove the autonomous controller loop in a container."
  exit 1
fi

cd "$ROOT_DIR"

docker build -t "$IMAGE_NAME" .

docker run --rm "$IMAGE_NAME" bash -lc '
  python scripts/autonomous_audit.py &&
  python scripts/autonomous_controller.py status &&
  python scripts/autonomous_controller.py next &&
  python scripts/autonomous_controller.py run-cycle &&
  python scripts/autonomous_controller.py assert-artifacts &&
  python -m pytest tests/test_autonomous_audit.py tests/test_autonomous_controller.py tests/test_local_agent_runner.py
'
