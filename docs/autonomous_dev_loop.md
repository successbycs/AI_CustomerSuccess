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

## Core Six-Role Execution Pattern

### 1. Prework

The prework role prepares bounded milestone context before planning and implementation.

Prework responsibilities:

- inspect the selected milestone and identify the likely schema, service, export, doc, and test surfaces
- identify reusable blockers, dependency gaps, and likely verification pain points before the planner starts
- gather read-only tool evidence when declared tools are relevant
- produce a concise prep summary that reduces rediscovery work for the planner and builder
- remain read-only and avoid changing milestone state or repo files directly

### 2. Controller

The controller orchestrates the cycle.

Controller responsibilities:

- select the active milestone from the local state files
- stop early if dependencies or required state are missing
- invoke the local cycle wrapper and verification commands
- confirm the prompt sequence for the cycle: prework -> planner -> builder -> reviewer -> QA
- record milestone transitions and run history
- treat prompt docs as execution inputs for a local runner, not as implicit automation
- classify failed verification results as actionable-internal vs external-blocker
- retry the same milestone when the failure is actionable and still inside the retry budget
- create one minimal capability milestone when a reusable missing execution capability is blocking the current milestone
- update both `docs/implementation_plan.md` and `milestone_registry.json` when a new capability milestone is required
- resume the blocked parent milestone after the capability milestone is complete
- expose declared `tools/` capabilities to roles through controller-owned packets and access rules

### 3. Planner

The planner confirms the milestone scope before implementation starts.

Planner responsibilities:

- restate the milestone objective and acceptance criteria
- incorporate the prework output before finalizing scope, files, tests, and proof
- identify likely changed files, tests, and verification commands
- call out blockers, dependencies, and proof requirements
- keep the builder from drifting into adjacent milestones
- identify whether the milestone requires declared tools from `tools/`
- use repo-owned direct tooling when a milestone needs tool access

### 4. Builder

The builder implements the selected milestone.

Builder responsibilities:

- inspect the current repo first
- keep changes bounded to the milestone
- update docs affected by the milestone
- add or update tests whenever the milestone changes behavior
- create missing tests when existing coverage does not prove the acceptance criteria
- run the relevant tests and verification commands
- report changed files, risks, and next step

### 5. Reviewer

The reviewer checks whether the implementation is actually aligned with the architecture and guardrails.

Reviewer responsibilities:

- review the changed files only
- compare implementation against the milestone acceptance criteria
- identify doc drift, hidden risks, and silent failure paths
- decide whether the milestone is really complete or just feature-present

### 6. QA

The QA pass verifies runtime behavior, artifacts, and failure handling.

QA responsibilities:

- run milestone-specific verification
- check runtime behavior and output artifacts
- confirm tests cover the milestone adequately
- explicitly mark pass/fail for milestone completion

## Post-Completion Auditors

The audit roles run after milestone completion or retrospectively across older milestones.

### Closeout Auditor

The closeout auditor runs immediately after the controller marks a milestone complete.
When an audit backend is available, the completion should stand only if the closeout audit succeeds.

Responsibilities:

- inspect the completed milestone against its latest implementation and proof
- record residual risks, weak proof, accepted caveats, and overstatements
- append a milestone-specific audit entry to `docs/audit/audit.md`
- avoid reopening the milestone by default unless a human explicitly chooses to act on the audit

### Backfill Auditor

The backfill auditor is used for older completed milestones that do not yet have an audit entry.

Responsibilities:

- assess whether the historical completion claim is still defensible
- capture stale or missing proof honestly
- append a retrospective audit entry to `docs/audit/audit.md`
- normalize the audit log without silently changing milestone status

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
- Start each implementation iteration with the prework role so the cycle has a current gap map, file-touch map, and verification plan.
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
- `scripts/openai_agent_cli.py`

Execution model:

