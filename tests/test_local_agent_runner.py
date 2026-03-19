"""Tests for the repo-native local agent runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

from scripts import local_agent_runner


def test_local_agent_runner_generates_packet_and_history(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("AUTONOMOUS_AGENT_CLI", raising=False)
    monkeypatch.setenv("AUTONOMOUS_CYCLE_ID", "cycle-test")
    create_file(tmp_path, "docs/agents/planner_agent.md", "# Planner Agent Prompt\n\nRead:\n- `docs/implementation_plan.md`\n")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M08 Public directory experience\nStatus: `not_started`\n\nObjective:\nTest objective\n",
    )
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": "M08"}))
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M08",
                        "title": "Public directory experience",
                        "status": "not_started",
                        "dependencies": [],
                        "verify": ["pytest tests/test_directory_dataset.py"],
                    }
                ]
            }
        ),
    )
    create_file(tmp_path, "runs/run_history.json", "[]")

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/planner_agent.md",
        milestone_id="M08",
        changed_files=["docs/website/vendor.html"],
        artifact_paths=["outputs/directory_dataset.json"],
    )

    output_path = tmp_path / "runs/agent_outputs/test_packet.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet), encoding="utf-8")
    local_agent_runner.append_history_entry(tmp_path, packet, output_path)

    history = json.loads((tmp_path / "runs/run_history.json").read_text(encoding="utf-8"))
    assert packet["role"] == "planner"
    assert packet["producer_role"] == "planner"
    assert packet["phase"] == "planner"
    assert packet["backend"] == "repo_native_packet"
    assert packet["model"] is None
    assert packet["cycle_id"] == "cycle-test"
    assert packet["delegation_contract"]["task_id"] == "cycle-test:M08:planner"
    assert packet["delegation_contract"]["execution_mode"] == "read_only"
    assert packet["delegation_contract"]["write_scope"] == []
    assert packet["milestone"]["id"] == "M08"
    assert packet["changed_files"] == ["docs/website/vendor.html"]
    assert packet["artifact_checks"][0]["exists"] is False
    assert packet["autonomy_state"]["recommended_next_action"] == "start_iteration"
    assert history[-1]["action"] == "agent_output"
    assert history[-1]["role"] == "planner"
    assert history[-1]["producer_role"] == "planner"
    assert history[-1]["phase"] == "planner"
    assert history[-1]["backend"] == "repo_native_packet"
    assert history[-1]["cycle_id"] == "cycle-test"
    assert history[-1]["task_id"] == "cycle-test:M08:planner"
    assert history[-1]["execution_mode"] == "read_only"
    assert history[-1]["write_scope"] == []


def test_local_agent_runner_uses_configured_cli(monkeypatch, tmp_path: Path):
    create_file(tmp_path, "docs/agents/reviewer_agent.md", "# Reviewer Agent Prompt\n\nRead:\n- `docs/implementation_plan.md`\n")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M08 Public directory experience\nStatus: `not_started`\n\nObjective:\nTest objective\n",
    )
    create_file(
        tmp_path,
        "project_state.json",
        json.dumps({"current_focus": "M08", "agent_runner": {}}),
    )
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M08",
                        "title": "Public directory experience",
                        "status": "not_started",
                        "dependencies": [],
                        "verify": ["pytest tests/test_directory_dataset.py"],
                    }
                ]
            }
        ),
    )
    create_file(tmp_path, "runs/run_history.json", "[]")

    captured: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        if kwargs.get("input") is None:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        captured["input"] = kwargs["input"]
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"status": "pass", "summary": "review ok", "issues": []}),
            stderr="",
        )

    monkeypatch.setattr(local_agent_runner.subprocess, "run", fake_run)
    monkeypatch.setenv("AUTONOMOUS_AGENT_CLI", ".venv/bin/python scripts/openai_agent_cli.py --model gpt-5.4")

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/reviewer_agent.md",
        milestone_id="M08",
        changed_files=[],
        artifact_paths=[],
    )

    assert packet["runner_mode"] == "external_local_ai_cli"
    assert packet["result"]["status"] == "pass"
    assert packet["backend"] == "openai"
    assert packet["model"] == "gpt-5.4"
    assert json.loads(captured["input"])["role"] == "reviewer"


def test_local_agent_runner_adds_repo_changes_artifacts_and_history(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("AUTONOMOUS_AGENT_CLI", raising=False)
    create_file(tmp_path, "docs/agents/qa_agent.md", "# QA Agent Prompt\n\nRead:\n- `docs/implementation_plan.md`\n")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M13B Autonomous execution backend integration\nStatus: `in_progress`\n\nObjective:\nTest objective\n",
    )
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": "M13B", "agent_runner": {}}))
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M13B",
                        "title": "Autonomous execution backend integration",
                        "status": "in_progress",
                        "dependencies": [],
                        "verify": ["bash scripts/verify_project.sh"],
                    }
                ]
            }
        ),
    )
    create_file(
        tmp_path,
        "runs/run_history.json",
        json.dumps(
            [
                {
                    "timestamp": "2026-03-17T00:00:00+00:00",
                    "action": "verify",
                    "milestone": "M13B",
                    "command": "bash scripts/verify_project.sh",
                    "exit_code": 0,
                    "success": True,
                    "note": "verification passed",
                }
            ]
        ),
    )
    create_file(tmp_path, "scripts/local_agent_runner.py", "print('runner')\n")
    create_file(tmp_path, "scripts/openai_agent_cli.py", "print('adapter')\n")
    create_file(tmp_path, "scripts/run_autonomous_cycle.sh", "#!/usr/bin/env bash\n")
    create_file(tmp_path, "scripts/prove_container_autonomous_loop.sh", "#!/usr/bin/env bash\n")
    create_file(tmp_path, "milestone_registry.json", (tmp_path / "milestone_registry.json").read_text(encoding="utf-8"))

    monkeypatch.setattr(
        local_agent_runner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=" M README.md\n?? scripts/openai_agent_cli.py\n?? runs/agent_outputs/generated.json\n", stderr=""),
    )

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/qa_agent.md",
        milestone_id="M13B",
        changed_files=[],
        artifact_paths=[],
        cli_command=None,
    )

    assert "README.md" in packet["changed_files"]
    assert "scripts/openai_agent_cli.py" in packet["changed_files"]
    assert all(not item.startswith("runs/") for item in packet["changed_files"])
    assert any(item["path"] == "scripts/openai_agent_cli.py" for item in packet["artifact_checks"])
    assert packet["history_evidence"]["verify"]["success"] is True


def test_local_agent_runner_includes_retry_state_from_failed_verify(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("AUTONOMOUS_AGENT_CLI", raising=False)
    create_file(tmp_path, "docs/agents/planner_agent.md", "# Planner Agent Prompt\n\nRead:\n- `docs/implementation_plan.md`\n")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M08 Public directory experience\nStatus: `in_progress`\n\nObjective:\nTest objective\n",
    )
    create_file(
        tmp_path,
        "project_state.json",
        json.dumps(
            {
                "current_focus": "M08",
                "controller_policy": {"max_same_milestone_retries": 2},
            }
        ),
    )
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M08",
                        "title": "Public directory experience",
                        "status": "in_progress",
                        "dependencies": [],
                        "verify": ["pytest tests/test_directory_dataset.py"],
                    }
                ]
            }
        ),
    )
    create_file(
        tmp_path,
        "runs/run_history.json",
        json.dumps(
            [
                {
                    "timestamp": "2026-03-17T00:00:00+00:00",
                    "action": "verify",
                    "milestone": "M08",
                    "command": "pytest tests/test_directory_dataset.py",
                    "exit_code": 1,
                    "success": False,
                    "note": "artifact assertions failed",
                    "manual_checks_pending": [],
                    "artifact_assertions": [
                        {"path": "outputs/directory_dataset.json", "success": False, "error": "empty json payload"}
                    ],
                    "commands": [{"stdout": "", "stderr": ""}],
                }
            ]
        ),
    )

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/planner_agent.md",
        milestone_id="M08",
        changed_files=[],
        artifact_paths=[],
    )

    assert packet["autonomy_state"]["recommended_next_action"] == "retry_same_milestone"
    assert packet["autonomy_state"]["retry_count"] == 1


def test_local_agent_runner_includes_declared_tools_for_role(tmp_path: Path):
    create_file(tmp_path, "docs/agents/builder_agent.md", "# Builder Agent Prompt\n\nRead:\n- `docs/implementation_plan.md`\n")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M13C Tool registry and tool-access components\nStatus: `in_progress`\n\nObjective:\nTest objective\n",
    )
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": "M13C"}))
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M13C",
                        "title": "Tool registry and tool-access components",
                        "status": "in_progress",
                        "dependencies": [],
                        "verify": ["pytest tests/test_local_agent_runner.py"],
                    }
                ]
            }
        ),
    )
    create_file(tmp_path, "runs/run_history.json", "[]")
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
                "description": "Supabase tool",
                "development_only": True,
                "applicable_milestones": ["M13C"],
                "source_of_truth": ["supabase/core_persistence_schema.sql"],
                "backends": [{"id": "direct_repo"}],
                "role_access": {
                    "builder": {
                        "operations": ["inspect_schema", "apply_schema"],
                        "write_allowed": True,
                        "approval_required": True,
                    }
                },
            }
        ),
    )

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/builder_agent.md",
        milestone_id="M13C",
        changed_files=[],
        artifact_paths=[],
    )

    assert packet["available_tools"][0]["id"] == "supabase"
    assert packet["available_tools"][0]["allowed_operations"] == ["inspect_schema", "apply_schema"]
    assert packet["available_tools"][0]["write_allowed"] is True
    assert packet["delegation_contract"]["execution_mode"] == "bounded_write"
    assert "tools/" in packet["delegation_contract"]["write_scope"]


def test_local_agent_runner_recognizes_auditor_roles(tmp_path: Path):
    create_file(tmp_path, "docs/agents/closeout_auditor_agent.md", "# Closeout Auditor Agent Prompt\n")
    create_file(tmp_path, "docs/implementation_plan.md", "## M17 Internal launch readiness\nStatus: `complete`\n")
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": None}))
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M17",
                        "title": "Internal launch readiness",
                        "status": "complete",
                        "dependencies": [],
                        "verify": [],
                    }
                ]
            }
        ),
    )
    create_file(tmp_path, "runs/run_history.json", "[]")

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/closeout_auditor_agent.md",
        milestone_id="M17",
        changed_files=[],
        artifact_paths=[],
    )

    assert packet["role"] == "closeout_auditor"
    assert packet["delegation_contract"]["execution_mode"] == "bounded_write"
    assert packet["delegation_contract"]["write_scope"] == ["docs/audit/audit.md"]


def test_local_agent_runner_recognizes_prework_role(tmp_path: Path):
    create_file(tmp_path, "docs/agents/prework_agent.md", "# Prework Agent Prompt\n")
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M18 Vendor intelligence schema expansion and deep enrichment\nStatus: `in_progress`\n\nObjective:\nPrep objective\n",
    )
    create_file(tmp_path, "project_state.json", json.dumps({"current_focus": "M18"}))
    create_file(
        tmp_path,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M18",
                        "title": "Vendor intelligence schema expansion and deep enrichment",
                        "status": "in_progress",
                        "dependencies": [],
                        "verify": [],
                    }
                ]
            }
        ),
    )
    create_file(tmp_path, "runs/run_history.json", "[]")

    packet = local_agent_runner.create_role_packet(
        root=tmp_path,
        prompt_path=tmp_path / "docs/agents/prework_agent.md",
        milestone_id="M18",
        changed_files=[],
        artifact_paths=[],
    )

    assert packet["role"] == "prework"
    assert packet["delegation_contract"]["execution_mode"] == "read_only"
    assert packet["delegation_contract"]["write_scope"] == []


def create_file(root: Path, relative_path: str, contents: str = "") -> None:
    """Write a file relative to a temp repo root."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents + ("\n" if contents and not contents.endswith("\n") else ""), encoding="utf-8")
