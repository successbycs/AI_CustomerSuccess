"""Repo-native milestone audit runner for closeout and backfill audits."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "docs" / "audit" / "audit.md"
MILESTONE_REGISTRY_PATH = PROJECT_ROOT / "milestone_registry.json"
IMPLEMENTATION_PLAN_PATH = PROJECT_ROOT / "docs" / "implementation_plan.md"
PROJECT_STATE_PATH = PROJECT_ROOT / "project_state.json"
PROJECT_BRAIN_PATH = PROJECT_ROOT / "docs" / "project_brain.md"
RUN_HISTORY_PATH = PROJECT_ROOT / "runs" / "run_history.json"

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 120
AUDIT_HEADER = "# Milestone Audits"
MODE_CONFIG = {
    "closeout": {
        "prompt_path": PROJECT_ROOT / "docs" / "agents" / "closeout_auditor_agent.md",
        "auditor_label": "AI engineer closeout auditor",
        "role_name": "closeout_auditor",
    },
    "backfill": {
        "prompt_path": PROJECT_ROOT / "docs" / "agents" / "backfill_auditor_agent.md",
        "auditor_label": "AI engineer backfill auditor",
        "role_name": "backfill_auditor",
    },
}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generate milestone audit entries for closeout and backfill workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    closeout_parser = subparsers.add_parser("closeout", help="Run the closeout auditor for a completed milestone.")
    closeout_parser.add_argument("milestone_id")
    closeout_parser.add_argument("--dry-run", action="store_true")

    backfill_parser = subparsers.add_parser("backfill", help="Run the backfill auditor for one or more milestones.")
    backfill_parser.add_argument("milestone_ids", nargs="*")
    backfill_parser.add_argument("--all-unaudited", action="store_true")
    backfill_parser.add_argument("--dry-run", action="store_true")

    return parser


def load_json(path: Path, label: str) -> Any:
    """Load one required JSON file."""
    if not path.exists():
        raise RuntimeError(f"Required {label} was not found at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Required {label} at {path} is malformed JSON: {error}") from error


def load_milestones(root: Path) -> list[dict[str, Any]]:
    """Load milestones from the registry."""
    payload = load_json(root / "milestone_registry.json", "milestone registry")
    milestones = payload.get("milestones")
    if not isinstance(milestones, list):
        raise RuntimeError("milestone_registry.json must contain a milestones list")
    return [item for item in milestones if isinstance(item, dict)]


def get_milestone(root: Path, milestone_id: str) -> dict[str, Any]:
    """Return a milestone record by id."""
    for milestone in load_milestones(root):
        if str(milestone.get("id") or "").strip() == milestone_id:
            return milestone
    raise RuntimeError(f"Milestone {milestone_id} was not found in milestone_registry.json")


def load_audit_text(root: Path) -> str:
    """Load the audit file or return the default header."""
    path = root / "docs" / "audit" / "audit.md"
    if not path.exists():
        return AUDIT_HEADER + "\n"
    return path.read_text(encoding="utf-8")


def audited_milestone_ids(root: Path) -> set[str]:
    """Return the milestone ids already present in audit.md."""
    text = load_audit_text(root)
    return set(re.findall(r"^## (M[0-9A-Z]+)\b", text, re.MULTILINE))


def extract_milestone_section_text(plan_text: str, milestone_id: str) -> str:
    """Extract one milestone section from docs/implementation_plan.md."""
    lines = plan_text.splitlines()
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


def milestone_history_slice(root: Path, milestone_id: str) -> list[dict[str, Any]]:
    """Return run-history entries for one milestone."""
    path = root / "runs" / "run_history.json"
    if not path.exists():
        return []
    payload = load_json(path, "run history")
    if not isinstance(payload, list):
        raise RuntimeError("runs/run_history.json must be a JSON list")
    return [item for item in payload if isinstance(item, dict) and item.get("milestone") == milestone_id]


def latest_history_entries(root: Path, milestone_id: str) -> dict[str, dict[str, Any] | None]:
    """Return the latest role/control entries for one milestone."""
    entries = milestone_history_slice(root, milestone_id)

    def latest(action: str) -> dict[str, Any] | None:
        for entry in reversed(entries):
            if entry.get("action") == action:
                return entry
        return None

    return {
        "verify": latest("verify"),
        "review": latest("review"),
        "qa": latest("qa"),
        "complete": latest("complete"),
        "closeout_audit": latest("closeout_audit"),
        "backfill_audit": latest("backfill_audit"),
    }


def load_declared_audit_tools(root: Path, milestone_id: str, mode: str) -> list[dict[str, Any]]:
    """Return repo-declared read-only tools available to the current audit role."""
    registry_path = root / "tools" / "tool_registry.json"
    if not registry_path.exists():
        return []

    payload = load_json(registry_path, "tool registry")
    raw_tools = payload.get("tools")
    if not isinstance(raw_tools, list):
        raise RuntimeError("tools/tool_registry.json must contain a tools list")

    role_name = MODE_CONFIG[mode]["role_name"]
    declared: list[dict[str, Any]] = []
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict) or not raw_tool.get("enabled", True):
            continue
        spec_path_text = str(raw_tool.get("spec_path") or "").strip()
        if not spec_path_text:
            continue
        spec_path = root / spec_path_text
        if not spec_path.exists():
            continue
        spec_payload = load_json(spec_path, f"tool spec for {raw_tool.get('id') or spec_path_text}")
        if not isinstance(spec_payload, dict):
            continue
        applicable = spec_payload.get("applicable_milestones")
        if isinstance(applicable, list) and applicable and milestone_id not in {str(item) for item in applicable}:
            continue
        role_access = spec_payload.get("role_access", {}).get(role_name)
        if not isinstance(role_access, dict):
            continue
        declared.append(
            {
                "id": str(spec_payload.get("id") or raw_tool.get("id") or "").strip(),
                "name": str(raw_tool.get("name") or spec_payload.get("id") or "").strip(),
                "spec_path": spec_path_text,
                "entrypoint": str(spec_payload.get("entrypoint") or "").strip(),
                "development_only": bool(spec_payload.get("development_only", False)),
                "allowed_operations": [
                    str(item).strip() for item in role_access.get("operations", []) if str(item).strip()
                ],
                "write_allowed": bool(role_access.get("write_allowed", False)),
                "approval_required": bool(role_access.get("approval_required", False)),
            }
        )
    return declared


def build_context(root: Path, milestone_id: str, mode: str) -> dict[str, Any]:
    """Build the audit context for one milestone."""
    milestone = get_milestone(root, milestone_id)
    project_state = load_json(root / "project_state.json", "project state")
    plan_text = (root / "docs" / "implementation_plan.md").read_text(encoding="utf-8")
    project_brain = (root / "docs" / "project_brain.md").read_text(encoding="utf-8") if (root / "docs" / "project_brain.md").exists() else ""
    audit_text = load_audit_text(root)
    history_entries = milestone_history_slice(root, milestone_id)
    return {
        "mode": mode,
        "date": str(date.today()),
        "milestone": {
            "id": str(milestone.get("id") or ""),
            "title": str(milestone.get("title") or ""),
            "status": str(milestone.get("status") or ""),
            "dependencies": milestone.get("dependencies") if isinstance(milestone.get("dependencies"), list) else [],
            "verify": milestone.get("verify") if isinstance(milestone.get("verify"), list) else [],
            "implementation_plan_section": extract_milestone_section_text(plan_text, milestone_id),
        },
        "project_state": {
            "current_focus": project_state.get("current_focus"),
        },
        "latest_history": latest_history_entries(root, milestone_id),
        "history_entries": history_entries[-12:],
        "available_tools": load_declared_audit_tools(root, milestone_id, mode),
        "existing_audits": sorted(audited_milestone_ids(root)),
        "audit_file_excerpt": audit_text[-6000:],
        "project_brain_excerpt": project_brain[-4000:],
    }


def build_system_prompt(prompt_text: str, mode: str) -> str:
    """Build the system prompt for one audit mode."""
    config = MODE_CONFIG[mode]
    return (
        f"{prompt_text}\n\n"
        "You are operating inside a milestone-driven software delivery control plane. "
        "Return exactly one markdown audit entry for the target milestone. "
        "Do not wrap the result in code fences. "
        f"Use the auditor label `{config['auditor_label']}` exactly. "
        "Do not include explanatory text before or after the audit entry."
    )


def build_user_prompt(context: dict[str, Any]) -> str:
    """Build the user prompt for one audit request."""
    return (
        "Create the milestone audit entry from this repo context.\n\n"
        f"{json.dumps(context, indent=2)}"
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


def call_openai_markdown(prompt_text: str, context: dict[str, Any]) -> str:
    """Call the OpenAI Responses API and return markdown text."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run milestone audits")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    timeout = int(os.environ.get("OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    response = requests.post(
        f"{base_url.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": build_system_prompt(prompt_text, context['mode'])}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": build_user_prompt(context)}],
                },
            ],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    text = extract_response_text(payload)
    if not text:
        raise RuntimeError("OpenAI audit response did not contain any text output")
    return text


