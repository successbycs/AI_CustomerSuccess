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
- LLM-default enrichment with safe merge behavior and fallback tracking
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
- The autonomous control plane exists, but a real local AI backend is not yet configured and proven through the repo-native runner
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

## M05 LLM-default enrichment and safe merge
Status: `complete`

Objective:
Run LLM enrichment by default on normal pipeline executions while keeping deterministic extraction as an operator-visible resilience fallback.

Acceptance criteria:
- LLM extraction runs by default when runtime configuration is valid
- Malformed or empty LLM output does not break the pipeline
- Deterministic values are not silently weakened by LLM output
- LLM fallback or skip behavior is surfaced to operators through run-level visibility instead of failing silently

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
- `.venv/bin/python scripts/run_pipeline.py --no-serve-preview`

Current status:
- The export path is no longer blocked by stale Supabase deduplication. Live pipeline runs now rebuild a non-empty `outputs/directory_dataset.json` again.
- `M07` has been closed through controller verification, review, and QA. Follow-up concerns from the AI-engineer audit are recorded in `docs/audit/audit.md`.

## M08 Public directory experience
Status: `complete`

Objective:
Render a static listing page and vendor profile page from exported data.

Acceptance criteria:
- Listing page renders real dataset rows
- Vendor detail page resolves a vendor from the exported dataset
- Filter and browse behavior works without a frontend framework

Verification:
- `.venv/bin/python -m pytest tests/test_directory_dataset.py`
- Local preview check of `landing.html` and `vendor.html`

Current status:
- The exported `outputs/directory_dataset.json` is non-empty again under live Supabase-backed runs.
- `landing.html` and `vendor.html` are present and wired to the exported JSON dataset.
- `M08` has been closed through controller verification, review, and QA, with follow-up concerns recorded in `docs/audit/audit.md`.

## M09 Admin visibility and operator actions
Status: `complete`

Objective:
Give operators read access to candidates, vendors, and runs, plus safe include/exclude/rerun controls.

Acceptance criteria:
- Admin API exists
- Admin page renders JSON-backed tables
- Operator actions are wired through explicit admin actions
- Local fallback artifacts keep the admin view usable when persistence is incomplete

Verification:
- `.venv/bin/python -m pytest tests/test_admin_api.py tests/test_admin_actions.py tests/test_admin_update_vendor.py tests/test_run_store.py`

Current status:
- The admin UI and JSON endpoints are live through the local preview server.
- Candidate, vendor, and run visibility are backed by current data.
- A real include/exclude cycle succeeded through the admin API against a live vendor record.
- `M09` has been closed through controller verification, review, and QA.

## M10 Run tracking and scheduled operation hardening
Status: `complete`

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

Current status:
- Run records are being persisted and surfaced through the admin/runtime outputs.
- The scheduler test slice is green.
- Both discovery and digest scheduler entrypoints were executed successfully through controller verification.
- `M10` has been closed through controller verification, review, and QA.

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

## M13B Autonomous execution backend integration
Status: `complete`

Objective:
Finish the remaining autonomous setup work so the repo-native control plane can drive a real local AI-backed milestone cycle instead of packet generation alone.

Acceptance criteria:
- `scripts/local_agent_runner.py` can call a configured local AI CLI and normalize its JSON response
- `tools/agent_cli/cli.py` exists as the canonical repo-owned backend entrypoint for `AUTONOMOUS_AGENT_CLI`, with `scripts/openai_agent_cli.py` preserved as a compatibility path
- `scripts/autonomous_controller.py` uses structured reviewer and QA outputs as milestone-close evidence
- Autonomous setup artifacts are asserted through the controller for this milestone
- One supervised autonomous cycle runs through the repo-native wrapper and records structured role outputs for the active milestone
- The operator docs describe how to configure `AUTONOMOUS_AGENT_CLI` and what proof is still required before this milestone can close

