"""Website exploration helpers for discovering high-signal vendor pages."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import requests

from services.extraction.page_text_extractor import extract_visible_text

logger = logging.getLogger(__name__)

PagePayload = dict[str, str | int]
ExploredPages = dict[str, PagePayload]

PAGE_PATTERNS = {
    "pricing_page": ("pricing",),
    "product_page": ("product", "platform", "features", "solutions", "integrations"),
    "case_studies_page": (
        "case studies",
        "case-study",
        "case-study",
        "customer stories",
        "customer-story",
        "customers",
    ),
    "about_page": ("about", "company"),
    "security_page": ("security", "trust", "compliance"),
}

PAGE_PRIORITY = [
    "pricing_page",
    "product_page",
    "case_studies_page",
    "about_page",
    "security_page",
]

MAX_PAGES_PER_VENDOR = 5


def explore_vendor_site(homepage_payload: PagePayload) -> ExploredPages:
    """Return a small set of high-signal pages discovered from the homepage."""
    explored_pages: ExploredPages = {"homepage": homepage_payload}
    homepage_html = str(homepage_payload.get("html", ""))
    homepage_url = str(homepage_payload.get("website", ""))

    if not homepage_html or not homepage_url:
        return explored_pages

    candidate_links = _find_candidate_links(homepage_url, homepage_html)

    for page_key in PAGE_PRIORITY:
        if len(explored_pages) >= MAX_PAGES_PER_VENDOR:
            break

        page_url = candidate_links.get(page_key)
        if not page_url:
            continue

        page_payload = _fetch_page(page_url, page_key)
        if int(page_payload["status_code"]) == 0 or int(page_payload["status_code"]) >= 400:
            continue
        explored_pages[page_key] = page_payload

    return explored_pages


def _find_candidate_links(homepage_url: str, homepage_html: str) -> dict[str, str]:
    """Return same-domain candidate links for high-signal vendor pages."""
    homepage_domain = _normalized_domain(homepage_url)
    hrefs = re.findall(
        r"<a[^>]+href=[\"'](.*?)[\"']",
        homepage_html,
        flags=re.IGNORECASE,
    )

    candidate_links: dict[str, str] = {}
    for href in hrefs:
        absolute_url = urljoin(homepage_url, href)
        if not _is_same_domain(absolute_url, homepage_domain):
            continue

        lowered_url = absolute_url.lower()
        for page_key, patterns in PAGE_PATTERNS.items():
            if page_key in candidate_links:
                continue
            if any(pattern in lowered_url for pattern in patterns):
                candidate_links[page_key] = _normalize_page_url(absolute_url)
                break

    return candidate_links


def _fetch_page(url: str, page_type: str) -> PagePayload:
    """Fetch a discovered page and return extracted text."""
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as error:
        logger.warning("Skipping unreachable %s at %s: %s", page_type, url, error)
        return {
            "vendor_name": "",
            "website": url,
            "page_type": page_type,
            "status_code": 0,
            "html": "",
            "text": "",
        }

    return {
        "vendor_name": "",
        "website": _normalize_page_url(url),
        "page_type": page_type,
        "status_code": response.status_code,
        "html": response.text,
        "text": extract_visible_text(response.text),
    }


def _normalize_page_url(url: str) -> str:
    """Return a simple normalized URL without query strings."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if path == "/":
        path = ""
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _normalized_domain(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        return domain[4:]
    return domain


def _is_same_domain(url: str, homepage_domain: str) -> bool:
    return _normalized_domain(url) == homepage_domain
