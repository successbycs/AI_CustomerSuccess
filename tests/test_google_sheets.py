"""Tests for the Google Sheets export module."""

import csv
from pathlib import Path

from services.extraction.vendor_intel import VendorIntelligence
from services.export import google_sheets


def test_vendor_intelligence_to_sheet_row():
    vendor = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        icp=["SaaS", "Mid-market"],
        lifecycle_stages=["Adopt", "Renew"],
        case_studies=["Increased retention by 20%", "Reduced churn"],
        value_statements=["Increases retention", "Boosts ARR"],
        pricing=["$99/mo", "$199/mo"]
    )

    result = google_sheets.vendor_intelligence_to_sheet_row(vendor)

    expected = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "use_cases": "SaaS|Mid-market",
        "lifecycle_stages": "Adopt|Renew",
        "value_statements": "Increases retention|Boosts ARR",
        "customers": "Increased retention by 20%|Reduced churn",
        "pricing": "$99/mo|$199/mo",
        "evidence_urls": ""
    }

    assert result == expected


def test_write_rows_to_csv(tmp_path: Path):
    rows = [
        {
            "vendor_name": "ExampleCorp",
            "website": "https://example.com",
            "use_cases": "SaaS|Mid-market",
            "lifecycle_stages": "Adopt|Renew",
            "value_statements": "Increases retention|Boosts ARR",
            "customers": "Acme|Globex",
            "pricing": "$99/mo|$199/mo",
            "evidence_urls": "",
        }
    ]

    output_path = tmp_path / "outputs" / "vendor_rows.csv"

    google_sheets.write_rows_to_csv(rows, output_path)

    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        result = list(reader)

    assert reader.fieldnames == [
        "vendor_name",
        "website",
        "use_cases",
        "lifecycle_stages",
        "value_statements",
        "customers",
        "pricing",
        "evidence_urls",
    ]
    assert result == rows