Verification:
- `.venv/bin/python scripts/autonomous_audit.py`
- `.venv/bin/python -m pytest tests/test_autonomous_controller.py tests/test_local_agent_runner.py`
- `.venv/bin/python scripts/local_agent_runner.py docs/agents/planner_agent.md M13B`
- `.venv/bin/python scripts/autonomous_controller.py assert-artifacts M13B`
- Run `bash scripts/run_autonomous_cycle.sh` with `AUTONOMOUS_AGENT_CLI` configured
- Configure and run one real `AUTONOMOUS_AGENT_CLI` backend through `scripts/local_agent_runner.py`

## M14 Container and devcontainer parity
Status: `complete`

Objective:
Ensure autonomous execution can run in a clean containerized environment rather than depending on local machine drift.

Acceptance criteria:
- Dockerfile is verified against current repo commands
- Devcontainer config exists and is usable
- Core build, test, and pipeline commands run inside the container

Verification:
- `docker build -t ai-customer-success .`
- `docker run --rm ai-customer-success python -m pytest`

Current status:
- The Docker image now includes `git`, which was required for the repo-native runner tests inside a clean container.
- The rebuilt image passed the full `python -m pytest` suite.
- A devcontainer-equivalent workspace run from `/workspaces/AI_CustomerSuccess` also passed the full suite and the controller audit/status commands.
- `M14` has been closed through controller verification, review, and QA.

## M15 Supabase schema and persistence hardening
Status: `complete`

Objective:
Move from fallback-tolerant behavior to schema-consistent persistence behavior for the core operator paths, and unblock live export/runtime milestones that now fail because of schema drift.

Acceptance criteria:
- Required tables and columns are documented, versioned in the repo, and verified
- Persistence code degrades safely when unavailable
- Admin and export behavior no longer depends on seeded demo artifacts to appear populated
- The current `M07` blocker is resolved and the pipeline can persist/export without missing-table or missing-column failures on the core paths
- verification fails fast when no datastore schema-admin path is configured for this environment

Verification:
- `.venv/bin/python scripts/autonomous_controller.py status`
- `.venv/bin/python scripts/check_supabase.py`
- `.venv/bin/python scripts/autonomous_controller.py assert-artifacts M15`
- `.venv/bin/python -m pytest tests/test_check_supabase.py tests/test_persistence.py tests/test_run_store.py tests/test_discovery_store.py tests/test_enrichment_runner.py tests/test_admin_api.py tests/test_mvp_pipeline.py tests/test_directory_dataset.py tests/test_vendor_review_dataset.py`

Current status:
- The live Supabase schema contract in `supabase/core_persistence_schema.sql` has been applied to the remote project.
- `scripts/check_supabase.py` now passes against the real environment.
- Direct schema-admin access is proven through `scripts/prove_supabase_schema_access.py`.
- `M15` has been closed through controller verification, review, and QA.

## M13C Tool registry and tool-access components
Status: `complete`

Objective:
Add a repo-owned tools capability pattern for the project so agents and controller workflows can use declared tools through a stable registry and access model instead of ad hoc integrations.

Acceptance criteria:
- A `tools/` capability layer exists in the repo
- A tool registry schema exists and defines the tools available to the project plus their allowed usage
- Agents and controller workflows are wired to the `tools/` registry and explicitly told they may use declared tools
- Tool access rules define what each role may do with each tool, including write restrictions and approvals
- `tools/supabase/` exists as the first project tool
- The Supabase tool scope is documented clearly: schema inspection, schema application, schema verification, and controlled CRUD for vendors, candidates, and runs
- The tool design preserves `supabase/` SQL files as the source of truth and treats `tools/supabase/` as the execution layer
- Operator guidance explains when each tool is safe to use, what approvals are required, and what environments it may target

Verification:
- `.venv/bin/python scripts/autonomous_controller.py assert-artifacts M13C`
- `.venv/bin/python -m pytest tests/test_autonomous_audit.py tests/test_autonomous_controller.py tests/test_local_agent_runner.py`
- Review the `tools/` and `tools/supabase/` structure
- Verify the tool registry schema and tool specs are present and readable
- Verify operator docs in `README.md` and autonomous docs explain the tool boundary, role access model, and usage model
- Verify the tool contract stays aligned with `supabase/core_persistence_schema.sql`

