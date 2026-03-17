"""Local milestone state, verification, and run-history controller."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_STATE_PATH = PROJECT_ROOT / "project_state.json"
MILESTONE_REGISTRY_PATH = PROJECT_ROOT / "milestone_registry.json"
RUN_HISTORY_PATH = PROJECT_ROOT / "runs" / "run_history.json"
VERIFY_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_project.sh"


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Manage local milestone state and verification for autonomous development.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show current focus, milestone summary, and latest run.")
    subparsers.add_parser("next", help="Show the next unfinished milestone.")
    subparsers.add_parser("verify", help="Run scripts/verify_project.sh and record the result.")

    complete_parser = subparsers.add_parser("complete", help="Mark a milestone complete.")
    complete_parser.add_argument("milestone_id")

    fail_parser = subparsers.add_parser("fail", help="Mark a milestone blocked with a note.")
    fail_parser.add_argument("milestone_id")
    fail_parser.add_argument("--note", required=True)

    review_parser = subparsers.add_parser("review", help="Record reviewer outcome for a milestone.")
    review_parser.add_argument("milestone_id")
    review_parser.add_argument("--status", choices=("pass", "fail"), required=True)
    review_parser.add_argument("--note", required=True)

    qa_parser = subparsers.add_parser("qa", help="Record QA outcome for a milestone.")
    qa_parser.add_argument("milestone_id")
    qa_parser.add_argument("--status", choices=("pass", "fail"), required=True)
    qa_parser.add_argument("--note", required=True)
    qa_parser.add_argument(
        "--manual-checks-complete",
        action="store_true",
        help="Mark any manual verification checks for the milestone as complete.",
    )
    qa_parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Optional artifact path to validate and record during QA.",
    )

    subparsers.add_parser("run-cycle", help="Show the next milestone and prompt sequence.")
    return parser


def load_required_json(path: Path, label: str) -> Any:
    """Load a required JSON file or fail clearly."""
    if not path.exists():
        raise RuntimeError(f"Required {label} was not found at {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Required {label} at {path} is malformed JSON: {error}") from error


def load_project_state(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Load project_state.json."""
    payload = load_required_json(root / "project_state.json", "project state")
    if not isinstance(payload, dict):
        raise RuntimeError(f"Required project state at {root / 'project_state.json'} must be a JSON object")
    return payload


def load_milestone_registry(root: Path = PROJECT_ROOT) -> tuple[Any, list[dict[str, Any]]]:
    """Load and normalize milestone_registry.json."""
    path = root / "milestone_registry.json"
    payload = load_required_json(path, "milestone registry")
    milestones = normalize_milestones(payload, path)
    return payload, milestones


def get_milestone_by_id(milestones: list[dict[str, Any]], milestone_id: str) -> dict[str, Any]:
    """Return one milestone or fail clearly."""
    for milestone in milestones:
        if milestone["id"] == milestone_id:
            return milestone
    raise RuntimeError(f"Milestone {milestone_id} was not found in milestone_registry.json")


