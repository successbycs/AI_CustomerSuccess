"""Local milestone state, verification, and run-history controller."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import milestone_auditor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_STATE_PATH = PROJECT_ROOT / "project_state.json"
MILESTONE_REGISTRY_PATH = PROJECT_ROOT / "milestone_registry.json"
RUN_HISTORY_PATH = PROJECT_ROOT / "runs" / "run_history.json"
VERIFY_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_project.sh"
TOOL_REGISTRY_PATH = PROJECT_ROOT / "tools" / "tool_registry.json"
SCHEMA_ADMIN_MILESTONES = {"M15"}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Manage local milestone state and verification for autonomous development.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show current focus, milestone summary, and latest run.")
    subparsers.add_parser("next", help="Show the next unfinished milestone.")
    subparsers.add_parser("verify", help="Run scripts/verify_project.sh and record the result.")
    next_action_parser = subparsers.add_parser(
        "next-action",
        help="Decide the next controller action for the current or selected milestone.",
    )
    next_action_parser.add_argument("milestone_id", nargs="?")
    next_action_parser.add_argument("--json", action="store_true", dest="json_output")
    artifacts_parser = subparsers.add_parser(
        "assert-artifacts",
        help="Check milestone-aware artifact assertions for the current or selected milestone.",
    )
    artifacts_parser.add_argument("milestone_id", nargs="?")

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

    closeout_audit_parser = subparsers.add_parser(
        "audit-closeout",
        help="Run the closeout auditor for a completed milestone and append the audit entry.",
    )
    closeout_audit_parser.add_argument("milestone_id")

    backfill_audit_parser = subparsers.add_parser(
        "audit-backfill",
        help="Run the backfill auditor for one or more completed milestones.",
    )
    backfill_audit_parser.add_argument("milestone_ids", nargs="*")
    backfill_audit_parser.add_argument("--all-unaudited", action="store_true")

    subparsers.add_parser("run-cycle", help="Show the next milestone and prompt sequence.")
    auto_iterate_parser = subparsers.add_parser(
        "auto-iterate",
        help="Run a bounded controller-owned milestone loop for the current or selected milestone.",
    )
    auto_iterate_parser.add_argument("milestone_id", nargs="?")
    auto_iterate_parser.add_argument("--max-iterations", type=int)
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


def load_tool_registry(root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    """Load and resolve the repo tool registry when present."""
    path = root / "tools" / "tool_registry.json"
    if not path.exists():
        return []

    payload = load_required_json(path, "tool registry")
    if not isinstance(payload, dict) or not isinstance(payload.get("tools"), list):
        raise RuntimeError(f"Required tool registry at {path} must be an object with a tools list")

    tools: list[dict[str, Any]] = []
    for raw_item in payload["tools"]:
        if not isinstance(raw_item, dict):
            raise RuntimeError(f"Tool registry at {path} contains a non-object tool entry")
        tool_id = str(raw_item.get("id") or "").strip()
        name = str(raw_item.get("name") or tool_id).strip()
        spec_path_text = str(raw_item.get("spec_path") or "").strip()
        if not tool_id or not spec_path_text:
            raise RuntimeError(f"Tool registry at {path} has an entry missing id or spec_path")

        spec_path = root / spec_path_text
        spec_payload: dict[str, Any] = {}
        if spec_path.exists():
            spec_value = load_required_json(spec_path, f"tool spec for {tool_id}")
            if not isinstance(spec_value, dict):
                raise RuntimeError(f"Tool spec at {spec_path} must be a JSON object")
            spec_payload = spec_value

        tools.append(
            {
                "id": tool_id,
                "name": name,
                "enabled": bool(raw_item.get("enabled", True)),
                "spec_path": spec_path_text,
                "description": str(spec_payload.get("description") or raw_item.get("description") or "").strip(),
                "development_only": bool(spec_payload.get("development_only", False)),
                "entrypoint": str(spec_payload.get("entrypoint") or "").strip(),
                "applicable_milestones": _coerce_string_list(spec_payload.get("applicable_milestones")),
                "source_of_truth": _coerce_string_list(spec_payload.get("source_of_truth")),
                "required_backends": _coerce_string_list(spec_payload.get("required_backends")),
                "backends": spec_payload.get("backends") if isinstance(spec_payload.get("backends"), list) else [],
                "role_access": spec_payload.get("role_access") if isinstance(spec_payload.get("role_access"), dict) else {},
            }
        )
    return tools


def available_tools_for_role(
    root: Path,
    milestone_id: str,
    role: str,
) -> list[dict[str, Any]]:
    """Return the declared tools available to one role for one milestone."""
    tools = load_tool_registry(root)
    available: list[dict[str, Any]] = []
    for tool in tools:
        if not tool.get("enabled", True):
            continue
        applicable = tool.get("applicable_milestones") or []
        if applicable and milestone_id not in applicable:
            continue
        role_access = tool.get("role_access", {}).get(role)
        if not isinstance(role_access, dict):
            continue
        available.append(
            {
                "id": tool["id"],
                "name": tool["name"],
                "description": tool.get("description", ""),
                "spec_path": tool["spec_path"],
                "entrypoint": str(tool.get("entrypoint") or ""),
                "development_only": bool(tool.get("development_only", False)),
                "source_of_truth": list(tool.get("source_of_truth") or []),
                "required_backends": list(tool.get("required_backends") or []),
                "backends": list(tool.get("backends") or []),
                "allowed_operations": _coerce_string_list(role_access.get("operations")),
                "write_allowed": bool(role_access.get("write_allowed", False)),
                "approval_required": bool(role_access.get("approval_required", False)),
            }
        )
    return available


def load_local_env(root: Path = PROJECT_ROOT) -> dict[str, str]:
    """Load simple key=value pairs from .env without exporting them."""
    values: dict[str, str] = {}
    env_path = root / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cleaned = value.strip().strip('"').strip("'")
            if cleaned:
                values[key.strip()] = cleaned
    for key, value in os.environ.items():
        if value:
            values[key] = value
    return values


def datastore_capabilities(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Return the currently available datastore runtime/admin capabilities."""
    env_values = load_local_env(root)
    runtime_data_access = bool(env_values.get("SUPABASE_URL") and env_values.get("SUPABASE_KEY"))
    schema_admin_direct = has_direct_schema_admin_access(env_values)
    schema_admin_access = schema_admin_direct
    reasons: list[str] = []
    if not runtime_data_access:
        reasons.append("SUPABASE_URL and SUPABASE_KEY are required for runtime datastore access")
    if not schema_admin_access:
        reasons.append("schema-admin access requires DATABASE_URL/SUPABASE_DB_URL with psql or psycopg")
    return {
        "runtime_data_access": runtime_data_access,
        "schema_admin_access": schema_admin_access,
        "schema_admin_direct": schema_admin_direct,
        "reasons": reasons,
    }