## M13D Supabase executable tool support
Status: `complete`

Objective:
Turn the repo-owned Supabase tool from a spec-only capability into an executable development tool with a stable CLI entrypoint and real schema-admin plus CRUD coverage through direct access.

Acceptance criteria:
- `tools/supabase/cli.py` exists and executes declared Supabase tool operations
- the executable tool covers schema admin plus create/read/update/delete for vendors, candidates, and runs
- The tool spec exposes an executable entrypoint and direct backend support
- Direct repo access remains the source-of-truth execution path when available
- Tests prove the Supabase tool can resolve direct execution, validate controlled CRUD inputs, and enforce schema-admin prerequisites

Verification:
- `.venv/bin/python scripts/autonomous_controller.py assert-artifacts M13D`
- `.venv/bin/python -m pytest tests/test_supabase_tool.py tests/test_autonomous_audit.py`
- Review `tools/supabase/cli.py` and `tools/supabase/tool_spec.json`
- Verify tool docs explain the direct execution boundary clearly

## M13E Prework acceleration role
Status: `complete`

Objective:
Add a lightweight read-only prework role that prepares milestone context before planning and implementation so the autonomous loop spends less time rediscovering the repo.

Acceptance criteria:
- A dedicated `prework` role prompt exists under `docs/agents/`
- The controller prompt sequence includes `prework -> planner -> builder -> reviewer -> QA`
- The repo-native runner recognizes the `prework` role and emits structured packets for it
- The controller-owned iteration loop executes prework before planner and builder
- The autonomous docs describe prework as a read-only acceleration step rather than a separate milestone owner

Verification:
- `.venv/bin/python -m pytest tests/test_autonomous_audit.py tests/test_autonomous_controller.py tests/test_local_agent_runner.py`
- Review `docs/agents/prework_agent.md`, `docs/autonomous_dev_loop.md`, `docs/autonomous_kickoff_prompt.md`, `scripts/autonomous_controller.py`, and `scripts/local_agent_runner.py`

## M16 End-to-end runtime hardening
Status: `complete`

Objective:
Validate that a real run produces coherent outputs, pages, and admin views without manual patching between steps.

Acceptance criteria:
- Pipeline run produces fresh outputs for directory, review, and run snapshots
- Landing, vendor, review, and admin surfaces all render from generated data
- Failure paths are visible rather than silent

Verification:
- `.venv/bin/python scripts/run_pipeline.py`
- Local preview checks of `landing.html`, `vendor.html`, `admin.html`, and `outputs/vendor_review.html`

Current status:
- A fresh live pipeline run completed successfully and regenerated the directory dataset, vendor review dataset, vendor review report, run snapshot, and CSV output.
- The preview server served `landing.html`, `vendor.html`, `admin.html`, and `outputs/vendor_review.html` from the generated runtime state.
- Admin JSON endpoints reflected the new run snapshot and current vendor/candidate state without manual patching between steps.
- Runtime warnings remained visible: the latest run recorded `completed_with_warnings`, and malformed Google Sheets credentials were surfaced in logs instead of failing silently.
- `M16` has been closed through controller verification, review, and QA.

## M17 Internal launch readiness
Status: `complete`

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

Current status:
- All prior milestones are complete in `milestone_registry.json`.
- `bash scripts/verify_project.sh` passes cleanly.
- The full local pytest suite passes with `201` tests.
- The operator walkthrough now includes inspect endpoints, include/exclude controls, and a live successful `rerun-enrichment` action.
- Accepted launch caveats remain explicit rather than hidden: browser-render proof is still indirect, and Google Sheets remains a warning-only path in this environment because credentials are malformed.
- `M17` has been closed through controller verification, review, and QA.

## M18 Vendor intelligence schema expansion and deep enrichment
Status: `complete`

Objective:
Deepen the product from a basic AI-in-CS vendor directory into a richer lead-magnet intelligence asset by expanding the vendor schema, hardening field normalization, and extracting more specific commercial evidence from vendor websites. This milestone now explicitly includes defining and implementing a superset vendor-intelligence schema based on real vendor-site evidence from platforms such as Gainsight.

