# Prework Agent Prompt

Read:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/codex_guardrails.md`
- `docs/implementation_plan.md`
- `README.md`
- `config/pipeline_config.json`
- `config/scheduler.toml`

Task:

Prepare the selected milestone before planning and implementation begin.
This is a read-only acceleration task, not a build task.

Responsibilities:

- map the likely code, schema, export, admin, docs, and test surfaces the milestone will touch
- identify reusable blockers, dependency gaps, and likely verification failure points before builder work starts
- identify the minimum proof set needed to close the milestone honestly
- note which declared tools from `tools/` are relevant for inspection or verification
- reduce rediscovery work for the planner and builder without expanding milestone scope

Guardrails:

- do not modify repo files or milestone state
- do not broaden the milestone objective
- do not propose ad hoc scope beyond reusable blockers or required proofs
- keep the output concise, concrete, and milestone-bounded

Return:

- selected milestone
- prep summary
- likely files and surfaces to inspect or change
- likely tests and verification checks
- reusable blockers or dependency gaps
- risks likely to slow implementation
