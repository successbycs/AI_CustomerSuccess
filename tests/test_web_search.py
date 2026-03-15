"""Tests for the discovery web search module."""

from services.discovery import web_search


def test_search_web_calls_api_and_returns_urls(monkeypatch):
    called = {}

    def fake_api(query: str):
        called["query"] = query
        return ["https://gainsight.com", "https://vitally.io"]

    monkeypatch.setattr(web_search, "_call_search_api", fake_api)

    results = web_search.search_web("customer success case studies")

    assert called["query"] == "customer success case studies"
    expected = [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com", "source": "web_search"},
        {"vendor_name": "Vitally", "website": "https://vitally.io", "source": "web_search"}
    ]
    assert results == expected
