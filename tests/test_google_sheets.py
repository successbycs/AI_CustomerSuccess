"""Tests for the Google Sheets export module."""

from services.extraction.vendor_intel import VendorIntelligence
from services.export import google_sheets


def test_vendor_intelligence_to_sheet_row():
    vendor = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        icp=["SaaS", "Mid-market"],
        case_studies=["Increased retention by 20%", "Reduced churn"],
        value_statements=["Increases retention", "Boosts ARR"],
        pricing=["$99/mo", "$199/mo"]
    )

    result = google_sheets.vendor_intelligence_to_sheet_row(vendor)

    expected = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "use_cases": "SaaS|Mid-market",
        "value_statements": "Increases retention|Boosts ARR",
        "customers": "Increased retention by 20%|Reduced churn",
        "pricing": "$99/mo|$199/mo",
        "evidence_urls": ""
    }

    assert result == expected