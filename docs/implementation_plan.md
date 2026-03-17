# Implementation Plan

This plan reflects the actual state of the repository as of March 17, 2026. It is not the original starter-pack milestone list copied forward unchanged. The first half of the system is already implemented; the remaining milestones focus on consolidation, hardening, repeatability, and launch readiness.

## Status Legend

- `not_started`
- `in_progress`
- `blocked`
- `complete`

Evidence rule:

- If a milestone is not fully proven by implementation evidence, test evidence, and the required verification checks, it must not be marked `complete`
- If completion is uncertain, prefer `not_started` or `in_progress` over `complete`
- If acceptance criteria are not adequately covered by automated tests, the missing tests must be added before the milestone can be marked `complete`, unless the milestone explicitly defines a manual-only check

## Current Snapshot

Implemented so far:

- Discovery pipeline and candidate normalization
- Two-phase discovery -> enrichment flow
- Bounded website exploration and page text extraction
- Deterministic vendor intelligence extraction
- Optional LLM enrichment with safe merge behavior
- Directory relevance scoring and include/exclude decisions
- Supabase persistence plus local fallback artifacts
- Google Sheets export and operator review exports
- Static directory listing and vendor profile pages
- Read-only admin API plus operator actions
- Run tracking, local review artifacts, and scheduler entrypoints
- Dockerfile and docker-compose scaffolding

Partially complete or still needing hardening:

- Config source-of-truth is still split across runtime surfaces, even though the docs now describe that split consistently
- Supabase schema assumptions are not fully hardened against drift
- Verification now has a repo-native script, but several milestone-specific runtime checks are still manual
- Docker/devcontainer workflow is not yet a fully verified autonomous runtime
- Launch readiness criteria are not yet locked down

## Milestones

## M01 Discovery foundation
Status: `complete`

Objective:
Maintain a reliable discovery layer that turns search results into normalized vendor candidates.

Acceptance criteria:
- Search-driven discovery returns normalized candidate domains
- Junk domains and obvious non-vendor results are filtered
- Candidate metadata is preserved for later enrichment

Verification:
- `.venv/bin/python -m pytest tests/test_apify_sources.py tests/test_discovery_config.py tests/test_web_search.py`

## M02 Two-phase candidate -> enrichment pipeline
Status: `complete`

Objective:
Keep discovery and enrichment explicitly separated, with candidate status tracking between them.

Acceptance criteria:
- Discovery produces candidate records and statuses
- Enrichment consumes queued domains instead of redoing discovery logic
- Candidate records can be reviewed outside the in-memory pipeline

Verification:
- `.venv/bin/python -m pytest tests/test_discovery_runner.py tests/test_discovery_store.py tests/test_enrichment_runner.py tests/test_mvp_pipeline.py`

## M03 Bounded website exploration
Status: `complete`

Objective:
Explore a small, high-value set of internal vendor pages without turning the system into an open crawl.

Acceptance criteria:
- Site exploration stays on-domain
- Priority page types are recognized
- Exploration remains bounded by configured limits

Verification:
- `.venv/bin/python -m pytest tests/test_site_explorer.py tests/test_vendor_fetcher.py`

## M04 Deterministic extraction baseline
Status: `complete`

Objective:
Ensure the system can build useful vendor profiles without any LLM dependency.

Acceptance criteria:
- Deterministic extraction populates structured vendor intelligence
- Lifecycle stages remain Python-owned and deterministic
- Vendor profile assembly works without LLM output

Verification:
- `.venv/bin/python -m pytest tests/test_page_text_extractor.py tests/test_vendor_intel_extraction.py tests/test_vendor_profile_builder.py`

## M05 Optional LLM enrichment and safe merge
Status: `complete`

Objective:
Use LLM enrichment as a bounded enhancement layer rather than a dependency for system correctness.

Acceptance criteria:
- LLM extraction is optional
- Malformed or empty LLM output does not break the pipeline
- Deterministic values are not silently weakened by LLM output

