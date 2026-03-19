"""Build a directory-ready vendor profile from explored site data."""

from __future__ import annotations

from urllib.parse import urlparse

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
    vendor_name = str(
        homepage_payload.get("vendor_name")
        or intelligence.vendor_name
        or vendor.get("vendor_name")
        or vendor.get("company_name")
        or ""
    )
    website = str(
        homepage_payload.get("website")
        or homepage_payload.get("url")
        or intelligence.website
        or vendor.get("website", "")
    )
    directory_fit, directory_category, include_in_directory = evaluate_directory_relevance(intelligence)
    if _looks_like_invalid_directory_vendor(vendor_name, website, intelligence):
        directory_fit = "low"
        directory_category = "infra"
        include_in_directory = False

    return VendorIntelligence(
        vendor_name=vendor_name,
        website=website,
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
        products=intelligence.products,
        leadership=intelligence.leadership,
        company_hq=intelligence.company_hq,
        contact_email=intelligence.contact_email,
        contact_page_url=intelligence.contact_page_url,
        demo_url=intelligence.demo_url,
        help_center_url=intelligence.help_center_url,
        support_url=intelligence.support_url,
        about_url=intelligence.about_url,
        team_url=intelligence.team_url,
        integration_categories=intelligence.integration_categories,
        integrations=intelligence.integrations,
        support_signals=intelligence.support_signals,
        case_studies=intelligence.case_studies,
        case_study_details=intelligence.case_study_details,
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


def _looks_like_invalid_directory_vendor(
    vendor_name: str,
    website: str,
    intelligence: VendorIntelligence,
) -> bool:
    """Return True when a profile still looks like content, docs, or blocked junk."""
    lowered_name = vendor_name.strip().lower()
    lowered_signal_text = " ".join(
        [
            intelligence.mission,
            intelligence.usp,
            *intelligence.use_cases,
            *intelligence.value_statements,
        ]
    ).lower()
    domain = urlparse(website).netloc.lower()

    if any(marker in lowered_signal_text for marker in ("403 forbidden", "access denied", "just a moment")):
        return True
    if _looks_like_article_title(lowered_name):
        return True
    if _has_noise_subdomain(domain):
        return True
    if not intelligence.lifecycle_stages and not intelligence.use_cases and not intelligence.icp and not any(
        hint in lowered_signal_text for hint in ("customer success", "renewal", "onboarding", "adoption", "churn")
    ):
        return True
    return False


def _looks_like_article_title(text: str) -> bool:
    if not text:
        return True
    article_hints = (
        "what is ",
        "how to ",
        "best ",
        "top ",
        "guide",
        "blog",
        "review",
        "reviews",
        "compare",
        "comparison",
        "maximizing",
        "maximize ",
        "releases for ",
    )
    return len(text.split()) > 5 or any(hint in text for hint in article_hints)


def _has_noise_subdomain(domain: str) -> bool:
    return domain.startswith(
        (
            "academy.",
            "blog.",
            "community.",
            "developers.",
            "docs.",
            "help.",
            "knowledge.",
            "learn.",
            "support.",
        )
    )
