# AI_CustomerSuccess

Vendor-first MVP for discovering AI-enabled Customer Success vendors, fetching their homepages, extracting lightweight vendor intelligence, and shaping the result into Google Sheets-ready rows.

## Python Setup

This project requires Python 3.12+.

Create a virtual environment and install dependencies:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The CLI loads environment variables from a local `.env` file automatically.
Google Sheets output is optional and uses `GOOGLE_SHEETS_ID` plus
`GOOGLE_SHEETS_CREDENTIALS_JSON`.

Discovery crawl depth is configured in `config/discovery.toml`.
The current repo-level default is `max_pages_per_query = 20`.

## Run Tests

Use the local virtual environment for deterministic test runs:

```sh
.venv/bin/python -m pytest
```

## Run the Pipeline

Write Google Sheets-ready CSV output to `outputs/vendor_rows.csv`:

```sh
.venv/bin/python scripts/run_pipeline.py "ai customer success platform"
```

Run the Python-owned scheduler:

```sh
.venv/bin/python -m services.pipeline.scheduler
```

Run one scheduled job manually:

```sh
.venv/bin/python -m services.pipeline.scheduler --run-now discovery
.venv/bin/python -m services.pipeline.scheduler --run-now digest
```

Optional Supabase smoke test:

```sh
.venv/bin/python scripts/check_supabase.py
```

Integration diagnostics:

```sh
.venv/bin/python scripts/check_integrations.py
```

## MVP Flow

The current codebase follows the MVP pipeline described in `docs/product_design.md`:

1. `services/discovery/` finds vendor candidates from web search
2. `services/enrichment/` fetches vendor homepage content
3. `services/extraction/` converts homepage payloads into `VendorIntelligence`
4. `services/export/` converts vendor intelligence into Google Sheets-ready rows
5. `services/pipeline/` orchestrates the end-to-end flow

`docker-compose.yml` remains in the repo for future infrastructure work, but Docker is not required for the current Python MVP or test suite.