def normalize_milestones(payload: Any, path: Path) -> list[dict[str, Any]]:
    """Normalize common milestone registry shapes into a list of milestone dicts."""
    raw_items: list[Any]
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("milestones"), list):
        raw_items = payload["milestones"]
    elif isinstance(payload, dict):
        raw_items = []
        for milestone_id, value in payload.items():
            if not isinstance(value, dict):
                raise RuntimeError(f"Milestone entry {milestone_id} in {path} must be a JSON object")
            raw_item = dict(value)
            raw_item.setdefault("id", milestone_id)
            raw_items.append(raw_item)
    else:
        raise RuntimeError(f"Milestone registry at {path} must be a JSON object or list")

    normalized: list[dict[str, Any]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise RuntimeError(f"Milestone registry at {path} contains a non-object milestone entry")
        milestone_id = str(raw_item.get("id") or raw_item.get("milestone_id") or "").strip()
        title = str(raw_item.get("title") or "").strip()
        status = str(raw_item.get("status") or "").strip()
        if not milestone_id or not title or not status:
            raise RuntimeError(f"Milestone registry at {path} has an entry missing id, title, or status")

        dependencies = _coerce_string_list(raw_item.get("dependencies"))
        verify = _coerce_string_list(raw_item.get("verify"))
        normalized.append(
            {
                "id": milestone_id,
                "title": title,
                "status": status,
                "dependencies": dependencies,
                "verify": verify,
            }
        )

    normalized.sort(key=lambda item: milestone_sort_key(item["id"]))
    return normalized


def _coerce_string_list(value: Any) -> list[str]:
    """Normalize a possibly missing or scalar string-list field."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def milestone_sort_key(milestone_id: str) -> tuple[int, str]:
    """Sort milestone ids like M01, M2, M10 predictably."""
    digits = "".join(character for character in milestone_id if character.isdigit())
    return (int(digits) if digits else 999999, milestone_id)


def load_run_history(root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    """Load run history if it exists, otherwise return an empty list."""
    path = root / "runs" / "run_history.json"
    if not path.exists():
        return []

    payload = load_required_json(path, "run history")
    if not isinstance(payload, list):
        raise RuntimeError(f"Required run history at {path} must be a JSON list")
    return payload


def ensure_run_history(root: Path = PROJECT_ROOT) -> Path:
    """Create an empty run history file only when needed."""
    path = root / "runs" / "run_history.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]\n", encoding="utf-8")
    return path


def append_run_history(entry: dict[str, Any], root: Path = PROJECT_ROOT) -> None:
    """Append one entry to run_history.json."""
    path = ensure_run_history(root)
    payload = load_required_json(path, "run history")
    if not isinstance(payload, list):
        raise RuntimeError(f"Required run history at {path} must be a JSON list")
    payload.append(entry)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def determine_next_milestone(milestones: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    """Choose the next unfinished milestone or report blocking dependencies."""
    milestone_map = {milestone["id"]: milestone for milestone in milestones}

    for desired_status in ("in_progress", "not_started"):
        for milestone in milestones:
            if milestone["status"] != desired_status:
                continue
            incomplete_dependencies = [
                dependency
                for dependency in milestone["dependencies"]
                if milestone_map.get(dependency, {}).get("status") != "complete"
            ]
            return milestone, incomplete_dependencies

    return None, []


def update_milestone_status(payload: Any, milestone_id: str, new_status: str) -> None:
    """Update the milestone status while preserving the existing payload shape."""
    if isinstance(payload, list):
        for milestone in payload:
            if isinstance(milestone, dict) and (
                milestone.get("id") == milestone_id or milestone.get("milestone_id") == milestone_id
            ):
                milestone["status"] = new_status
                return
    elif isinstance(payload, dict) and isinstance(payload.get("milestones"), list):
        update_milestone_status(payload["milestones"], milestone_id, new_status)
        return
    elif isinstance(payload, dict):
        for key, milestone in payload.items():
            if not isinstance(milestone, dict):
                continue
            candidate_id = milestone.get("id") or milestone.get("milestone_id") or key
            if candidate_id == milestone_id:
                milestone["status"] = new_status
                return

    raise RuntimeError(f"Milestone {milestone_id} was not found in milestone_registry.json")


def save_json(path: Path, payload: Any) -> None:
    """Write deterministic JSON output."""
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_history_entry(
    *,
    action: str,
    milestone: str | None,
    command: str,
    exit_code: int,
    success: bool,
    note: str,
) -> dict[str, Any]:
    """Build one structured run history entry."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "milestone": milestone,
        "command": command,
        "exit_code": exit_code,
        "success": success,
        "note": note,
    }


