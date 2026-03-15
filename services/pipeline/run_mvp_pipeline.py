"""Beginner-friendly MVP pipeline orchestration."""

from __future__ import annotations

import logging

from services.discovery import web_search
from services.enrichment import vendor_fetcher
from services.extraction import vendor_intel
from services.export import google_sheets

logger = logging.getLogger(__name__)


def run_mvp_pipeline(query: str) -> list[dict[str, str]]:
    """Run the MVP vendor intelligence pipeline for a search query."""
    logger.info("Starting MVP pipeline for query: %s", query)
    vendor_rows: list[dict[str, str]] = []

    vendor_candidates = web_search.search_web(query)
    logger.info("Discovered %s vendor candidates", len(vendor_candidates))

    for vendor in vendor_candidates:
        logger.info("Processing vendor: %s", vendor["vendor_name"])
        homepage_payload = vendor_fetcher.fetch_vendor_homepage(vendor)
        intelligence = vendor_intel.extract_vendor_intelligence(homepage_payload)
        sheet_row = google_sheets.vendor_intelligence_to_sheet_row(intelligence)
        vendor_rows.append(sheet_row)

    logger.info("Pipeline completed with %s sheet rows", len(vendor_rows))
    return vendor_rows
