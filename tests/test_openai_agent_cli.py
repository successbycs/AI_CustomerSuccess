"""Tests for the OpenAI-backed autonomous role CLI."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest

from scripts import openai_agent_cli


def test_call_openai_normalizes_responses_payload(monkeypatch):
    packet = {"role": "reviewer", "milestone": {"id": "M13B"}}

    captured: dict[str, object] = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"status":"pass","summary":"review ok","issues":[],"manual_checks_required":false,"manual_checks_complete":false}',
                            }
                        ]
                    }
                ]
            },
        )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_agent_cli.requests, "post", fake_post)

    result = openai_agent_cli.call_openai(packet, model="gpt-5.4", base_url="https://api.openai.com/v1", timeout=30)

    assert result["status"] == "pass"
    assert result["summary"] == "review ok"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "gpt-5.4"


def test_main_requires_openai_api_key(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"role": "planner"})))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = openai_agent_cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "OPENAI_API_KEY is required" in captured.err


def test_normalize_result_defaults_invalid_status():
    result = openai_agent_cli.normalize_result(
        {"status": "maybe", "summary": "work remains", "issues": ["gap detected"]}
    )

    assert result["status"] == "in_progress"
    assert result["issues"] == ["gap detected"]
