"""Tests for vendor site exploration."""

from services.enrichment import site_explorer


def test_explore_vendor_site_discovers_high_signal_pages(monkeypatch):
    homepage_payload = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "source": "google_search",
        "page_type": "homepage",
        "status_code": 200,
        "html": (
            '<html><body>'
            '<a href="/pricing">Pricing</a>'
            '<a href="/platform">Platform</a>'
            '<a href="/customers">Customers</a>'
            '<a href="/about">About</a>'
            '<a href="/security">Security</a>'
            '<a href="https://reddit.com/r/customersuccess">Reddit</a>'
            "</body></html>"
        ),
        "text": "Homepage text",
    }

    class MockResponse:
        def __init__(self, status_code: int, text: str):
            self.status_code = status_code
            self.text = text

    def mock_get(url: str, timeout: int = 10):
        responses = {
            "https://example.com/pricing": MockResponse(200, "<html><body>$99 per user per month</body></html>"),
            "https://example.com/platform": MockResponse(200, "<html><body>Customer success platform</body></html>"),
            "https://example.com/customers": MockResponse(200, "<html><body>Customer stories</body></html>"),
            "https://example.com/about": MockResponse(200, "<html><body>About ExampleCorp</body></html>"),
        }
        return responses[url]

    monkeypatch.setattr(site_explorer.requests, "get", mock_get)

    result = site_explorer.explore_vendor_site(homepage_payload)

    assert list(result) == [
        "homepage",
        "pricing_page",
        "product_page",
        "case_studies_page",
        "about_page",
    ]
    assert len(result) == 5
    assert result["pricing_page"]["website"] == "https://example.com/pricing"
    assert result["product_page"]["text"] == "Customer success platform"
    assert "security_page" not in result
