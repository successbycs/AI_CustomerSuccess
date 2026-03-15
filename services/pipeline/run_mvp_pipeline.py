"""Beginner-friendly MVP pipeline orchestration."""

from __future__ import annotations

from services.discovery import web_search
from services.enrichment import vendor_fetcher
from services.extraction import vendor_intel
from services.export import google_sheets
from services.persistence import supabase_client
from services.pipeline import orchestrator


def run_mvp_pipeline(query: str) -> list[dict[str, str]]:
    """Run the MVP vendor intelligence pipeline for a search query."""
    vendor_exists_fn = None
    upsert_vendor_result_fn = None

    if supabase_client.is_configured():
        vendor_exists_fn = supabase_client.vendor_exists
        upsert_vendor_result_fn = supabase_client.upsert_vendor_result

    return orchestrator.run_mvp_pipeline(
        query,
        search_web_fn=web_search.search_web,
        fetch_vendor_homepage_fn=vendor_fetcher.fetch_vendor_homepage,
        extract_vendor_intelligence_fn=vendor_intel.extract_vendor_intelligence,
        vendor_intelligence_to_sheet_row_fn=google_sheets.vendor_intelligence_to_sheet_row,
        vendor_exists_fn=vendor_exists_fn,
        upsert_vendor_result_fn=upsert_vendor_result_fn,
    )