Acceptance criteria:
- A repo-owned superset schema contract exists for rich vendor intelligence, covering:
  - core vendor identity and canonical web/contact fields
  - product and use-case structure
  - buyer personas and broad ICP
  - leadership/founder/company metadata
  - support/help/demo surfaces
  - categorized integrations
  - structured proof tables such as case studies and later search-visibility evidence
- The vendor data model supports both broad ICP and buyer-oriented ICP (`icp_buyer`)
- Case studies are no longer treated as flat proof labels only; the system can store structured case-study evidence with client, use case, value realized, and source reference
- Vendor-level value statements remain separate from case-study-specific realized value
- Website exploration explicitly covers the pages most likely to contain enrichment signals, including `about`, `team`, `contact`, `demo`, and help/support surfaces where available
- The schema and extraction model support additional company intelligence fields such as founder/CEO details, headquarters/contact details, demo URL, help-center URL, and categorized integrations
- The schema and processing layer enforce canonical formatting and validation for website URLs and email addresses before persistence
- The system can extract and persist richer product/commercial fields needed for the directory and lead-magnet workflow, including integration categories, pricing model, free-trial detail, support/customer-success signals, and company metadata
- The implementation plan for later expansion remains explicit for deferred fields such as Product Hunt ingestion, Trustpilot/G2 enrichment depth, funding/news enrichment, and knowledge-base chat use cases when they are not fully completed in this milestone
- The schema design is informed by real multi-product CS vendors, so it can represent examples like:
  - multiple products under one vendor
  - multiple buyer personas
  - executive leadership and founder information
  - support/docs/help-center URLs
  - structured customer-story outcomes
  - categorized integrations and ecosystem signals

Verification:
- `.venv/bin/python -m pytest tests/test_vendor_intel_extraction.py tests/test_llm_extractor.py tests/test_merge_results.py tests/test_site_explorer.py tests/test_vendor_profile_builder.py tests/test_supabase_client.py`
- `.venv/bin/python scripts/check_supabase.py`
- Review `supabase/core_persistence_schema.sql`, `services/extraction/vendor_intel.py`, `services/extraction/llm_extractor.py`, `services/enrichment/site_explorer.py`, and the relevant export/admin surfaces
- Review the superset schema design against a real reference vendor such as Gainsight to confirm it supports multi-product, multi-buyer, leadership, help/support, integration, and case-study structures
- Verify the schema and docs clearly distinguish vendor value statements from structured case-study realized value
- Verify the schema/processing rules normalize websites and emails into canonical valid formats before persistence

## M19 Role-based search visibility tracking and ranking intelligence
Status: `not_started`

Objective:
Measure how different buyer personas would discover vendors through both classic search and AI-native search, then persist those ranked results so the directory can compare vendor visibility by role, query, and channel.

Acceptance criteria:
- The system defines one or more database tables for role-based search visibility results rather than storing them as ad hoc text blobs
- Search tracking is structured around `icp_buyer` personas such as `VP Customer Success`, `Chief Customer Officer`, `CS Operations leader`, and other supported buyer roles
- For each buyer persona, the system can persist the top search prompts used for:
  - classic Google-style search
  - AI/GEO-style search prompts
- For each executed query, the system can persist ranked surfaced vendors with fields such as:
  - buyer role
  - search channel (`google` or `geo - openai`)
  - query text
  - observed rank position
  - surfaced vendor name
  - surfaced vendor website
  - source URL or response reference where available
  - visibility score or rank-derived score
  - run timestamp
- The search visibility result is query-centric and vendor-centric, so the product can answer both:
  - “what would a VP Customer Success see for these searches?”
  - “how often and how highly does Gainsight surface across buyer-role searches?”
- The docs clearly distinguish:
  - vendor website enrichment
  - buyer-intent query generation
  - role-based search ranking observation
- The milestone defines a reviewable output shape for reporting, such as a role-by-query ranking table and vendor visibility summary

