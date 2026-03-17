# Codex Guardrails

## Purpose

These rules constrain autonomous development so progress remains safe, reviewable, and aligned with the product intent of this repo.

## Primary Product Rule

This project is a vendor-first AI Customer Success intelligence system.
The core unit of analysis is the vendor/company/product, not generic pages or generic content blobs.

## Source of Truth

Always align with:

- `docs/product_design.md`
- `docs/architecture.md`
- `docs/implementation_plan.md`
- this file: `docs/codex_guardrails.md`

The canonical Customer Success lifecycle is defined in `docs/product_design.md` and must remain consistent across discovery, extraction, classification, storage, export, and the public directory.

## Non-Negotiables

- Read the anchor docs before implementing a milestone
- Do not redesign the architecture unless the milestone explicitly requires it
- Deterministic extraction remains the baseline safety net
- Lifecycle stage assignment remains deterministic in Python
- LLM enrichment is optional, bounded, and must fail safely
- Supabase is the intended canonical data store even when local fallback artifacts exist
- Google Sheets is an ops/export layer, not the source of truth
- Public directory pages remain static for v1

## Implementation Rules

- Complete the active milestone only; do not roam into unrelated work
- Make the smallest change that satisfies the milestone
- Inspect the current repo before changing code
- Do not refactor unrelated files
- Do not add dependencies unless clearly necessary
- Keep the code beginner-friendly and explicit
- Prefer simple functions and clear naming over abstraction
- Prefer modifying existing files over introducing many new files
- Do not hard-code machine-specific paths

## Configuration Rule

The current runtime source of truth is still mixed:

- `config/pipeline_config.json` drives most pipeline behavior
- `config/scheduler.toml` drives scheduler timing

Do not assume the other split TOML config files are already the active runtime source of truth unless the code confirms it.

## Separation of Responsibilities

Keep modules separated by responsibility:

- discovery = find vendor candidates
- enrichment = fetch vendor pages
- extraction = convert page content into structured intelligence
- storage = persist data
- reporting = export or summarize data
- admin = operator visibility and controlled actions

Do not mix these responsibilities unless the milestone explicitly requires it.

## Safety Rules

- Do not let empty or weak LLM values overwrite stronger deterministic values
- Do not allow malformed LLM output to break the pipeline
- Do not silently change export schemas
- Do not ship admin write actions without explicit logging
- Do not treat local fallback artifacts as proof that persistence is healthy
- Do not expose internal admin endpoints publicly without clear warning

## Verification Rules

After implementation:

- run the milestone verification commands
- run the relevant tests
- add or update tests whenever behavior changes
- treat missing test coverage as a completion problem, not a documentation footnote
- confirm expected artifacts are produced when the milestone requires them
- update affected docs before marking the milestone complete

## Review Rules

When acting as reviewer or QA:

- be repo-specific
- cite files where possible
- call out doc vs implementation mismatches
- call out hidden fallback dependence
- call out silent failure risks
