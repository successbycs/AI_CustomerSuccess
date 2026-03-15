"""Web search discovery service.

This module provides a minimal search interface for discovering candidate vendor records.

The actual search API implementation is a placeholder and should be replaced with a real
integration (e.g., Google Search API, Bing Search API, etc.) in an MVP build.
"""

from __future__ import annotations

from typing import List, Dict, Any
from urllib.parse import urlparse


def search_web(query: str) -> List[Dict[str, Any]]:
    """Return a list of candidate vendor records for the given query.

    Args:
        query: The search query string.

    Returns:
        A list of vendor candidate dictionaries.
    """

    # TODO: Replace this placeholder implementation with a real search API call.
    urls = _call_search_api(query)
    return _normalize_urls_to_vendors(urls)


def _call_search_api(query: str) -> List[str]:
    """Placeholder for search API integration.

    This function is intentionally simplistic so it can be mocked in tests.
    """

    del query  # placeholder

    # In the MVP, this would call an external API and return URLs.
    return ["https://gainsight.com", "https://vitally.io"]


def _normalize_urls_to_vendors(urls: List[str]) -> List[Dict[str, Any]]:
    """Convert URLs to normalized vendor candidate dictionaries."""
    vendors = []
    for url in urls:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        vendor_name = domain.split('.')[0].capitalize()
        website = f"https://{domain}"
        vendors.append({
            "vendor_name": vendor_name,
            "website": website,
            "source": "web_search"
        })
    return vendors
