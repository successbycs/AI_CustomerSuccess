# Architecture

This repository implements the pipeline described in `docs/product_design.md`. The core unit of analysis is the vendor, not individual web pages. Python owns all orchestration, scheduling, and business logic. Apify is used exclusively as a crawling utility called on instruction from Python.

This version introduces a dual extraction architecture:
Level 1 deterministic extraction and Level 2 LLM extraction using a ChatGPT model. Both operate independently and are merged by Python before persistence.

---

# Module Boundaries

services/discovery/

Instructs Apify to crawl discovery sources and returns normalised vendor candidates to the orchestrator.

Contains `apify_sources.py` with four functions:

fetch_producthunt()  
fetch_google_search(queries)  
fetch_g2_categories(urls)  
fetch_rag_browser(query)

Each function:

1. Calls the Apify API
2. Waits for the actor run to complete
3. Pulls the output dataset
4. Normalises the results into candidate objects

Discovery contains no business logic.

Candidate normalisation is handled via `normalise_candidates.py` to ensure consistent structure across discovery sources.

Normalised candidate schema:

company_name  
website  
raw_description  
source  

---

services/enrichment/

Fetches vendor homepage content using Python requests.

Responsibilities:

- Fetch homepage HTML
- Strip HTML tags
- Extract visible text
- Normalise whitespace
- Truncate content to ~5000 characters
- Return clean text ready for extraction

Apify is not used for enrichment.

---

services/extraction/

Implements the dual extraction architecture.

rule_extractor.py

Level 1 deterministic extraction using rule-based keyword detection. Extracts baseline signals such as:

use_cases  
value_statements  
product_capabilities  

This extractor guarantees structured output even if LLM extraction fails.

llm_extractor.py

Level 2 semantic extraction using a ChatGPT model.

Python sends homepage text to the OpenAI API and receives structured JSON containing richer commercial intelligence including:

mission  
unique selling proposition  
expanded use cases  
pricing signals  
free trial signals  
SOC2 mentions  
founded information  
confidence score  

merge_results.py

Combines the deterministic extraction results and the LLM extraction results into a single `VendorIntelligence` object.

If the LLM call fails, deterministic results are still used.

Vendors where:

is_cs_relevant = false  
confidence = low  

are dropped before persistence.

---

services/classification/

Contains `lifecycle_classifier.py`.

Lifecycle classification is deterministic and handled by Python, not the LLM.

Extracted signals are mapped to the SuccessByCS 7-stage lifecycle framework:

Sign  
Onboard  
Activate  
Adopt  
Expand  
Renew  
Advocate  

Multiple lifecycle stages may be assigned to a vendor.

Example signal mappings:

health score → Adopt  
churn prediction → Renew  
NPS → Advocate  
upsell detection → Expand  
onboarding automation → Onboard  

---

services/persistence/

Contains `supabase_client.py`.

Provides:

is_known_vendor(website)  
Checks whether the vendor domain already exists in Supabase.

upsert_vendor(vendor)

Writes vendor intelligence into the `cs_vendors` table using:

ON CONFLICT (website) DO UPDATE

Domain normalisation ensures the following map to the same record:

gainsight.com  
www.gainsight.com  
https://gainsight.com  

---

services/export/

Handles human-facing outputs.

google_sheets.py

Appends new vendor rows to the Google Sheet used for browsing the vendor landscape.

slack.py

Builds and posts the weekly Slack digest summarising vendors discovered in the past week grouped by lifecycle stage.

---

services/pipeline/

orchestrator.py

Runs the end-to-end flow:

discovery  
candidate normalisation  
domain deduplication  
Supabase deduplication check  
homepage enrichment  
dual extraction  
lifecycle classification  
persistence  
Google Sheets export

scheduler.py

APScheduler entry point.

Runs:

run_discovery() daily at 07:00 UTC  
run_digest() Monday at 08:00 UTC

---

services/utils/

retry.py

Provides retry logic with exponential backoff for external API calls.

Used by:

Apify client  
OpenAI client  
Supabase client  
Google Sheets client  
Slack client

