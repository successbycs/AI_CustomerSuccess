"""Tests for the autonomous repo readiness audit."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import autonomous_audit


def test_audit_repo_detects_required_and_optional_files(tmp_path: Path):
    create_file(tmp_path, "docs/product_design.md")
    create_file(tmp_path, "docs/architecture.md")
    create_file(tmp_path, "docs/codex_guardrails.md")
    create_file(tmp_path, "docs/implementation_plan.md")
    create_file(tmp_path, "docs/definition_of_done.md")
    create_file(tmp_path, "docs/project_brain.md")
    create_file(tmp_path, "docs/autonomous_dev_loop.md")
    create_file(tmp_path, "docs/agents/controller_agent.md")
    create_file(tmp_path, "docs/agents/prework_agent.md")
    create_file(tmp_path, "docs/agents/planner_agent.md")
    create_file(tmp_path, "docs/agents/builder_agent.md")
    create_file(tmp_path, "docs/agents/reviewer_agent.md")
    create_file(tmp_path, "docs/agents/qa_agent.md")
    create_file(tmp_path, "docs/agents/closeout_auditor_agent.md")
    create_file(tmp_path, "docs/agents/backfill_auditor_agent.md")
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n")
    create_file(tmp_path, "project_state.json", "{}")
    create_file(tmp_path, "milestone_registry.json", "{}")
    create_file(tmp_path, "runs/run_history.json", "[]")
    create_file(tmp_path, "config/pipeline_config.json", "{}")
    create_file(tmp_path, "supabase/core_persistence_schema.sql")
    create_file(tmp_path, "tools/tool_registry.json", "{}")
    create_file(tmp_path, "tools/supabase/tool_spec.json", "{}")
    create_file(tmp_path, "tools/supabase/cli.py")
    create_file(tmp_path, "scripts/verify_project.sh")
    create_file(tmp_path, "scripts/run_autonomous_cycle.sh")
    create_file(tmp_path, "scripts/local_agent_runner.py")
    create_file(tmp_path, "scripts/openai_agent_cli.py")
    create_file(tmp_path, "scripts/milestone_auditor.py")
    create_file(tmp_path, "Dockerfile")
    create_file(tmp_path, "docker-compose.yml")

    report = autonomous_audit.audit_repo(tmp_path)

    assert report["ready_for_autonomous_dev"] is True
    assert report["summary"]["missing_optional"] > 0
    assert report["summary"]["missing_required"] == 0


def test_audit_repo_reports_missing_required_files(tmp_path: Path):
    report = autonomous_audit.audit_repo(tmp_path)

    assert report["ready_for_autonomous_dev"] is False
    assert report["summary"]["missing_required"] > 0
    assert any(
        item["path"] == "docs/product_design.md" and item["status"] == "missing_required"
        for item in report["files"]
    )


def test_audit_repo_reports_malformed_json(tmp_path: Path):
    create_file(tmp_path, "docs/product_design.md")
    create_file(tmp_path, "docs/architecture.md")
    create_file(tmp_path, "docs/codex_guardrails.md")
    create_file(tmp_path, "docs/implementation_plan.md")
    create_file(tmp_path, "docs/definition_of_done.md")
    create_file(tmp_path, "docs/project_brain.md")
    create_file(tmp_path, "docs/autonomous_dev_loop.md")
    create_file(tmp_path, "docs/agents/controller_agent.md")
    create_file(tmp_path, "docs/agents/prework_agent.md")
    create_file(tmp_path, "docs/agents/planner_agent.md")
    create_file(tmp_path, "docs/agents/builder_agent.md")
    create_file(tmp_path, "docs/agents/reviewer_agent.md")
    create_file(tmp_path, "docs/agents/qa_agent.md")
    create_file(tmp_path, "docs/agents/closeout_auditor_agent.md")
    create_file(tmp_path, "docs/agents/backfill_auditor_agent.md")
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n")
    create_file(tmp_path, "project_state.json", "{}")
    create_file(tmp_path, "milestone_registry.json", "{}")
    create_file(tmp_path, "runs/run_history.json", "[]")
    create_file(tmp_path, "config/pipeline_config.json", "{bad json")
    create_file(tmp_path, "supabase/core_persistence_schema.sql")
    create_file(tmp_path, "tools/tool_registry.json", "{}")
    create_file(tmp_path, "tools/supabase/tool_spec.json", "{}")
    create_file(tmp_path, "tools/supabase/cli.py")
    create_file(tmp_path, "scripts/verify_project.sh")
    create_file(tmp_path, "scripts/run_autonomous_cycle.sh")
    create_file(tmp_path, "scripts/local_agent_runner.py")
    create_file(tmp_path, "scripts/openai_agent_cli.py")
    create_file(tmp_path, "scripts/milestone_auditor.py")
    create_file(tmp_path, "Dockerfile")
    create_file(tmp_path, "docker-compose.yml")

    report = autonomous_audit.audit_repo(tmp_path)

    pipeline_config = next(item for item in report["files"] if item["path"] == "config/pipeline_config.json")
    assert pipeline_config["status"] == "malformed_json"
    assert report["ready_for_autonomous_dev"] is False


def test_audit_repo_json_output_shape(tmp_path: Path):
    create_file(tmp_path, "docs/product_design.md")
    create_file(tmp_path, "docs/architecture.md")
    create_file(tmp_path, "docs/codex_guardrails.md")
    create_file(tmp_path, "docs/implementation_plan.md")
    create_file(tmp_path, "docs/definition_of_done.md")
    create_file(tmp_path, "docs/project_brain.md")
    create_file(tmp_path, "docs/autonomous_dev_loop.md")
    create_file(tmp_path, "docs/agents/controller_agent.md")
    create_file(tmp_path, "docs/agents/prework_agent.md")
    create_file(tmp_path, "docs/agents/planner_agent.md")
    create_file(tmp_path, "docs/agents/builder_agent.md")
    create_file(tmp_path, "docs/agents/reviewer_agent.md")
    create_file(tmp_path, "docs/agents/qa_agent.md")
    create_file(tmp_path, "docs/agents/closeout_auditor_agent.md")
    create_file(tmp_path, "docs/agents/backfill_auditor_agent.md")
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n")
    create_file(tmp_path, "project_state.json", "{}")
    create_file(tmp_path, "milestone_registry.json", "{}")
    create_file(tmp_path, "runs/run_history.json", "[]")
    create_file(tmp_path, "config/pipeline_config.json", json.dumps({"ok": True}))
    create_file(tmp_path, "supabase/core_persistence_schema.sql")
    create_file(tmp_path, "tools/tool_registry.json", json.dumps({"tools": []}))
    create_file(tmp_path, "tools/supabase/tool_spec.json", json.dumps({"id": "supabase"}))
    create_file(tmp_path, "tools/supabase/cli.py")
    create_file(tmp_path, "scripts/verify_project.sh")
    create_file(tmp_path, "scripts/run_autonomous_cycle.sh")
    create_file(tmp_path, "scripts/local_agent_runner.py")
    create_file(tmp_path, "scripts/openai_agent_cli.py")
    create_file(tmp_path, "scripts/milestone_auditor.py")
    create_file(tmp_path, "Dockerfile")
    create_file(tmp_path, "docker-compose.yml")

    report = autonomous_audit.audit_repo(tmp_path)

    assert set(report) == {"root", "ready_for_autonomous_dev", "summary", "files", "consistency_issues"}
    assert isinstance(report["files"], list)


def test_audit_repo_reports_consistency_issues(tmp_path: Path):
    create_file(tmp_path, "docs/product_design.md")
    create_file(tmp_path, "docs/architecture.md")
    create_file(tmp_path, "docs/codex_guardrails.md")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M07 Review and public export artifacts\nStatus: `complete`\n",
    )
    create_file(tmp_path, "docs/definition_of_done.md")
    create_file(
        tmp_path,
        "docs/project_brain.md",
        "- M13B is complete; the current active milestone is `M13C` Tool registry and tool-access components\n",
    )
    create_file(tmp_path, "docs/autonomous_dev_loop.md")
    create_file(tmp_path, "docs/agents/controller_agent.md")
    create_file(tmp_path, "docs/agents/prework_agent.md")
    create_file(tmp_path, "docs/agents/planner_agent.md")
    create_file(tmp_path, "docs/agents/builder_agent.md")
    create_file(tmp_path, "docs/agents/reviewer_agent.md")
    create_file(tmp_path, "docs/agents/qa_agent.md")
    create_file(tmp_path, "docs/agents/closeout_auditor_agent.md")
    create_file(tmp_path, "docs/agents/backfill_auditor_agent.md")
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n")
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": "M07"}))
    create_file(tmp_path, "milestone_registry.json", json.dumps({"milestones": [{"id": "M07", "title": "Review and public export artifacts", "status": "blocked", "dependencies": [], "verify": []}]}))
    create_file(tmp_path, "runs/run_history.json", "[]")
    create_file(tmp_path, "config/pipeline_config.json", "{}")
    create_file(tmp_path, "supabase/core_persistence_schema.sql")
    create_file(tmp_path, "tools/tool_registry.json", json.dumps({"tools": []}))
    create_file(tmp_path, "tools/supabase/tool_spec.json", json.dumps({"id": "supabase"}))
    create_file(tmp_path, "tools/supabase/cli.py")
    create_file(tmp_path, "scripts/verify_project.sh")
    create_file(tmp_path, "scripts/run_autonomous_cycle.sh")
    create_file(tmp_path, "scripts/local_agent_runner.py")
    create_file(tmp_path, "scripts/openai_agent_cli.py")
    create_file(tmp_path, "scripts/milestone_auditor.py")
    create_file(tmp_path, "Dockerfile")
    create_file(tmp_path, "docker-compose.yml")

    report = autonomous_audit.audit_repo(tmp_path)

    assert report["ready_for_autonomous_dev"] is False
    assert report["summary"]["consistency_issues"] == 2


def test_audit_repo_reports_missing_schema_admin_for_m15_focus(tmp_path: Path, monkeypatch):
    create_file(tmp_path, "docs/product_design.md")
    create_file(tmp_path, "docs/architecture.md")
    create_file(tmp_path, "docs/codex_guardrails.md")
    create_file(tmp_path, "docs/implementation_plan.md", "## M15 Supabase schema and persistence hardening\nStatus: `in_progress`\n")
    create_file(
        tmp_path,
        "docs/project_brain.md",
        "- current active milestone is `M15`\n",
    )
    create_file(tmp_path, "docs/autonomous_dev_loop.md")
    create_file(tmp_path, "docs/definition_of_done.md")
    create_file(tmp_path, "docs/agents/controller_agent.md")
    create_file(tmp_path, "docs/agents/prework_agent.md")
    create_file(tmp_path, "docs/agents/planner_agent.md")
    create_file(tmp_path, "docs/agents/builder_agent.md")
    create_file(tmp_path, "docs/agents/reviewer_agent.md")
    create_file(tmp_path, "docs/agents/qa_agent.md")
    create_file(tmp_path, "docs/agents/closeout_auditor_agent.md")
    create_file(tmp_path, "docs/agents/backfill_auditor_agent.md")
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n")
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": "M15"}))
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps({"milestones": [{"id": "M15", "title": "Supabase schema and persistence hardening", "status": "in_progress", "dependencies": [], "verify": []}]}),
    )
    create_file(tmp_path, "runs/run_history.json", "[]")
    create_file(tmp_path, "config/pipeline_config.json", "{}")
    create_file(tmp_path, "supabase/core_persistence_schema.sql")
    create_file(tmp_path, "tools/tool_registry.json", json.dumps({"tools": []}))
    create_file(tmp_path, "tools/supabase/tool_spec.json", json.dumps({"id": "supabase"}))
    create_file(tmp_path, "tools/supabase/cli.py")
    create_file(tmp_path, "scripts/verify_project.sh")
    create_file(tmp_path, "scripts/run_autonomous_cycle.sh")
    create_file(tmp_path, "scripts/local_agent_runner.py")
    create_file(tmp_path, "scripts/openai_agent_cli.py")
    create_file(tmp_path, "scripts/milestone_auditor.py")
    create_file(tmp_path, "Dockerfile")
    create_file(tmp_path, "docker-compose.yml")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setattr(autonomous_audit.shutil, "which", lambda command: None)

    report = autonomous_audit.audit_repo(tmp_path)

    assert report["ready_for_autonomous_dev"] is False
    assert any("schema-admin access" in issue for issue in report["consistency_issues"])


def create_file(root: Path, relative_path: str, contents: str = "") -> None:
    """Write a file relative to a temp repo root."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
