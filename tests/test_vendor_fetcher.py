"""Tests for the vendor fetcher enrichment module."""

from services.enrichment import vendor_fetcher


def test_fetch_vendor_homepage_returns_structured_payload(monkeypatch):
    # Mock requests.get
    class MockResponse:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

    def mock_get(url, timeout=None):
        return MockResponse(200, "<html><body>Hello World</body></html>")

    monkeypatch.setattr(vendor_fetcher.requests, "get", mock_get)

    vendor = {
        "vendor_name": "Gainsight",
        "website": "https://gainsight.com",
        "source": "web_search"
    }

    result = vendor_fetcher.fetch_vendor_homepage(vendor)

    expected = {
        "vendor_name": "Gainsight",
        "website": "https://gainsight.com",
        "page_type": "homepage",
        "status_code": 200,
        "html": "<html><body>Hello World</body></html>",
        "text": "Hello World"
    }

    assert result == expected


def test_fetch_vendor_homepage_handles_network_error(monkeypatch):
    # Mock requests.get to raise exception
    def mock_get(url, timeout=None):
        raise vendor_fetcher.requests.RequestException("Network error")

    monkeypatch.setattr(vendor_fetcher.requests, "get", mock_get)

    vendor = {
        "vendor_name": "Gainsight",
        "website": "https://gainsight.com",
        "source": "web_search"
    }

    result = vendor_fetcher.fetch_vendor_homepage(vendor)

    expected = {
        "vendor_name": "Gainsight",
        "website": "https://gainsight.com",
        "page_type": "homepage",
        "status_code": 0,
        "html": "",
        "text": ""
    }

    assert result == expected