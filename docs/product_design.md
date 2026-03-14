# Product Design (MVP)

This document describes the Minimum Viable Product (MVP) architecture for the AI Customer Success system.

## Overview

The system is designed to discover relevant customer success content on the web, enrich it via crawling, extract key artifacts (ICP, case studies, value statements, pricing), store results in Postgres, and enable reporting via Google Sheets.

---

## 1) Discovery (Web Search)

### Goal
Find potential customer success resources (e.g., case study pages, pricing pages, testimonials) by issuing targeted web searches.

### Process
1. Generate search queries based on target industry/vertical and product keywords.
2. Use a web search API (e.g., Google Search API, Bing Search API) to retrieve URLs.
3. Filter and prioritize results (e.g., domain trust, relevance, last updated).


---

## 2) Enrichment (Website Crawling)

### Goal
Fetch full content for discovered URLs and gather additional linked pages for context.

### Process
1. Fetch the HTML of each discovered URL.
2. Crawl internal links (within the same domain) up to a depth limit.
3. Extract raw text, metadata (title, meta description), and structured data (JSON-LD, schema.org snippets).

### Deliverables
- Full HTML/text for each crawled page
- Seed URL and crawler link graph
- Page metadata (title, description, canonical URL)


---

## 3) Extraction (ICP, Case Studies, Value Statements, Pricing)

### Goal
Extract structured data and key information from crawled content.

### Artifacts
- **ICP (Ideal Customer Profile)**: industry, company size, use cases, pain points, buyer personas.
- **Case Studies**: customer name, challenge, solution, results, quotes.
- **Value Statements**: feature benefits, ROI claims, differentiators.
- **Pricing**: tiers, unit pricing, free/paid features, contract terms.

### Process
1. Apply NLP/LLM pipelines to parse the enriched content.
2. Use templates or extraction rules to identify relevant sections.
3. Normalize entities and store structured records.


---

## 4) Storage (Postgres)

### Goal
Persist all extracted artifacts and supporting metadata in a relational database for reliable querying and reporting.

### Core Tables (Example)
- `sources` (seed URL, domain, discovered_at)
- `pages` (url, title, html, text, crawl_date)
- `icp_profiles` (source_id, industry, company_size, pain_points)
- `case_studies` (source_id, customer_name, challenge, solution, results)
- `value_statements` (source_id, statement, category)
- `pricing_plans` (source_id, tier, price, details)


---

## 5) Reporting (Google Sheets)

### Goal
Provide easy, shareable reporting and dashboards for business users.

### Process
1. Export selected Postgres query results to CSV.
2. Push data to Google Sheets via Google Sheets API (or use a sync tool).
3. Build dashboards in Google Sheets with charts, filters, and summary tables.

### Example Reports
- Top 10 value statements by frequency
- ICP segments with most case studies
- Pricing comparison matrix across competitors


---

## Architecture Diagram

```mermaid
flowchart TD
  A[Discovery Service\n(Web Search API)] -->|URLs| B[Enrichment Service\n(Web Crawler)]
  B -->|Page Content| C[Extraction Service\n(LLM/NLP)]
  C -->|Structured Records| D[Postgres Storage]
  D -->|Export/Sync| E[Google Sheets Reporting]

  subgraph ""
    direction LR
    A -->|seed queries| A
  end

  click A "" "Discovery uses search APIs"
  click B "" "Enrichment crawls and collects content"
  click C "" "Extraction identifies ICP/case studies/pricing"
  click D "" "Postgres stores normalized data"
  click E "" "Sheets for reporting"
```

---

## Next Steps (MVP Execution)

1. Implement a lightweight discovery service that can run search queries and persist URLs.
2. Build a simple web crawler that fetches pages and stores raw HTML.
3. Develop extraction routines (initially rule-based, evolving to LLM-based) for ICP and case study data.
4. Create a Postgres schema and migration strategy.
5. Add a reporting pipeline to push results into Google Sheets.