Retry policy:

3 retries  
exponential backoff  
timeout handling

domain.py

Handles domain normalisation to ensure consistent vendor deduplication.

Example normalisation:

https://www.gainsight.com  
http://gainsight.com  
gainsight.com

→ gainsight.com

---

scripts/run_pipeline.py

CLI wrapper for running the pipeline manually.

Examples:

python scripts/run_pipeline.py --run-now discovery  
python scripts/run_pipeline.py --run-now digest

---

# Current Pipeline Flow

1. Python scheduler fires at 07:00 UTC and calls `orchestrator.run_discovery()`.

2. The orchestrator calls each discovery source in `services/discovery/apify_sources.py`, which instructs Apify to crawl and returns candidate vendors.

3. Candidates are normalised and deduplicated by domain within the batch.

4. Each candidate website is checked against Supabase using `is_known_vendor(website)`. Known vendors are skipped.

5. Each new vendor homepage is fetched via `fetch_vendor_homepage()`.

6. Deterministic extraction runs via `rule_extractor`.

7. LLM extraction runs via `llm_extractor` using a ChatGPT model.

8. Extraction results are merged into a `VendorIntelligence` object.

9. Lifecycle stages are assigned using `lifecycle_classifier`.

10. Each vendor object is persisted via `upsert_vendor()`.

11. Each vendor row is appended to Google Sheets.

12. On Monday at 08:00 UTC, `run_digest()` queries vendors added in the past week and posts a Slack digest grouped by lifecycle stage.

13. Vendors included in the digest have `is_new = FALSE`.

---

# Apify Integration Notes

Apify is used exclusively as a crawling utility.

Apify does not:

control pipeline execution  
perform classification  
write to databases  
call LLM APIs  

Python instructs Apify which actors to run. Apify returns crawl results. Python immediately resumes control.

If Apify is replaced with another crawling provider, only `services/discovery/apify_sources.py` changes.

The four Apify actors currently used:

apify/product-hunt-scraper — ProductHunt AI launches (daily)

apify/google-search-scraper — targeted Customer Success AI search queries (daily)

apify/website-content-crawler — G2 category pages (weekly)

apify/rag-web-browser — newsletter and blog discovery (daily)

---

# Scheduling Notes

The Python process runs continuously as a persistent service deployed on Railway or Render.

APScheduler manages the schedule internally.

No GitHub Actions, no external cron, and no n8n are required.

The process must remain alive between scheduled runs.

---

# Environment Variables

All credentials are read from environment variables.

SUPABASE_URL  
SUPABASE_KEY  
OPENAI_API_KEY  
APIFY_API_TOKEN  
GOOGLE_SHEETS_ID  
GOOGLE_SHEETS_CREDENTIALS  
SLACK_BOT_TOKEN  
SLACK_CHANNEL_ID  

---

# Observability

The pipeline logs the following operational metrics:

vendors discovered  
vendors skipped as duplicates  
vendors enriched  
vendors extracted  
vendors dropped  
vendors persisted  
rows exported to Sheets  
weekly digest posted  

Structured logging enables debugging and pipeline monitoring.

---

# Tests

All services have corresponding test files in `tests/`.

External services are mocked:

Apify  
OpenAI  
Supabase  
Google Sheets  
Slack

No live API calls occur during tests.

Run tests:

python3 -m venv .venv  
.venv/bin/pip install -r requirements.txt  
.venv/bin/python -m pytest

Test files:

tests/test_discovery.py  
tests/test_enrichment.py  
tests/test_extraction.py  
tests/test_classification.py  
tests/test_persistence.py  
tests/test_export.py  
tests/test_pipeline.py

---

# MVP Notes

Vendor is the core entity, not individual pages.

Apify is used for discovery crawling only.

Homepage enrichment uses Python requests.

Extraction uses two independent systems:

Level 1 deterministic rules  
Level 2 ChatGPT semantic extraction

Lifecycle classification is deterministic and handled by Python.

Supabase is the canonical datastore.

Google Sheets is a human-readable export layer.