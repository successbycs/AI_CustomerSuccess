"""Canonical tool entrypoint for the repo-owned autonomous agent CLI."""

from __future__ import annotations

from scripts.openai_agent_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
