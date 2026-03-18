"""Repo-native local runner for autonomous role packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import autonomous_controller


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generate structured local role output for an autonomous milestone step.",
    )
    parser.add_argument("prompt_path", help="Path to the prompt markdown file.")
    parser.add_argument("milestone_id", help="Milestone id to generate the role packet for.")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument(
        "--cli-command",
        help="Optional local AI CLI command. If omitted, AUTONOMOUS_AGENT_CLI is used when set.",
    )
    return parser


def infer_role(prompt_path: Path) -> str:
    """Infer the role name from the prompt file path."""
    name = prompt_path.stem.lower()
    for role in (
        "closeout_auditor",
        "backfill_auditor",
        "controller",
        "planner",
        "builder",
        "reviewer",
        "qa",
    ):
        if role in name:
            return role
    return "unknown"


def extract_prompt_reads(prompt_text: str) -> list[str]:
    """Extract the bullet list under the first Read: section."""
    reads: list[str] = []
    in_read_block = False
    for line in prompt_text.splitlines():
        stripped = line.strip()
        if stripped == "Read:":
            in_read_block = True
            continue
        if in_read_block and stripped.startswith("- "):
            reads.append(stripped[2:].strip("`"))
            continue
        if in_read_block and stripped:
            break
    return reads


def extract_milestone_section_text(implementation_plan_text: str, milestone_id: str) -> str:
    """Extract one milestone section from the implementation plan."""
    lines = implementation_plan_text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if line.startswith(f"## {milestone_id} "):
            start_index = index
            break
    if start_index is None:
        return ""

    collected: list[str] = []
    for line in lines[start_index:]:
        if collected and line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def build_role_checklist(role: str, milestone: dict[str, Any], available_tools: list[dict[str, Any]]) -> list[str]:
    """Return a deterministic checklist for the role."""
    if role == "controller":
        checklist = [
            "Confirm current_focus and dependency status",
            "Confirm the next milestone still matches milestone_registry.json",
            "Run verification hooks through the controller",
            "Record review and QA outcomes before milestone closure",
        ]
        if available_tools:
            checklist.append("Expose declared repo tools to roles through the controller-governed access model")
        return checklist
    if role == "planner":
        checklist = [
            f"Restate the objective for {milestone['id']}",
            "List acceptance criteria and proof requirements",
            "Identify files likely to change",
            "Identify tests to add or update",
            "List manual/runtime checks required before closure",
        ]
        if available_tools:
            checklist.append("Identify which declared tools are relevant and what level of access the milestone needs")
        return checklist
    if role == "builder":
        checklist = [
            "Keep changes bounded to the milestone",
            "Update stale docs caused by the implementation",
            "Add or update tests for changed behavior",
            "Run executable verification commands before handoff",
        ]
        if available_tools:
            checklist.append("Use only declared tools that are allowed for the builder role")
        return checklist
    if role == "reviewer":
        checklist = [
            "Inspect changed files only",
            "Check architecture and guardrail alignment",
            "Call out missing tests and silent failure paths",
            "State whether the milestone is actually closeable",
        ]
        if available_tools:
            checklist.append("Confirm tool use stayed within the declared role access rules")
        return checklist
    if role == "qa":
        checklist = [
            "Check milestone verification results",
            "Check artifact existence and runtime/manual checks",
            "State whether manual checks are still pending",
            "Record pass/fail with a concrete note",
        ]
        if available_tools:
            checklist.append("Use declared read/verify tools to confirm the milestone evidence where appropriate")
        return checklist
    if role == "closeout_auditor":
        checklist = [
            "Inspect the latest completion proof for the milestone",
            "Record residual risks and accepted caveats without reopening the milestone by default",
            "Append one closeout audit entry to docs/audit/audit.md",
        ]
        if available_tools:
            checklist.append("Use only declared read-only tools to inspect supporting evidence")
        return checklist
    if role == "backfill_auditor":
        checklist = [
            "Inspect the historical milestone claim against the current repo state and run history",
            "Use docs/audit/audit.md as historical context and mark the new entry as backfill-authored",
            "Append one backfill audit entry to docs/audit/audit.md without changing milestone status",
        ]
        if available_tools:
            checklist.append("Use only declared read-only tools to inspect supporting evidence")
        return checklist
    return ["Review the prompt and milestone metadata"]


def build_fallback_result(role: str, milestone: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic fallback role result."""
    return {
        "status": "packet_only",
        "summary": (
            f"No local AI CLI was configured for the {role} role. "
            f"A structured packet was generated for {milestone['id']} instead."
        ),
        "issues": [
            "A human operator or configured local AI CLI must complete this role step.",
        ],
        "manual_checks_required": role == "qa",
    }


