# Autonomous Development Loop

This document defines the repo-native milestone loop for autonomous development. It is intended to work with the actual codebase and the current implementation plan, not the original starter-pack assumptions.

## Anchor Docs

Every milestone cycle starts by reading:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/codex_guardrails.md`
- `docs/implementation_plan.md`
- `README.md`
- `config/pipeline_config.json`
- `config/scheduler.toml`

Read additional files only as needed for the selected milestone.

## Milestone Selection Rule

Use the milestone list in `docs/implementation_plan.md`.

1. If any milestone is `in_progress`, continue the lowest-numbered `in_progress` milestone.
2. Otherwise, select the lowest-numbered `not_started` milestone.
3. Do not skip ahead unless a human explicitly redirects the work.

## Five-Role Execution Pattern

### 1. Controller

The controller orchestrates the cycle.

Controller responsibilities:

- select the active milestone from the local state files
- stop early if dependencies or required state are missing
- invoke the local cycle wrapper and verification commands
- record milestone transitions and run history
- treat prompt docs as execution inputs for a local runner, not as implicit automation

### 2. Planner

The planner confirms the milestone scope before implementation starts.

Planner responsibilities:

- restate the milestone objective and acceptance criteria
- identify likely changed files, tests, and verification commands
- call out blockers, dependencies, and proof requirements
- keep the builder from drifting into adjacent milestones

### 3. Builder

The builder implements the selected milestone.

Builder responsibilities:

- inspect the current repo first
- keep changes bounded to the milestone
- update docs affected by the milestone
- add or update tests whenever the milestone changes behavior
- create missing tests when existing coverage does not prove the acceptance criteria
- run the relevant tests and verification commands
- report changed files, risks, and next step

### 4. Reviewer

The reviewer checks whether the implementation is actually aligned with the architecture and guardrails.

Reviewer responsibilities:

- review the changed files only
- compare implementation against the milestone acceptance criteria
- identify doc drift, hidden risks, and silent failure paths
- decide whether the milestone is really complete or just feature-present

### 5. QA

The QA pass verifies runtime behavior, artifacts, and failure handling.

QA responsibilities:

- run milestone-specific verification
- check runtime behavior and output artifacts
- confirm tests cover the milestone adequately
- explicitly mark pass/fail for milestone completion

## Standard Builder Prompt

Read:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/codex_guardrails.md`
- `docs/implementation_plan.md`
- `README.md`
- `config/pipeline_config.json`
- `config/scheduler.toml`

Task:

Complete the currently selected milestone from `docs/implementation_plan.md`.
Inspect the repo first.
Keep changes bounded to that milestone.
Update any docs made stale by the implementation.
Add or update tests whenever the milestone changes behavior.
If existing tests do not prove the acceptance criteria, create the missing tests before closing the milestone.
Run the milestone verification commands and relevant tests.

Return:

- summary of changes
- changed files
- verification results
- test results
- milestone status
- risks
- next recommended milestone

## Official Kickoff Prompt

Use this prompt to start or resume the autonomous loop from the current repo state:

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
- Keep changes bounded to the selected milestone.
- Update any docs made stale by the implementation before closing the milestone.
- Add or update tests whenever behavior changes.
- If existing tests do not prove the milestone acceptance criteria, create the missing tests before closing the milestone.
- Respect docs/codex_guardrails.md.
- Do not mark a milestone complete unless acceptance criteria are implemented, tests pass, verification succeeds, and any required runtime/manual checks have been run.
- If any acceptance criterion is not proven, leave the milestone as in_progress or not_started and say exactly what is still unverified.

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

## Local Execution Layer

The repo includes a local execution bootstrap for the control plane:

- `project_state.json`
- `milestone_registry.json`
- `runs/run_history.json`
- `scripts/autonomous_controller.py`
- `scripts/run_autonomous_cycle.sh`
- `scripts/verify_project.sh`
- `scripts/local_agent_runner.py`

Execution model:

- `scripts/autonomous_controller.py` manages local milestone state and verification history
- `scripts/run_autonomous_cycle.sh` chains the local controller checks via subprocess
- if `AUTONOMOUS_AGENT_RUNNER` is configured, `scripts/run_autonomous_cycle.sh` will invoke that local executable for `planner -> builder -> reviewer -> QA`
- if `AUTONOMOUS_AGENT_RUNNER` is not configured, `scripts/local_agent_runner.py` generates structured local role packets for `planner -> builder -> reviewer -> QA`
- reviewer and QA outcomes should be recorded through `scripts/autonomous_controller.py review ...` and `scripts/autonomous_controller.py qa ...`

## Post-QA Decision Rule

After the QA step:

- if verification, review, and QA have all passed, the controller may mark the milestone `complete`
- if QA identifies fixable gaps, the milestone remains `in_progress` and loops back through builder -> reviewer -> QA
- if QA identifies an unresolved blocker, the controller should mark the milestone `blocked` and stop for human review

## Standard Reviewer Prompt

Read:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/codex_guardrails.md`
- `docs/implementation_plan.md`
- the files changed for the milestone

Task:

Review the completed milestone implementation.
This is a review task, not a build task.

Check:

- architecture alignment
- guardrail compliance
- doc vs implementation mismatches
- hidden risks
- silent failure risks
- maintainability
- whether tests actually prove the milestone acceptance criteria
- whether missing automated coverage should block milestone completion

Return:

- what is strong
- what is risky
- what is incomplete
- what must change before the milestone is truly complete

## Standard QA Prompt

Read:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/codex_guardrails.md`
- `docs/implementation_plan.md`
- changed files
- relevant tests and runtime commands

Task:

Verify whether the milestone is actually complete.
This is a QA task, not a coding task.

Check:

- acceptance criteria
- verification commands
- failure handling
- test coverage and missing cases
- output artifacts
- whether automated tests cover the changed behavior well enough to support milestone completion
- whether runtime/manual checks are still required beyond the automated tests

Return:

- pass/fail assessment
- issues found
- missing tests
- whether milestone should be marked complete

## Milestone Close Rule

A milestone may be marked `complete` only when all of the following are true:

- acceptance criteria are met
- verification commands succeed
- relevant tests pass
- missing or inadequate test coverage has been addressed
- docs affected by the milestone are updated
- a passing review result is recorded
- a passing QA result is recorded
- any required manual checks have been explicitly confirmed before closure
- reviewer and QA feedback do not identify an unresolved blocker

## Doc Update Rule

When a milestone changes system behavior, the builder must update any affected docs before closing the milestone. At minimum, check:

- `README.md`
- `docs/product_design.md`
- `docs/architecture.md`
- `docs/implementation_plan.md`
- `docs/autonomous_dev_loop.md`
- `docs/autonomous_kickoff_prompt.md`
- `docs/agents/`

## Human Role

Human review should happen at milestone boundaries, not every small code change. The human decides:

- whether to accept reviewer or QA concerns as blockers
- whether to re-scope a milestone
- whether to stop, continue, or reprioritize the loop
