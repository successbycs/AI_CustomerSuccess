"""Tests for merging vendor page intelligence into a profile."""

from services.extraction.vendor_intel import VendorIntelligence
from services.extraction.vendor_profile_builder import build_vendor_profile


def test_build_vendor_profile_merges_source_and_evidence_urls():
    vendor = {
        "vendor_name": "Search Title",
        "website": "https://example.com",
        "source": "google_search",
    }
    explored_pages = {
        "homepage": {
            "vendor_name": "ExampleCorp",
            "website": "https://example.com",
            "text": "Homepage text",
        },
        "pricing_page": {
            "vendor_name": "",
            "website": "https://example.com/pricing",
            "text": "$99 per seat",
        },
    }
    intelligence = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        mission="Help customer success teams retain more revenue.",
        usp="reduce churn",
        icp=["SaaS companies"],
        use_cases=["health scoring"],
        lifecycle_stages=["Adopt", "Renew"],
        pricing=["$", "per seat"],
        case_studies=["case study"],
        customers=["Acme"],
        value_statements=["reduce churn"],
        confidence="medium",
    )

    result = build_vendor_profile(vendor, explored_pages, intelligence)

    assert result.vendor_name == "ExampleCorp"
    assert result.source == "google_search"
    assert result.evidence_urls == [
        "https://example.com",
        "https://example.com/pricing",
    ]
