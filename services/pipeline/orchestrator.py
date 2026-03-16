"""Pipeline orchestration with optional persistence hooks."""

from __future__ import annotations

import logging
from typing import Callable

from services.discovery import web_search
from services.enrichment import site_explorer
from services.enrichment import vendor_fetcher
from services.extraction import llm_extractor
from services.extraction import merge_results
from services.extraction import vendor_intel
from services.extraction import vendor_profile_builder
from services.export import google_sheets
from services.extraction.vendor_intel import VendorIntelligence
from services.persistence import supabase_client
from services.pipeline import discovery_runner
from services.pipeline import enrichment_runner

logger = logging.getLogger(__name__)

VendorCandidate = dict[str, str]
HomepagePayload = dict[str, str | int]
ExploredPages = dict[str, object]
SheetRow = dict[str, str]


def run_mvp_pipeline(
    query: str | list[str] | None,
    *,
    search_web_candidates_fn: Callable[[str | list[str] | None], list[dict[str, object]]] | None = None,
    fetch_vendor_homepage_fn: Callable[[VendorCandidate], HomepagePayload] | None = None,
    explore_vendor_site_fn: Callable[[HomepagePayload], ExploredPages] | None = None,
    extract_vendor_intelligence_fn: Callable[[dict[str, object]], VendorIntelligence] | None = None,
    extract_vendor_intelligence_llm_fn: Callable[[dict[str, object]], object | None] | None = None,
    merge_vendor_intelligence_fn: Callable[[VendorIntelligence, object | None], VendorIntelligence] | None = None,
    build_vendor_profile_fn: Callable[[VendorCandidate, ExploredPages, VendorIntelligence], VendorIntelligence]
    | None = None,
    vendor_intelligence_to_sheet_row_fn: Callable[[VendorIntelligence], SheetRow] | None = None,
    vendor_exists_fn: Callable[[str], bool] | None = None,
    upsert_vendor_result_fn: Callable[[VendorCandidate, HomepagePayload, VendorIntelligence], object]
    | None = None,
    run_discovery_phase_fn: Callable[..., tuple[list[dict[str, object]], list[VendorCandidate], int]] | None = None,
    run_enrichment_phase_fn: Callable[..., tuple[list[SheetRow], list[dict[str, object]], int, int]] | None = None,
) -> list[SheetRow]:
    """Run the MVP pipeline with optional persistence."""
    search_web_candidates_fn = search_web_candidates_fn or web_search.search_web_candidates
    fetch_vendor_homepage_fn = fetch_vendor_homepage_fn or vendor_fetcher.fetch_vendor_homepage
    explore_vendor_site_fn = explore_vendor_site_fn or site_explorer.explore_vendor_site
    extract_vendor_intelligence_fn = (
        extract_vendor_intelligence_fn or vendor_intel.extract_vendor_intelligence
    )
    extract_vendor_intelligence_llm_fn = (
        extract_vendor_intelligence_llm_fn or llm_extractor.extract_vendor_intelligence
    )
    merge_vendor_intelligence_fn = (
        merge_vendor_intelligence_fn or merge_results.merge_vendor_intelligence
    )
    build_vendor_profile_fn = build_vendor_profile_fn or vendor_profile_builder.build_vendor_profile
    vendor_intelligence_to_sheet_row_fn = (
        vendor_intelligence_to_sheet_row_fn
        or google_sheets.vendor_intelligence_to_sheet_row
    )
    run_discovery_phase_fn = run_discovery_phase_fn or discovery_runner.run_discovery_phase
    run_enrichment_phase_fn = run_enrichment_phase_fn or enrichment_runner.run_enrichment_phase

    if vendor_exists_fn is None and supabase_client.is_configured():
        vendor_exists_fn = supabase_client.vendor_exists

    if upsert_vendor_result_fn is None and supabase_client.is_configured():
        upsert_vendor_result_fn = supabase_client.upsert_vendor_result

    logger.info("Starting MVP pipeline for query set: %s", _format_query_log(query))
    llm_extractor.start_pipeline_run()
    llm_extractor.log_runtime_configuration()
    try:
        candidate_records, queued_vendor_candidates, skipped_existing_count = run_discovery_phase_fn(
            query,
            fetch_candidate_records_fn=search_web_candidates_fn,
            vendor_exists_fn=vendor_exists_fn,
        )
    except Exception as error:
        if supabase_client.is_persistence_unavailable_error(error):
            logger.warning("Persistence unavailable, continuing without deduplication: %s", error)
            vendor_exists_fn = None
            upsert_vendor_result_fn = None
            candidate_records, queued_vendor_candidates, skipped_existing_count = run_discovery_phase_fn(
                query,
                fetch_candidate_records_fn=search_web_candidates_fn,
                vendor_exists_fn=None,
            )
        else:
            raise

    logger.info(
        "Phase 1 discovery produced %s candidate domains and queued %s vendors for enrichment",
        len(candidate_records),
        len(queued_vendor_candidates),
    )

    vendor_rows, enrichment_results, llm_success_count, llm_fallback_count = run_enrichment_phase_fn(
        queued_vendor_candidates,
        fetch_vendor_homepage_fn=fetch_vendor_homepage_fn,
        explore_vendor_site_fn=explore_vendor_site_fn,
        extract_vendor_intelligence_fn=extract_vendor_intelligence_fn,
        extract_vendor_intelligence_llm_fn=extract_vendor_intelligence_llm_fn,
        merge_vendor_intelligence_fn=merge_vendor_intelligence_fn,
        build_vendor_profile_fn=build_vendor_profile_fn,
        vendor_intelligence_to_sheet_row_fn=vendor_intelligence_to_sheet_row_fn,
        upsert_vendor_result_fn=upsert_vendor_result_fn,
        drop_reason_fn=_drop_reason,
    )

    _apply_enrichment_statuses(candidate_records, enrichment_results)

    google_sheets.append_rows_to_google_sheet(vendor_rows)
    logger.info(
        "LLM stage summary: successes=%s fallback_or_skipped=%s",
        llm_success_count,
        llm_fallback_count,
    )
    logger.info(
        "Pipeline completed with %s sheet rows; skipped %s existing vendors",
        len(vendor_rows),
        skipped_existing_count,
    )
    return vendor_rows