def has_direct_schema_admin_access(env_values: dict[str, str]) -> bool:
    """Return True when a direct schema-admin client is available."""
    if not (env_values.get("DATABASE_URL") or env_values.get("SUPABASE_DB_URL")):
        return False
    if shutil.which("psql"):
        return True
    try:
        import psycopg  # noqa: F401
    except Exception:
        return False
    return True


def milestone_requires_schema_admin(milestone_id: str) -> bool:
    """Return True when a milestone depends on live datastore schema-admin access."""
    return milestone_id in SCHEMA_ADMIN_MILESTONES


def datastore_preflight_failure(milestone_id: str, root: Path = PROJECT_ROOT) -> str | None:
    """Return a blocking datastore-capability failure for a milestone, if any."""
    capabilities = datastore_capabilities(root)
    if milestone_requires_schema_admin(milestone_id) and not capabilities["schema_admin_access"]:
        return (
            f"{milestone_id} requires datastore schema-admin access, but it is unavailable: "
            + "; ".join(capabilities["reasons"])
        )
    return None


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


def load_controller_policy(project_state: dict[str, Any]) -> dict[str, Any]:
    """Return controller retry and blocker policy with safe defaults."""
    raw_policy = project_state.get("controller_policy")
    policy = raw_policy if isinstance(raw_policy, dict) else {}

    retry_limit = policy.get("max_same_milestone_retries", 2)
    if not isinstance(retry_limit, int) or retry_limit < 0:
        retry_limit = 2

    return {
        "max_same_milestone_retries": retry_limit,
        "retry_on_actionable_failures": bool(policy.get("retry_on_actionable_failures", True)),
        "stop_on_external_blockers": bool(policy.get("stop_on_external_blockers", True)),
        "max_controller_iterations_per_cycle": (
            policy.get("max_controller_iterations_per_cycle")
            if isinstance(policy.get("max_controller_iterations_per_cycle"), int)
            and int(policy.get("max_controller_iterations_per_cycle")) > 0
            else 4
        ),
        "auto_mark_blocked_on_external_failure": bool(policy.get("auto_mark_blocked_on_external_failure", True)),
    }


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


def sync_implementation_plan_statuses(root: Path, milestones: list[dict[str, Any]]) -> None:
    """Keep docs/implementation_plan.md aligned with milestone_registry.json statuses."""
    path = root / "docs" / "implementation_plan.md"
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    for milestone in milestones:
        pattern = re.compile(
            rf"(^## {re.escape(milestone['id'])}\b[^\n]*\nStatus:\s*`)([^`]+)(`)",
            re.MULTILINE,
        )
        text = pattern.sub(rf"\g<1>{milestone['status']}\3", text, count=1)
    path.write_text(text, encoding="utf-8")


