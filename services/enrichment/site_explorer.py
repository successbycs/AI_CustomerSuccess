"""Website exploration helpers for discovering high-signal vendor pages."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

from services.config.load_config import EnrichmentConfig, load_pipeline_config
from services.extraction.page_text_extractor import extract_visible_text
from services.enrichment.vendor_fetcher import _should_skip_page

logger = logging.getLogger(__name__)

PagePayload = dict[str, str | int]
ExploredPages = dict[str, object]


@dataclass(frozen=True)
class _LinkCandidate:
    page_key: str
    url: str
    score: int


def explore_vendor_site(homepage_payload: PagePayload) -> ExploredPages:
    """Return a bounded page bundle for downstream extraction."""
    config = load_pipeline_config().enrichment
    explored_pages: ExploredPages = {
        "homepage": homepage_payload,
        "extra_pages": [],
    }
    homepage_html = str(homepage_payload.get("html", ""))
    homepage_url = str(homepage_payload.get("website", ""))

    if not homepage_html or not homepage_url:
        return explored_pages

    selected_candidates = _select_page_candidates(homepage_url, homepage_html, config)
    named_pages_added = 0

    for candidate in selected_candidates:
        if named_pages_added >= config.max_non_homepage_pages:
            break

        page_payload = _fetch_page(candidate.url, candidate.page_key, config)
        if int(page_payload["status_code"]) == 0 or int(page_payload["status_code"]) >= 400:
            continue

        if candidate.page_key in {
            "pricing_page",
            "product_page",
            "case_studies_page",
            "security_page",
            "about_page",
            "team_page",
            "contact_page",
            "demo_page",
            "help_page",
            "support_page",
            "integrations_page",
        } and candidate.page_key not in explored_pages:
            explored_pages[candidate.page_key] = page_payload
        else:
            extra_pages = explored_pages.setdefault("extra_pages", [])
            if isinstance(extra_pages, list):
                extra_pages.append(page_payload)

        named_pages_added += 1

    return explored_pages


def _select_page_candidates(
    homepage_url: str,
    homepage_html: str,
    config: EnrichmentConfig,
) -> list[_LinkCandidate]:
    """Return ranked same-domain page candidates."""
    homepage_domain = _normalized_domain(homepage_url)
    link_parser = _LinkParser()
    link_parser.feed(homepage_html)
    link_parser.close()

    best_named_candidates: dict[str, _LinkCandidate] = {}
    extra_candidates: dict[str, _LinkCandidate] = {}

    for href, anchor_text in link_parser.links:
        normalized_url = _normalize_page_url(urljoin(homepage_url, href))
        if not normalized_url or not _is_same_domain(normalized_url, homepage_domain):
            continue
        if normalized_url == _normalize_page_url(homepage_url):
            continue

        candidate = _build_candidate(normalized_url, anchor_text, config)
        if candidate is None:
            continue

        if candidate.page_key == "extra_page":
            previous_candidate = extra_candidates.get(candidate.url)
            if previous_candidate is None or candidate.score > previous_candidate.score:
                extra_candidates[candidate.url] = candidate
            continue

        previous_candidate = best_named_candidates.get(candidate.page_key)
        if previous_candidate is None or candidate.score > previous_candidate.score:
            best_named_candidates[candidate.page_key] = candidate

    ranked_named_candidates = [
        best_named_candidates[page_key]
        for page_key in config.page_priority
        if page_key in best_named_candidates
    ]
    ranked_extra_candidates = sorted(
        extra_candidates.values(),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    return ranked_named_candidates + ranked_extra_candidates


def _build_candidate(
    url: str,
    anchor_text: str,
    config: EnrichmentConfig,
) -> _LinkCandidate | None:
    """Classify and score one internal link."""
    lowered_url = url.lower()
    lowered_anchor_text = anchor_text.lower()
    combined_text = f"{lowered_url} {lowered_anchor_text}".strip()
    if not combined_text:
        return None

    is_junk = _looks_like_junk_page(combined_text, config)
    page_patterns = config.page_patterns
    matched_page_keys = [
        page_key
        for page_key, patterns in page_patterns.items()
        if any(pattern in lowered_url or pattern in lowered_anchor_text for pattern in patterns)
    ]

    if not matched_page_keys and is_junk:
        return None

    if matched_page_keys:
        page_key = min(
            matched_page_keys,
            key=lambda candidate_key: config.page_priority.index(candidate_key)
            if candidate_key in config.page_priority
            else len(config.page_priority),
        )
        score = _candidate_score(page_key, lowered_url, lowered_anchor_text, is_junk, config)
        return _LinkCandidate(page_key=page_key, url=url, score=score)

    if _looks_like_high_value_extra(combined_text):
        score = _candidate_score("extra_page", lowered_url, lowered_anchor_text, is_junk, config)
        return _LinkCandidate(page_key="extra_page", url=url, score=score)

    return None


def _candidate_score(
    page_key: str,
    lowered_url: str,
    lowered_anchor_text: str,
    is_junk: bool,
    config: EnrichmentConfig,
) -> int:
    """Return a simple deterministic score for candidate selection."""
    priority_bonus = 0
    if page_key in config.page_priority:
        priority_bonus = (len(config.page_priority) - config.page_priority.index(page_key)) * 10

    path = urlparse(lowered_url).path
    path_parts = [segment for segment in path.split("/") if segment]
    direct_path_bonus = max(0, 4 - len(path_parts))

    match_bonus = 0
    for pattern in config.page_patterns.get(page_key, ()):
        if pattern in lowered_url:
            match_bonus += 4
        if pattern in lowered_anchor_text:
            match_bonus += 3

    if page_key == "extra_page":
        match_bonus += 5

    junk_penalty = 20 if is_junk else 0
    query_penalty = 2 if "?" in lowered_url else 0
    return priority_bonus + direct_path_bonus + match_bonus - junk_penalty - query_penalty


def _looks_like_junk_page(text: str, config: EnrichmentConfig) -> bool:
    """Return True when a page looks operational, legal, or low-value."""
    return any(hint in text for hint in config.junk_hints)


def _looks_like_high_value_extra(text: str) -> bool:
    """Return True when a page looks useful but does not map to a primary slot."""
    return any(
        hint in text
        for hint in (
            "ai",
            "automation",
            "customer success",
            "contact",
            "demo",
            "help",
            "demo",
            "feature",
            "platform",
            "solution",
            "use case",
        )
    )


def _fetch_page(url: str, page_type: str, config: EnrichmentConfig) -> PagePayload:
    """Fetch a discovered page and return extracted text."""
    try:
        response = requests.get(url, timeout=config.request_timeout_seconds)
    except requests.RequestException as error:
        logger.warning("Skipping unreachable %s at %s: %s", page_type, url, error)
        return _empty_page_payload(url, page_type, status_code=0)

    if _should_skip_page(response.status_code, response.text):
        logger.info("Skipping blocked or invalid %s at %s", page_type, url)
        return _empty_page_payload(_normalize_page_url(url), page_type, status_code=response.status_code)

    normalized_url = _normalize_page_url(url)
    return {
        "vendor_name": "",
        "website": normalized_url,
        "url": normalized_url,
        "page_type": page_type,
        "status_code": response.status_code,
        "html": response.text,
        "text": extract_visible_text(response.text),
    }


def _empty_page_payload(url: str, page_type: str, *, status_code: int) -> PagePayload:
    return {
        "vendor_name": "",
        "website": url,
        "url": url,
        "page_type": page_type,
        "status_code": status_code,
        "html": "",
        "text": "",
    }


def _normalize_page_url(url: str) -> str:
    """Return a simple normalized URL without query strings."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""

    domain = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if path == "/":
        path = ""
    return f"{parsed.scheme.lower()}://{domain}{path}"


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