def normalize_cli_result(raw_result: Any) -> dict[str, Any]:
    """Normalize one CLI result payload into a predictable shape."""
    if not isinstance(raw_result, dict):
        raise RuntimeError("Local AI CLI output must be a JSON object")

    status = str(raw_result.get("status") or "").strip()
    summary = str(raw_result.get("summary") or "").strip()
    issues = raw_result.get("issues")
    if not isinstance(issues, list):
        issues = []

    normalized = dict(raw_result)
    normalized["status"] = status or "unknown"
    normalized["summary"] = summary
    normalized["issues"] = [str(item) for item in issues]
    normalized["manual_checks_required"] = bool(raw_result.get("manual_checks_required", False))
    return normalized


def run_local_ai_cli(
    *,
    cli_command: str,
    packet: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Run a configured local AI CLI and parse its JSON response."""
    completed = subprocess.run(
        shlex.split(cli_command),
        cwd=root,
        input=json.dumps(packet),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Local AI CLI failed with exit {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}"
        )

    try:
        raw_result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Local AI CLI did not return valid JSON: {error}") from error

    return normalize_cli_result(raw_result)


def default_output_path(root: Path, role: str, milestone_id: str) -> Path:
    """Build the default output path for a generated role packet."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / "runs" / "agent_outputs" / f"{timestamp}_{role}_{milestone_id}.json"


def current_cycle_id() -> str:
    """Return the current cycle id or create a one-off id."""
    existing = str(os.environ.get("AUTONOMOUS_CYCLE_ID", "")).strip()
    if existing:
        return existing
    return f"cycle-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def backend_metadata(cli_command: str | None) -> dict[str, Any]:
    """Infer backend attribution from the configured CLI command."""
    if not cli_command:
        return {"backend": "repo_native_packet", "model": None}

    tokens = shlex.split(cli_command)
    if any(token.endswith("openai_agent_cli.py") for token in tokens):
        model = None
        for index, token in enumerate(tokens):
            if token == "--model" and index + 1 < len(tokens):
                model = tokens[index + 1]
                break
        if model is None:
            model = str(os.environ.get("OPENAI_MODEL", "")).strip() or None
        return {"backend": "openai", "model": model}

    return {"backend": "custom_cli", "model": None}


def collect_changed_files(root: Path) -> list[str]:
    """Return changed repo files, excluding generated run artifacts."""
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if completed.returncode != 0:
        return []

    changed_files: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1].strip()
        if not candidate:
            continue
        if candidate.startswith("runs/") or candidate.startswith("imports/") or "__pycache__" in candidate:
            continue
        changed_files.append(candidate)
    return sorted(dict.fromkeys(changed_files))


def default_artifact_paths(milestone_id: str) -> list[str]:
    """Return controller-defined artifact paths for a milestone."""
    return [spec["path"] for spec in autonomous_controller.milestone_artifact_specs(milestone_id)]


def recent_history_evidence(root: Path, milestone_id: str) -> dict[str, Any]:
    """Return the latest verification/review/QA history entries for a milestone."""
    run_history = autonomous_controller.load_run_history(root)
    return {
        "verify": autonomous_controller.latest_history_entry(run_history, action="verify", milestone_id=milestone_id),
        "review": autonomous_controller.latest_history_entry(run_history, action="review", milestone_id=milestone_id),
        "qa": autonomous_controller.latest_history_entry(run_history, action="qa", milestone_id=milestone_id),
    }


def autonomy_state(root: Path, milestone_id: str) -> dict[str, Any]:
    """Return controller-side routing state for one milestone."""
    decision = autonomous_controller.determine_next_action(root, milestone_id)
    return {
        "recommended_next_action": decision["action"],
        "reason": decision["reason"],
        "retry_count": decision["retry_count"],
        "max_retries": decision["max_retries"],
        "failure_kind": decision["failure_kind"],
    }


