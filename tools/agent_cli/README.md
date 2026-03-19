# Agent CLI Tool

This tool is the canonical tool-registry entry for the repo-owned autonomous role backend.

Entrypoints:

- canonical tool entrypoint: `tools/agent_cli/cli.py`
- current implementation source: `scripts/openai_agent_cli.py`

Behavior:

- role packets are read from stdin and one normalized JSON result is written to stdout
- OpenAI Responses is the default evaluator backend
- Codex-backed execution is available for builder and any other roles enabled through `AUTONOMOUS_AGENTIC_ROLES`

Configuration:

- `AUTONOMOUS_AGENT_CLI=".venv/bin/python tools/agent_cli/cli.py --model gpt-5.4"`
- `AUTONOMOUS_BUILDER_CLI` may override the mutating builder backend command
- `OPENAI_API_KEY` is required for the default OpenAI evaluator path
- `AUTONOMOUS_CODEX_COMMAND` may override the `codex` binary path
