"""Audit local repo readiness for milestone-driven autonomous development."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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
    ("docs/agents/planner_agent.md", "agent_prompts", True, False),
    ("docs/agents/builder_agent.md", "agent_prompts", True, False),
    ("docs/agents/reviewer_agent.md", "agent_prompts", True, False),
    ("docs/agents/qa_agent.md", "agent_prompts", True, False),
    ("project_state.json", "state_files", True, True),
    ("milestone_registry.json", "state_files", True, True),
    ("runs/run_history.json", "state_files", True, True),
    ("config/pipeline_config.json", "runtime", True, True),
    ("scripts/verify_project.sh", "runtime", True, False),
    ("scripts/run_autonomous_cycle.sh", "runtime", True, False),
    ("scripts/local_agent_runner.py", "runtime", True, False),
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

    return {
        "root": str(root),
        "ready_for_autonomous_dev": not required_broken,
        "summary": summary,
        "files": file_results,
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
        f"{summary['malformed_json']} malformed JSON"
    )

    for result in report["files"]:
        status = result["status"]
        if status == "present":
            continue
        suffix = f" ({result['error']})" if "error" in result else ""
        print(f"- {status}: {result['path']}{suffix}")


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