Verification:
- `.venv/bin/python -m pytest tests/test_llm_extractor.py tests/test_merge_results.py`

## M06 Directory relevance scoring
Status: `complete`

Objective:
Separate true directory-fit vendors from adjacent or non-core results.

Acceptance criteria:
- `directory_fit`, `directory_category`, and `include_in_directory` are populated
- Relevance remains deterministic and reviewable

Verification:
- `.venv/bin/python -m pytest tests/test_vendor_profile_builder.py tests/test_directory_relevance.py`

## M07 Review and public export artifacts
Status: `complete`

Objective:
Produce stable artifacts for operators and the public directory from the pipeline output.

Acceptance criteria:
- `outputs/directory_dataset.json` is generated
- `outputs/vendor_review_dataset.json` is generated
- `outputs/vendor_review.html` is generated
- CSV export remains available for Sheets-oriented workflows

Verification:
- `.venv/bin/python -m pytest tests/test_directory_dataset.py tests/test_vendor_review_dataset.py tests/test_google_sheets.py`
- `.venv/bin/python scripts/export_directory_dataset.py`

## M08 Public directory experience
Status: `not_started`

Objective:
Render a static listing page and vendor profile page from exported data.

Acceptance criteria:
- Listing page renders real dataset rows
- Vendor detail page resolves a vendor from the exported dataset
- Filter and browse behavior works without a frontend framework

Verification:
- `.venv/bin/python -m pytest tests/test_directory_dataset.py`
- Local preview check of `landing.html` and `vendor.html`

## M09 Admin visibility and operator actions
Status: `not_started`

Objective:
Give operators read access to candidates, vendors, and runs, plus safe include/exclude/rerun controls.

Acceptance criteria:
- Admin API exists
- Admin page renders JSON-backed tables
- Operator actions are wired through explicit admin actions
- Local fallback artifacts keep the admin view usable when persistence is incomplete

Verification:
- `.venv/bin/python -m pytest tests/test_admin_api.py tests/test_admin_actions.py tests/test_admin_update_vendor.py tests/test_run_store.py`

## M10 Run tracking and scheduled operation hardening
Status: `not_started`

Objective:
Make repeated execution and operational run history reliable enough for unattended use.

Acceptance criteria:
- Run records persist consistently
- Scheduler jobs use the same runtime assumptions as manual runs
- Discovery and digest jobs are both smoke-tested from the current codebase

Verification:
- `.venv/bin/python -m pytest tests/test_scheduler.py tests/test_run_store.py tests/test_mvp_pipeline.py`
- `.venv/bin/python -m services.pipeline.scheduler --run-now discovery`
- `.venv/bin/python -m services.pipeline.scheduler --run-now digest`

## M11 Documentation and config source-of-truth alignment
Status: `complete`

Objective:
Make the docs describe the runtime that actually exists, and make config ownership unambiguous.

Acceptance criteria:
- Product, architecture, README, and autonomous docs agree on current system state
- Active config files are clearly identified
- Transitional config surfaces are called out explicitly instead of implied to be complete

Verification:
- Manual doc review across `README.md`, `docs/product_design.md`, `docs/architecture.md`, `docs/codex_guardrails.md`, `docs/autonomous_dev_loop.md`, `docs/autonomous_kickoff_prompt.md`, `docs/agents/*.md`, `docs/website/ops-console.html`, `config/pipeline_config.json`, and `config/scheduler.toml`

## M12 Autonomous development control plane
Status: `complete`

Objective:
Add repo-native milestone control docs and prompts so autonomous work can proceed against the real repo state.

Acceptance criteria:
- Repo-native implementation plan exists
- Repo-native autonomous loop doc exists
- Repo-native kickoff prompt exists
- Controller, planner, builder, reviewer, and QA prompts exist under `docs/agents/`

Verification:
- Read `docs/implementation_plan.md`
- Read `docs/autonomous_dev_loop.md`
- Read `docs/autonomous_kickoff_prompt.md`
- Read `docs/agents/*.md`