def normalize_audit_entry(markdown: str, milestone_id: str, mode: str) -> str:
    """Normalize and validate one audit entry."""
    cleaned = markdown.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned).strip()

    match = re.search(rf"(^## {re.escape(milestone_id)}\b.*)", cleaned, re.MULTILINE | re.DOTALL)
    if match:
        cleaned = match.group(1).strip()

    if not cleaned.startswith(f"## {milestone_id}"):
        raise RuntimeError(f"Audit entry did not start with '## {milestone_id}'")

    expected_label = MODE_CONFIG[mode]["auditor_label"]
    if f"Auditor: {expected_label}" not in cleaned:
        raise RuntimeError(f"Audit entry did not include 'Auditor: {expected_label}'")

    expected_mode_line = f"Audit mode: {mode}"
    if expected_mode_line not in cleaned:
        raise RuntimeError(f"Audit entry did not include '{expected_mode_line}'")

    return cleaned + "\n"


def upsert_audit_entry(root: Path, milestone_id: str, audit_entry: str) -> Path:
    """Replace any existing section for the milestone and append the new entry."""
    path = root / "docs" / "audit" / "audit.md"
    existing = load_audit_text(root).strip()
    if not existing:
        existing = AUDIT_HEADER

    pattern = re.compile(rf"^## {re.escape(milestone_id)}\b.*?(?=^## M[0-9A-Z]+\b|\Z)", re.MULTILINE | re.DOTALL)
    normalized = pattern.sub("", existing).strip()
    if not normalized.startswith(AUDIT_HEADER):
        normalized = f"{AUDIT_HEADER}\n\n{normalized}".strip()

    final_text = normalized.rstrip() + "\n\n" + audit_entry.strip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(final_text, encoding="utf-8")
    return path


