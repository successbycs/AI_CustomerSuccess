"""Audit local repo readiness for milestone-driven autonomous development."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FILE_SPECS = (
    ("docs/product_design.md", "core_docs", True, False),
    ("docs/architecture.md", "core_docs", True, False),
    ("docs/codex_guardrails.md", "core_docs", True, False),
    ("docs/implementation_plan.md", "core_docs", True, False),
    ("docs/definition_of_done.md", "core_docs", True, False),
    ("docs/project_brain.md", "core_docs", True, False),
    ("docs/autonomous_dev_loop.md", "core_docs", True, False),
    ("docs/agents/controller_agent.md", "agent_prompts", True, False),
    ("docs/agents/prework_agent.md", "agent_prompts", True, False),
    ("docs/agents/planner_agent.md", "agent_prompts", True, False),
    ("docs/agents/builder_agent.md", "agent_prompts", True, False),
    ("docs/agents/reviewer_agent.md", "agent_prompts", True, False),
    ("docs/agents/qa_agent.md", "agent_prompts", True, False),
    ("docs/agents/closeout_auditor_agent.md", "agent_prompts", True, False),
    ("docs/agents/backfill_auditor_agent.md", "agent_prompts", True, False),
    ("docs/audit/audit.md", "agent_prompts", True, False),
    ("project_state.json", "state_files", True, True),
    ("milestone_registry.json", "state_files", True, True),
    ("runs/run_history.json", "state_files", True, True),
    ("config/pipeline_config.json", "runtime", True, True),
    ("supabase/core_persistence_schema.sql", "runtime", True, False),
    ("tools/tool_registry.json", "runtime", True, True),
    ("tools/supabase/tool_spec.json", "runtime", True, True),
    ("tools/supabase/cli.py", "runtime", True, False),
    ("scripts/verify_project.sh", "runtime", True, False),
    ("scripts/run_autonomous_cycle.sh", "runtime", True, False),
    ("scripts/local_agent_runner.py", "runtime", True, False),
    ("scripts/openai_agent_cli.py", "runtime", False, False),
    ("scripts/milestone_auditor.py", "runtime", True, False),
    ("Dockerfile", "runtime", True, False),
    ("docker-compose.yml", "runtime", True, False),
    (".devcontainer/devcontainer.json", "runtime", False, False),
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Audit repo readiness for milestone-driven autonomous development.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print machine-readable JSON output.",
    )
    return parser


def audit_repo(root: Path) -> dict[str, Any]:
    """Return a structured audit report for the target repo root."""
    file_results: list[dict[str, Any]] = []
    summary = {
        "present": 0,
        "missing_required": 0,
        "missing_optional": 0,
        "malformed_json": 0,
        "consistency_issues": 0,
    }
    required_broken = False

    for relative_path, category, required, is_json in FILE_SPECS:
        result = inspect_path(
            root=root,
            relative_path=relative_path,
            category=category,
            required=required,
            is_json=is_json,
        )
        file_results.append(result)
        summary[result["status"]] += 1
        if required and result["status"] in {"missing_required", "malformed_json"}:
            required_broken = True

    consistency_issues = collect_consistency_issues(root)
    summary["consistency_issues"] = len(consistency_issues)
    if consistency_issues:
        required_broken = True

    return {
        "root": str(root),
        "ready_for_autonomous_dev": not required_broken,
        "summary": summary,
        "files": file_results,
        "consistency_issues": consistency_issues,
    }


def inspect_path(
    *,
    root: Path,
    relative_path: str,
    category: str,
    required: bool,
    is_json: bool,
) -> dict[str, Any]:
    """Inspect one path and report its readiness classification."""
    absolute_path = root / relative_path
    result: dict[str, Any] = {
        "path": relative_path,
        "category": category,
        "required": required,
        "status": "present",
    }

    if not absolute_path.exists():
        result["status"] = "missing_required" if required else "missing_optional"
        return result

    if is_json:
        try:
            json.loads(absolute_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            result["status"] = "malformed_json"
            result["error"] = f"{type(error).__name__}: {error}"

    return result


def collect_consistency_issues(root: Path) -> list[str]:
    """Return doc/state consistency issues that weaken autonomous trust."""
    issues: list[str] = []
    project_state_path = root / "project_state.json"
    registry_path = root / "milestone_registry.json"
    plan_path = root / "docs" / "implementation_plan.md"
    brain_path = root / "docs" / "project_brain.md"

    if not project_state_path.exists() or not registry_path.exists():
        return issues

    try:
        project_state = json.loads(project_state_path.read_text(encoding="utf-8"))
        registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return issues

    current_focus = str(project_state.get("current_focus") or "").strip()
    milestones = registry_payload.get("milestones")
    if not isinstance(milestones, list):
        return issues
    registry_statuses = {
        str(item.get("id") or "").strip(): str(item.get("status") or "").strip()
        for item in milestones
        if isinstance(item, dict)
    }

    if plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        pattern = re.compile(r"^## (M[0-9A-Z]+)\b.*?\nStatus:\s*`([^`]+)`", re.MULTILINE)
        for milestone_id, plan_status in pattern.findall(plan_text):
            registry_status = registry_statuses.get(milestone_id)
            if registry_status and registry_status != plan_status.strip():
                issues.append(
                    f"implementation_plan status for {milestone_id} is {plan_status.strip()} but milestone_registry.json says {registry_status}"
                )

    if brain_path.exists():
        brain_text = brain_path.read_text(encoding="utf-8")
        active_match = re.search(r"current active milestone is `([^`]+)`", brain_text)
        complete_match = "- there is no active milestone; all milestones are complete" in brain_text
        if active_match:
            remembered_focus = active_match.group(1).strip()
            if current_focus and remembered_focus != current_focus:
                issues.append(
                    f"project_brain current active milestone is {remembered_focus} but project_state.json current_focus is {current_focus}"
                )
            if not current_focus:
                issues.append(
                    "project_brain says there is an active milestone but project_state.json current_focus is empty"
                )
        elif complete_match and current_focus:
            issues.append(
                f"project_brain says there is no active milestone but project_state.json current_focus is {current_focus}"
            )

    if current_focus == "M15":
        env_values = load_local_env(root)
        has_schema_admin = bool(
            (
                (env_values.get("DATABASE_URL") or env_values.get("SUPABASE_DB_URL"))
                and (shutil.which("psql") or _python_import_available("psycopg"))
            )
        )
        if not has_schema_admin:
            issues.append(
                "current_focus M15 requires datastore schema-admin access, but DATABASE_URL/SUPABASE_DB_URL with psql or psycopg is not available"
            )

    return issues


def load_local_env(root: Path) -> dict[str, str]:
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


def _python_import_available(module_name: str) -> bool:
    """Return True when a Python module can be imported in the current interpreter."""
    try:
        __import__(module_name)
    except Exception:
        return False
    return True


def print_human_report(report: dict[str, Any]) -> None:
    """Print a concise human-readable readiness report."""
    readiness = "READY" if report["ready_for_autonomous_dev"] else "NOT READY"
    summary = report["summary"]
    print(f"Autonomous development audit: {readiness}")
    print(f"Repo root: {report['root']}")
    print(
        "Summary: "
        f"{summary['present']} present, "
        f"{summary['missing_required']} missing required, "
        f"{summary['missing_optional']} missing optional, "
        f"{summary['malformed_json']} malformed JSON, "
        f"{summary['consistency_issues']} consistency issues"
    )

    for result in report["files"]:
        status = result["status"]
        if status == "present":
            continue
        suffix = f" ({result['error']})" if "error" in result else ""
        print(f"- {status}: {result['path']}{suffix}")
    for issue in report.get("consistency_issues", []):
        print(f"- consistency_issue: {issue}")


def main() -> int:
    """Run the audit CLI."""
    args = build_parser().parse_args()
    report = audit_repo(PROJECT_ROOT)
    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report)
    return 0 if report["ready_for_autonomous_dev"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