## M12A Autonomous controller pipeline bootstrap
Status: `complete`

Objective:
Bootstrap the local controller runtime so the autonomous loop has executable state, subprocess entrypoints, and run-history plumbing.

Acceptance criteria:
- `project_state.json` exists and reflects the current repo milestone focus
- `milestone_registry.json` exists and mirrors the implementation plan at a practical level
- `scripts/run_autonomous_cycle.sh` exists and chains the local controller checks through subprocess execution
- Planner and controller prompt docs exist under `docs/agents/`
- The local cycle bootstrap explains the boundary between prompt docs and an optional local AI runner
- Reviewer and QA outcomes can be recorded before milestone closure

Verification:
- `.venv/bin/python scripts/autonomous_audit.py`
- `.venv/bin/python scripts/autonomous_controller.py status`
- `.venv/bin/python scripts/autonomous_controller.py next`
- `bash scripts/run_autonomous_cycle.sh`

## M13 Milestone-close verification script
Status: `complete`

Objective:
Replace ad hoc verification with a repeatable script that confirms milestone-close health.

Acceptance criteria:
- `scripts/verify_project.sh` exists
- Script runs the core checks expected at milestone close
- Script exits non-zero when key checks fail

Verification:
- `bash scripts/verify_project.sh`

## M14 Container and devcontainer parity
Status: `not_started`

Objective:
Ensure autonomous execution can run in a clean containerized environment rather than depending on local machine drift.

Acceptance criteria:
- Dockerfile is verified against current repo commands
- Devcontainer config exists and is usable
- Core build, test, and pipeline commands run inside the container

Verification:
- `docker build -t ai-customer-success .`
- `docker run --rm ai-customer-success python -m pytest`

## M15 Supabase schema and persistence hardening
Status: `not_started`

Objective:
Move from fallback-tolerant behavior to schema-consistent persistence behavior for the core operator paths.

Acceptance criteria:
- Required tables and columns are documented and verified
- Persistence code degrades safely when unavailable
- Admin and export behavior no longer depends on seeded demo artifacts to appear populated

Verification:
- `.venv/bin/python scripts/check_supabase.py`
- Targeted persistence and admin tests

## M16 End-to-end runtime hardening
Status: `not_started`

Objective:
Validate that a real run produces coherent outputs, pages, and admin views without manual patching between steps.

Acceptance criteria:
- Pipeline run produces fresh outputs for directory, review, and run snapshots
- Landing, vendor, review, and admin surfaces all render from generated data
- Failure paths are visible rather than silent

Verification:
- `.venv/bin/python scripts/run_pipeline.py`
- Local preview checks of `landing.html`, `vendor.html`, `admin.html`, and `outputs/vendor_review.html`

## M17 Internal launch readiness
Status: `not_started`

Objective:
Define the project as done for internal launch, not just feature-complete in code.

Acceptance criteria:
- All prior milestones are complete
- Verification script passes
- Operators can inspect, rerun, and override vendor records
- Docs accurately describe system behavior and operational caveats
- Known launch blockers are either closed or explicitly accepted

Verification:
- Full milestone-close review
- Full test suite
- End-to-end runtime and operator walkthrough

## Milestone Selection Rule

Autonomous work should follow this order:

1. If any milestone is `in_progress`, finish the lowest-numbered `in_progress` milestone first.
2. Otherwise, complete the lowest-numbered `not_started` milestone.
3. Do not mark a milestone `complete` until its acceptance criteria and verification steps have both been satisfied.

## Completion Rule

A milestone is only truly complete when:

- the implementation exists in the repo
- the docs reflect the implementation accurately
- relevant tests pass
- changed behavior is covered by adequate automated tests
- milestone verification succeeds
- a passing review result is recorded when the milestone is closed through the local controller
- a passing QA result is recorded when the milestone is closed through the local controller
- no unresolved blocker remains hidden behind fallback behavior
- if any required proof is missing or uncertain, the milestone remains `not_started`, `in_progress`, or `blocked`