def _drop_reason(profile: VendorIntelligence | dict[str, object], llm_result: object | None) -> str:
    """Return a drop reason when a profile should not be persisted or exported."""
    llm_relevant = getattr(llm_result, "is_cs_relevant", None)
    if llm_relevant is False:
        return "llm_marked_non_cs_relevant"

    confidence = _profile_confidence(profile).lower()
    if confidence == "low":
        return "low_confidence"

    return ""


def _profile_confidence(profile: VendorIntelligence | dict[str, object]) -> str:
    if isinstance(profile, dict):
        return str(profile.get("confidence", ""))
    return profile.confidence


def _profile_name(profile: VendorIntelligence | dict[str, object]) -> str:
    if isinstance(profile, dict):
        return str(profile.get("vendor_name", ""))
    return profile.vendor_name


def _format_query_log(query: str | list[str] | None) -> str:
    """Format one or more discovery queries for logging."""
    if query is None:
        return "config default queries"
    if isinstance(query, str):
        return query
    return ", ".join(query)


def _count_page_payloads(explored_pages: ExploredPages) -> int:
    """Return the number of fetched page payloads in an explored page bundle."""
    page_count = 0
    for page_value in explored_pages.values():
        if isinstance(page_value, dict):
            page_count += 1
            continue
        if isinstance(page_value, list):
            page_count += sum(1 for item in page_value if isinstance(item, dict))
    return page_count


def _apply_enrichment_statuses(
    candidate_records: list[dict[str, object]],
    enrichment_results: list[dict[str, object]],
) -> None:
    """Update candidate record statuses from Phase 2 results."""
    result_by_domain = {
        str(result.get("candidate_domain", "")): result
        for result in enrichment_results
    }
    for candidate_record in candidate_records:
        candidate_domain = str(candidate_record.get("candidate_domain", ""))
        if candidate_domain in result_by_domain:
            result = result_by_domain[candidate_domain]
            status = str(result.get("status", ""))
            candidate_record["candidate_status"] = status
            candidate_record["status"] = status
            drop_reason = str(result.get("drop_reason", "")).strip()
            if drop_reason:
                candidate_record["drop_reason"] = drop_reason
