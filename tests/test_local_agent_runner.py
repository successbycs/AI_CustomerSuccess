"""Tests for the repo-native local agent runner."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import local_agent_runner


def test_local_agent_runner_generates_packet_and_history(tmp_path: Path):
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
    assert packet["milestone"]["id"] == "M08"
    assert packet["changed_files"] == ["docs/website/vendor.html"]
    assert packet["artifact_checks"][0]["exists"] is False
    assert history[-1]["action"] == "agent_output"
    assert history[-1]["role"] == "planner"


def create_file(root: Path, relative_path: str, contents: str = "") -> None:
    """Write a file relative to a temp repo root."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents + ("\n" if contents and not contents.endswith("\n") else ""), encoding="utf-8")
