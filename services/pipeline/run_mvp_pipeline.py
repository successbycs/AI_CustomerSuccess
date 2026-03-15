"""Beginner-friendly MVP pipeline orchestration."""

from __future__ import annotations

from services.discovery import web_search
from services.enrichment import vendor_fetcher
from services.extraction import vendor_intel
from services.export import google_sheets


def run_mvp_pipeline(query: str) -> list[dict]:
    """Run the MVP vendor intelligence pipeline for a search query."""
    vendor_rows = []

    vendor_candidates = web_search.search_web(query)
    for vendor in vendor_candidates:
        homepage_payload = vendor_fetcher.fetch_vendor_homepage(vendor)
        intelligence = vendor_intel.extract_vendor_intelligence(homepage_payload)
        sheet_row = google_sheets.vendor_intelligence_to_sheet_row(intelligence)
        vendor_rows.append(sheet_row)

    return vendor_rows
