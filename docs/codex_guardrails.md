# Codex Guardrails

## Primary Product Rule
This project is a vendor-first AI Customer Success intelligence system.
The core unit of analysis is vendor/company/product, not generic pages or content.

## Source of Truth
Always align with:
- docs/product_design.md
- this file: docs/codex_guardrails.md

The canonical Customer Success lifecycle is defined in `docs/product_design.md` and must be kept consistent across discovery, extraction, classification, storage, and export.

## Implementation Rules
- Make the smallest change that satisfies the task
- Do not redesign the architecture unless explicitly requested
- Do not refactor unrelated files
- Do not add new dependencies unless explicitly requested
- Keep the code beginner-friendly and easy to follow
- Prefer simple functions and clear naming over abstraction
- Prefer modifying existing files over introducing many new files

## Separation of Responsibilities
Keep modules separated by responsibility:
- discovery = find vendor candidates
- enrichment = fetch vendor pages
- extraction = convert page content into structured intelligence
- storage = persist data
- reporting = export or summarize data

Do not mix these responsibilities unless explicitly requested.

## MVP Scope Rules
- Web search is the MVP source unless stated otherwise
- Do not add GitHub, Product Hunt, newsletters, UI, or dashboard work unless explicitly requested
- Do not redesign the database early
- Do not build future phases early

## Testing Rules
- Run pytest after each change
- Keep tests deterministic and simple
- Fix only issues relevant to the current task
- Do not rewrite tests to hide real problems

## Output Rules
- Briefly explain what changed
- Briefly explain why
- Report pytest results
- Flag any assumptions or risks
