"""Thin Apify Google Search discovery adapter."""

from __future__ import annotations

import os
from urllib.parse import urlparse

GOOGLE_SEARCH_ACTOR = "apify/google-search-scraper"


def fetch_google_search(queries: list[str]) -> list[dict[str, str]]:
    """Fetch and normalize vendor candidates from Apify Google Search."""
    if not queries:
        return []

    client = get_apify_client()
    candidates: list[dict[str, str]] = []

    for query in queries:
        run = client.actor(GOOGLE_SEARCH_ACTOR).call(
            run_input={
                "queries": query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10,
            }
        )
        items = client.dataset(run["defaultDatasetId"]).list_items().items
        candidates.extend(_normalize_google_search_items(items))

    return _deduplicate_candidates_by_domain(candidates)


def discover_vendor_candidates(query: str) -> list[dict[str, str]]:
    """Compatibility wrapper for the current discovery layer."""
    return fetch_google_search([query])


def get_apify_client():
    """Create an Apify client from APIFY_API_TOKEN."""
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        raise RuntimeError("APIFY_API_TOKEN must be set")

    from apify_client import ApifyClient

    return ApifyClient(api_token)


def _normalize_google_search_items(
    items: list[dict[str, object]],
) -> list[dict[str, str]]:
    """Normalize Apify Google Search dataset items into vendor candidates."""
    candidates: list[dict[str, str]] = []

    for item in items:
        organic_results = item.get("organicResults")
        if isinstance(organic_results, list) and organic_results:
            for organic_result in organic_results:
                if not isinstance(organic_result, dict):
                    continue
                candidate = _normalize_google_search_result(organic_result)
                if candidate:
                    candidates.append(candidate)
            continue

        candidate = _normalize_google_search_result(item)
        if candidate:
            candidates.append(candidate)

    return candidates


def _normalize_google_search_result(
    item: dict[str, object],
) -> dict[str, str] | None:
    """Normalize one Google Search result into a vendor candidate."""
    website = _normalize_website(item.get("url"))
    if not website:
        return None

    company_name = _clean_text(item.get("title")) or _company_name_from_website(website)
    return {
        "company_name": company_name,
        "website": website,
        "raw_description": _clean_text(item.get("description")),
        "source": "google_search",
    }


def _deduplicate_candidates_by_domain(
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Deduplicate candidates by website domain."""
    unique_candidates: list[dict[str, str]] = []
    seen_domains: set[str] = set()

    for candidate in candidates:
        website = _normalize_website(candidate.get("website"))
        if not website:
            continue

        domain = _domain_from_website(website)
        if domain in seen_domains:
            continue

        seen_domains.add(domain)
        normalized_candidate = dict(candidate)
        normalized_candidate["website"] = website
        unique_candidates.append(normalized_candidate)

    return unique_candidates


def _normalize_website(value: object) -> str:
    """Normalize a website to a simple https://domain format."""
    if not value:
        return ""

    website = str(value).strip()
    if not website:
        return ""

    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"

    parsed = urlparse(website)
    domain = parsed.netloc.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain:
        return ""

    return f"https://{domain}"


def _domain_from_website(website: str) -> str:
    """Return the normalized domain for a website."""
    return urlparse(website).netloc.lower()


def _company_name_from_website(website: str) -> str:
    """Build a simple fallback company name from a website domain."""
    domain = _domain_from_website(website)
    return domain.split(".")[0].replace("-", " ").title()


def _clean_text(value: object) -> str:
    """Return a stripped string value."""
    if value is None:
        return ""
    return str(value).strip()
