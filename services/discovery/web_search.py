"""Compatibility wrapper around the Apify-based discovery layer."""

from __future__ import annotations

from services.discovery import apify_sources


def search_web(query: str) -> list[dict[str, str]]:
    """Return vendor candidates using Apify Google Search."""
    candidates = apify_sources.fetch_google_search([query])
    return [
        {
            "company_name": candidate["company_name"],
            "vendor_name": candidate["company_name"],
            "website": candidate["website"],
            "source": candidate["source"],
            "raw_description": candidate.get("raw_description", ""),
        }
        for candidate in candidates
    ]
