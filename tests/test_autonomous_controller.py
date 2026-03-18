"""Tests for the local autonomous development controller."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import autonomous_controller


def test_status_command_reports_focus_and_latest_run(tmp_path: Path, capsys):
    create_state_files(tmp_path)
    create_run_history(
        tmp_path,
        [
            {
                "timestamp": "2026-03-17T00:00:00+00:00",
                "action": "verify",
                "milestone": "M02",
                "command": "bash scripts/verify_project.sh",
                "exit_code": 0,
                "success": True,
                "note": "verification passed",
            }
        ],
    )

    exit_code = autonomous_controller.command_status(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Current focus: M02" in output
    assert "M01: Discovery foundation [complete]" in output
    assert "Latest run:" in output
    assert "Latest role outputs:" in output


def test_next_command_prefers_in_progress_milestone(tmp_path: Path, capsys):
    create_state_files(tmp_path)

    exit_code = autonomous_controller.command_next(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Next milestone: M02 - Two-phase pipeline" in output


def test_next_command_reports_declared_tools(tmp_path: Path, capsys):
    create_state_files(tmp_path)
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
                "applicable_milestones": ["M02"],
                "role_access": {
                    "builder": {
                        "operations": ["inspect_schema"],
                        "write_allowed": False,
                        "approval_required": False,
                    }
                },
            }
        ),
    )

    exit_code = autonomous_controller.command_next(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Tools:" in output
    assert "supabase: tools/supabase/tool_spec.json" in output


def test_next_command_reports_blocked_dependency_without_failing(tmp_path: Path, capsys):
    create_state_files(tmp_path)
    registry = load_json(tmp_path / "milestone_registry.json")
    registry["milestones"][1]["dependencies"] = ["M99"]
    create_file(tmp_path, "milestone_registry.json", json.dumps(registry))

    exit_code = autonomous_controller.command_next(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Blocked by incomplete dependencies: M99" in output


def test_verify_command_records_success(monkeypatch, tmp_path: Path, capsys):
    create_state_files(tmp_path)
    create_file(tmp_path, "scripts/verify_project.sh", "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(
        autonomous_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok\n", stderr=""),
    )

    exit_code = autonomous_controller.command_verify(tmp_path)

    output = capsys.readouterr().out
    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert "Verification passed" in output
    assert history[-1]["action"] == "verify"
    assert history[-1]["success"] is True


def test_verify_command_records_failure(monkeypatch, tmp_path: Path, capsys):
    create_state_files(tmp_path)
    create_file(tmp_path, "scripts/verify_project.sh", "#!/usr/bin/env bash\nexit 1\n")

    monkeypatch.setattr(
        autonomous_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=3, stdout="", stderr="bad\n"),
    )

    exit_code = autonomous_controller.command_verify(tmp_path)

    output = capsys.readouterr().out
    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 3
    assert "Verification failed" in output
    assert history[-1]["success"] is False
    assert history[-1]["exit_code"] == 3


def test_complete_command_updates_registry_and_focus(tmp_path: Path):
    create_state_files(tmp_path)
    monkeypatch_verify_success(tmp_path)
    autonomous_controller.command_review("M02", "pass", "review passed", tmp_path)
    autonomous_controller.command_qa("M02", "pass", "qa passed", False, [], tmp_path)
    original_trigger = autonomous_controller.trigger_closeout_audit
    autonomous_controller.trigger_closeout_audit = lambda milestone_id, root=tmp_path: {
        "status": "generated",
        "audit_path": str(root / "docs" / "audit" / "audit.md"),
        "note": "audit generated",
    }

    try:
        exit_code = autonomous_controller.command_complete("M02", tmp_path)
    finally:
        autonomous_controller.trigger_closeout_audit = original_trigger

    registry = load_json(tmp_path / "milestone_registry.json")
    project_state = load_json(tmp_path / "project_state.json")
    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert registry["milestones"][1]["status"] == "complete"
    assert project_state["current_focus"] == "M03"
    assert any(entry["action"] == "complete" for entry in history)


def test_fail_command_updates_registry_and_history(tmp_path: Path):
    create_state_files(tmp_path)

    exit_code = autonomous_controller.command_fail("M02", "verification failed", tmp_path)

    registry = load_json(tmp_path / "milestone_registry.json")
    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert registry["milestones"][1]["status"] == "blocked"
    assert history[-1]["action"] == "fail"
    assert history[-1]["note"] == "verification failed"


def test_complete_requires_verification_review_and_qa(tmp_path: Path):
    create_state_files(tmp_path)

    try:
        autonomous_controller.command_complete("M02", tmp_path)
    except RuntimeError as error:
        assert "successful verification" in str(error)
    else:
        raise AssertionError("command_complete should require verification evidence")


def test_verify_initializes_missing_run_history(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path, include_run_history=False)
    create_file(tmp_path, "scripts/verify_project.sh", "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(
        autonomous_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    autonomous_controller.command_verify(tmp_path)

    history = load_json(tmp_path / "runs" / "run_history.json")
    assert isinstance(history, list)
    assert history[-1]["action"] == "verify"
    assert history[-1]["manual_checks_pending"] == []


def test_run_cycle_reports_controller_and_prompt_sequence(tmp_path: Path, capsys):
    create_state_files(tmp_path)
    create_file(tmp_path, "docs/agents/controller_agent.md")
    create_file(tmp_path, "docs/agents/planner_agent.md")
    create_file(tmp_path, "docs/agents/builder_agent.md")
    create_file(tmp_path, "docs/agents/reviewer_agent.md")
    create_file(tmp_path, "docs/agents/qa_agent.md")

    exit_code = autonomous_controller.command_run_cycle(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Controller:" in output
    assert "Prompt sequence:" in output
    assert "Planner:" in output
    assert "QA:" in output
    assert "record review:" in output
    assert "artifact assertions:" in output


def test_run_cycle_reports_blocked_dependency_without_failing(tmp_path: Path, capsys):
    create_state_files(tmp_path)
    registry = load_json(tmp_path / "milestone_registry.json")
    registry["milestones"][1]["dependencies"] = ["M99"]
    create_file(tmp_path, "milestone_registry.json", json.dumps(registry))

    exit_code = autonomous_controller.command_run_cycle(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Blocked by incomplete dependencies: M99" in output


def test_main_reports_missing_required_files_cleanly(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(autonomous_controller, "PROJECT_ROOT", tmp_path)

    exit_code = autonomous_controller.main(["status"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Error: Required project state was not found" in output


def test_verify_records_manual_checks_pending(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path)
    registry = load_json(tmp_path / "milestone_registry.json")
    registry["milestones"][1]["verify"] = [
        "pytest tests/test_mvp_pipeline.py",
        "Local preview check of vendor.html",
    ]
    create_file(tmp_path, "milestone_registry.json", json.dumps(registry))
    create_file(tmp_path, "scripts/verify_project.sh", "#!/usr/bin/env bash\nexit 0\n")

    monkeypatch.setattr(
        autonomous_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    exit_code = autonomous_controller.command_verify(tmp_path)

    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert history[-1]["manual_checks_pending"] == ["Local preview check of vendor.html"]


def test_next_action_blocks_schema_admin_milestone_without_datastore_admin(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path)
    project_state = load_json(tmp_path / "project_state.json")
    project_state["current_focus"] = "M15"
    create_file(tmp_path, "project_state.json", json.dumps(project_state))
    registry = load_json(tmp_path / "milestone_registry.json")
    registry["milestones"][1]["id"] = "M15"
    registry["milestones"][1]["title"] = "Supabase schema and persistence hardening"
    registry["milestones"][1]["verify"] = ["python scripts/check_supabase.py"]
    create_file(tmp_path, "milestone_registry.json", json.dumps(registry))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setattr(autonomous_controller.shutil, "which", lambda command: None)

    decision = autonomous_controller.determine_next_action(tmp_path, "M15")

    assert decision["action"] == "blocked_external"
    assert "schema-admin access" in decision["reason"]


def test_verify_fails_fast_for_schema_admin_milestone_without_datastore_admin(monkeypatch, tmp_path: Path, capsys):
    create_state_files(tmp_path)
    project_state = load_json(tmp_path / "project_state.json")
    project_state["current_focus"] = "M15"
    create_file(tmp_path, "project_state.json", json.dumps(project_state))
    registry = load_json(tmp_path / "milestone_registry.json")
    registry["milestones"][1]["id"] = "M15"
    registry["milestones"][1]["title"] = "Supabase schema and persistence hardening"
    registry["milestones"][1]["verify"] = ["python scripts/check_supabase.py"]
    create_file(tmp_path, "milestone_registry.json", json.dumps(registry))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setattr(autonomous_controller.shutil, "which", lambda command: None)

    exit_code = autonomous_controller.command_verify(tmp_path)

    output = capsys.readouterr().out
    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 1
    assert "datastore preflight" in output
    assert history[-1]["action"] == "verify"
    assert history[-1]["success"] is False
    assert "schema-admin access" in history[-1]["note"]


def test_assert_artifacts_reports_results(tmp_path: Path, capsys):
    create_state_files(tmp_path)
    create_file(tmp_path, "outputs/pipeline_runs.json", json.dumps([{"run_id": "1"}]))

    exit_code = autonomous_controller.command_assert_artifacts("M10", tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Artifact assertions for M10" in output


def test_next_action_retries_same_milestone_for_actionable_verify_failure(tmp_path: Path):
    create_state_files(tmp_path)
    create_run_history(
        tmp_path,
        [
            {
                "timestamp": "2026-03-17T00:00:00+00:00",
                "action": "verify",
                "milestone": "M02",
                "command": "bash scripts/verify_project.sh",
                "exit_code": 1,
                "success": False,
                "note": "verification commands failed, artifact assertions failed",
                "manual_checks_pending": [],
                "artifact_assertions": [
                    {"path": "outputs/directory_dataset.json", "success": False, "error": "empty json payload"}
                ],
                "commands": [{"stdout": "", "stderr": ""}],
            }
        ],
    )

    decision = autonomous_controller.determine_next_action(tmp_path, "M02")

    assert decision["action"] == "retry_same_milestone"
    assert decision["failure_kind"] == "actionable_retry"
    assert decision["retry_count"] == 1


def test_next_action_stops_on_external_blocker(tmp_path: Path):
    create_state_files(tmp_path)
    create_run_history(
        tmp_path,
        [
            {
                "timestamp": "2026-03-17T00:00:00+00:00",
                "action": "verify",
                "milestone": "M02",
                "command": "bash scripts/verify_project.sh",
                "exit_code": 1,
                "success": False,
                "note": "verification commands failed",
                "manual_checks_pending": [],
                "artifact_assertions": [],
                "commands": [
                    {
                        "stdout": "",
                        "stderr": "Could not find the table 'public.pipeline_runs' in the schema cache",
                    }
                ],
            }
        ],
    )

    decision = autonomous_controller.determine_next_action(tmp_path, "M02")

    assert decision["action"] == "blocked_external"
    assert decision["failure_kind"] == "external_blocker"


def test_next_action_requests_review_and_qa_after_successful_verify(tmp_path: Path):
    create_state_files(tmp_path)
    monkeypatch_verify_success(tmp_path)

    decision = autonomous_controller.determine_next_action(tmp_path, "M02")

    assert decision["action"] == "run_review_and_qa"


def test_next_action_allows_completion_when_verify_review_and_qa_pass(tmp_path: Path):
    create_state_files(tmp_path)
    monkeypatch_verify_success(tmp_path)
    autonomous_controller.command_review("M02", "pass", "review passed", tmp_path)
    autonomous_controller.command_qa("M02", "pass", "qa passed", False, [], tmp_path)

    decision = autonomous_controller.determine_next_action(tmp_path, "M02")

    assert decision["action"] == "complete_milestone"


def test_auto_iterate_records_iteration_and_blocks_on_external_failure(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path)

    decisions = iter(
        [
            {
                "milestone": "M02",
                "action": "start_iteration",
                "reason": "no verification has been recorded yet",
                "retry_count": 0,
                "max_retries": 2,
                "failure_kind": "",
            },
            {
                "milestone": "M02",
                "action": "blocked_external",
                "reason": "missing external schema",
                "retry_count": 1,
                "max_retries": 2,
                "failure_kind": "external_blocker",
            },
        ]
    )

    monkeypatch.setattr(autonomous_controller, "determine_next_action", lambda root, milestone_id=None: next(decisions))
    monkeypatch.setattr(
        autonomous_controller,
        "run_role_phase",
        lambda root, milestone_id, role: {
            "role": role,
            "command": f"{role} {milestone_id}",
            "exit_code": 0,
            "success": True,
            "stdout": "",
            "stderr": "",
            "runner_mode": "repo_native_runner",
        },
    )
    monkeypatch.setattr(autonomous_controller, "repo_evidence", lambda root: {"changed_files": ["README.md"], "diff_stat": "1 file changed"})
    monkeypatch.setattr(autonomous_controller, "command_verify", lambda root: 1)

    exit_code = autonomous_controller.command_auto_iterate("M02", max_iterations=2, root=tmp_path)

    history = load_json(tmp_path / "runs" / "run_history.json")
    registry = load_json(tmp_path / "milestone_registry.json")
    assert exit_code == 0
    assert any(entry["action"] == "iteration_step" for entry in history)
    assert history[-1]["action"] == "fail"
    assert registry["milestones"][1]["status"] == "blocked"


def test_auto_iterate_completes_when_controller_says_complete(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path)
    monkeypatch_verify_success(tmp_path)
    autonomous_controller.command_review("M02", "pass", "review passed", tmp_path)
    autonomous_controller.command_qa("M02", "pass", "qa passed", False, [], tmp_path)
    monkeypatch.setattr(
        autonomous_controller,
        "trigger_closeout_audit",
        lambda milestone_id, root=tmp_path: {
            "status": "generated",
            "audit_path": str(root / "docs" / "audit" / "audit.md"),
            "note": "audit generated",
        },
    )

    monkeypatch.setattr(
        autonomous_controller,
        "determine_next_action",
        lambda root, milestone_id=None: {
            "milestone": "M02",
            "action": "complete_milestone",
            "reason": "ready",
            "retry_count": 0,
            "max_retries": 2,
            "failure_kind": "",
        },
    )

    exit_code = autonomous_controller.command_auto_iterate("M02", max_iterations=1, root=tmp_path)

    registry = load_json(tmp_path / "milestone_registry.json")
    assert exit_code == 0
    assert registry["milestones"][1]["status"] == "complete"


def test_complete_uses_role_output_files(tmp_path: Path):
    create_state_files(tmp_path)
    monkeypatch_verify_success(tmp_path)
    create_role_output(tmp_path, "reviewer", "M02", "pass")
    create_role_output(tmp_path, "qa", "M02", "pass")
    original_trigger = autonomous_controller.trigger_closeout_audit
    autonomous_controller.trigger_closeout_audit = lambda milestone_id, root=tmp_path: {
        "status": "generated",
        "audit_path": str(root / "docs" / "audit" / "audit.md"),
        "note": "audit generated",
    }

    try:
        exit_code = autonomous_controller.command_complete("M02", tmp_path)
    finally:
        autonomous_controller.trigger_closeout_audit = original_trigger

    assert exit_code == 0


def test_complete_triggers_closeout_audit_and_records_history(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path)
    monkeypatch_verify_success(tmp_path)
    autonomous_controller.command_review("M02", "pass", "review passed", tmp_path)
    autonomous_controller.command_qa("M02", "pass", "qa passed", False, [], tmp_path)
    monkeypatch.setattr(
        autonomous_controller,
        "trigger_closeout_audit",
        lambda milestone_id, root=tmp_path: {
            "status": "appended",
            "audit_path": str(root / "docs" / "audit" / "audit.md"),
            "note": "closeout audit generated",
        },
    )

    exit_code = autonomous_controller.command_complete("M02", tmp_path)

    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert any(entry["action"] == "complete" for entry in history)


def test_complete_syncs_implementation_plan_and_project_brain(tmp_path: Path):
    create_state_files(tmp_path)
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M01 Discovery foundation\nStatus: `complete`\n\n"
        "## M02 Two-phase pipeline\nStatus: `in_progress`\n\n"
        "## M03 Bounded website exploration\nStatus: `not_started`\n",
    )
    create_file(
        tmp_path,
        "docs/project_brain.md",
        "# Project Brain\n\n## Current Operating Assumptions\n\n- current active milestone is `M02`\n",
    )
    monkeypatch_verify_success(tmp_path)
    autonomous_controller.command_review("M02", "pass", "review passed", tmp_path)
    autonomous_controller.command_qa("M02", "pass", "qa passed", False, [], tmp_path)
    original_trigger = autonomous_controller.trigger_closeout_audit
    autonomous_controller.trigger_closeout_audit = lambda milestone_id, root=tmp_path: {
        "status": "generated",
        "audit_path": str(root / "docs" / "audit" / "audit.md"),
        "note": "audit generated",
    }

    try:
        exit_code = autonomous_controller.command_complete("M02", tmp_path)
    finally:
        autonomous_controller.trigger_closeout_audit = original_trigger

    plan_text = (tmp_path / "docs" / "implementation_plan.md").read_text(encoding="utf-8")
    brain_text = (tmp_path / "docs" / "project_brain.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "## M02 Two-phase pipeline\nStatus: `complete`" in plan_text
    assert "current active milestone is `M03`" in brain_text


def test_fail_syncs_implementation_plan_status(tmp_path: Path):
    create_state_files(tmp_path)
    create_file(
        tmp_path,
        "docs/implementation_plan.md",
        "## M01 Discovery foundation\nStatus: `complete`\n\n"
        "## M02 Two-phase pipeline\nStatus: `in_progress`\n",
    )
    create_file(
        tmp_path,
        "docs/project_brain.md",
        "# Project Brain\n\n## Current Operating Assumptions\n\n- current active milestone is `M02`\n",
    )

    exit_code = autonomous_controller.command_fail("M02", "verification failed", tmp_path)

    plan_text = (tmp_path / "docs" / "implementation_plan.md").read_text(encoding="utf-8")
    brain_text = (tmp_path / "docs" / "project_brain.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "## M02 Two-phase pipeline\nStatus: `blocked`" in plan_text
    assert "current active milestone is `M02`" in brain_text


def test_command_audit_backfill_records_history(monkeypatch, tmp_path: Path):
    create_state_files(tmp_path)
    registry = load_json(tmp_path / "milestone_registry.json")
    registry["milestones"][0]["status"] = "complete"
    registry["milestones"][1]["status"] = "complete"
    create_file(tmp_path, "milestone_registry.json", json.dumps(registry))
    create_file(tmp_path, "docs/audit/audit.md", "# Milestone Audits\n")
    monkeypatch.setattr(
        autonomous_controller.milestone_auditor,
        "unaudited_complete_milestones",
        lambda root: ["M01", "M02"],
    )
    monkeypatch.setattr(
        autonomous_controller.milestone_auditor,
        "run_audit",
        lambda root, milestone_id, mode, append=True: {
            "status": "appended",
            "audit_path": str(root / "docs" / "audit" / "audit.md"),
            "note": f"{mode} audit generated for {milestone_id}",
        },
    )

    exit_code = autonomous_controller.command_audit_backfill([], all_unaudited=True, root=tmp_path)

    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert [entry["action"] for entry in history[-2:]] == ["backfill_audit", "backfill_audit"]


def test_review_and_qa_commands_record_history(tmp_path: Path):
    create_state_files(tmp_path)
    create_file(tmp_path, "outputs/directory_dataset.json", "{}")

    review_exit = autonomous_controller.command_review("M02", "pass", "review ok", tmp_path)
    qa_exit = autonomous_controller.command_qa(
        "M02",
        "pass",
        "qa ok",
        True,
        ["outputs/directory_dataset.json"],
        tmp_path,
    )

    history = load_json(tmp_path / "runs" / "run_history.json")
    assert review_exit == 0
    assert qa_exit == 0
    assert history[-2]["action"] == "review"
    assert history[-2]["review_status"] == "pass"
    assert history[-2]["producer_role"] == "reviewer"
    assert history[-2]["phase"] == "reviewer"
    assert history[-1]["action"] == "qa"
    assert history[-1]["manual_checks_complete"] is True
    assert history[-1]["producer_role"] == "qa"
    assert history[-1]["phase"] == "qa"
    assert history[-1]["artifact_checks"][0]["exists"] is True


def test_qa_pass_rejects_missing_artifact(tmp_path: Path):
    create_state_files(tmp_path)

    try:
        autonomous_controller.command_qa(
            "M02",
            "pass",
            "qa ok",
            True,
            ["outputs/missing.json"],
            tmp_path,
        )
    except RuntimeError as error:
        assert "required artifacts are missing" in str(error)
    else:
        raise AssertionError("QA pass should fail when required artifacts are missing")


def create_state_files(root: Path, *, include_run_history: bool = True) -> None:
    """Create a minimal autonomous state model for controller tests."""
    create_file(
        root,
        "project_state.json",
        json.dumps(
            {
                "current_focus": "M02",
                "milestones": ["M01", "M02", "M03"],
                "verification_script": "scripts/verify_project.sh",
                "runtime_environment": "local",
            }
        ),
    )
    create_file(
        root,
        "milestone_registry.json",
        json.dumps(
            {
                "milestones": [
                    {
                        "id": "M01",
                        "title": "Discovery foundation",
                        "status": "complete",
                        "dependencies": [],
                        "verify": ["pytest tests/test_apify_sources.py"],
                    },
                    {
                        "id": "M02",
                        "title": "Two-phase pipeline",
                        "status": "in_progress",
                        "dependencies": ["M01"],
                        "verify": ["pytest tests/test_mvp_pipeline.py"],
                    },
                    {
                        "id": "M03",
                        "title": "Bounded website exploration",
                        "status": "not_started",
                        "dependencies": ["M02"],
                        "verify": ["pytest tests/test_site_explorer.py"],
                    },
                ]
            }
        ),
    )
    if include_run_history:
        create_run_history(root, [])


def create_run_history(root: Path, payload: list[dict[str, object]]) -> None:
    """Write a run history file for tests."""
    create_file(root, "runs/run_history.json", json.dumps(payload))


def create_file(root: Path, relative_path: str, contents: str = "") -> None:
    """Write a file relative to a temp repo root."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents + ("\n" if contents and not contents.endswith("\n") else ""), encoding="utf-8")


def load_json(path: Path):
    """Read one JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def monkeypatch_verify_success(root: Path) -> None:
    """Seed successful verification, review, and QA evidence."""
    create_run_history(
        root,
        [
            {
                "timestamp": "2026-03-17T00:00:00+00:00",
                "action": "verify",
                "milestone": "M02",
                "command": "bash scripts/verify_project.sh",
                "exit_code": 0,
                "success": True,
                "note": "verification passed",
                "manual_checks_pending": [],
            }
        ],
    )


def create_role_output(root: Path, role: str, milestone_id: str, status: str) -> None:
    """Create one structured role output file."""
    path = root / "runs" / "agent_outputs" / f"{role}_{milestone_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-03-17T00:00:00+00:00",
                "role": role,
                "milestone": {"id": milestone_id},
                "result": {"status": status, "summary": f"{role} {status}", "issues": []},
            }
        ),
        encoding="utf-8",
    )