Expected result shape:
- a `buyer_search_queries` table for the generated buyer-role prompts
- a `buyer_search_results` table for the ranked observed results per query
- example review rows should look like:
  - `VP Customer Success | google | tools to improve SaaS retention | rank 1 | Gainsight | https://www.gainsight.com | score 100`
  - `VP Customer Success | geo | What AI tools help reduce SaaS churn? | rank 2 | ChurnZero | https://churnzero.com | score 85`

Verification:
- Review the Supabase schema and the role-search result model for `buyer_search_queries` and `buyer_search_results`
- Verify the implementation persists both Google-style and GEO-style queries per buyer role
- Verify the implementation persists ranked result rows with vendor identity, query identity, channel, and score
- Verify the reporting/export surface can show a role-based ranking table and a vendor visibility summary
- `.venv/bin/python -m pytest` for the new role-search persistence, extraction, and export coverage added by the milestone

## M20 Structured case-study intelligence
Status: `not_started`

Objective:
Turn customer stories into structured proof rows rather than flat labels so the directory can show who used the product, for what, and what value was realized.

Acceptance criteria:
- The schema supports structured case-study rows with fields such as `client`, `title`, `use_case`, `value_realized`, `metric`, and `source_url`
- Vendor-level marketing value statements remain separate from case-study-specific realized value
- Extraction can populate structured case-study evidence from customer-story pages
- Review and export surfaces can show case-study evidence in a table-friendly shape

Verification:
- `.venv/bin/python -m pytest tests/test_vendor_intel_extraction.py tests/test_merge_results.py tests/test_supabase_client.py`
- Review the case-study schema and export shape for table-style rendering

## M21 Leadership, company, and contact intelligence
Status: `not_started`

Objective:
Extract and persist company metadata needed for a high-trust lead magnet, including leadership, founding, headquarters, and contact surfaces.

Acceptance criteria:
- The schema supports fields for `ceo_name`, leadership/founder details, `hq_address`, `phone_numbers`, `contact_emails`, `demo_url`, `support_url`, `help_center_url`, and `developer_docs_url`
- Website exploration explicitly includes likely `about`, `team`, `leadership`, `contact`, `demo`, and support/help surfaces
- Extraction can populate these fields from real vendor sites where available

Verification:
- `.venv/bin/python -m pytest tests/test_site_explorer.py tests/test_vendor_intel_extraction.py tests/test_supabase_client.py`
- Review the schema and extraction mapping for leadership/contact fields

## M22 Canonical identity and validation layer
Status: `not_started`

Objective:
Make persisted identity/contact fields trustworthy by enforcing canonical normalization and validation for websites, domains, emails, and other core identifiers.

Acceptance criteria:
- Shared normalization exists for website URLs, domains, emails, and other core identity fields before persistence
- Malformed URLs and emails are rejected, normalized, or explicitly flagged
- The schema and processing rules preserve canonical vendor identity for dedupe and exports

Verification:
- `.venv/bin/python -m pytest tests/test_apify_sources.py tests/test_vendor_profile_builder.py tests/test_supabase_client.py`
- Verify the schema/processing rules normalize websites and emails into canonical valid formats before persistence

## M23 Buyer persona search-intent engine
Status: `not_started`

Objective:
Operationalize `icp_buyer` by generating realistic buyer-role search behavior for both classic search and AI-native search.

Acceptance criteria:
- The system can generate and persist top buyer-role query sets for `google` and `geo`
- Query generation is linked to specific `icp_buyer` personas rather than vendor-wide generic prompts
- Prompt/version context is reviewable and persisted

Verification:
- `.venv/bin/python -m pytest tests/test_llm_extractor.py tests/test_merge_results.py`
- Review the buyer-role query generation contract and stored query shape

## M24 Lead magnet conversion surface
Status: `not_started`

Objective:
Turn the directory into a clearer demand-generation surface for `successbycs.com`, with stronger CTA, capture, and service-positioning flows.

Acceptance criteria:
- Public directory and vendor surfaces can include lead-generation CTAs and capture opportunities
- The product can support a gated lead-magnet flow similar to competitive directory experiences
- Conversion/capture instrumentation is defined clearly enough for later runtime wiring