def create_role_packet(
    *,
    root: Path,
    prompt_path: Path,
    milestone_id: str,
    changed_files: list[str],
    artifact_paths: list[str],
    cli_command: str | None = None,
) -> dict[str, Any]:
    """Build one structured role packet."""
    project_state = autonomous_controller.load_project_state(root)
    _, milestones = autonomous_controller.load_milestone_registry(root)
    milestone = autonomous_controller.get_milestone_by_id(milestones, milestone_id)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    implementation_plan_text = (root / "docs" / "implementation_plan.md").read_text(encoding="utf-8")
    role = infer_role(prompt_path)
    effective_changed_files = changed_files or collect_changed_files(root)
    effective_artifact_paths = artifact_paths or default_artifact_paths(milestone_id)
    declared_tools = autonomous_controller.available_tools_for_role(root, milestone_id, role)
    cycle_id = current_cycle_id()
    delegation_contract = autonomous_controller.delegation_contract(
        project_state=project_state,
        milestone_id=milestone_id,
        role=role,
        available_tools=declared_tools,
        cycle_id=cycle_id,
    )

    artifact_checks = [{"path": path, "exists": (root / path).exists()} for path in effective_artifact_paths]

    packet = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "producer_role": role,
        "phase": role,
        "prompt_path": str(prompt_path),
        "milestone": {
            "id": milestone["id"],
            "title": milestone["title"],
            "status": milestone["status"],
            "dependencies": milestone["dependencies"],
            "verify": milestone["verify"],
            "section_text": extract_milestone_section_text(implementation_plan_text, milestone_id),
        },
        "current_focus": project_state.get("current_focus"),
        "context_files": extract_prompt_reads(prompt_text),
        "changed_files": effective_changed_files,
        "artifact_checks": artifact_checks,
        "available_tools": declared_tools,
        "delegation_contract": delegation_contract,
        "history_evidence": recent_history_evidence(root, milestone_id),
        "autonomy_state": autonomy_state(root, milestone_id),
        "checklist": build_role_checklist(role, milestone, declared_tools),
        "runner_mode": "repo_native_local_packet",
        "notes": "This runner generates structured local packets and can optionally invoke a local AI CLI.",
        "cycle_id": cycle_id,
    }
    configured_cli = str(project_state.get("agent_runner", {}).get("cli_command") or "").strip()
    env_cli = str(os.environ.get("AUTONOMOUS_AGENT_CLI", "")).strip()
    effective_cli = (cli_command or "").strip() or env_cli or configured_cli
    packet.update(backend_metadata(effective_cli))
    if effective_cli:
        packet["runner_mode"] = "external_local_ai_cli"
        packet["result"] = run_local_ai_cli(cli_command=effective_cli, packet=packet, root=root)
        packet["cli_command"] = effective_cli
    else:
        packet["result"] = build_fallback_result(role, milestone)
    return packet


def append_history_entry(root: Path, packet: dict[str, Any], output_path: Path) -> None:
    """Append one structured run-history entry for the generated role packet."""
    entry = autonomous_controller.build_history_entry(
        action="agent_output",
        milestone=packet["milestone"]["id"],
        command=f"local_agent_runner {packet['role']}",
        exit_code=0,
        success=True,
        note=f"generated {packet['role']} packet",
    )
    entry["role"] = packet["role"]
    entry["output_path"] = str(output_path)
    entry["changed_files"] = packet["changed_files"]
    entry["artifact_checks"] = packet["artifact_checks"]
    entry["runner_mode"] = packet["runner_mode"]
    entry["result_status"] = packet.get("result", {}).get("status")
    entry["producer_role"] = packet["producer_role"]
    entry["phase"] = packet["phase"]
    entry["backend"] = packet["backend"]
    entry["model"] = packet["model"]
    entry["cycle_id"] = packet["cycle_id"]
    entry["task_id"] = packet.get("delegation_contract", {}).get("task_id")
    entry["execution_mode"] = packet.get("delegation_contract", {}).get("execution_mode")
    entry["read_only"] = packet.get("delegation_contract", {}).get("read_only")
    entry["write_scope"] = packet.get("delegation_contract", {}).get("write_scope", [])
    autonomous_controller.append_run_history(entry, root)


def main(argv: list[str] | None = None) -> int:
    """Run the local agent runner CLI."""
    args = build_parser().parse_args(argv)
    root = PROJECT_ROOT
    prompt_path = (root / args.prompt_path).resolve()

    if not prompt_path.exists():
        print(f"Error: prompt file was not found at {prompt_path}")
        return 1

    packet = create_role_packet(
        root=root,
        prompt_path=prompt_path,
        milestone_id=args.milestone_id,
        changed_files=args.changed_file,
        artifact_paths=args.artifact,
        cli_command=args.cli_command,
    )
    output_path = Path(args.output).resolve() if args.output else default_output_path(
        root,
        packet["role"],
        args.milestone_id,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    append_history_entry(root, packet, output_path)

    print(f"Generated {packet['role']} packet for {args.milestone_id}: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
