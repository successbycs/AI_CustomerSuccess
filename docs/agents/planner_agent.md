# Planner Agent Prompt

Read:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/codex_guardrails.md`
- `docs/implementation_plan.md`
- `README.md`
- `config/pipeline_config.json`
- `config/scheduler.toml`

Task:

Plan the selected milestone before implementation begins.
This is a planning task, not a build task.

Responsibilities:

- confirm the exact acceptance criteria for the selected milestone
- incorporate the prework role output before finalizing scope, blockers, files, tests, and verification
- identify dependencies, blockers, and proof requirements
- name the code, docs, config, and tests likely to be touched
- define the verification commands and runtime/manual checks required to close the milestone
- identify any missing tests that should be created during the builder step
- identify which declared tools from `tools/` are relevant to the milestone
- state whether the milestone needs direct repo-owned tool access and which tool operations are required
- recommend a capability milestone when a reusable missing tool or execution path is blocking the current milestone
- identify whether the delegated builder task needs a bounded write scope and whether parallel work would be unsafe

Return:

- selected milestone
- scope summary
- dependencies and blockers
- files likely to change
- tools likely to be used
- tests to add or update
- verification plan
- risks that must be watched during implementation
