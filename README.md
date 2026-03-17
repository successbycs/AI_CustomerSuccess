# AI_CustomerSuccess

Vendor-first MVP for discovering AI-enabled Customer Success vendors, fetching their homepages, extracting lightweight vendor intelligence, and shaping the result into Google Sheets-ready rows.

## Python Setup

This project requires Python 3.12+.

Create a virtual environment and install dependencies:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The CLI loads environment variables from a local `.env` file automatically.
Google Sheets output is optional and uses `GOOGLE_SHEETS_ID` plus
`GOOGLE_SHEETS_CREDENTIALS_JSON`.

Operator-tunable settings are currently split across two active runtime surfaces:
- `config/pipeline_config.json` is the primary runtime source of truth for discovery, enrichment, directory relevance, LLM, and Google Sheets behavior
- `config/scheduler.toml` controls APScheduler timing and digest cadence

Additional TOML files currently exist under `config/` as transitional or reference artifacts. Config consolidation is still an active milestone rather than a completed part of the system.

The current default discovery depth is `max_pages_per_query = 5`.

## Run Tests

Use the local virtual environment for deterministic test runs:

```sh
.venv/bin/python -m pytest
```

## Run the Pipeline

Write Google Sheets-ready CSV output to `outputs/vendor_rows.csv`:

```sh
.venv/bin/python scripts/run_pipeline.py "ai customer success platform"
```

Run the Python-owned scheduler:

```sh
.venv/bin/python -m services.pipeline.scheduler
```

Run one scheduled job manually:

```sh
.venv/bin/python -m services.pipeline.scheduler --run-now discovery
.venv/bin/python -m services.pipeline.scheduler --run-now digest
```

Optional Supabase smoke test:

```sh
.venv/bin/python scripts/check_supabase.py
```

Integration diagnostics:

```sh
.venv/bin/python scripts/check_integrations.py
```

## MVP Flow

The current codebase follows the MVP pipeline described in `docs/product_design.md`:

1. `services/discovery/` finds vendor candidates from web search
2. `services/enrichment/` fetches vendor homepage content
3. `services/extraction/` converts homepage payloads into `VendorIntelligence`
4. `services/export/` converts vendor intelligence into Google Sheets-ready rows
5. `services/pipeline/` orchestrates the end-to-end flow

`docker-compose.yml` remains in the repo for future infrastructure work, but Docker is not required for the current Python MVP or test suite.

## Autonomous Development Docs

The repo now includes an autonomous milestone-control doc set:

- `docs/implementation_plan.md` tracks current progress and remaining milestones
- `docs/autonomous_dev_loop.md` defines the controller -> planner -> builder -> reviewer -> QA milestone loop
- `docs/autonomous_kickoff_prompt.md` provides the reusable kickoff prompt for each milestone cycle
- `docs/agents/` contains reusable prompts for the controller, planner, builder, reviewer, and QA roles
- `docs/codex_guardrails.md` defines implementation constraints for autonomous work
- `project_state.json`, `milestone_registry.json`, and `runs/run_history.json` provide local cycle state
- `scripts/autonomous_controller.py`, `scripts/run_autonomous_cycle.sh`, `scripts/local_agent_runner.py`, and `scripts/verify_project.sh` provide local execution and verification entrypoints

Common local controller commands:

```sh
.venv/bin/python scripts/autonomous_controller.py status
.venv/bin/python scripts/autonomous_controller.py next
.venv/bin/python scripts/autonomous_controller.py verify
.venv/bin/python scripts/autonomous_controller.py review M08 --status pass --note "review complete"
.venv/bin/python scripts/autonomous_controller.py qa M08 --status pass --note "qa complete" --manual-checks-complete --artifact outputs/directory_dataset.json
.venv/bin/python scripts/autonomous_controller.py complete M08
bash scripts/run_autonomous_cycle.sh
```

Before using the autonomous loop, read:

```sh
docs/product_design.md
docs/architecture.md
docs/codex_guardrails.md
docs/implementation_plan.md
README.md
config/pipeline_config.json
config/scheduler.toml
```
