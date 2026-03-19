"""Autonomous role CLI with evaluator and agentic-builder backends."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import requests

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_CODEX_COMMAND = "codex"
ROLE_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["pass", "fail", "in_progress", "blocked"],
        },
        "summary": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "manual_checks_required": {"type": "boolean"},
        "manual_checks_complete": {"type": "boolean"},
    },
    "required": [
        "status",
        "summary",
        "issues",
        "manual_checks_required",
        "manual_checks_complete",
    ],
    "additionalProperties": True,
}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Read one autonomous role packet from stdin and return a normalized OpenAI JSON result.",
    )
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def load_packet() -> dict[str, Any]:
    """Read one JSON packet from stdin."""
    raw = sys.stdin.read().strip()
    if not raw:
        raise RuntimeError("OpenAI agent CLI expected one JSON packet on stdin")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"OpenAI agent CLI received malformed JSON: {error}") from error

    if not isinstance(payload, dict):
        raise RuntimeError("OpenAI agent CLI expected a JSON object packet")
    return payload


def build_system_prompt(packet: dict[str, Any]) -> str:
    """Build the system prompt for one role packet."""
    role = str(packet.get("role") or "unknown")
    return (
        "You are the {role} role in a milestone-driven software delivery loop. "
        "Read the packet carefully and return exactly one JSON object. "
        "Do not wrap it in markdown. "
        "Allowed keys are: status, summary, issues, manual_checks_required, manual_checks_complete. "
        "status must be one of: pass, fail, in_progress, blocked. "
        "issues must be a JSON array of short strings. "
        "summary must be concise and concrete. "
        "manual_checks_required and manual_checks_complete must be booleans."
    ).format(role=role)


def build_user_prompt(packet: dict[str, Any]) -> str:
    """Build the user prompt for one role packet."""
    return (
        "Evaluate this autonomous role packet and return the required JSON object.\n\n"
        f"{json.dumps(packet, indent=2)}"
    )


def build_builder_prompt(packet: dict[str, Any]) -> str:
    """Build the builder prompt for a real agentic repo-writing pass."""
    return (
        "You are the builder role in a milestone-driven software delivery loop.\n"
        "Implement the milestone directly in the repository, not just by describing the work.\n"
        "Inspect the repo first, keep changes bounded to the delegated write scope, "
        "update stale docs caused by the implementation, add or update tests, and run the relevant verification commands.\n"
        "Respect the milestone acceptance criteria, the delegated task contract, and the role checklist in the packet.\n"
        "When you finish, return exactly one JSON object with keys: "
        "status, summary, issues, manual_checks_required, manual_checks_complete.\n"
        "Use status='pass' only when the builder-side implementation and its executable verification are complete.\n"
        "Use status='in_progress' when meaningful implementation landed but review/QA/manual proof still remains.\n"
        "Use status='blocked' or 'fail' when you cannot proceed or the implementation attempt failed.\n"
        "manual_checks_complete should remain false for the builder role.\n\n"
        f"{json.dumps(packet, indent=2)}"
    )


def extract_response_text(payload: dict[str, Any]) -> str:
    """Extract plain text from a Responses API payload."""
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    fragments: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") in {"output_text", "text"} and isinstance(part.get("text"), str):
                    fragments.append(part["text"])
    return "\n".join(fragment for fragment in fragments if fragment.strip()).strip()


def normalize_result(raw_result: Any) -> dict[str, Any]:
    """Normalize model output to the local runner contract."""
    if not isinstance(raw_result, dict):
        raise RuntimeError("OpenAI agent CLI must return a JSON object")

    issues = raw_result.get("issues")
    if not isinstance(issues, list):
        issues = []

    status = str(raw_result.get("status") or "").strip().lower()
    if status not in {"pass", "fail", "in_progress", "blocked"}:
        status = "in_progress"

    return {
        "status": status,
        "summary": str(raw_result.get("summary") or "").strip(),
        "issues": [str(item) for item in issues],
        "manual_checks_required": bool(raw_result.get("manual_checks_required", False)),
        "manual_checks_complete": bool(raw_result.get("manual_checks_complete", False)),
    }


def codex_command() -> str:
    """Return the codex binary path."""
    configured = os.environ.get("AUTONOMOUS_CODEX_COMMAND", "").strip()
    if configured:
        return configured
    resolved = shutil.which(DEFAULT_CODEX_COMMAND)
    if not resolved:
        raise RuntimeError("codex is required for agentic builder execution")
    return resolved


def call_builder_agent(packet: dict[str, Any], *, model: str) -> dict[str, Any]:
    """Run the builder role through Codex CLI so it can actually modify the repo."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as schema_file:
        schema_file.write(json.dumps(ROLE_RESULT_SCHEMA))
        schema_path = Path(schema_file.name)
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as output_file:
        output_path = Path(output_file.name)

    command = [
        codex_command(),
        "-a",
        "never",
        "exec",
        "-s",
        "workspace-write",
        "--skip-git-repo-check",
        "--ephemeral",
        "-C",
        str(Path.cwd()),
        "-m",
        model,
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
        build_builder_prompt(packet),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip()
                or completed.stdout.strip()
                or f"Codex builder exited with {completed.returncode}"
            )

        response_text = output_path.read_text(encoding="utf-8").strip()
        if not response_text:
            raise RuntimeError("Codex builder did not return a final JSON message")

        raw_result = json.loads(response_text)
        normalized = normalize_result(raw_result)
        normalized["backend"] = "codex_exec"
        return normalized
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Codex builder returned invalid JSON: {error}") from error
    finally:
        schema_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def call_openai(packet: dict[str, Any], *, model: str, base_url: str, timeout: int) -> dict[str, Any]:
    """Call the OpenAI Responses API and return normalized JSON."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to use scripts/openai_agent_cli.py")

    request_payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": build_system_prompt(packet)}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": build_user_prompt(packet)}],
            },
        ],
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=request_payload,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    text = extract_response_text(payload)
    if not text:
        raise RuntimeError("OpenAI response did not contain any text output")

    try:
        raw_result = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"OpenAI response text was not valid JSON: {error}") from error

    return normalize_result(raw_result)


def main(argv: list[str] | None = None) -> int:
    """Run the OpenAI-backed CLI."""
    args = build_parser().parse_args(argv)
    try:
        packet = load_packet()
        if str(packet.get("role") or "").strip().lower() == "builder":
            result = call_builder_agent(packet, model=args.model)
        else:
            result = call_openai(
                packet,
                model=args.model,
                base_url=args.base_url,
                timeout=args.timeout,
            )
    except Exception as error:  # noqa: BLE001 - surface a clear CLI error
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
