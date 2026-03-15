"""Helpers for extracting readable text from vendor HTML pages."""

from __future__ import annotations

import html
import re

_REMOVAL_PATTERNS = [
    r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
    r"<(nav|footer|aside)[^>]*>.*?</\1>",
    r"<header[^>]*>.*?</header>",
    r"<form[^>]*>.*?</form>",
    (
        r"<([a-z0-9]+)[^>]*(?:class|id)=[\"'][^\"']*"
        r"(?:nav|menu|footer|breadcrumb|sidebar|cookie|newsletter|social)"
        r"[^\"']*[\"'][^>]*>.*?</\1>"
    ),
]


def extract_visible_text(html_content: str) -> str:
    """Return cleaned visible text from HTML for deterministic extraction."""
    if not html_content:
        return ""

    cleaned_html = html_content
    for pattern in _REMOVAL_PATTERNS:
        cleaned_html = re.sub(
            pattern,
            " ",
            cleaned_html,
            flags=re.IGNORECASE | re.DOTALL,
        )

    cleaned_html = re.sub(r"<[^>]+>", " ", cleaned_html)
    cleaned_html = html.unescape(cleaned_html)
    return re.sub(r"\s+", " ", cleaned_html).strip()
