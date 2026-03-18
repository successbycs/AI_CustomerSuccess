"""Tests for the repo-native milestone auditor."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import milestone_auditor


def test_run_audit_appends_entry(monkeypatch, tmp_path: Path):
    create_repo_state(tmp_path)
    monkeypatch.setattr(
        milestone_auditor,
        "call_openai_markdown",
        lambda prompt_text, context: (
            "## M02 Two-phase pipeline\n\n"
            "Date: 2026-03-18\n"
            "Auditor: AI engineer closeout auditor\n"
            "Audit mode: closeout\n"
            "Milestone status at audit time: `complete`\n\n"
            "Findings:\n1. Example finding\n\n"
            "Residual risks:\n- Example risk\n\n"
            "Completion assessment:\n- Example assessment.\n"
        ),
    )

    result = milestone_auditor.run_audit(tmp_path, "M02", "closeout", append=True)

    audit_text = (tmp_path / "docs" / "audit" / "audit.md").read_text(encoding="utf-8")
    assert result["status"] == "appended"
    assert "## M02 Two-phase pipeline" in audit_text


def test_run_audit_replaces_existing_entry_for_same_milestone(monkeypatch, tmp_path: Path):
    create_repo_state(tmp_path)
    create_file(
        tmp_path,
        "docs/audit/audit.md",
        "# Milestone Audits\n\n## M02 Two-phase pipeline\n\nDate: 2026-03-17\nOld entry\n",
    )
    monkeypatch.setattr(
        milestone_auditor,
        "call_openai_markdown",
        lambda prompt_text, context: (
            "## M02 Two-phase pipeline\n\n"
            "Date: 2026-03-18\n"
            "Auditor: AI engineer closeout auditor\n"
            "Audit mode: closeout\n"
            "Milestone status at audit time: `complete`\n\n"
            "Findings:\n1. New finding\n\n"
            "Residual risks:\n- New risk\n\n"
            "Completion assessment:\n- New assessment.\n"
        ),
    )

    milestone_auditor.run_audit(tmp_path, "M02", "closeout", append=True)

    audit_text = (tmp_path / "docs" / "audit" / "audit.md").read_text(encoding="utf-8")
    assert audit_text.count("## M02 Two-phase pipeline") == 1
    assert "New finding" in audit_text
    assert "Old entry" not in audit_text


def test_unaudited_complete_milestones_reports_missing_ids(tmp_path: Path):
    create_repo_state(tmp_path)
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n\n## M01 Discovery foundation\n")

    missing = milestone_auditor.unaudited_complete_milestones(tmp_path)

    assert missing == ["M02"]


def test_build_context_exposes_declared_read_only_tools_for_auditors(tmp_path: Path):
    create_repo_state(tmp_path)
    create_file(
        tmp_path,
        "tools/tool_registry.json",
        json.dumps(
            {
                "tools": [
                    {
                        "id": "supabase",
                        "name": "Supabase",
                        "enabled": True,
                        "spec_path": "tools/supabase/tool_spec.json",
                    }
                ]
            }
        ),
    )
    create_file(
        tmp_path,
        "tools/supabase/tool_spec.json",
        json.dumps(
            {
                "id": "supabase",
                "entrypoint": "tools/supabase/cli.py",
                "applicable_milestones": ["M02"],
                "role_access": {
                    "closeout_auditor": {
                        "operations": ["read_runs", "verify_schema"],
                        "write_allowed": False,
                        "approval_required": False,
                    }
                },
            }
        ),
    )

    context = milestone_auditor.build_context(tmp_path, "M02", "closeout")

    assert context["available_tools"] == [
        {
            "id": "supabase",
            "name": "Supabase",
            "spec_path": "tools/supabase/tool_spec.json",
            "entrypoint": "tools/supabase/cli.py",
            "development_only": False,
            "allowed_operations": ["read_runs", "verify_schema"],
            "write_allowed": False,
            "approval_required": False,
        }
    ]


def create_repo_state(root: Path) -> None:
    """Create a minimal repo shape for the milestone auditor tests."""
    create_file(root, "docs/agents/closeout_auditor_agent.md", "closeout")
    create_file(root, "docs/agents/backfill_auditor_agent.md", "backfill")
    create_file(root, "docs/implementation_plan.md", "## M02 Two-phase pipeline\nStatus: `complete`\n")
    create_file(root, "docs/project_brain.md", "brain")
    create_file(root, "project_state.json", json.dumps({"current_focus": None}))
    create_file(
        root,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {"id": "M01", "title": "Discovery foundation", "status": "complete", "dependencies": [], "verify": []},
                    {"id": "M02", "title": "Two-phase pipeline", "status": "complete", "dependencies": ["M01"], "verify": []},
                ]
            }
        ),
    )
    create_file(
        root,
        "runs/run_history.json",
        json.dumps(
            [
                {"action": "verify", "milestone": "M02", "success": True, "note": "verify ok"},
                {"action": "review", "milestone": "M02", "success": True, "note": "review ok"},
                {"action": "qa", "milestone": "M02", "success": True, "note": "qa ok"},
                {"action": "complete", "milestone": "M02", "success": True, "note": "complete ok"},
            ]
        ),
    )
    create_file(root, "docs/audit/audit.md", "# Milestone Audits\n")


def create_file(root: Path, relative_path: str, contents: str = "") -> None:
    """Write a file relative to a temp repo root."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
