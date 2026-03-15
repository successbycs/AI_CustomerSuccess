"""Vendor enrichment service.

This module provides functions to fetch and enrich vendor website data.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import requests

from services.extraction.page_text_extractor import extract_visible_text


def fetch_vendor_homepage(vendor: dict[str, str]) -> dict[str, str | int]:
    """Fetch the homepage for a vendor and return structured page data.

    Args:
        vendor: A dictionary with vendor information, including 'website'.

    Returns:
        A dictionary with vendor name, website, page type, status code, HTML, and extracted text.
        If fetch fails, status_code is 0 and html/text are empty.
    """
    website = vendor["website"]
    vendor_name = _resolve_vendor_name(vendor.get("vendor_name", ""), website, "")
    try:
        response = requests.get(website, timeout=10)
        html = response.text
        vendor_name = _resolve_vendor_name(vendor.get("vendor_name", ""), website, html)
        text = extract_visible_text(html)
        status_code = response.status_code
    except requests.RequestException:
        html = ""
        text = ""
        status_code = 0
    return {
        "vendor_name": vendor_name,
        "website": website,
        "source": vendor.get("source", ""),
        "page_type": "homepage",
        "status_code": status_code,
        "html": html,
        "text": text
    }


def _resolve_vendor_name(search_name: str, website: str, html_content: str) -> str:
    """Prefer homepage-derived naming, then cleaned search hint, then domain fallback."""
    for candidate in _homepage_name_candidates(html_content):
        cleaned_candidate = _clean_vendor_name_candidate(candidate)
        if cleaned_candidate:
            return cleaned_candidate

    cleaned_search_name = _clean_vendor_name_candidate(search_name)
    if cleaned_search_name:
        return cleaned_search_name

    return _company_name_from_website(website)


def _homepage_name_candidates(html_content: str) -> list[str]:
    """Return possible vendor names extracted from homepage HTML."""
    if not html_content:
        return []

    patterns = [
        r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']application-name["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']apple-mobile-web-app-title["\'][^>]+content=["\'](.*?)["\']',
        r"<title[^>]*>(.*?)</title>",
        r"<h1[^>]*>(.*?)</h1>",
    ]

    candidates: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, html_content, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        candidate = re.sub(r"<[^>]+>", " ", match.group(1))
        candidate = re.sub(r"\s+", " ", html.unescape(candidate)).strip()
        if candidate:
            candidates.append(candidate)

    return candidates


def _clean_vendor_name_candidate(candidate: str) -> str:
    """Return a vendor-like name or an empty string when the candidate looks weak."""
    normalized_candidate = re.sub(r"\s+", " ", html.unescape(candidate)).strip()
    if not normalized_candidate:
        return ""

    for separator in (" | ", " - ", " – ", " — ", ": "):
        if separator in normalized_candidate:
            for segment in normalized_candidate.split(separator):
                cleaned_segment = _clean_vendor_name_candidate(segment)
                if cleaned_segment:
                    return cleaned_segment

    lowered = normalized_candidate.lower()
    if _looks_like_article_title(lowered):
        return ""
    if len(normalized_candidate.split()) > 5:
        return ""
    if len(normalized_candidate) > 40:
        return ""

    return normalized_candidate


def _looks_like_article_title(text: str) -> bool:
    """Return True when a title looks like an article, listicle, or category page."""
    generic_name_hints = (
        "customer success platform",
        "customer success software",
        "onboarding platform",
        "customer onboarding platform",
    )
    if text in generic_name_hints:
        return True

    if re.search(r"\b\d{4}\b", text):
        return True

    article_hints = (
        "best ",
        "blog",
        "case studies",
        "case study",
        "compare",
        "comparison",
        "guide",
        "guides",
        "how to",
        "review",
        "reviews",
        "top ",
        " vs ",
    )
    return any(hint in text for hint in article_hints)


def _company_name_from_website(website: str) -> str:
    """Build a simple fallback name from the website domain."""
    domain = urlparse(website).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.split(".")[0].replace("-", " ").title()
