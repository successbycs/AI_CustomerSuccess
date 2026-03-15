"""Google Sheets export service.

This module provides functions to export vendor intelligence to Google Sheets format.
"""

from __future__ import annotations

import csv
from pathlib import Path

from services.extraction.vendor_intel import VendorIntelligence


def vendor_intelligence_to_sheet_row(
    vendor_intel: VendorIntelligence,
) -> dict[str, str]:
    """Convert a VendorIntelligence object into a flat Google Sheets row dictionary.

    Args:
        vendor_intel: The VendorIntelligence object to convert.

    Returns:
        A dictionary representing a row for Google Sheets.
    """
    return {
        "vendor_name": vendor_intel.vendor_name,
        "website": vendor_intel.website,
        "use_cases": "|".join(vendor_intel.icp),  # Map ICP to use_cases
        "lifecycle_stages": "|".join(vendor_intel.lifecycle_stages),
        "value_statements": "|".join(vendor_intel.value_statements),
        "customers": "|".join(vendor_intel.case_studies),  # Map case_studies to customers
        "pricing": "|".join(vendor_intel.pricing),
        "evidence_urls": ""  # Placeholder, not yet implemented
    }


def write_rows_to_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write Google Sheets-ready rows to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "vendor_name",
        "website",
        "use_cases",
        "lifecycle_stages",
        "value_statements",
        "customers",
        "pricing",
        "evidence_urls",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# Placeholder for future Google Sheets API integration
def append_to_google_sheet(rows: list[dict[str, str]], sheet_id: str) -> None:
    """Placeholder function to append rows to a Google Sheet.

    This is a stub for future implementation.
    """
    # TODO: Implement Google Sheets API integration
    pass
