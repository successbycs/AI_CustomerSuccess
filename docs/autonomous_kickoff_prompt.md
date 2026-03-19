# Autonomous Kickoff Prompt

Use this prompt to start or resume the autonomous milestone loop for this repo.

For local orchestration, pair this prompt with:

- `scripts/autonomous_controller.py`
- `scripts/run_autonomous_cycle.sh`
- `scripts/verify_project.sh`

```text
Read first:
- docs/product_design.md
- docs/architecture.md
- docs/codex_guardrails.md
- docs/implementation_plan.md
- README.md
- config/pipeline_config.json
- config/scheduler.toml

Task:
Inspect the current repo first, then continue the autonomous milestone loop.

Milestone selection rule:
1. If any milestone in docs/implementation_plan.md is marked in_progress, continue the lowest-numbered in_progress milestone.
2. Otherwise, select the lowest-numbered not_started milestone.
3. Do not skip ahead unless explicitly instructed by the human.

Execution rules:
- Start each milestone iteration with the repo prework role so the planner and builder receive a current gap map and verification-focused prep context.
- Keep changes bounded to the selected milestone.
- Update any docs made stale by the implementation before closing the milestone.
- Add or update tests whenever behavior changes.
- If existing tests do not prove the milestone acceptance criteria, create the missing tests before closing the milestone.
- Respect docs/codex_guardrails.md.
- Do not mark a milestone complete unless acceptance criteria are implemented, tests pass, verification succeeds, and any required runtime/manual checks have been run.
- If any acceptance criterion is not proven, leave the milestone as in_progress or not_started and say exactly what is still unverified.
- If verification fails but the failure is actionable within the current milestone, keep iterating inside the same milestone instead of stopping at status reporting.
- Only stop retrying when the issue is an external blocker, a required manual check, a destructive action, a product-scope decision, or the retry limit is reached.
- If the current milestone is blocked by a missing reusable capability, create one minimal capability milestone, add it to both docs/implementation_plan.md and milestone_registry.json, complete it, then resume the blocked parent milestone.
- For tool-access blockers, implement the missing capability through the repo tool pattern under tools/ instead of ad hoc access.
- Use direct repo-owned access for declared tools instead of adding ad hoc execution paths.
- When tools are declared in the repo registry, roles may use those tools only through the controller-governed access model.

Run:
- relevant tests
- new or updated tests required to prove changed behavior
- milestone-specific verification commands
- runtime/manual checks when the milestone involves UI, admin, scheduler, container, or operator workflows

Return:
- selected milestone
- summary of changes
- changed files
- test results
- verification results
- runtime/manual checks run
- verified items
- not verified items
- deferred checks
- risks
- recommended next milestone
- final milestone status: complete, in_progress, or blocked
```
