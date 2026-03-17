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


def test_next_command_prefers_in_progress_milestone(tmp_path: Path, capsys):
    create_state_files(tmp_path)

    exit_code = autonomous_controller.command_next(tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Next milestone: M02 - Two-phase pipeline" in output


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

    exit_code = autonomous_controller.command_complete("M02", tmp_path)

    registry = load_json(tmp_path / "milestone_registry.json")
    project_state = load_json(tmp_path / "project_state.json")
    history = load_json(tmp_path / "runs" / "run_history.json")
    assert exit_code == 0
    assert registry["milestones"][1]["status"] == "complete"
    assert project_state["current_focus"] == "M03"
    assert history[-1]["action"] == "complete"


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
    assert history[-1]["action"] == "qa"
    assert history[-1]["manual_checks_complete"] is True
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
