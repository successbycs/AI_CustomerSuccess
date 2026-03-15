"""Google Sheets export service.

This module provides functions to export vendor intelligence to Google Sheets format.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

from services.extraction.vendor_intel import VendorIntelligence

logger = logging.getLogger(__name__)

GOOGLE_SHEETS_COLUMNS = [
    "vendor_name",
    "website",
    "source",
    "mission",
    "usp",
    "use_cases",
    "lifecycle_stages",
    "pricing",
    "free_trial",
    "soc2",
    "founded",
    "confidence",
    "evidence_urls",
]


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
        "source": vendor_intel.source,
        "mission": vendor_intel.mission,
        "usp": vendor_intel.usp,
        "use_cases": "|".join(vendor_intel.icp),  # Map ICP to use_cases
        "lifecycle_stages": "|".join(vendor_intel.lifecycle_stages),
        "pricing": "|".join(vendor_intel.pricing),
        "free_trial": _stringify_boolean(vendor_intel.free_trial),
        "soc2": _stringify_boolean(vendor_intel.soc2),
        "founded": vendor_intel.founded,
        "confidence": vendor_intel.confidence,
        "evidence_urls": "|".join(vendor_intel.evidence_urls),
    }


def write_rows_to_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write Google Sheets-ready rows to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "vendor_name",
        "website",
        "source",
        "mission",
        "usp",
        "use_cases",
        "lifecycle_stages",
        "pricing",
        "free_trial",
        "soc2",
        "founded",
        "confidence",
        "evidence_urls",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_rows_to_google_sheet(rows: list[dict[str, str]]) -> None:
    """Append Google Sheets-ready rows to the vendors sheet when configured."""
    if not rows:
        return

    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        logger.warning("GOOGLE_SHEETS_ID is not set, skipping Google Sheets output")
        return

    credentials_info = _load_google_sheets_credentials_info()
    if credentials_info is None:
        logger.warning("Google Sheets credentials are unavailable, skipping Google Sheets output")
        return

    service = _build_google_sheets_service(credentials_info)
    values = [_row_to_ordered_values(row) for row in rows]
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=sheet_id,
            range="vendors!A:M",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        )
        .execute()
    )


def _load_google_sheets_credentials_info() -> dict[str, Any] | None:
    """Load Google Sheets service account credentials from env vars."""
    credentials_json = (
        os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    )

    if credentials_json:
        try:
            return json.loads(credentials_json)
        except json.JSONDecodeError as error:
            logger.warning("Could not parse GOOGLE_SHEETS_CREDENTIALS_JSON: %s", error)
            return None

    return None


def _build_google_sheets_service(credentials_info: dict[str, Any]):
    """Build a Google Sheets API service using service account credentials."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _row_to_ordered_values(row: dict[str, str]) -> list[str]:
    """Convert a row dictionary into deterministic Google Sheets column order."""
    return [row.get(column, "") for column in GOOGLE_SHEETS_COLUMNS]


def _stringify_boolean(value: bool | None) -> str:
    """Return a Google Sheets-friendly string for a boolean value."""
    if value is None:
        return ""
    return "TRUE" if value else "FALSE"
