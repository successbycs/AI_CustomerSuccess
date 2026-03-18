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
- container proof script: `scripts/prove_container_autonomous_loop.sh`
- audit script: `scripts/autonomous_audit.py`
- milestone audit runner: `scripts/milestone_auditor.py`
- OpenAI CLI adapter: `scripts/openai_agent_cli.py`
- tool registry: `tools/tool_registry.json`

## Current Operating Assumptions

- milestone order is controlled by `milestone_registry.json`
- `current_focus` in `project_state.json` is the active milestone for controller commands
- `controller_policy` in `project_state.json` controls same-milestone retry limits and stop conditions
- `delegation_policy` in `project_state.json` controls delegated task contracts, write-scope requirements, and default serial execution
- milestone closure requires verification plus recorded review and QA outcomes
- milestone completion should trigger the `Closeout Auditor`, which appends one audit entry to `docs/audit/audit.md`
- historical audit gaps are filled by the manual `Backfill Auditor`
- `AUTONOMOUS_AGENT_RUNNER` is optional; without it, `scripts/local_agent_runner.py` generates structured local role packets for planner, builder, reviewer, and QA
- `AUTONOMOUS_AGENT_CLI` can point at a local AI CLI that reads JSON from stdin and returns JSON on stdout; the repo-native runner will capture that structured result
- `scripts/openai_agent_cli.py` is the default repo-native example for wiring the control plane to the OpenAI API
- `M13B` is complete; `M13C` is also complete
- current active milestone is `M18`
- `supabase/core_persistence_schema.sql` is now the repo-owned schema contract for the core Supabase tables used by exports, candidate persistence, and run tracking
- `M13C` defines the reusable repo pattern for `tools/`, tool registry schema, role-based tool access, and the first `tools/supabase/` capability layer
- `M13D` is the follow-on capability milestone that makes the Supabase tool executable through direct repo-owned access
- role packets should include declared tools for the current milestone and role when the registry is present
- normal product runs are expected to use LLM extraction by default when configuration is valid; deterministic extraction is the resilience fallback and should remain visible to operators when used

## Known Gaps

- several milestone verification steps still require manual/runtime checks
- container and devcontainer parity are now proven through the rebuilt Docker image and a devcontainer-equivalent workspace run
- `M07` is complete again, and the live persistence schema is now aligned through `M15`
- the repo now has a tool registry and executable `tools/supabase/` capability layer, and direct schema-admin access is available through the configured database URL
- `M15` is complete; focus has returned to the product milestones starting with `M08`
- `M08` is complete; the public directory dataset is non-empty again under live Supabase-backed runs, and focus has advanced to `M09`
- `M09` is complete; the admin UI, JSON visibility endpoints, and include/exclude operator actions are all proven against the live stack
- `M10` is complete; run tracking and both scheduler smoke paths are now proven from the current environment
- `M14` is complete; the container image and devcontainer-equivalent workspace both pass the full test suite
- `M16` is complete; a fresh runtime pass regenerated outputs, served the preview surfaces, and kept warnings visible instead of silent
- `M18` is now the active product milestone for richer vendor intelligence: buyer ICP, structured case studies, leadership/contact metadata, categorized integrations, stronger field normalization, and a Gainsight-style superset vendor schema contract
- `M19` is queued after `M18` to persist role-based Google/GEO query sets and ranked vendor visibility results by buyer persona
- `M20` through `M31` now capture the next product expansion arc: structured case studies, leadership/contact intelligence, canonical identity validation, buyer search intent, lead-magnet conversion, code-owned editorial governance, multi-product modeling, integration taxonomy, render proof, proof artifact persistence, external enrichment connectors, and help-center detection
- `M32` is reserved for the change/update/enhancement pipeline and a dedicated `Solution Enhancement` agent so future requests enter the milestone system cleanly
- the controller now distinguishes actionable retryable failures from external blockers instead of stopping at generic verification failure
