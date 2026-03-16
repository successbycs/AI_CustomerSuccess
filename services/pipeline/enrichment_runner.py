"""Helpers for the explicit Phase 2 vendor enrichment crawl."""

from __future__ import annotations

import logging
from typing import Callable

from services.extraction.vendor_intel import VendorIntelligence
from services.persistence import supabase_client

logger = logging.getLogger(__name__)

VendorCandidate = dict[str, str]
HomepagePayload = dict[str, str | int]
ExploredPages = dict[str, object]
SheetRow = dict[str, str]
EnrichmentResult = dict[str, object]


def run_enrichment_phase(
    queued_vendor_candidates: list[VendorCandidate],
    *,
    fetch_vendor_homepage_fn: Callable[[VendorCandidate], HomepagePayload],
    explore_vendor_site_fn: Callable[[HomepagePayload], ExploredPages],
    extract_vendor_intelligence_fn: Callable[[dict[str, object]], VendorIntelligence],
    extract_vendor_intelligence_llm_fn: Callable[[dict[str, object]], object | None],
    merge_vendor_intelligence_fn: Callable[[VendorIntelligence, object | None], VendorIntelligence],
    build_vendor_profile_fn: Callable[[VendorCandidate, ExploredPages, VendorIntelligence], VendorIntelligence],
    vendor_intelligence_to_sheet_row_fn: Callable[[VendorIntelligence], SheetRow],
    upsert_vendor_result_fn: Callable[[VendorCandidate, HomepagePayload, VendorIntelligence], object] | None,
    drop_reason_fn: Callable[[VendorIntelligence | dict[str, object], object | None], str],
) -> tuple[list[SheetRow], list[EnrichmentResult], int, int]:
    """Run Phase 2 enrichment for queued vendor domains."""
    vendor_rows: list[SheetRow] = []
    enrichment_results: list[EnrichmentResult] = []
    llm_success_count = 0
    llm_fallback_count = 0

    for vendor in queued_vendor_candidates:
        vendor_name = vendor["vendor_name"]
        logger.info("Phase 2 enrichment crawl for vendor: %s", vendor_name)
        homepage_payload = fetch_vendor_homepage_fn(vendor)
        try:
            explored_pages = explore_vendor_site_fn(homepage_payload)
        except Exception as error:
            logger.warning("Site exploration failed for %s, using homepage only: %s", vendor_name, error)
            explored_pages = {"homepage": homepage_payload, "extra_pages": []}

        deterministic_intelligence = extract_vendor_intelligence_fn(explored_pages)
        llm_result = extract_vendor_intelligence_llm_fn(explored_pages)
        if llm_result is None:
            llm_fallback_count += 1
        else:
            llm_success_count += 1

        intelligence = merge_vendor_intelligence_fn(deterministic_intelligence, llm_result)
        profile = build_vendor_profile_fn(vendor, explored_pages, intelligence)
        drop_reason = drop_reason_fn(profile, llm_result)

        if drop_reason:
            logger.info("Dropping vendor %s during Phase 2: %s", profile.vendor_name, drop_reason)
            enrichment_results.append(
                {
                    "candidate_domain": vendor.get("candidate_domain", ""),
                    "status": "failed",
                    "drop_reason": drop_reason,
                    "profile": profile,
                }
            )
            continue

        if upsert_vendor_result_fn:
            try:
                upsert_vendor_result_fn(vendor, homepage_payload, profile)
            except Exception as error:
                if supabase_client.is_persistence_unavailable_error(error):
                    logger.warning("Persistence unavailable, continuing without upsert: %s", error)
                    upsert_vendor_result_fn = None
                else:
                    raise

        vendor_rows.append(vendor_intelligence_to_sheet_row_fn(profile))
        enrichment_results.append(
            {
                "candidate_domain": vendor.get("candidate_domain", ""),
                "status": "enriched",
                "drop_reason": "",
                "profile": profile,
            }
        )

    return vendor_rows, enrichment_results, llm_success_count, llm_fallback_count
