"""Repo-native local runner for autonomous role packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
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
    return parser


def infer_role(prompt_path: Path) -> str:
    """Infer the role name from the prompt file path."""
    name = prompt_path.stem.lower()
    for role in ("controller", "planner", "builder", "reviewer", "qa"):
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


def build_role_checklist(role: str, milestone: dict[str, Any]) -> list[str]:
    """Return a deterministic checklist for the role."""
    if role == "controller":
        return [
            "Confirm current_focus and dependency status",
            "Confirm the next milestone still matches milestone_registry.json",
            "Run verification hooks through the controller",
            "Record review and QA outcomes before milestone closure",
        ]
    if role == "planner":
        return [
            f"Restate the objective for {milestone['id']}",
            "List acceptance criteria and proof requirements",
            "Identify files likely to change",
            "Identify tests to add or update",
            "List manual/runtime checks required before closure",
        ]
    if role == "builder":
        return [
            "Keep changes bounded to the milestone",
            "Update stale docs caused by the implementation",
            "Add or update tests for changed behavior",
            "Run executable verification commands before handoff",
        ]
    if role == "reviewer":
        return [
            "Inspect changed files only",
            "Check architecture and guardrail alignment",
            "Call out missing tests and silent failure paths",
            "State whether the milestone is actually closeable",
        ]
    if role == "qa":
        return [
            "Check milestone verification results",
            "Check artifact existence and runtime/manual checks",
            "State whether manual checks are still pending",
            "Record pass/fail with a concrete note",
        ]
    return ["Review the prompt and milestone metadata"]


def default_output_path(root: Path, role: str, milestone_id: str) -> Path:
    """Build the default output path for a generated role packet."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / "runs" / "agent_outputs" / f"{timestamp}_{role}_{milestone_id}.json"


def create_role_packet(
    *,
    root: Path,
    prompt_path: Path,
    milestone_id: str,
    changed_files: list[str],
    artifact_paths: list[str],
) -> dict[str, Any]:
    """Build one structured role packet."""
    project_state = autonomous_controller.load_project_state(root)
    _, milestones = autonomous_controller.load_milestone_registry(root)
    milestone = autonomous_controller.get_milestone_by_id(milestones, milestone_id)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    implementation_plan_text = (root / "docs" / "implementation_plan.md").read_text(encoding="utf-8")
    role = infer_role(prompt_path)

    artifact_checks = [{"path": path, "exists": (root / path).exists()} for path in artifact_paths]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
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
        "changed_files": changed_files,
        "artifact_checks": artifact_checks,
        "checklist": build_role_checklist(role, milestone),
        "runner_mode": "repo_native_local_packet",
        "notes": "This runner generates structured local packets and does not call external AI services.",
    }


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
