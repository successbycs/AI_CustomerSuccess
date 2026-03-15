"""Build a directory-ready vendor profile from explored site data."""

from __future__ import annotations

from services.extraction.vendor_intel import VendorIntelligence

PagePayload = dict[str, str | int]
ExploredPages = dict[str, PagePayload]


def build_vendor_profile(
    vendor: dict[str, str],
    explored_pages: ExploredPages,
    intelligence: VendorIntelligence,
) -> VendorIntelligence:
    """Merge discovery metadata and extracted signals into one profile."""
    homepage_payload = explored_pages.get("homepage", {})
    evidence_urls = _collect_evidence_urls(explored_pages)

    return VendorIntelligence(
        vendor_name=str(
            homepage_payload.get("vendor_name")
            or intelligence.vendor_name
            or vendor.get("vendor_name")
            or vendor.get("company_name")
            or ""
        ),
        website=str(homepage_payload.get("website") or intelligence.website or vendor.get("website", "")),
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
    )


def _collect_evidence_urls(explored_pages: ExploredPages) -> list[str]:
    """Collect page URLs that informed the deterministic profile."""
    evidence_urls: list[str] = []
    for page_payload in explored_pages.values():
        page_url = str(page_payload.get("website", "")).strip()
        if page_url and page_url not in evidence_urls:
            evidence_urls.append(page_url)
    return evidence_urls
