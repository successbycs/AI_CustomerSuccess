# Product Design (v2.2)

This document describes the architecture for the AI Customer Success Vendor Intelligence system.

The system discovers companies offering AI-enabled products that support the Customer Success lifecycle, enriches vendor websites to collect key information, extracts structured commercial intelligence, classifies vendors against the SuccessByCS 8-stage lifecycle framework, and produces a structured dataset in Supabase and Google Sheets.

The core unit of analysis is the vendor/company, not individual web pages.

The target architecture introduces a dual-extraction model:
Level 1 deterministic extraction and Level 2 LLM-assisted extraction.

Current implementation status:
the codebase at this checkpoint runs Level 1 deterministic extraction as the baseline
and Level 2 LLM-assisted extraction as an active optional enrichment layer.
If Level 2 is unavailable, the MVP pipeline falls back to Level 1 without failing the run.

---

# Primary Deliverable

The system produces a continuously updated dataset of AI-enabled Customer Success vendors.

The canonical dataset lives in Supabase.

Google Sheets is a human-readable export layer used for browsing and sharing the vendor landscape.

Each vendor row contains fields such as:

vendor_name  
website  
source  
mission  
usp  
icp  
use_cases  
lifecycle_stages  
pricing  
free_trial  
soc2  
founded  
case_studies  
customers  
value_statements  
confidence  
evidence_urls  
directory_fit  
directory_category  
include_in_directory  

---

# The SuccessByCS 8-Stage Lifecycle Framework

Every vendor in the system is classified against this framework.

Stage names are canonical and must not be altered.

A vendor may belong to multiple stages.

Sign  
Conversational intelligence, AI notetakers, meeting summaries, sales-to-CS handoff tools

Onboard  
Implementation portals, PSA tools, onboarding automation, time-to-value acceleration

Activate  
In-app guidance, user education, product walkthroughs, adoption nudges

Adopt  
Health scoring, usage analytics, sentiment analysis, signal-to-playbook automation

Support  
Support automation, ticket triage, agent assist, help desk copilots, knowledge base tooling

Expand  
Upsell detection, cross-sell intelligence, expansion revenue tools, stakeholder mapping

Renew  
Churn prediction, renewal automation, risk alerts, forecasting

Advocate  
NPS, Voice of Customer programs, reference management, case study tools

Lifecycle stage classification is performed by Python, not the LLM.

---

# Architecture Overview

Python is the controller, scheduler, and decision-maker for the entire system.

Apify is used only as a crawling utility.

Apify fetches pages and returns raw content. It never touches the database, never calls an LLM, and never makes business decisions.

Python process (Railway / Render)

APScheduler  
owns daily and weekly scheduling

services/discovery  
calls Apify actors and returns normalised vendor candidates

services/enrichment  
fetches homepage content, explores vendor pages, and extracts visible text

services/extraction  
performs vendor intelligence extraction (Level 1 deterministic + Level 2 LLM)

services/classification  
maps extracted signals to lifecycle stages

services/persistence  
deduplication checks and upserts into Supabase

services/export  
writes rows to Google Sheets and sends Slack digest

services/pipeline  
orchestrator controlling the full pipeline

If Apify were replaced with another crawling provider tomorrow, only services/discovery/apify_sources.py would change.

---

# System Pipeline

The crawl model is now explicit:

Phase 1 = discovery crawl  
Phase 2 = vendor enrichment crawl  

Daily pipeline

Pipeline stages

Vendor Discovery  
Homepage Fetch  
Website Exploration  
Page Text Extraction  
Vendor Intelligence Extraction  
Vendor Profile Builder  
Dataset Export  

Python APScheduler fires using the configured discovery schedule in `config/scheduler.toml`  
↓  
Python orchestrator triggers discovery  
↓  
Python loads crawl/runtime settings from `config/pipeline_config.json` and calls Apify actors for discovery sources  
↓  
Apify returns candidate URLs and metadata  
↓  
Python normalises candidates into candidate-domain records and deduplicates by domain across all configured queries  
↓  
Python marks accepted domains as queued for enrichment and skips already-enriched domains  
↓  
Phase 2 enrichment proceeds only on queued domains  
↓  
Python fetches homepage text (3000-5000 characters)  
↓  
Python explores a bounded set of high-signal internal pages from `config/pipeline_config.json`  
↓  
Python extracts clean visible text from those pages  
↓  
Level 1 deterministic extraction runs  
↓  
Level 2 LLM extraction runs when configured in `config/pipeline_config.json`  
↓  
Python merges deterministic and LLM signals into one vendor profile record  
↓  
Python classifies lifecycle stages  
↓  
Python assigns directory relevance labels and include/exclude decisions  
↓  
Vendors marked non-relevant or low-confidence are dropped  
↓  
Python upserts to Supabase  
↓  
Python appends row to Google Sheets

Weekly digest