def run_audit(root: Path, milestone_id: str, mode: str, *, append: bool = True) -> dict[str, Any]:
    """Run one milestone audit and optionally append it to docs/audit/audit.md."""
    config = MODE_CONFIG[mode]
    prompt_path = config["prompt_path"]
    if not prompt_path.exists():
        raise RuntimeError(f"Audit prompt file was not found at {prompt_path}")

    milestone = get_milestone(root, milestone_id)
    if mode == "closeout" and str(milestone.get("status") or "") != "complete":
        raise RuntimeError(f"Closeout audits require a completed milestone, but {milestone_id} is {milestone.get('status')}")

    context = build_context(root, milestone_id, mode)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    markdown = normalize_audit_entry(call_openai_markdown(prompt_text, context), milestone_id, mode)
    if append:
        path = upsert_audit_entry(root, milestone_id, markdown)
    else:
        path = root / "docs" / "audit" / "audit.md"
    return {
        "mode": mode,
        "milestone": milestone_id,
        "status": "appended" if append else "generated",
        "audit_path": str(path),
        "audit_markdown": markdown,
        "note": f"{mode} audit generated for {milestone_id}",
    }


def unaudited_complete_milestones(root: Path) -> list[str]:
    """Return completed milestones that do not yet have audit entries."""
    audited = audited_milestone_ids(root)
    milestone_ids: list[str] = []
    for milestone in load_milestones(root):
        milestone_id = str(milestone.get("id") or "").strip()
        if str(milestone.get("status") or "") != "complete":
            continue
        if milestone_id not in audited:
            milestone_ids.append(milestone_id)
    return milestone_ids


def command_closeout(milestone_id: str, *, dry_run: bool, root: Path = PROJECT_ROOT) -> int:
    """Run a closeout audit for one milestone."""
    result = run_audit(root, milestone_id, "closeout", append=not dry_run)
    print(f"Closeout audit {result['status']} for {milestone_id}: {result['audit_path']}")
    if dry_run:
        print(result["audit_markdown"])
    return 0


def command_backfill(
    milestone_ids: list[str],
    *,
    all_unaudited: bool,
    dry_run: bool,
    root: Path = PROJECT_ROOT,
) -> int:
    """Run backfill audits for the selected milestones."""
    targets = list(milestone_ids)
    if all_unaudited or not targets:
        targets = unaudited_complete_milestones(root)
    if not targets:
        print("No target milestones selected for backfill audit.")
        return 0

    for milestone_id in targets:
        result = run_audit(root, milestone_id, "backfill", append=not dry_run)
        print(f"Backfill audit {result['status']} for {milestone_id}: {result['audit_path']}")
        if dry_run:
            print(result["audit_markdown"])
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the milestone auditor CLI."""
    args = build_parser().parse_args(argv)
    if args.command == "closeout":
        return command_closeout(args.milestone_id, dry_run=args.dry_run)
    if args.command == "backfill":
        return command_backfill(
            args.milestone_ids,
            all_unaudited=args.all_unaudited,
            dry_run=args.dry_run,
        )
    raise RuntimeError(f"Unsupported command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
