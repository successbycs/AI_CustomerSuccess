"""Tests for the discovery web search module."""

from services.discovery import web_search


def test_search_web_calls_apify_google_search_and_returns_vendor_records(monkeypatch):
    called = {}

    def fake_fetch_google_search(queries: list[str]):
        called["queries"] = queries
        return [
            {
                "company_name": "Gainsight",
                "website": "https://gainsight.com",
                "raw_description": "Customer success platform",
                "source": "google_search",
            },
            {
                "company_name": "Vitally",
                "website": "https://vitally.io",
                "raw_description": "Customer health software",
                "source": "google_search",
            },
        ]

    monkeypatch.setattr(
        web_search.apify_sources,
        "fetch_google_search",
        fake_fetch_google_search,
    )

    results = web_search.search_web("customer success case studies")

    assert called["queries"] == ["customer success case studies"]
    expected = [
        {
            "vendor_name": "Gainsight",
            "website": "https://gainsight.com",
            "source": "google_search",
            "raw_description": "Customer success platform",
        },
        {
            "vendor_name": "Vitally",
            "website": "https://vitally.io",
            "source": "google_search",
            "raw_description": "Customer health software",
        },
    ]
    assert results == expected
