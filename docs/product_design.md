# Product Design (MVP)

This document describes the Minimum Viable Product (MVP) architecture for the **AI Customer Success Vendor Intelligence system**.

The system discovers companies offering AI-enabled products that support the Customer Success lifecycle, enriches vendor websites to collect key information, extracts structured commercial intelligence, and produces a structured dataset that can be shared in Google Sheets.

The **core unit of analysis is the vendor/company**, not individual web pages.

The objective is to build a **structured dataset of AI-enabled Customer Success vendors**.

---

# Primary MVP Deliverable

The primary output of this system is a **Google Sheet containing AI-enabled Customer Success vendors and their commercial intelligence signals**.

Each row represents a vendor and includes fields such as:

Vendor name  
Website  
Discovery source  
AI capability summary  
Customer Success lifecycle stages supported  
ICP signals  
Use cases  
Customer brands / case studies  
Value statements  
Pricing signals  
Evidence URLs  

The Google Sheet acts as a **research dataset that can be shared, filtered, and expanded as new vendors are discovered**.

The entire system is designed to populate and improve this dataset.

---

# System Pipeline

The system follows a vendor intelligence pipeline:

Vendor Discovery  
↓  
Vendor Enrichment  
↓  
Vendor Intelligence Extraction  
↓  
Structured Vendor Dataset  
↓  
Google Sheets Output

Storage in Postgres supports structured querying and historical analysis.

---

# 1) Vendor Discovery

## Goal

Identify companies offering AI-enabled products that support Customer Success teams or the Customer Success lifecycle.

## Sources

Initial MVP sources:

Web search APIs (Google / Bing)

Future sources may include:

Product Hunt launches  
AI startup announcements  
GitHub repositories related to Customer Success automation  
SaaS directories  
startup databases

## Process

1. Generate search queries targeting AI tools for Customer Success.

Example queries:

"AI customer success platform"  
"AI churn prediction software"  
"AI customer onboarding automation"  
"AI customer support automation SaaS"

2. Use a search API to retrieve results.

3. Extract candidate vendor signals including:

company_name  
product_name  
website  
description  
discovery source  

4. Normalize vendors and deduplicate by domain.

## Deliverables

Candidate vendor records

company_name  
product_name  
website  
source  
description  
discovered_at

---

# 2) Vendor Enrichment (Website Collection)

## Goal

Collect key website pages that contain commercial information about the vendor.

The objective is to gather the pages most likely to contain intelligence signals such as value propositions, pricing, and customer references.

## Target Pages

For each vendor website attempt to collect:

homepage  
product page  
pricing page  
customers page  
case studies page  
solutions page

These pages typically contain the highest density of commercial intelligence.

## Enrichment Modes

Two enrichment modes are supported.

### Mode 1 (MVP)

Simple HTTP fetch using Python requests.

This collects:

homepage HTML  
visible page text  
basic metadata

### Mode 2 (Upgrade)

Apify-based website crawling.

Apify can be used to collect structured website content including:

homepage  
pricing pages  
customer case studies  
product documentation  
solutions pages

Apify improves coverage and reliability but is **not required for the MVP**.

The enrichment layer should remain modular so either method can be used.

## Process

1. Fetch homepage HTML.
2. Identify relevant internal links such as:

/product  
/pricing  
/customers  
/case-studies  
/solutions  

3. Fetch those pages.
4. Extract raw HTML, visible text, and metadata.

## Deliverables

Vendor page records

vendor_id  
url  
page_type  
html  
text  
title  
crawl_date

---

# 3) Vendor Intelligence Extraction

## Goal

Extract structured commercial intelligence about each vendor.

Extraction converts raw website text into structured vendor signals.

## Vendor Metadata

Extract:

company_name  
product_name  
AI capability description  
product category

## Customer Success Lifecycle Coverage

Identify which Customer Success lifecycle stages the product supports:

onboarding  
adoption  
support  
health scoring  
churn prediction  
renewals  
expansion  
voice of customer

## ICP (Ideal Customer Profile)

Extract signals describing the target customer:

industry  
company size  
target segment  
buyer persona

## Case Studies

Extract:

customer brand names  
challenge  
solution  
results or outcomes

## Value Statements

Identify positioning and value claims such as:

reduce churn  
increase adoption  
automate support workflows  
reduce time to value  
improve customer health visibility

## Pricing Signals

Extract indicators such as:

pricing tiers  
entry price  
free trial availability  
enterprise-only pricing  
usage-based pricing

## Extraction Approach

Extraction may combine:

rule-based pattern matching  
keyword detection  
LLM-assisted classification

MVP extraction should start with **simple rule-based logic** and evolve toward LLM-based extraction.

---

# 4) Storage (Postgres)

## Goal

Persist structured vendor intelligence in a relational database for reliable querying and reporting.

## Core Tables

vendors

id  
company_name  
product_name  
website  
source  
description  
discovered_at  

vendor_pages

id  
vendor_id  
url  
page_type  
html  
text  
crawl_date  

vendor_icp

vendor_id  
industry  
company_size  
buyer_persona  
segment  

vendor_case_studies

vendor_id  
customer_name  
challenge  
solution  
results  

vendor_value_statements

vendor_id  
statement  
category  

vendor_pricing

vendor_id  
tier  
price  
details  

vendor_lifecycle

vendor_id  
stage  
confidence

---

# 5) Reporting (Google Sheets)

## Goal

Provide a simple, shareable dataset and dashboard interface for business users.

The Google Sheet is the **primary MVP output**.

## Process

1. Query structured vendor intelligence from Postgres.
2. Export results as a flat dataset.
3. Push rows into Google Sheets using the Google Sheets API.
4. Build dashboards and filters within Google Sheets.

## Example Reports

AI tools supporting Customer Success lifecycle stages

Vendors by lifecycle stage coverage

Pricing comparison across vendors

Most common value propositions

Vendors targeting specific ICP segments

---

# Architecture Diagram

flowchart TD

A[Vendor Discovery (Web Search)]  
--> B[Vendor Enrichment (Website Collection / Apify Optional)]

B --> C[Vendor Intelligence Extraction]

C --> D[Postgres Vendor Intelligence Database]

D --> E[Google Sheets Dataset]

---

# MVP Execution Plan

1. Implement vendor discovery using web search queries.
2. Normalize and deduplicate vendor domains.
3. Fetch vendor homepage content.
4. Extract basic vendor intelligence signals.
5. Produce structured vendor records.
6. Export vendor rows to Google Sheets.

Once this pipeline works end-to-end, enrichment can be expanded using Apify to collect deeper vendor intelligence.