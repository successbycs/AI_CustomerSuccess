"""Pipeline orchestration with optional persistence hooks."""

from __future__ import annotations

import logging
from typing import Callable

from services.discovery import web_search
from services.enrichment import vendor_fetcher
from services.extraction import vendor_intel
from services.export import google_sheets
from services.extraction.vendor_intel import VendorIntelligence
from services.persistence import supabase_client

logger = logging.getLogger(__name__)

VendorCandidate = dict[str, str]
HomepagePayload = dict[str, str | int]
SheetRow = dict[str, str]


def run_mvp_pipeline(
    query: str,
    *,
    search_web_fn: Callable[[str], list[VendorCandidate]] | None = None,
    fetch_vendor_homepage_fn: Callable[[VendorCandidate], HomepagePayload] | None = None,
    extract_vendor_intelligence_fn: Callable[[HomepagePayload], VendorIntelligence] | None = None,
    vendor_intelligence_to_sheet_row_fn: Callable[[VendorIntelligence], SheetRow] | None = None,
    vendor_exists_fn: Callable[[str], bool] | None = None,
    upsert_vendor_result_fn: Callable[[VendorCandidate, HomepagePayload, VendorIntelligence], object]
    | None = None,
) -> list[SheetRow]:
    """Run the MVP pipeline with optional persistence."""
    search_web_fn = search_web_fn or web_search.search_web
    fetch_vendor_homepage_fn = fetch_vendor_homepage_fn or vendor_fetcher.fetch_vendor_homepage
    extract_vendor_intelligence_fn = (
        extract_vendor_intelligence_fn or vendor_intel.extract_vendor_intelligence
    )
    vendor_intelligence_to_sheet_row_fn = (
        vendor_intelligence_to_sheet_row_fn
        or google_sheets.vendor_intelligence_to_sheet_row
    )

    if vendor_exists_fn is None and supabase_client.is_configured():
        vendor_exists_fn = supabase_client.vendor_exists

    if upsert_vendor_result_fn is None and supabase_client.is_configured():
        upsert_vendor_result_fn = supabase_client.upsert_vendor_result

    logger.info("Starting MVP pipeline for query: %s", query)
    vendor_rows: list[SheetRow] = []
    skipped_existing_count = 0

    vendor_candidates = search_web_fn(query)
    logger.info("Discovered %s vendor candidates after discovery filtering", len(vendor_candidates))

    for vendor in vendor_candidates:
        website = vendor["website"]
        vendor_name = vendor["vendor_name"]

        if vendor_exists_fn:
            try:
                if vendor_exists_fn(website):
                    logger.info("Skipping existing vendor: %s", vendor_name)
                    skipped_existing_count += 1
                    continue
            except Exception as error:
                if supabase_client.is_persistence_unavailable_error(error):
                    logger.warning("Persistence unavailable, continuing without deduplication: %s", error)
                    vendor_exists_fn = None
                    upsert_vendor_result_fn = None
                else:
                    raise

        logger.info("Processing vendor: %s", vendor_name)
        homepage_payload = fetch_vendor_homepage_fn(vendor)
        intelligence = extract_vendor_intelligence_fn(homepage_payload)

        if upsert_vendor_result_fn:
            try:
                upsert_vendor_result_fn(vendor, homepage_payload, intelligence)
            except Exception as error:
                if supabase_client.is_persistence_unavailable_error(error):
                    logger.warning("Persistence unavailable, continuing without upsert: %s", error)
                    upsert_vendor_result_fn = None
                    vendor_exists_fn = None
                else:
                    raise

        sheet_row = vendor_intelligence_to_sheet_row_fn(intelligence)
        if not sheet_row.get("source"):
            sheet_row["source"] = vendor.get("source", "")
        vendor_rows.append(sheet_row)

    google_sheets.append_rows_to_google_sheet(vendor_rows)
    logger.info(
        "Pipeline completed with %s sheet rows; skipped %s existing vendors",
        len(vendor_rows),
        skipped_existing_count,
    )
    return vendor_rows