def latest_history_entry(
    run_history: list[dict[str, Any]],
    *,
    action: str,
    milestone_id: str,
) -> dict[str, Any] | None:
    """Return the newest history entry for one action and milestone."""
    for entry in reversed(run_history):
        if entry.get("action") == action and entry.get("milestone") == milestone_id:
            return entry
    return None


def is_executable_verify_command(command: str) -> bool:
    """Return True when the verify command looks shell-executable."""
    stripped = command.strip()
    executable_prefixes = (
        ".venv/bin/python ",
        "python ",
        "python3 ",
        "bash ",
        "sh ",
        "pytest ",
        "docker ",
        "curl ",
    )
    return stripped.startswith(executable_prefixes)


def run_shell_command(command: str, root: Path) -> subprocess.CompletedProcess[str]:
    """Run one shell command and capture output."""
    return subprocess.run(
        command,
        cwd=root,
        shell=True,
        executable="/bin/bash",
        capture_output=True,
        text=True,
        check=False,
    )


def command_status(root: Path = PROJECT_ROOT) -> int:
    """Print current focus, milestone summary, and latest run entry."""
    project_state = load_project_state(root)
    _, milestones = load_milestone_registry(root)
    run_history = load_run_history(root)

    print(f"Current focus: {project_state.get('current_focus', 'unknown')}")
    print("Milestones:")
    for milestone in milestones:
        print(f"- {milestone['id']}: {milestone['title']} [{milestone['status']}]")

    if run_history:
        latest = run_history[-1]
        print("Latest run:")
        print(
            f"- {latest.get('timestamp')} | {latest.get('action')} | "
            f"exit={latest.get('exit_code')} | success={latest.get('success')}"
        )
    else:
        print("Latest run: none")

    return 0


def command_next(root: Path = PROJECT_ROOT) -> int:
    """Print the next unfinished milestone."""
    _, milestones = load_milestone_registry(root)
    milestone, incomplete_dependencies = determine_next_milestone(milestones)
    if milestone is None:
        print("No unfinished milestones found.")
        return 0

    print(f"Next milestone: {milestone['id']} - {milestone['title']}")
    print(f"Status: {milestone['status']}")
    print(f"Dependencies: {', '.join(milestone['dependencies']) or 'none'}")
    print("Verify:")
    for command in milestone["verify"]:
        print(f"- {command}")

    if incomplete_dependencies:
        print(f"Blocked by incomplete dependencies: {', '.join(incomplete_dependencies)}")
        return 1
    return 0


def command_verify(root: Path = PROJECT_ROOT) -> int:
    """Run the verification script and append a structured history entry."""
    project_state = load_project_state(root)
    milestone = project_state.get("current_focus")
    if not isinstance(milestone, str) or not milestone.strip():
        raise RuntimeError("project_state.json must define current_focus before verification can run")

    _, milestones = load_milestone_registry(root)
    milestone_record = get_milestone_by_id(milestones, milestone)

    all_commands: list[str] = []
    verification_script = str(project_state.get("verification_script") or "").strip()
    if verification_script:
        all_commands.append(f"bash {shlex.quote(verification_script)}")
    for command in milestone_record["verify"]:
        if command not in all_commands:
            all_commands.append(command)

    executed_results: list[dict[str, Any]] = []
    manual_checks_pending: list[str] = []
    overall_exit_code = 0

    for command in all_commands:
        if not is_executable_verify_command(command):
            manual_checks_pending.append(command)
            continue

        completed = run_shell_command(command, root)
        executed_results.append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "success": completed.returncode == 0,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        if completed.returncode != 0 and overall_exit_code == 0:
            overall_exit_code = completed.returncode

    note_parts: list[str] = []
    if overall_exit_code == 0:
        note_parts.append("verification commands passed")
    else:
        note_parts.append("verification commands failed")
    if manual_checks_pending:
        note_parts.append("manual verification still required")

    entry = build_history_entry(
        action="verify",
        milestone=milestone,
        command="; ".join(all_commands),
        exit_code=overall_exit_code,
        success=overall_exit_code == 0,
        note=", ".join(note_parts),
    )
    entry["commands"] = executed_results
    entry["manual_checks_pending"] = manual_checks_pending
    append_run_history(entry, root)

    print(
        f"Verification {'passed' if overall_exit_code == 0 else 'failed'} "
        f"for {milestone} (exit {overall_exit_code})"
    )
    for result in executed_results:
        print(f"- {result['command']} -> exit {result['exit_code']}")
    if manual_checks_pending:
        print("Manual checks pending:")
        for command in manual_checks_pending:
            print(f"- {command}")

    return overall_exit_code


