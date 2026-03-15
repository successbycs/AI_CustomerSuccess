# Architecture

This repository follows the MVP pipeline in `docs/product_design.md` and stays vendor-first.

## Module Boundaries

`services/discovery/`
Finds vendor candidates from web search.

`services/enrichment/`
Fetches vendor website content, starting with the homepage in the MVP.

`services/extraction/`
Converts fetched page payloads into structured `VendorIntelligence`.

`services/export/`
Converts structured vendor intelligence into Google Sheets-ready row dictionaries.

`services/pipeline/`
Runs the end-to-end orchestration from discovery through export.

`scripts/run_pipeline.py`
Provides a small CLI wrapper for running the MVP pipeline locally.

## Current MVP Flow

1. A search query is passed to `search_web(...)`.
2. Each discovered vendor is passed to `fetch_vendor_homepage(...)`.
3. Each homepage payload is converted with `extract_vendor_intelligence(...)`.
4. Each `VendorIntelligence` object is converted with `vendor_intelligence_to_sheet_row(...)`.
5. The pipeline returns a list of row dictionaries ready for Google Sheets import.

## MVP Notes

- The core unit is the vendor, not individual pages.
- Web search is the current discovery source.
- Homepage fetching is the current enrichment mode.
- Extraction is intentionally minimal and beginner-friendly.
- Export currently returns dictionaries and does not call the Google Sheets API.