def sync_project_brain_focus(root: Path, current_focus: str | None) -> None:
    """Keep docs/project_brain.md active-focus memory aligned with project_state.json."""
    path = root / "docs" / "project_brain.md"
    if not path.exists():
        return

    target_line = (
        f"- current active milestone is `{current_focus}`"
        if current_focus
        else "- there is no active milestone; all milestones are complete"
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    replaced = False
    inserted = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- current active milestone is `") or stripped == "- there is no active milestone; all milestones are complete":
            if not replaced:
                updated_lines.append(target_line)
                replaced = True
            continue
        updated_lines.append(line)
        if not inserted and line.strip() == "## Current Operating Assumptions" and not replaced:
            updated_lines.append("")
            updated_lines.append(target_line)
            inserted = True
            replaced = True

    if not replaced:
        if updated_lines and updated_lines[-1] != "":
            updated_lines.append("")
        updated_lines.append("## Current Operating Assumptions")
        updated_lines.append("")
        updated_lines.append(target_line)

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def sync_repo_state_docs(root: Path, project_state: dict[str, Any], milestones: list[dict[str, Any]]) -> None:
    """Synchronize derived docs immediately after controller-owned state transitions."""
    sync_implementation_plan_statuses(root, milestones)
    current_focus = str(project_state.get("current_focus") or "").strip() or None
    sync_project_brain_focus(root, current_focus)


def current_cycle_id() -> str | None:
    """Return the current cycle id when one is set."""
    value = str(os.environ.get("AUTONOMOUS_CYCLE_ID", "")).strip()
    return value or None


def load_delegation_policy(project_state: dict[str, Any]) -> dict[str, Any]:
    """Return normalized delegation-policy settings for role packet execution."""
    defaults = {
        "enabled": True,
        "record_task_contracts": True,
        "max_parallel_tasks": 1,
        "require_declared_write_scope": True,
        "stop_on_scope_violation": True,
        "mutating_roles": ["controller", "builder", "closeout_auditor", "backfill_auditor"],
    }
    raw_policy = project_state.get("delegation_policy")
    if not isinstance(raw_policy, dict):
        return defaults

    policy = dict(defaults)
    policy["enabled"] = bool(raw_policy.get("enabled", defaults["enabled"]))
    policy["record_task_contracts"] = bool(
        raw_policy.get("record_task_contracts", defaults["record_task_contracts"])
    )
    policy["require_declared_write_scope"] = bool(
        raw_policy.get("require_declared_write_scope", defaults["require_declared_write_scope"])
    )
    policy["stop_on_scope_violation"] = bool(
        raw_policy.get("stop_on_scope_violation", defaults["stop_on_scope_violation"])
    )
    max_parallel = raw_policy.get("max_parallel_tasks", defaults["max_parallel_tasks"])
    try:
        policy["max_parallel_tasks"] = max(1, int(max_parallel))
    except (TypeError, ValueError):
        policy["max_parallel_tasks"] = defaults["max_parallel_tasks"]
    policy["mutating_roles"] = _coerce_string_list(raw_policy.get("mutating_roles")) or defaults["mutating_roles"]
    return policy


def role_write_scope(role: str) -> list[str]:
    """Return the bounded write scope for one role."""
    scopes = {
        "controller": [
            "project_state.json",
            "milestone_registry.json",
            "runs/run_history.json",
            "docs/implementation_plan.md",
            "docs/project_brain.md",
            "docs/audit/audit.md",
        ],
        "builder": [
            "services/",
            "scripts/",
            "tests/",
            "docs/",
            "config/",
            "tools/",
            "supabase/",
            "README.md",
            "project_state.json",
            "milestone_registry.json",
        ],
        "closeout_auditor": [
            "docs/audit/audit.md",
        ],
        "backfill_auditor": [
            "docs/audit/audit.md",
        ],
    }
    return list(scopes.get(role, []))


def delegation_contract(
    *,
    project_state: dict[str, Any],
    milestone_id: str,
    role: str,
    available_tools: list[dict[str, Any]],
    cycle_id: str | None,
) -> dict[str, Any]:
    """Return the execution contract for one delegated role packet."""
    policy = load_delegation_policy(project_state)
    write_scope = role_write_scope(role)
    mutating_role = role in set(policy["mutating_roles"])
    read_only = not mutating_role
    parallel_allowed = policy["max_parallel_tasks"] > 1 and read_only
    allowed_tool_ids = [str(tool.get("id") or "").strip() for tool in available_tools if str(tool.get("id") or "").strip()]
    task_prefix = cycle_id or "adhoc"
    task_id = f"{task_prefix}:{milestone_id}:{role}"
    execution_mode = "read_only" if read_only else "bounded_write"
    rules = [
        "Use only the declared role packet, repo state, and allowed tools for this task.",
        "Do not touch files outside the declared write scope.",
        "Do not duplicate work owned by another role in the same cycle.",
        "Stop and surface a blocker when the task requires out-of-scope writes or undeclared tool access.",
    ]
    if read_only:
        rules.append("This role is read-only and must not change repo files or remote state.")
    else:
        rules.append("This role may mutate only the declared write scope and must report changed files explicitly.")

    return {
        "task_id": task_id,
        "role": role,
        "milestone": milestone_id,
        "execution_mode": execution_mode,
        "read_only": read_only,
        "parallel_allowed": parallel_allowed,
        "max_parallel_tasks": policy["max_parallel_tasks"],
        "require_declared_write_scope": bool(policy["require_declared_write_scope"]),
        "stop_on_scope_violation": bool(policy["stop_on_scope_violation"]),
        "write_scope": write_scope,
        "allowed_tool_ids": allowed_tool_ids,
        "ownership_note": f"{role} owns only this {execution_mode} task for {milestone_id}",
        "rules": rules,
    }


def history_actor_metadata(action: str) -> dict[str, Any]:
    """Return attribution metadata for one history action."""
    metadata_map = {
        "verify": {"producer_role": "controller", "phase": "controller", "backend": "local_controller", "model": None},
        "complete": {"producer_role": "controller", "phase": "controller", "backend": "local_controller", "model": None},
        "fail": {"producer_role": "controller", "phase": "controller", "backend": "local_controller", "model": None},
        "review": {"producer_role": "reviewer", "phase": "reviewer", "backend": "local_controller", "model": None},
        "qa": {"producer_role": "qa", "phase": "qa", "backend": "local_controller", "model": None},
        "closeout_audit": {
            "producer_role": "closeout_auditor",
            "phase": "closeout_auditor",
            "backend": "local_controller",
            "model": None,
        },
        "backfill_audit": {
            "producer_role": "backfill_auditor",
            "phase": "backfill_auditor",
            "backend": "local_controller",
            "model": None,
        },
        "agent_output": {"producer_role": "agent_runner", "phase": "agent_output", "backend": "repo_native_runner", "model": None},
        "iteration_step": {"producer_role": "controller", "phase": "controller", "backend": "local_controller", "model": None},
        "auto_iterate": {"producer_role": "controller", "phase": "controller", "backend": "local_controller", "model": None},
    }
    return dict(metadata_map.get(action, {"producer_role": "controller", "phase": "controller", "backend": "local_controller", "model": None}))


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
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "milestone": milestone,
        "command": command,
        "exit_code": exit_code,
        "success": success,
        "note": note,
    }
    entry.update(history_actor_metadata(action))
    cycle_id = current_cycle_id()
    if cycle_id:
        entry["cycle_id"] = cycle_id
    return entry


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


def role_output_status(output: dict[str, Any] | None) -> str:
    """Return the normalized status for a structured role output."""
    if output is None:
        return ""
    return str(output.get("result", {}).get("status") or "").strip().lower()


def role_output_dir(root: Path = PROJECT_ROOT) -> Path:
    """Return the directory used for structured role outputs."""
    return root / "runs" / "agent_outputs"


def load_role_outputs(root: Path, milestone_id: str, role: str | None = None) -> list[dict[str, Any]]:
    """Load structured role outputs for one milestone."""
    output_dir = role_output_dir(root)
    if not output_dir.exists():
        return []

    outputs: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("milestone", {}).get("id") != milestone_id:
            continue
        if role is not None and payload.get("role") != role:
            continue
        payload["_path"] = str(path)
        outputs.append(payload)

    outputs.sort(key=lambda item: str(item.get("timestamp", "")))
    return outputs


def latest_role_output(root: Path, milestone_id: str, role: str) -> dict[str, Any] | None:
    """Return the newest structured role output for one milestone and role."""
    outputs = load_role_outputs(root, milestone_id, role)
    return outputs[-1] if outputs else None


def role_output_passes(output: dict[str, Any] | None) -> bool:
    """Return True when a structured role output explicitly passes."""
    if output is None:
        return False
    status = role_output_status(output)
    return status in {"pass", "passed", "approve", "approved", "complete", "completed"}


def role_output_fails(output: dict[str, Any] | None) -> bool:
    """Return True when a structured role output explicitly fails or blocks."""
    status = role_output_status(output)
    return status in {"fail", "failed", "blocked"}


def role_output_manual_checks_complete(output: dict[str, Any] | None) -> bool:
    """Return True when a QA role output explicitly marks manual checks complete."""
    if output is None:
        return False
    result = output.get("result", {})
    if not isinstance(result, dict):
        return False
    return bool(result.get("manual_checks_complete", False))


def milestone_artifact_specs(milestone_id: str) -> list[dict[str, str]]:
    """Return milestone-aware artifact assertions."""
    specs: dict[str, list[dict[str, str]]] = {
        "M07": [
            {"path": "outputs/directory_dataset.json", "kind": "json_nonempty"},
            {"path": "outputs/vendor_review_dataset.json", "kind": "json_nonempty"},
            {"path": "outputs/vendor_review.html", "kind": "text_nonempty"},
            {"path": "outputs/vendor_rows.csv", "kind": "text_nonempty"},
        ],
        "M08": [
            {"path": "outputs/directory_dataset.json", "kind": "json_nonempty"},
            {"path": "docs/website/landing.html", "kind": "text_nonempty"},
            {"path": "docs/website/vendor.html", "kind": "text_nonempty"},
        ],
        "M09": [
            {"path": "docs/website/admin.html", "kind": "text_nonempty"},
            {"path": "docs/website/admin.js", "kind": "text_nonempty"},
            {"path": "outputs/pipeline_runs.json", "kind": "json_nonempty"},
        ],
        "M10": [
            {"path": "outputs/pipeline_runs.json", "kind": "json_nonempty"},
        ],
        "M13B": [
            {"path": "scripts/local_agent_runner.py", "kind": "text_nonempty"},
            {"path": "scripts/openai_agent_cli.py", "kind": "text_nonempty"},
            {"path": "scripts/run_autonomous_cycle.sh", "kind": "text_nonempty"},
            {"path": "scripts/prove_container_autonomous_loop.sh", "kind": "text_nonempty"},
            {"path": "project_state.json", "kind": "json_nonempty"},
            {"path": "milestone_registry.json", "kind": "json_nonempty"},
        ],
        "M13C": [
            {"path": "tools/tool_registry.json", "kind": "json_nonempty"},
            {"path": "tools/supabase/tool_spec.json", "kind": "json_nonempty"},
            {"path": "tools/README.md", "kind": "text_nonempty"},
            {"path": "tools/supabase/README.md", "kind": "text_nonempty"},
        ],
        "M13D": [
            {"path": "tools/supabase/cli.py", "kind": "text_nonempty"},
            {"path": "tools/supabase/tool_spec.json", "kind": "json_nonempty"},
            {"path": "tools/supabase/README.md", "kind": "text_nonempty"},
        ],
        "M15": [
            {"path": "scripts/check_supabase.py", "kind": "text_nonempty"},
            {"path": "supabase/core_persistence_schema.sql", "kind": "text_nonempty"},
        ],
        "M16": [
            {"path": "outputs/directory_dataset.json", "kind": "json_nonempty"},
            {"path": "outputs/vendor_review_dataset.json", "kind": "json_nonempty"},
            {"path": "outputs/vendor_review.html", "kind": "text_nonempty"},
            {"path": "outputs/pipeline_runs.json", "kind": "json_nonempty"},
        ],
        "M17": [
            {"path": "outputs/directory_dataset.json", "kind": "json_nonempty"},
            {"path": "outputs/vendor_review_dataset.json", "kind": "json_nonempty"},
            {"path": "outputs/vendor_review.html", "kind": "text_nonempty"},
            {"path": "outputs/pipeline_runs.json", "kind": "json_nonempty"},
        ],
    }
    return specs.get(milestone_id, [])


def assert_artifact_spec(root: Path, spec: dict[str, str]) -> dict[str, Any]:
    """Evaluate one artifact assertion."""
    path = root / spec["path"]
    result: dict[str, Any] = {
        "path": spec["path"],
        "kind": spec["kind"],
        "exists": path.exists(),
        "success": False,
    }
    if not path.exists():
        result["error"] = "missing file"
        return result

    if spec["kind"] == "text_nonempty":
        text = path.read_text(encoding="utf-8")
        result["success"] = bool(text.strip())
        if not result["success"]:
            result["error"] = "empty text file"
        return result

    if spec["kind"] == "json_nonempty":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            result["error"] = f"malformed json: {error}"
            return result
        if isinstance(payload, list):
            result["success"] = len(payload) > 0
        elif isinstance(payload, dict):
            result["success"] = len(payload) > 0
        else:
            result["success"] = payload is not None
        if not result["success"]:
            result["error"] = "empty json payload"
        return result

    result["error"] = f"unsupported artifact kind {spec['kind']}"
    return result


def evaluate_milestone_artifacts(root: Path, milestone_id: str) -> list[dict[str, Any]]:
    """Evaluate all configured artifact assertions for one milestone."""
    return [assert_artifact_spec(root, spec) for spec in milestone_artifact_specs(milestone_id)]


def failed_verify_attempt_count(
    run_history: list[dict[str, Any]],
    milestone_id: str,
    *,
    cycle_id: str | None = None,
) -> int:
    """Return the number of failed verify attempts for a milestone."""
    count = 0
    for entry in run_history:
        if entry.get("action") != "verify" or entry.get("milestone") != milestone_id:
            continue
        if cycle_id and entry.get("cycle_id") != cycle_id:
            continue
        if not entry.get("success"):
            count += 1
    return count


def summarize_verify_failure(entry: dict[str, Any]) -> str:
    """Build one searchable failure summary from a verify history entry."""
    parts: list[str] = [str(entry.get("note") or "")]
    for command_result in entry.get("commands") or []:
        if not isinstance(command_result, dict):
            continue
        parts.append(str(command_result.get("stdout") or ""))
        parts.append(str(command_result.get("stderr") or ""))
    for assertion in entry.get("artifact_assertions") or []:
        if isinstance(assertion, dict):
            parts.append(str(assertion.get("error") or ""))
            parts.append(str(assertion.get("path") or ""))
    return "\n".join(part for part in parts if part).strip()


def classify_verify_failure(entry: dict[str, Any]) -> dict[str, str]:
    """Classify a failed verify result as actionable or externally blocked."""
    summary = summarize_verify_failure(entry)
    lowered = summary.lower()
    external_markers = [
        "schema cache",
        "could not find the table",
        "temporary failure in name resolution",
        "connection refused",
        "permission denied",
        "authentication",
        "must be set",
        "api key",
        "credential",
        "docker: command not found",
        "docker command not found",
        "google_sheets_credentials_json",
        "supabase config missing",
        "manual verification still required",
    ]
    for marker in external_markers:
        if marker in lowered:
            return {"kind": "external_blocker", "summary": summary or marker}
    return {"kind": "actionable_retry", "summary": summary or "verification failed without an external blocker marker"}


def latest_role_verdict(root: Path, milestone_id: str, role: str) -> str:
    """Return one normalized role verdict using role output first, then history."""
    output = latest_role_output(root, milestone_id, role)
    if role_output_passes(output):
        return "pass"
    if role_output_fails(output):
        return "fail"

    run_history = load_run_history(root)
    history_entry = latest_history_entry(run_history, action=role if role != "reviewer" else "review", milestone_id=milestone_id)
    if history_entry is None:
        return "missing"
    if role == "reviewer":
        return "pass" if history_entry.get("success") else "fail"
    if role == "qa":
        return "pass" if history_entry.get("success") else "fail"
    return "missing"


def determine_next_action(root: Path, milestone_id: str | None = None) -> dict[str, Any]:
    """Return the next controller action for the current or selected milestone."""
    project_state = load_project_state(root)
    policy = load_controller_policy(project_state)
    _, milestones = load_milestone_registry(root)
    target_milestone = milestone_id or str(project_state.get("current_focus") or "").strip()
    if not target_milestone:
        raise RuntimeError("No milestone was provided and project_state.json has no current_focus")

    milestone = get_milestone_by_id(milestones, target_milestone)
    milestone_map = {item["id"]: item for item in milestones}
    incomplete_dependencies = [
        dependency
        for dependency in milestone["dependencies"]
        if milestone_map.get(dependency, {}).get("status") != "complete"
    ]
    if incomplete_dependencies:
        return {
            "milestone": target_milestone,
            "action": "blocked_dependency",
            "reason": f"incomplete dependencies: {', '.join(incomplete_dependencies)}",
            "retry_count": 0,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "",
        }

    preflight_failure = datastore_preflight_failure(target_milestone, root)
    if preflight_failure:
        return {
            "milestone": target_milestone,
            "action": "blocked_external",
            "reason": preflight_failure,
            "retry_count": 0,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "external_blocker",
        }

    run_history = load_run_history(root)
    current_cycle = current_cycle_id()
    retry_count = failed_verify_attempt_count(run_history, target_milestone, cycle_id=current_cycle)
    latest_verify = latest_history_entry(run_history, action="verify", milestone_id=target_milestone)
    latest_review = latest_history_entry(run_history, action="review", milestone_id=target_milestone)
    latest_qa = latest_history_entry(run_history, action="qa", milestone_id=target_milestone)
    latest_reviewer_output = latest_role_output(root, target_milestone, "reviewer")
    latest_qa_output = latest_role_output(root, target_milestone, "qa")

    if latest_verify is None:
        return {
            "milestone": target_milestone,
            "action": "start_iteration",
            "reason": "no verification has been recorded yet for this milestone",
            "retry_count": retry_count,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "",
        }

    if not latest_verify.get("success"):
        failure = classify_verify_failure(latest_verify)
        if failure["kind"] == "external_blocker" and policy["stop_on_external_blockers"]:
            return {
                "milestone": target_milestone,
                "action": "blocked_external",
                "reason": failure["summary"],
                "retry_count": retry_count,
                "max_retries": policy["max_same_milestone_retries"],
                "failure_kind": failure["kind"],
            }
        if retry_count >= policy["max_same_milestone_retries"]:
            return {
                "milestone": target_milestone,
                "action": "blocked_retry_limit",
                "reason": failure["summary"],
                "retry_count": retry_count,
                "max_retries": policy["max_same_milestone_retries"],
                "failure_kind": failure["kind"],
            }
        if policy["retry_on_actionable_failures"]:
            return {
                "milestone": target_milestone,
                "action": "retry_same_milestone",
                "reason": failure["summary"],
                "retry_count": retry_count,
                "max_retries": policy["max_same_milestone_retries"],
                "failure_kind": failure["kind"],
            }

    if role_output_fails(latest_reviewer_output) or (latest_review is not None and not latest_review.get("success")):
        if retry_count >= policy["max_same_milestone_retries"]:
            action = "blocked_retry_limit"
        else:
            action = "retry_same_milestone"
        return {
            "milestone": target_milestone,
            "action": action,
            "reason": "reviewer reported issues that must be fixed before closure",
            "retry_count": retry_count,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "review_failure",
        }

    if role_output_fails(latest_qa_output) or (latest_qa is not None and not latest_qa.get("success")):
        if retry_count >= policy["max_same_milestone_retries"]:
            action = "blocked_retry_limit"
        else:
            action = "retry_same_milestone"
        return {
            "milestone": target_milestone,
            "action": action,
            "reason": "QA reported gaps that must be fixed before closure",
            "retry_count": retry_count,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "qa_failure",
        }

    if latest_review is None and latest_reviewer_output is None:
        return {
            "milestone": target_milestone,
            "action": "run_review_and_qa",
            "reason": "verification passed, but review has not been recorded",
            "retry_count": retry_count,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "",
        }

    if latest_qa is None and latest_qa_output is None:
        return {
            "milestone": target_milestone,
            "action": "run_review_and_qa",
            "reason": "verification passed, but QA has not been recorded",
            "retry_count": retry_count,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "",
        }

    manual_checks_pending = latest_verify.get("manual_checks_pending") or []
    qa_manual_checks_complete = role_output_manual_checks_complete(latest_qa_output) or bool(
        latest_qa and latest_qa.get("manual_checks_complete")
    )
    if manual_checks_pending and not qa_manual_checks_complete:
        return {
            "milestone": target_milestone,
            "action": "manual_checks_required",
            "reason": "manual verification steps are still pending",
            "retry_count": retry_count,
            "max_retries": policy["max_same_milestone_retries"],
            "failure_kind": "manual_checks_pending",
        }

    return {
        "milestone": target_milestone,
        "action": "complete_milestone",
        "reason": "verification, review, and QA all pass with no pending manual checks",
        "retry_count": retry_count,
        "max_retries": policy["max_same_milestone_retries"],
        "failure_kind": "",
    }


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


def python_bin(root: Path) -> str:
    """Return the preferred Python executable for repo-local commands."""
    venv_python = root / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return "python3"


def repo_evidence(root: Path) -> dict[str, Any]:
    """Return lightweight repo diff evidence for autonomous iteration handoffs."""
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    diff_stat = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    changed_files: list[str] = []
    if status.returncode == 0:
        for line in status.stdout.splitlines():
            if len(line) < 4:
                continue
            candidate = line[3:].strip()
            if " -> " in candidate:
                candidate = candidate.split(" -> ", 1)[1].strip()
            if not candidate:
                continue
            changed_files.append(candidate)
    return {
        "changed_files": sorted(dict.fromkeys(changed_files)),
        "diff_stat": diff_stat.stdout.strip() if diff_stat.returncode == 0 else "",
    }


def run_role_phase(root: Path, milestone_id: str, role: str) -> dict[str, Any]:
    """Run one controller-owned role phase and capture execution metadata."""
    prompt_path = root / "docs" / "agents" / f"{role}_agent.md"
    if not prompt_path.exists():
        raise RuntimeError(f"Prompt file for role {role} was not found at {prompt_path}")

    runner_command = str(os.environ.get("AUTONOMOUS_AGENT_RUNNER", "")).strip()
    if runner_command:
        command = (
            f"{runner_command} "
            f"{shlex.quote(str(prompt_path))} "
            f"{shlex.quote(milestone_id)}"
        )
        completed = run_shell_command(command, root)
        return {
            "role": role,
            "command": command,
            "exit_code": completed.returncode,
            "success": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "runner_mode": "external_runner",
        }

    command = [
        python_bin(root),
        "scripts/local_agent_runner.py",
        str(prompt_path.relative_to(root)),
        milestone_id,
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "role": role,
        "command": " ".join(shlex.quote(part) for part in command),
        "exit_code": completed.returncode,
        "success": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "runner_mode": "repo_native_runner",
    }


def command_status(root: Path = PROJECT_ROOT) -> int:
    """Print current focus, milestone summary, and latest run entry."""
    project_state = load_project_state(root)
    _, milestones = load_milestone_registry(root)
    run_history = load_run_history(root)

    print(f"Current focus: {project_state.get('current_focus', 'unknown')}")
    capabilities = datastore_capabilities(root)
    print(
        "Datastore capabilities: "
        f"runtime_data_access={capabilities['runtime_data_access']} "
        f"schema_admin_access={capabilities['schema_admin_access']} "
        f"(direct={capabilities['schema_admin_direct']})"
    )
    print("Milestones:")
    for milestone in milestones:
        print(f"- {milestone['id']}: {milestone['title']} [{milestone['status']}]")

    current_focus = str(project_state.get("current_focus") or "").strip()
    if current_focus:
        print("Latest role outputs:")
        for role in ("planner", "builder", "reviewer", "qa"):
            output = latest_role_output(root, current_focus, role)
            if output is None:
                print(f"- {role}: none")
                continue
            result = output.get("result", {})
            print(f"- {role}: {result.get('status', 'unknown')} ({output.get('_path')})")
        declared_tools = available_tools_for_role(root, current_focus, "builder")
        if declared_tools:
            print("Declared tools for current focus:")
            for tool in declared_tools:
                print(f"- {tool['id']}: {tool['spec_path']}")

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
    declared_tools = available_tools_for_role(root, milestone["id"], "builder")
    if declared_tools:
        print("Tools:")
        for tool in declared_tools:
            print(f"- {tool['id']}: {tool['spec_path']}")

    if incomplete_dependencies:
        print(f"Blocked by incomplete dependencies: {', '.join(incomplete_dependencies)}")
        return 0
    return 0


def command_next_action(
    milestone_id: str | None = None,
    *,
    json_output: bool = False,
    root: Path = PROJECT_ROOT,
) -> int:
    """Print the next controller action for the current or selected milestone."""
    decision = determine_next_action(root, milestone_id)
    if json_output:
        print(json.dumps(decision, indent=2))
        return 0

    print(f"Milestone: {decision['milestone']}")
    print(f"Next action: {decision['action']}")
    print(f"Reason: {decision['reason']}")
    print(f"Retry count: {decision['retry_count']} / {decision['max_retries']}")
    if decision.get("failure_kind"):
        print(f"Failure kind: {decision['failure_kind']}")
    return 0


def command_verify(root: Path = PROJECT_ROOT) -> int:
    """Run the verification script and append a structured history entry."""
    project_state = load_project_state(root)
    milestone = project_state.get("current_focus")
    if not isinstance(milestone, str) or not milestone.strip():
        raise RuntimeError("project_state.json must define current_focus before verification can run")

    _, milestones = load_milestone_registry(root)
    milestone_record = get_milestone_by_id(milestones, milestone)

    preflight_failure = datastore_preflight_failure(milestone, root)
    if preflight_failure:
        entry = build_history_entry(
            action="verify",
            milestone=milestone,
            command="datastore_preflight",
            exit_code=1,
            success=False,
            note=preflight_failure,
        )
        entry["commands"] = []
        entry["manual_checks_pending"] = []
        entry["artifact_assertions"] = []
        append_run_history(entry, root)
        print(f"Verification failed for {milestone} (exit 1)")
        print(f"- datastore preflight [failed]: {preflight_failure}")
        return 1

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
    artifact_assertions = evaluate_milestone_artifacts(root, milestone)
    artifact_failures = [item for item in artifact_assertions if not item["success"]]
    if artifact_failures and overall_exit_code == 0:
        overall_exit_code = 1
        entry["exit_code"] = 1
        entry["success"] = False
        note_parts.append("artifact assertions failed")
        entry["note"] = ", ".join(note_parts)
    entry["commands"] = executed_results
    entry["manual_checks_pending"] = manual_checks_pending
    entry["artifact_assertions"] = artifact_assertions
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
    if artifact_assertions:
        print("Artifact assertions:")
        for assertion in artifact_assertions:
            state = "ok" if assertion["success"] else "failed"
            print(f"- {assertion['path']} [{state}]")

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
    latest_reviewer_output = latest_role_output(root, milestone_id, "reviewer")
    latest_qa_output = latest_role_output(root, milestone_id, "qa")

    if latest_verify is None or not latest_verify.get("success"):
        raise RuntimeError(f"Milestone {milestone_id} cannot be completed before successful verification")
    if not role_output_passes(latest_reviewer_output) and (latest_review is None or not latest_review.get("success")):
        raise RuntimeError(f"Milestone {milestone_id} cannot be completed before a passing review result")
    if not role_output_passes(latest_qa_output) and (latest_qa is None or not latest_qa.get("success")):
        raise RuntimeError(f"Milestone {milestone_id} cannot be completed before a passing QA result")

    manual_checks_pending = latest_verify.get("manual_checks_pending") or []
    qa_manual_checks_complete = role_output_manual_checks_complete(latest_qa_output) or bool(
        latest_qa and latest_qa.get("manual_checks_complete")
    )
    if manual_checks_pending and not qa_manual_checks_complete:
        raise RuntimeError(
            f"Milestone {milestone_id} still has manual checks pending and QA has not marked them complete"
        )

    update_milestone_status(registry_payload, milestone_id, "complete")
    save_json(root / "milestone_registry.json", registry_payload)

    _, updated_milestones = load_milestone_registry(root)
    next_milestone, _ = determine_next_milestone(updated_milestones)
    project_state["current_focus"] = next_milestone["id"] if next_milestone is not None else None
    save_json(root / "project_state.json", project_state)
    sync_repo_state_docs(root, project_state, updated_milestones)

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

    audit_result = trigger_closeout_audit(milestone_id, root)
    if audit_result["status"] in {"appended", "generated"}:
        print(f"Closeout audit recorded for {milestone_id}: {audit_result['audit_path']}")
    elif audit_result["status"] == "skipped":
        print(f"Closeout audit skipped for {milestone_id}: {audit_result['note']}")
    else:
        print(f"Closeout audit failed for {milestone_id}: {audit_result['note']}")
    return 0


def trigger_closeout_audit(milestone_id: str, root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Run a post-completion audit without blocking milestone completion."""
    try:
        result = milestone_auditor.run_audit(root, milestone_id, "closeout", append=True)
        append_run_history(
            {
                **build_history_entry(
                    action="closeout_audit",
                    milestone=milestone_id,
                    command=f"audit-closeout {milestone_id}",
                    exit_code=0,
                    success=True,
                    note=result["note"],
                ),
                "audit_path": result["audit_path"],
            },
            root,
        )
        return result
    except RuntimeError as error:
        note = str(error)
        append_run_history(
            build_history_entry(
                action="closeout_audit",
                milestone=milestone_id,
                command=f"audit-closeout {milestone_id}",
                exit_code=1,
                success=False,
                note=note,
            ),
            root,
        )
        return {
            "mode": "closeout",
            "milestone": milestone_id,
            "status": "skipped" if "OPENAI_API_KEY is required" in note else "failed",
            "audit_path": str(root / "docs" / "audit" / "audit.md"),
            "note": note,
        }


def command_audit_closeout(milestone_id: str, root: Path = PROJECT_ROOT) -> int:
    """Run the closeout auditor for one milestone."""
    result = trigger_closeout_audit(milestone_id, root)
    if result["status"] in {"appended", "generated"}:
        print(f"Closeout audit recorded for {milestone_id}: {result['audit_path']}")
        return 0
    print(f"Closeout audit {result['status']} for {milestone_id}: {result['note']}")
    return 1


def command_audit_backfill(
    milestone_ids: list[str],
    *,
    all_unaudited: bool,
    root: Path = PROJECT_ROOT,
) -> int:
    """Run the backfill auditor for one or more milestones."""
    targets = list(milestone_ids)
    if all_unaudited or not targets:
        targets = milestone_auditor.unaudited_complete_milestones(root)
    if not targets:
        print("No target milestones selected for backfill audit.")
        return 0

    exit_code = 0
    for milestone_id in targets:
        try:
            result = milestone_auditor.run_audit(root, milestone_id, "backfill", append=True)
            append_run_history(
                {
                    **build_history_entry(
                        action="backfill_audit",
                        milestone=milestone_id,
                        command=f"audit-backfill {milestone_id}",
                        exit_code=0,
                        success=True,
                        note=result["note"],
                    ),
                    "audit_path": result["audit_path"],
                },
                root,
            )
            print(f"Backfill audit recorded for {milestone_id}: {result['audit_path']}")
        except RuntimeError as error:
            exit_code = 1
            note = str(error)
            append_run_history(
                build_history_entry(
                    action="backfill_audit",
                    milestone=milestone_id,
                    command=f"audit-backfill {milestone_id}",
                    exit_code=1,
                    success=False,
                    note=note,
                ),
                root,
            )
            print(f"Backfill audit failed for {milestone_id}: {note}")
    return exit_code


def command_assert_artifacts(milestone_id: str | None, root: Path = PROJECT_ROOT) -> int:
    """Evaluate milestone-aware artifact assertions."""
    target_milestone = milestone_id or str(load_project_state(root).get("current_focus") or "").strip()
    if not target_milestone:
        raise RuntimeError("No milestone was provided and project_state.json has no current_focus")

    assertions = evaluate_milestone_artifacts(root, target_milestone)
    if not assertions:
        print(f"No artifact assertions configured for {target_milestone}.")
        return 0

    exit_code = 0
    print(f"Artifact assertions for {target_milestone}:")
    for assertion in assertions:
        state = "ok" if assertion["success"] else "failed"
        print(f"- {assertion['path']} [{state}]")
        if not assertion["success"]:
            exit_code = 1
    return exit_code


def command_fail(milestone_id: str, note: str, root: Path = PROJECT_ROOT) -> int:
    """Mark one milestone blocked and append a failure note."""
    project_state = load_project_state(root)
    registry_payload, _ = load_milestone_registry(root)
    update_milestone_status(registry_payload, milestone_id, "blocked")
    save_json(root / "milestone_registry.json", registry_payload)
    _, updated_milestones = load_milestone_registry(root)
    sync_repo_state_docs(root, project_state, updated_milestones)

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
        return 0

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
    declared_tools = available_tools_for_role(root, milestone["id"], "builder")
    if declared_tools:
        print("Declared tools:")
        for tool in declared_tools:
            backend_names = []
            for backend in tool["backends"]:
                if isinstance(backend, dict):
                    backend_names.append(str(backend.get("id") or backend.get("kind") or "backend"))
            suffix = f" ({', '.join(backend_names)})" if backend_names else ""
            print(f"- {tool['id']}: {tool['spec_path']}{suffix}")

    print("Status transition reminder:")
    print(f"- controller next action: python scripts/autonomous_controller.py next-action {milestone['id']}")
    print(f"- bounded controller loop: python scripts/autonomous_controller.py auto-iterate {milestone['id']}")
    print(f"- record review: python scripts/autonomous_controller.py review {milestone['id']} --status pass|fail --note ...")
    print(
        f"- record qa: python scripts/autonomous_controller.py qa {milestone['id']} "
        "--status pass|fail --note ... [--manual-checks-complete] [--artifact path]"
    )
    print(f"- artifact assertions: python scripts/autonomous_controller.py assert-artifacts {milestone['id']}")
    print(f"- complete only after verify + review + qa: python scripts/autonomous_controller.py complete {milestone['id']}")
    print(f"- closeout audit is triggered automatically after completion and can be rerun with: python scripts/autonomous_controller.py audit-closeout {milestone['id']}")

    return 0


def command_auto_iterate(
    milestone_id: str | None = None,
    *,
    max_iterations: int | None = None,
    root: Path = PROJECT_ROOT,
) -> int:
    """Run a bounded controller-owned loop for one milestone."""
    project_state = load_project_state(root)
    policy = load_controller_policy(project_state)
    target_milestone = milestone_id or str(project_state.get("current_focus") or "").strip()
    if not target_milestone:
        raise RuntimeError("No milestone was provided and project_state.json has no current_focus")

    iteration_budget = max_iterations or policy["max_controller_iterations_per_cycle"]
    if iteration_budget <= 0:
        raise RuntimeError("max_iterations must be positive")

    for iteration_index in range(1, iteration_budget + 1):
        decision = determine_next_action(root, target_milestone)
        print(
            f"Auto-iterate {target_milestone} iteration {iteration_index}/{iteration_budget}: "
            f"{decision['action']} - {decision['reason']}"
        )

        if decision["action"] == "complete_milestone":
            return command_complete(target_milestone, root)

        if decision["action"] in {"blocked_dependency", "manual_checks_required"}:
            print(f"Stopping on controller decision: {decision['action']}")
            return 1

        if decision["action"] in {"blocked_external", "blocked_retry_limit"}:
            if policy["auto_mark_blocked_on_external_failure"]:
                return command_fail(target_milestone, decision["reason"], root)
            print(f"Stopping on controller decision: {decision['action']}")
            return 1

        if decision["action"] in {"start_iteration", "retry_same_milestone"}:
            before_evidence = repo_evidence(root)
            planner_result = run_role_phase(root, target_milestone, "planner")
            builder_result = run_role_phase(root, target_milestone, "builder")
            after_evidence = repo_evidence(root)
            append_run_history(
                {
                    **build_history_entry(
                        action="iteration_step",
                        milestone=target_milestone,
                        command=f"auto-iterate {target_milestone}",
                        exit_code=0 if planner_result["success"] and builder_result["success"] else 1,
                        success=planner_result["success"] and builder_result["success"],
                        note=f"planner/builder iteration {iteration_index}",
                    ),
                    "iteration_index": iteration_index,
                    "decision": decision,
                    "before_evidence": before_evidence,
                    "after_evidence": after_evidence,
                    "planner_result": planner_result,
                    "builder_result": builder_result,
                },
                root,
            )
            if not planner_result["success"] or not builder_result["success"]:
                raise RuntimeError("Planner or builder phase failed during auto-iterate")
            command_verify(root)
            continue

        if decision["action"] == "run_review_and_qa":
            reviewer_result = run_role_phase(root, target_milestone, "reviewer")
            qa_result = run_role_phase(root, target_milestone, "qa")
            append_run_history(
                {
                    **build_history_entry(
                        action="auto_iterate",
                        milestone=target_milestone,
                        command=f"auto-iterate {target_milestone} review_qa",
                        exit_code=0 if reviewer_result["success"] and qa_result["success"] else 1,
                        success=reviewer_result["success"] and qa_result["success"],
                        note="reviewer/qa phases executed",
                    ),
                    "iteration_index": iteration_index,
                    "decision": decision,
                    "reviewer_result": reviewer_result,
                    "qa_result": qa_result,
                },
                root,
            )
            if not reviewer_result["success"] or not qa_result["success"]:
                raise RuntimeError("Reviewer or QA phase failed during auto-iterate")
            continue

        raise RuntimeError(f"Unsupported controller decision during auto-iterate: {decision['action']}")

    raise RuntimeError(f"Auto-iterate reached its controller iteration budget for {target_milestone}")


def main(argv: list[str] | None = None) -> int:
    """Run the controller CLI."""
    args = build_parser().parse_args(argv)
    root = PROJECT_ROOT

    try:
        if args.command == "status":
            return command_status(root)
        if args.command == "next":
            return command_next(root)
        if args.command == "next-action":
            return command_next_action(args.milestone_id, json_output=args.json_output, root=root)
        if args.command == "verify":
            return command_verify(root)
        if args.command == "assert-artifacts":
            return command_assert_artifacts(args.milestone_id, root)
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
        if args.command == "audit-closeout":
            return command_audit_closeout(args.milestone_id, root)
        if args.command == "audit-backfill":
            return command_audit_backfill(args.milestone_ids, all_unaudited=args.all_unaudited, root=root)
        if args.command == "run-cycle":
            return command_run_cycle(root)
        if args.command == "auto-iterate":
            return command_auto_iterate(args.milestone_id, max_iterations=args.max_iterations, root=root)
    except RuntimeError as error:
        print(f"Error: {error}")
        return 1

    print(f"Error: unsupported command {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
