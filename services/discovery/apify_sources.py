"""Thin Apify Google Search discovery adapter."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_ACTOR = "apify/google-search-scraper"
DENYLISTED_DOMAINS = {
    "facebook.com",
    "gartner.com",
    "google.com",
    "instagram.com",
    "linkedin.com",
    "medium.com",
    "reddit.com",
    "substack.com",
    "twitter.com",
    "wikipedia.org",
    "x.com",
    "youtube.com",
}
ARTICLE_PATH_HINTS = (
    "/article",
    "/articles",
    "/blog",
    "/blogs",
    "/community",
    "/forum",
    "/forums",
    "/guide",
    "/guides",
    "/learn",
    "/news",
    "/resources",
)
CONTENT_HINTS = (
    "best ",
    "blog",
    "case studies",
    "case study",
    "community",
    "compare",
    "comparison",
    "forum",
    "guide",
    "guides",
    "how to",
    "listicle",
    "reddit",
    "review",
    "reviews",
    "top ",
    "vs ",
)
PRODUCT_HINTS = (
    "automation",
    "copilot",
    "platform",
    "software",
    "solution",
    "solutions",
    "tool",
    "tools",
    "workspace",
)
CUSTOMER_SUCCESS_HINTS = (
    "adoption nudge",
    "adoption nudges",
    "case study",
    "case studies",
    "churn",
    "conversational intelligence",
    "cross-sell",
    "customer health",
    "customer onboarding",
    "customer success",
    "expansion revenue",
    "forecasting",
    "handoff",
    "health score",
    "implementation portal",
    "implementation portals",
    "in-app guidance",
    "meeting summaries",
    "meeting summary",
    "nps",
    "onboarding automation",
    "playbook",
    "product walkthrough",
    "product walkthroughs",
    "psa",
    "reference management",
    "renewal",
    "retention",
    "risk alert",
    "risk alerts",
    "sales-to-cs",
    "support automation",
    "support platform",
    "ticket triage",
    "help desk",
    "agent assist",
    "knowledge base",
    "sentiment analysis",
    "stakeholder mapping",
    "time to value",
    "upsell",
    "usage analytics",
    "user education",
    "voice of customer",
    "voc",
)


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
        raw_results = _extract_google_search_results(items)
        query_candidates = _normalize_google_search_results(raw_results)
        logger.info(
            'Google Search query "%s" returned %s raw results and %s filtered candidates',
            query,
            len(raw_results),
            len(query_candidates),
        )
        candidates.extend(query_candidates)

    unique_candidates = _deduplicate_candidates_by_domain(candidates)
    logger.info(
        "Google Search deduplicated %s filtered candidates down to %s unique domains",
        len(candidates),
        len(unique_candidates),
    )
    return unique_candidates


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


def _extract_google_search_results(
    items: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Extract raw Google Search result records from dataset items."""
    results: list[dict[str, object]] = []

    for item in items:
        organic_results = item.get("organicResults")
        if isinstance(organic_results, list) and organic_results:
            for organic_result in organic_results:
                if isinstance(organic_result, dict):
                    results.append(organic_result)
            continue

        results.append(item)

    return results


def _normalize_google_search_results(
    items: list[dict[str, object]],
) -> list[dict[str, str]]:
    """Normalize raw Google Search results into vendor candidates."""
    candidates: list[dict[str, str]] = []

    for item in items:
        candidate = _normalize_google_search_result(item)
        if candidate:
            candidates.append(candidate)

    return candidates


def _normalize_google_search_result(
    item: dict[str, object],
) -> dict[str, str] | None:
    """Normalize one Google Search result into a vendor candidate."""
    raw_url = _clean_text(item.get("url"))
    if not _should_keep_google_search_result(raw_url, item):
        return None

    website = _normalize_website(raw_url)
    if not website:
        return None

    company_name = _select_company_name(
        title=_clean_text(item.get("title")),
        raw_url=raw_url,
        website=website,
    )
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


def _select_company_name(title: str, raw_url: str, website: str) -> str:
    """Prefer the domain name when the result title looks like article content."""
    if not title:
        return _company_name_from_website(website)

    parsed = urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    if _has_article_like_path(parsed.path.lower()) or _looks_like_generic_content(title.lower()) or _looks_like_listicle_title(
        title.lower()
    ):
        return _company_name_from_website(website)

    return title


def _clean_text(value: object) -> str:
    """Return a stripped string value."""
    if value is None:
        return ""
    return str(value).strip()


def _should_keep_google_search_result(raw_url: str, item: dict[str, object]) -> bool:
    """Return True when a search result looks like a vendor candidate."""
    if not raw_url:
        return False

    parsed = urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    domain = parsed.netloc.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or _is_denylisted_domain(domain):
        return False

    path = parsed.path.lower()
    title = _clean_text(item.get("title")).lower()
    description = _clean_text(item.get("description")).lower()
    text = f"{title} {description}".strip()
    if not _looks_like_customer_success_result(text):
        return False

    if _looks_like_listicle_title(title) and not _looks_like_product_description(description):
        return False

    if _has_article_like_path(path) and _looks_like_generic_content(text) and not _looks_like_product_description(
        description
    ):
        return False

    return True


def _is_denylisted_domain(domain: str) -> bool:
    """Return True when the domain is an obvious non-vendor source."""
    return domain in DENYLISTED_DOMAINS or any(
        domain.endswith(f".{blocked_domain}") for blocked_domain in DENYLISTED_DOMAINS
    )


def _has_article_like_path(path: str) -> bool:
    """Return True for paths that look like blogs, articles, or community pages."""
    return any(hint in path for hint in ARTICLE_PATH_HINTS)


def _looks_like_generic_content(text: str) -> bool:
    """Return True for titles and descriptions that read like content pages."""
    return any(hint in text for hint in CONTENT_HINTS)


def _looks_like_listicle_title(title: str) -> bool:
    """Return True when a title looks like a roundup, comparison, or review page."""
    return bool(
        re.search(r"\b\d+\b", title) or re.search(r"\b\d{4}\b", title)
    ) and any(
        hint in title for hint in ["platform", "platforms", "tool", "tools", "review", "reviews", "vendor", "vendors"]
    )


def _looks_like_product_description(description: str) -> bool:
    """Return True when the description sounds like software, not editorial content."""
    return any(hint in description for hint in PRODUCT_HINTS)


def _looks_like_customer_success_result(text: str) -> bool:
    """Return True when the result text maps to the Customer Success lifecycle."""
    return any(hint in text for hint in CUSTOMER_SUCCESS_HINTS)