def command_review(milestone_id: str, status: str, note: str, root: Path = PROJECT_ROOT) -> int:
    """Record a reviewer outcome for one milestone."""
    _, milestones = load_milestone_registry(root)
    get_milestone_by_id(milestones, milestone_id)

    append_run_history(
        {
            **build_history_entry(
                action="review",
                milestone=milestone_id,
                command=f"review {milestone_id}",
                exit_code=0 if status == "pass" else 1,
                success=status == "pass",
                note=note,
            ),
            "review_status": status,
        },
        root,
    )

    print(f"Recorded review {status} for {milestone_id}.")
    return 0


def command_qa(
    milestone_id: str,
    status: str,
    note: str,
    manual_checks_complete: bool,
    artifact_paths: list[str],
    root: Path = PROJECT_ROOT,
) -> int:
    """Record a QA outcome for one milestone."""
    _, milestones = load_milestone_registry(root)
    get_milestone_by_id(milestones, milestone_id)
    artifact_checks = [{"path": path, "exists": (root / path).exists()} for path in artifact_paths]

    if status == "pass" and any(not item["exists"] for item in artifact_checks):
        missing = [item["path"] for item in artifact_checks if not item["exists"]]
        raise RuntimeError(f"QA cannot pass while required artifacts are missing: {', '.join(missing)}")

    append_run_history(
        {
            **build_history_entry(
                action="qa",
                milestone=milestone_id,
                command=f"qa {milestone_id}",
                exit_code=0 if status == "pass" else 1,
                success=status == "pass",
                note=note,
            ),
            "qa_status": status,
            "manual_checks_complete": manual_checks_complete,
            "artifact_checks": artifact_checks,
        },
        root,
    )

    print(f"Recorded QA {status} for {milestone_id}.")
    return 0


def command_complete(milestone_id: str, root: Path = PROJECT_ROOT) -> int:
    """Mark one milestone complete and advance current_focus if possible."""
    project_state = load_project_state(root)
    registry_payload, milestones = load_milestone_registry(root)
    get_milestone_by_id(milestones, milestone_id)
    run_history = load_run_history(root)

    latest_verify = latest_history_entry(run_history, action="verify", milestone_id=milestone_id)
    latest_review = latest_history_entry(run_history, action="review", milestone_id=milestone_id)
    latest_qa = latest_history_entry(run_history, action="qa", milestone_id=milestone_id)

    if latest_verify is None or not latest_verify.get("success"):
        raise RuntimeError(f"Milestone {milestone_id} cannot be completed before successful verification")
    if latest_review is None or not latest_review.get("success"):
        raise RuntimeError(f"Milestone {milestone_id} cannot be completed before a passing review result")
    if latest_qa is None or not latest_qa.get("success"):
        raise RuntimeError(f"Milestone {milestone_id} cannot be completed before a passing QA result")

    manual_checks_pending = latest_verify.get("manual_checks_pending") or []
    if manual_checks_pending and not latest_qa.get("manual_checks_complete"):
        raise RuntimeError(
            f"Milestone {milestone_id} still has manual checks pending and QA has not marked them complete"
        )

    update_milestone_status(registry_payload, milestone_id, "complete")
    save_json(root / "milestone_registry.json", registry_payload)

    _, updated_milestones = load_milestone_registry(root)
    next_milestone, _ = determine_next_milestone(updated_milestones)
    project_state["current_focus"] = next_milestone["id"] if next_milestone is not None else None
    save_json(root / "project_state.json", project_state)

    append_run_history(
        build_history_entry(
            action="complete",
            milestone=milestone_id,
            command=f"complete {milestone_id}",
            exit_code=0,
            success=True,
            note="milestone marked complete",
        ),
        root,
    )

    print(f"Marked {milestone_id} complete.")
    if next_milestone is not None:
        print(f"Current focus updated to {next_milestone['id']}.")
    else:
        print("No unfinished milestone remains.")
    return 0