Verification:
- Local preview review of public surfaces and CTA placement
- Review the public product requirements against the lead-magnet objective

## M24A Lead capture, attribution, and follow-up operations
Status: `not_started`

Objective:
Turn lead-magnet interest into attributable pipeline for the `successbycs.com` fractional Head of CS business instead of stopping at page-level CTA clicks.

Acceptance criteria:
- A repo-owned lead capture model exists for gated assets, newsletter signup, or consultation-intent submissions
- Captured leads preserve source context such as entry page, vendor/profile context, CTA variant, referrer, and UTM attribution where available
- The product distinguishes lightweight content interest from higher-intent service interest such as advisory, audit, or fractional leadership conversations
- Operators can review captured leads and their follow-up status through an internal surface or export path
- The system defines the first follow-up handoff clearly enough to support owner notification, CRM sync, or a structured consultation-booking workflow
- Success metrics are framed around attributable leads and qualified follow-up outcomes, not just CTA clicks

Verification:
- Review the lead schema, attribution fields, and handoff model
- Verify public capture surfaces persist enough context to attribute a lead back to source page and CTA
- Verify the internal review/export path can show captured leads, attribution, and follow-up state
- `.venv/bin/python -m pytest` for the lead-capture and attribution coverage added by the milestone

## M25 Editorial auto-inclusion governance
Status: `not_started`

Objective:
Keep admin overrides as exceptions by making the code determine default inclusion/exclusion and surfacing why it made that decision.

Acceptance criteria:
- Include/exclude decisions are code-owned by default
- Admin overrides are preserved as explicit exceptions, not the primary workflow
- Review/export/admin surfaces expose enough reasoning for operators to trust the automated decision

Verification:
- `.venv/bin/python -m pytest tests/test_directory_relevance.py tests/test_admin_actions.py tests/test_vendor_profile_builder.py`
- Review the automated inclusion reasoning surfaced to operators

## M26 Multi-product vendor modeling
Status: `not_started`

Objective:
Support vendors with multiple products or modules, such as Gainsight, without collapsing everything into a single flat vendor row.

Acceptance criteria:
- The schema can represent multiple products under one vendor
- Product-level use cases, integrations, and demo/support surfaces can be captured
- The product model distinguishes vendor-level intelligence from product-level intelligence

Verification:
- `.venv/bin/python -m pytest tests/test_vendor_profile_builder.py tests/test_supabase_client.py`
- Review the multi-product schema and export/admin implications

## M27 Integration intelligence taxonomy
Status: `not_started`

Objective:
Normalize integrations into useful categories rather than one undifferentiated list or blob.

Acceptance criteria:
- Integration evidence can be categorized into groups such as CRM, CSP, PM, workflow, email/calendar, support, warehouse, and other
- Raw integration crawl evidence can be mapped into the normalized taxonomy
- Export/admin surfaces can show integrations in grouped form

Verification:
- `.venv/bin/python -m pytest tests/test_vendor_intel_extraction.py tests/test_supabase_client.py`
- Review the integration taxonomy and normalized output shape

## M28 Render-level proof and UX verification
Status: `not_started`

Objective:
Add real browser-level verification for public and admin experiences so milestone proof reflects what users actually see.

Acceptance criteria:
- Headless browser proof exists for key public/admin surfaces
- Render-level assertions check visible content, not just raw HTML fetches
- Proof artifacts such as screenshots and DOM snapshots are captured for verification

Verification:
- Browser-level verification of `landing.html`, `vendor.html`, and `admin.html`
- Review stored proof artifacts for at least one milestone closeout

## M29 Evidence and proof artifact persistence
Status: `not_started`

Objective:
Preserve stronger runtime/manual proof artifacts instead of relying mainly on summary notes in run history and audit text.

Acceptance criteria:
- Verification, QA, and closeout flows can store proof bundles under a repo-owned path
- Proof bundles capture command results, logs, screenshots/DOM snapshots where relevant, and artifact assertions
- Run history and audit entries can reference proof-bundle locations

Verification:
- Review proof bundle output structure and run-history linkage
- `.venv/bin/python -m pytest tests/test_autonomous_controller.py tests/test_milestone_auditor.py`

