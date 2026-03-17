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
- identify dependencies, blockers, and proof requirements
- name the code, docs, config, and tests likely to be touched
- define the verification commands and runtime/manual checks required to close the milestone
- identify any missing tests that should be created during the builder step

Return:

- selected milestone
- scope summary
- dependencies and blockers
- files likely to change
- tests to add or update
- verification plan
- risks that must be watched during implementation
