"""Vendor enrichment service.

This module provides functions to fetch and enrich vendor website data.
"""

from __future__ import annotations

import re
import requests


def fetch_vendor_homepage(vendor: dict[str, str]) -> dict[str, str | int]:
    """Fetch the homepage for a vendor and return structured page data.

    Args:
        vendor: A dictionary with vendor information, including 'website'.

    Returns:
        A dictionary with vendor name, website, page type, status code, HTML, and extracted text.
        If fetch fails, status_code is 0 and html/text are empty.
    """
    website = vendor["website"]
    try:
        response = requests.get(website, timeout=10)
        html = response.text
        # Basic text extraction: remove HTML tags
        text = re.sub(r'<[^>]+>', '', html).strip()
        status_code = response.status_code
    except requests.RequestException:
        html = ""
        text = ""
        status_code = 0
    return {
        "vendor_name": vendor["vendor_name"],
        "website": website,
        "page_type": "homepage",
        "status_code": status_code,
        "html": html,
        "text": text
    }