def command_fail(milestone_id: str, note: str, root: Path = PROJECT_ROOT) -> int:
    """Mark one milestone blocked and append a failure note."""
    registry_payload, _ = load_milestone_registry(root)
    update_milestone_status(registry_payload, milestone_id, "blocked")
    save_json(root / "milestone_registry.json", registry_payload)

    append_run_history(
        build_history_entry(
            action="fail",
            milestone=milestone_id,
            command=f"fail {milestone_id}",
            exit_code=1,
            success=False,
            note=note,
        ),
        root,
    )

    print(f"Marked {milestone_id} blocked.")
    print(f"Note: {note}")
    return 0


def command_run_cycle(root: Path = PROJECT_ROOT) -> int:
    """Print the next milestone and the planner/builder/reviewer/QA prompt sequence."""
    _, milestones = load_milestone_registry(root)
    milestone, incomplete_dependencies = determine_next_milestone(milestones)
    if milestone is None:
        print("No unfinished milestones found.")
        return 0

    print(f"Next milestone: {milestone['id']} - {milestone['title']}")
    if incomplete_dependencies:
        print(f"Blocked by incomplete dependencies: {', '.join(incomplete_dependencies)}")
        return 1

    controller_prompt = root / "docs" / "agents" / "controller_agent.md"
    controller_state = "present" if controller_prompt.exists() else "missing"
    print("Controller:")
    print(f"- {controller_prompt} [{controller_state}]")

    prompt_paths = [
        root / "docs" / "agents" / "planner_agent.md",
        root / "docs" / "agents" / "builder_agent.md",
        root / "docs" / "agents" / "reviewer_agent.md",
        root / "docs" / "agents" / "qa_agent.md",
    ]
    print("Prompt sequence:")
    for label, path in zip(("Planner", "Builder", "Reviewer", "QA"), prompt_paths):
        state = "present" if path.exists() else "missing"
        print(f"- {label}: {path} [{state}]")

    print("Verification reminder:")
    for command in milestone["verify"]:
        print(f"- {command}")

    print("Status transition reminder:")
    print(f"- record review: python scripts/autonomous_controller.py review {milestone['id']} --status pass|fail --note ...")
    print(
        f"- record qa: python scripts/autonomous_controller.py qa {milestone['id']} "
        "--status pass|fail --note ... [--manual-checks-complete] [--artifact path]"
    )
    print(f"- complete only after verify + review + qa: python scripts/autonomous_controller.py complete {milestone['id']}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the controller CLI."""
    args = build_parser().parse_args(argv)
    root = PROJECT_ROOT

    try:
        if args.command == "status":
            return command_status(root)
        if args.command == "next":
            return command_next(root)
        if args.command == "verify":
            return command_verify(root)
        if args.command == "complete":
            return command_complete(args.milestone_id, root)
        if args.command == "fail":
            return command_fail(args.milestone_id, args.note, root)
        if args.command == "review":
            return command_review(args.milestone_id, args.status, args.note, root)
        if args.command == "qa":
            return command_qa(
                args.milestone_id,
                args.status,
                args.note,
                args.manual_checks_complete,
                args.artifact,
                root,
            )
        if args.command == "run-cycle":
            return command_run_cycle(root)
    except RuntimeError as error:
        print(f"Error: {error}")
        return 1

    print(f"Error: unsupported command {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
