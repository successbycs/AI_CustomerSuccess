"""Build a directory-ready vendor profile from explored site data."""

from __future__ import annotations

from services.extraction.directory_relevance import evaluate_directory_relevance
from services.extraction.vendor_intel import VendorIntelligence

PagePayload = dict[str, str | int]
ExploredPages = dict[str, object]


def build_vendor_profile(
    vendor: dict[str, str],
    explored_pages: ExploredPages,
    intelligence: VendorIntelligence,
) -> VendorIntelligence:
    """Merge discovery metadata and extracted signals into one profile."""
    homepage_payload = explored_pages.get("homepage", {})
    evidence_urls = _collect_evidence_urls(explored_pages)
    directory_fit, directory_category, include_in_directory = evaluate_directory_relevance(intelligence)

    return VendorIntelligence(
        vendor_name=str(
            homepage_payload.get("vendor_name")
            or intelligence.vendor_name
            or vendor.get("vendor_name")
            or vendor.get("company_name")
            or ""
        ),
        website=str(
            homepage_payload.get("website")
            or homepage_payload.get("url")
            or intelligence.website
            or vendor.get("website", "")
        ),
        source=vendor.get("source", intelligence.source),
        mission=intelligence.mission,
        usp=intelligence.usp,
        icp=intelligence.icp,
        use_cases=intelligence.use_cases,
        lifecycle_stages=intelligence.lifecycle_stages,
        pricing=intelligence.pricing,
        free_trial=intelligence.free_trial,
        soc2=intelligence.soc2,
        founded=intelligence.founded,
        case_studies=intelligence.case_studies,
        customers=intelligence.customers,
        value_statements=intelligence.value_statements,
        confidence=intelligence.confidence,
        evidence_urls=evidence_urls or intelligence.evidence_urls,
        directory_fit=directory_fit,
        directory_category=directory_category,
        include_in_directory=include_in_directory,
    )


def _collect_evidence_urls(explored_pages: ExploredPages) -> list[str]:
    """Collect page URLs that informed the deterministic profile."""
    evidence_urls: list[str] = []
    for page_payload in _iter_page_payloads(explored_pages):
        page_url = str(page_payload.get("website") or page_payload.get("url") or "").strip()
        if page_url and page_url not in evidence_urls:
            evidence_urls.append(page_url)
    return evidence_urls


def _iter_page_payloads(explored_pages: ExploredPages) -> list[PagePayload]:
    page_payloads: list[PagePayload] = []
    for page_value in explored_pages.values():
        if isinstance(page_value, dict):
            page_payloads.append(page_value)
            continue
        if isinstance(page_value, list):
            for item in page_value:
                if isinstance(item, dict):
                    page_payloads.append(item)
    return page_payloads
