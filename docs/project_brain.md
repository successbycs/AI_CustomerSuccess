# Project Brain

This file is a short operational memory for the repository. It should stay concise and current.

## System Identity

- repository: `AI_CustomerSuccess`
- product type: vendor-first AI Customer Success intelligence pipeline
- canonical persistence: Supabase
- public serving layer: exported JSON artifacts
- internal operator layer: admin/API plus fallback artifacts when persistence is unavailable

## Active Runtime Surfaces

- primary pipeline config: `config/pipeline_config.json`
- scheduler config: `config/scheduler.toml`
- milestone plan: `docs/implementation_plan.md`
- autonomous loop definition: `docs/autonomous_dev_loop.md`
- local controller state: `project_state.json`, `milestone_registry.json`, `runs/run_history.json`

## Autonomous Control Plane

- controller CLI: `scripts/autonomous_controller.py`
- cycle wrapper: `scripts/run_autonomous_cycle.sh`
- repo-native role runner: `scripts/local_agent_runner.py`
- verification script: `scripts/verify_project.sh`
- audit script: `scripts/autonomous_audit.py`

## Current Operating Assumptions

- milestone order is controlled by `milestone_registry.json`
- `current_focus` in `project_state.json` is the active milestone for controller commands
- milestone closure requires verification plus recorded review and QA outcomes
- `AUTONOMOUS_AGENT_RUNNER` is optional; without it, `scripts/local_agent_runner.py` generates structured local role packets for planner, builder, reviewer, and QA

## Known Gaps

- several milestone verification steps still require manual/runtime checks
- container and devcontainer parity are not yet fully proven
- persistence hardening and full end-to-end runtime validation are still open milestones