## M30 External enrichment connectors
Status: `not_started`

Objective:
Add controlled external enrichment sources where they materially improve the directory, while keeping provenance and tool boundaries explicit.

Acceptance criteria:
- The `/tools` layer can define third-party enrichment tools with clear access boundaries
- The schema supports provenance, freshness, and source identity for externally enriched fields
- Deferred sources such as Product Hunt, G2, funding/news, and other external signals are represented cleanly enough for staged rollout

Verification:
- Review tool specs, schema provenance fields, and external-enrichment guardrails
- `.venv/bin/python scripts/autonomous_audit.py`

## M31 Knowledge-base and help-center detection
Status: `not_started`

Objective:
Detect whether vendors expose help centers or docs surfaces suitable for later knowledge-base/chat use cases.

Acceptance criteria:
- The system can detect likely help/support/docs portals and store their URLs
- The schema distinguishes support/help-center presence from general company contact pages
- The product can later use this field for KB/chat expansion without redesigning the core model

Verification:
- `.venv/bin/python -m pytest tests/test_site_explorer.py tests/test_vendor_intel_extraction.py`
- Review help/support/docs URL extraction behavior

## M32 Solution enhancement workflow and agent
Status: `not_started`

Objective:
Formalize how product changes, enhancements, and updates move through the autonomous milestone system instead of being handled as ad hoc requests.

Acceptance criteria:
- A repo-defined change/update/enhancement pipeline exists and is documented
- A `Solution Enhancement` agent prompt exists for turning requested changes into milestone-scoped implementation work
- The controller and runner can expose the enhancement role without bypassing the milestone contract
- Enhancement requests result in either:
  - an update to the active milestone
  - a new milestone
  - or an explicitly deferred enhancement record

Verification:
- Review the enhancement workflow docs and agent prompt
- `.venv/bin/python -m pytest tests/test_autonomous_controller.py tests/test_local_agent_runner.py`

## M33 n8n development tool integration
Status: `not_started`

Objective:
Add `n8n` to the repo tool layer as a development tool so the autonomous system can use it in a controlled way for workflow prototyping, automation experiments, and local integration support.

Acceptance criteria:
- The `/tools` layer declares `n8n` as a repo-owned development tool with a clear tool spec
- The docs explain what `n8n` may be used for during development and what is out of scope
- The tool boundary distinguishes:
  - local/development workflow automation
  - product/runtime automation
- Controller and runner documentation explain how roles may access `n8n` when it is declared for a milestone
- The tool contract captures allowed operations, environment assumptions, and approval/safety expectations

Verification:
- Review the `n8n` tool spec and tool-registry entry
- Review the docs for role access, development-only scope, and execution boundaries
- `.venv/bin/python scripts/autonomous_audit.py`

## M34 Background-agent acceleration and safe parallel delegation
Status: `not_started`

Objective:
Speed up autonomous development by introducing an explicit background-agent model for bounded read-only delegation, parallel prep/proof work, and deterministic handoff back into the main milestone loop.

Acceptance criteria:
- The docs define what a background agent is and how it differs from the main milestone-owner roles (`planner`, `builder`, `reviewer`, `qa`)
- The controller can declare safe background-task categories such as repo scanning, changed-file triage, test-impact discovery, doc-drift detection, and proof/artifact collection
- Background-agent work is read-only by default and may run in parallel only when the delegated task contract keeps scope explicit and non-overlapping
- Mutating implementation work remains serial unless a future milestone adds explicit isolated-write coordination
- Role packets and/or run history can link background-task outputs back to the owning milestone cycle in a deterministic way
- The control-plane docs explain when background delegation should be used, when it should not be used, and how its outputs must be consumed by the main role flow
- Tests prove that background delegation cannot bypass write-scope rules, milestone verification, review, QA, or completion gating

Verification:
- Review the updated autonomous-loop and controller docs for the background-agent task model and safety boundaries
- `.venv/bin/python -m pytest tests/test_autonomous_controller.py tests/test_local_agent_runner.py`

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