Python APScheduler fires using the configured digest schedule in `config/scheduler.toml`  
↓  
Python queries vendors added in last 7 days  
↓  
Python groups vendors by lifecycle stage  
↓  
Python posts summary to Slack  
↓  
Python marks vendors as no longer new

---

# Scheduling

Python owns its own scheduling.

The pipeline is triggered by the Python service itself, not by GitHub Actions.

No external cron or GitHub Actions are part of the target design.

APScheduler is used.

The active scheduler times, digest lookback window, and Slack timeout are repo-configured in:

`config/scheduler.toml`

Example:

from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

scheduler.add_job(run_daily_pipeline, 'cron', hour=7, minute=0)
scheduler.add_job(run_weekly_digest, 'cron', day_of_week='mon', hour=8)

scheduler.start()

The Python service must run continuously.  
Railway or Render must auto-restart the service if it crashes.

Manual runs can be triggered with:

python -m services.pipeline.scheduler --run-now discovery  
python -m services.pipeline.scheduler --run-now digest  

---

# Vendor Discovery

Goal

Identify companies building AI tools that support Customer Success teams.

Apify is used as the crawling utility.

Python instructs Apify which actors to run and retrieves the dataset results.

Discovery sources include:

ProductHunt  
Google search queries  
G2 category pages  
RAG web browser discovery

Each source function returns a normalised candidate structure:

company_name  
website  
raw_description  
discovery_source  

Python deduplicates candidates by domain before processing.

Google Search discovery and pipeline runtime settings are operator-configured in:

`config/pipeline_config.json`

The pipeline config controls:

queries  
Apify actor ID  
pages per query  
results per page  
max candidate domains per run  
Google result filtering and denylist heuristics  
max internal pages per vendor  
page matching and priority  
directory relevance thresholds and hints  
LLM enable flag and model  
Google Sheets worksheet name and columns  

Phase 1 discovery returns candidate records with fields such as:

candidate_domain  
candidate_title  
candidate_description  
source_query  
source_engine  
source_rank  
discovered_at  
candidate_status  
status  
discovery_notes  
drop_reason  

---

# Deduplication

Before enrichment, Python checks whether the website already exists in Supabase.

Known vendors are skipped.

Function:

is_known_vendor(website)

---

# Vendor Enrichment

Goal

Collect homepage content containing commercial intelligence.

Process

Python fetches homepage via requests  
configurable request timeout  
configurable cap of up to 5 non-homepage pages per vendor  
configurable page matching and priority for pricing, product, case studies, security, about, and integrations  
unreachable pages skipped safely  
same-domain links only  
obvious junk pages such as privacy, terms, careers, login, and docs are deprioritised or skipped  

Returned page payloads include cleaned visible text suitable for deterministic extraction.

Output structure

homepage  
pricing_page  
product_page  
case_studies_page  
about_page  
security_page  
integrations_page  
extra_pages  

---

# Page Text Extraction

Goal

Extract clean visible text from fetched vendor HTML pages.

Process

Remove scripts  
Remove navigation and footer noise  
Remove cookie-banner and consent noise where practical  
Normalise whitespace  
Support deterministic per-page truncation when needed  
Return clean readable text for rule extraction  

---

# Extraction Strategy

The target system uses two independent extraction methods.

Both operate on the same vendor page dataset.

Current checkpoint:
Level 1 deterministic extraction is active across homepage plus explored high-signal pages.
Level 2 LLM extraction is also active when OpenAI configuration is available.

Level 2 runtime knobs are repo-configured in:

`config/pipeline_config.json`

That config controls:

default OpenAI model  
request timeout  
per-page text cap  
total site-text cap  
error body truncation for logs  

Current deterministic fields include:

mission  
usp  
icp  
use_cases  
lifecycle_stages  
pricing  
free_trial  
soc2  
founded  
case_studies  
customers  
value_statements  
confidence  
directory_fit  
directory_category  
include_in_directory  

---

# Vendor Profile Builder

Goal

Merge discovery metadata, explored pages, and extracted signals into a single directory-ready vendor intelligence record.

Directory-compatible profile fields:

vendor_name  
website  
mission  
usp  
icp  
use_cases  
lifecycle_stages  
pricing  
free_trial  
soc2  
founded  
case_studies  
customers  
value_statements  
confidence  
evidence_urls  
source  
directory_fit  
directory_category  
include_in_directory  

Level 1 deterministic extraction is implemented and remains the baseline extraction layer.
Level 2 semantic extraction via LLM is active as an optional enrichment pass.

Level 1 guarantees baseline structured output even if Level 2 fails or is unavailable.

---

# Level 1 Extraction (Deterministic)

Goal

Provide reliable baseline signal extraction.

Implementation

services/extraction/vendor_intel.py

Rule-based keyword detection identifies:

use cases  
product capabilities  
value signals  

Example keyword groups:

onboarding  
churn  
retention  
support  
automation  
health  
adoption  
renewal  
expansion  
NPS  

Example value statements:

reduce churn  
increase retention  
improve adoption  
automate workflows  
improve customer health  
speed time to value  

Output structure

mission  
usp  
icp  
use_cases  
lifecycle_stages  
pricing  
free_trial  
soc2  
founded  
case_studies  
customers  
value_statements  
confidence  

This extraction method is deterministic and fully testable.

---

# Level 2 Extraction (LLM)

Goal

Generate richer commercial intelligence signals.

Implementation

services/extraction/llm_extractor.py

Python calls the OpenAI Responses API with vendor website text compiled from homepage plus explored pages.
Input size is bounded deterministically using the configured per-page and total site-text caps.

The LLM returns structured JSON containing:

mission  
usp  
use_cases  
pricing  
free_trial  
soc2  
founded  
confidence  

Example structure

{
  "is_cs_relevant": true,
  "mission": "...",
  "usp": "...",
  "use_cases": [],
  "pricing": "...",
  "free_trial": true,
  "soc2": false,
  "founded": "...",
  "confidence": "high"
}

If:

is_cs_relevant = false  
confidence = low  

the vendor is dropped.

Lifecycle stage classification is handled by Python using the extracted signals.
If the LLM call fails, deterministic extraction still produces the vendor profile.

---

# Lifecycle Classification

Python maps extracted signals to lifecycle stages.

Example mapping

health score → Adopt  
support automation → Support  
churn prediction → Renew  
NPS → Advocate  
upsell detection → Expand  
onboarding automation → Onboard  

Multiple stages may apply.

---

# Storage (Supabase)

Supabase is the canonical datastore.

Table: cs_vendors

CREATE TABLE cs_vendors (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 name TEXT NOT NULL,
 website TEXT UNIQUE NOT NULL,
 source TEXT,
 mission TEXT,
 usp TEXT,
 pricing TEXT,
 free_trial BOOLEAN,
 soc2 BOOLEAN,
 founded TEXT,
 use_cases TEXT[],
 lifecycle_stages TEXT[],
 raw_description TEXT,
 confidence TEXT,
 first_seen DATE DEFAULT CURRENT_DATE,
 last_updated TIMESTAMPTZ DEFAULT NOW(),
 is_new BOOLEAN DEFAULT TRUE
);

Upserts use:

ON CONFLICT (website) DO UPDATE

The running system currently keeps discovery candidates as explicit Phase 1 records in code and persists enriched vendor profiles to Supabase in Phase 2.

---

# Google Sheets Export

Google Sheets is a human-readable export layer.

The worksheet name and export column order are repo-configured in:

`config/pipeline_config.json`

Columns

vendor_name  
website  
source  
mission  
usp  
icp  
use_cases  
lifecycle_stages  
pricing  
free_trial  
soc2  
founded  
case_studies  
customers  
value_statements  
confidence  
evidence_urls  
directory_fit  
directory_category  
include_in_directory  

Python authenticates using a service account.

---

# Weekly Slack Digest

Every Monday the system summarises vendors discovered in the past week.

Process

Query vendors using the configured digest lookback window from `config/scheduler.toml`  
Flatten lifecycle_stages array  
Group vendors by stage  
Post grouped digest to Slack  

Example

CS AI Vendor Weekly Digest

SIGN  
Vendor | website  

ONBOARD  
Vendor | website  

SUPPORT  
Vendor | website  

ADVOCATE  
Vendor | website  

After posting the digest, vendors are marked is_new = FALSE.

---

# External API Resilience

All external API calls implement retry logic.

Apify  
OpenAI  
Supabase  
Google Sheets  
Slack  

Retry policy

3 retries  
exponential backoff  
timeout handling  

---

# Environment Variables

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

Pipeline logs include:

vendors discovered  
vendors skipped as duplicates  
vendors enriched  
vendors classified  
vendors dropped  
rows written to Sheets  
weekly digest posted  

---

# Tests

All external services are mocked.

Test coverage includes:

discovery adapters  
enrichment HTML extraction  
rule extractor  
LLM extraction parser  
classification mapping  
Supabase upsert logic  
Google Sheets export  
Slack digest formatting  
full pipeline orchestration

Run tests with:

python -m pytest

---

# Repository Structure

AI_CustomerSuccess

services  
 discovery  
 enrichment  
 extraction  
 classification  
 persistence  
 export  
 pipeline  

tests  

docs  
 product_design.md  

requirements.txt  
.env.example  
docker-compose.yml  

---

# Design Decisions

Python owns scheduling and orchestration.

Apify is used only as a crawling utility.

Supabase is the canonical datastore.

Google Sheets is an export layer.

Dual extraction architecture ensures reliability and flexibility.

Flat schema retained for MVP simplicity.

---

# Deferred Features

Deep crawl for pricing and customer pages  
Multi-table analytics schema  
LinkedIn discovery sources  
Crunchbase enrichment  
ICP extraction  
Case study extraction  
Public vendor directory frontend  
Lead capture backend