- `scripts/autonomous_controller.py` manages local milestone state and verification history
- `scripts/autonomous_controller.py auto-iterate` is the controller-owned bounded inner loop for same-milestone retries
- `scripts/run_autonomous_cycle.sh` chains the local controller checks via subprocess
- if `AUTONOMOUS_AGENT_RUNNER` is configured, `scripts/run_autonomous_cycle.sh` will invoke that local executable for `prework -> planner -> builder -> reviewer -> QA`
- if `AUTONOMOUS_AGENT_RUNNER` is not configured, `scripts/local_agent_runner.py` generates structured local role packets for `prework -> planner -> builder -> reviewer -> QA`
- `docs/agents/prework_agent.md` defines the read-only prep phase that accelerates later roles by mapping likely changes, blockers, and proof requirements
- `M13B` is the milestone that tracks real local AI backend integration for `AUTONOMOUS_AGENT_CLI`
- `scripts/openai_agent_cli.py` is the repo-native role CLI for `AUTONOMOUS_AGENT_CLI`
- when that CLI receives a `builder` packet, it must be agentic and repo-writing rather than packet-evaluative; the current repo-native path does that by invoking `codex exec`
- `AUTONOMOUS_BUILDER_CLI` may be set when the builder should use a different backend from the read-only evaluator roles
- `M13C` is the milestone that defines the reusable `tools/` registry pattern, role-based tool access, and the first `tools/supabase/` capability
- role packets should carry a delegated task contract with task ownership, read/write mode, bounded write scope, and allowed tool ids
- reviewer and QA outcomes should be recorded through `scripts/autonomous_controller.py review ...` and `scripts/autonomous_controller.py qa ...`
- `scripts/milestone_auditor.py` runs the closeout and backfill auditors against the repo state
- `scripts/autonomous_controller.py complete ...` triggers the closeout auditor automatically after completion
- `scripts/autonomous_controller.py audit-backfill ...` is the manual path for filling audit gaps across older completed milestones
- `scripts/autonomous_controller.py assert-artifacts` checks milestone-aware artifact assertions directly from the controller
- `scripts/prove_container_autonomous_loop.sh` is the repo-native Docker proof entrypoint for the controller loop

## Post-QA Decision Rule

After the QA step:

- if verification, review, and QA have all passed, the controller may mark the milestone `complete`
- after completion, the controller should trigger the `Closeout Auditor`
- if QA identifies fixable gaps, the milestone remains `in_progress` and loops back through builder -> reviewer -> QA
- builder packets should capture post-run changed files from the actual agentic implementation pass, not only the pre-run repo diff
- if QA identifies an unresolved blocker, the controller should mark the milestone `blocked` and stop for human review

## Post-Verify Retry Rule

After the verify step:

- if verification fails and the failure is actionable within the current milestone, the controller should keep the milestone `in_progress` and route the latest failure evidence back into planner -> builder for the same milestone
- if verification fails because of an external dependency, missing credentials, missing infrastructure, or required manual validation, the controller should stop retrying and surface an explicit blocker
- datastore schema-admin milestones must run a capability preflight before deeper verification; if no DB-admin path is configured, the controller should fail fast and mark the issue as an external blocker rather than spinning on downstream symptoms
- same-milestone retries must be bounded by `project_state.json` controller policy rather than looping indefinitely
- review and QA must not silently override a failed verification result
- delegated mutating roles must not run without a declared write scope
- parallel delegated work should remain opt-in and read-only unless file ownership is explicit and non-overlapping

## Capability-Milestone Rule

When the current milestone is blocked by a missing reusable capability that is outside its proper scope:

- create exactly one new capability milestone rather than burying the work inside the blocked milestone
- keep that capability milestone minimal, reusable, and clearly dependency-linked
- add it to both `docs/implementation_plan.md` and `milestone_registry.json`
- complete the capability milestone first
- then resume the blocked parent milestone
- do not create ad hoc milestones for one-off implementation details

## Tool Registry Rule

The repo tool model should follow these rules:

- `tools/` defines reusable repo-owned tools and their specs
- agents may use tools declared in the tool registry when the controller exposes them for the current milestone and role
- tool access rules must define which roles may read, verify, or write through each tool
- direct repo-owned access is preferred
- SQL and schema files remain the source of truth when direct tool execution is used

## QA Best-Practice Behaviors

The autonomous system should include these QA-oriented behaviors:

- bounded retries with a configured retry limit per milestone
- explicit external-blocker classification for schema drift, missing credentials, network issues, permissions, and missing infrastructure
- deterministic evidence capture for every verify/review/QA step, including failure summaries and artifact assertion results
- stale-artifact awareness so old outputs are not mistaken for fresh milestone proof
- dependency re-checks before milestone completion so blocked prerequisites do not get skipped silently
- no silent fallback: fallback behavior must be logged and visible to the operator
- changed-file scope checks so a milestone retry does not drift into unrelated areas
- manual-check gating so runtime/UI/operator checks cannot be skipped by a passing test suite alone
- retry handoff context in planner packets so the planner sees the latest failed verification evidence rather than starting from a blank context
- clear stop conditions for destructive actions, product-scope changes, and external system changes that the repo cannot fix by itself

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
