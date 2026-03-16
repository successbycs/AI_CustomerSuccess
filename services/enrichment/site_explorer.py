"""Website exploration helpers for discovering high-signal vendor pages."""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

from services.extraction.page_text_extractor import extract_visible_text
from services.enrichment.vendor_fetcher import _should_skip_page

logger = logging.getLogger(__name__)

PagePayload = dict[str, str | int]
ExploredPages = dict[str, PagePayload]

PAGE_PATTERNS = {
    "pricing_page": ("pricing",),
    "product_page": ("product", "platform", "features", "solutions", "integrations"),
    "case_studies_page": (
        "case studies",
        "case-study",
        "case-studies",
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
    link_parser = _LinkParser()
    link_parser.feed(homepage_html)
    link_parser.close()

    candidate_links: dict[str, str] = {}
    for href, anchor_text in link_parser.links:
        absolute_url = urljoin(homepage_url, href)
        if not _is_same_domain(absolute_url, homepage_domain):
            continue

        lowered_url = absolute_url.lower()
        lowered_anchor_text = anchor_text.lower()
        for page_key, patterns in PAGE_PATTERNS.items():
            if page_key in candidate_links:
                continue
            if any(pattern in lowered_url or pattern in lowered_anchor_text for pattern in patterns):
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

    if _should_skip_page(response.status_code, response.text):
        return {
            "vendor_name": "",
            "website": _normalize_page_url(url),
            "page_type": page_type,
            "status_code": response.status_code,
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


class _LinkParser(HTMLParser):
    """Collect homepage links and their visible anchor text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._current_href = ""
        self._current_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        self._current_href = ""
        self._current_parts = []
        for name, value in attrs:
            if name.lower() == "href" and value:
                self._current_href = value.strip()
                break

    def handle_data(self, data: str) -> None:
        if not self._current_href:
            return

        cleaned = " ".join(data.split())
        if cleaned:
            self._current_parts.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return

        anchor_text = " ".join(self._current_parts).strip()
        self.links.append((self._current_href, anchor_text))
        self._current_href = ""
        self._current_parts = []
