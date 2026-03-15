"""Tests for the Google Sheets export module."""

import csv
import json
from pathlib import Path

from services.extraction.vendor_intel import VendorIntelligence
from services.export import google_sheets


def test_vendor_intelligence_to_sheet_row():
    vendor = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        source="web_search",
        mission="Improve customer retention",
        usp="reduce churn",
        icp=["SaaS", "Mid-market"],
        lifecycle_stages=["Adopt", "Support", "Renew"],
        case_studies=["Increased retention by 20%", "Reduced churn"],
        value_statements=["Increases retention", "Boosts ARR"],
        pricing=["$99/mo", "$199/mo"],
        free_trial=True,
        soc2=True,
        founded="2021",
        confidence="high",
        evidence_urls=["https://example.com/proof"],
    )

    result = google_sheets.vendor_intelligence_to_sheet_row(vendor)

    expected = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "source": "web_search",
        "mission": "Improve customer retention",
        "usp": "reduce churn",
        "use_cases": "SaaS|Mid-market",
        "lifecycle_stages": "Adopt|Support|Renew",
        "pricing": "$99/mo|$199/mo",
        "free_trial": "TRUE",
        "soc2": "TRUE",
        "founded": "2021",
        "confidence": "high",
        "evidence_urls": "https://example.com/proof",
    }

    assert result == expected


def test_write_rows_to_csv(tmp_path: Path):
    rows = [
        {
            "vendor_name": "ExampleCorp",
            "website": "https://example.com",
            "source": "web_search",
            "mission": "Improve customer retention",
            "usp": "reduce churn",
            "use_cases": "SaaS|Mid-market",
            "lifecycle_stages": "Adopt|Support|Renew",
            "pricing": "$99/mo|$199/mo",
            "free_trial": "TRUE",
            "soc2": "TRUE",
            "founded": "2021",
            "confidence": "high",
            "evidence_urls": "https://example.com/proof",
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
    assert result == rows


class FakeAppendRequest:
    def __init__(self, recorder: dict):
        self.recorder = recorder

    def execute(self):
        self.recorder["executed"] = True
        return {"updates": {"updatedRows": 1}}


class FakeValuesResource:
    def __init__(self, recorder: dict):
        self.recorder = recorder

    def append(self, **kwargs):
        self.recorder["append_kwargs"] = kwargs
        return FakeAppendRequest(self.recorder)


class FakeSpreadsheetsResource:
    def __init__(self, recorder: dict):
        self.recorder = recorder

    def values(self):
        return FakeValuesResource(self.recorder)


class FakeSheetsService:
    def __init__(self, recorder: dict):
        self.recorder = recorder

    def spreadsheets(self):
        return FakeSpreadsheetsResource(self.recorder)


def test_load_google_sheets_credentials_info_from_json_env(monkeypatch):
    credentials_info = {"type": "service_account", "client_email": "json@example.com"}

    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS_JSON", json.dumps(credentials_info))

    result = google_sheets._load_google_sheets_credentials_info()

    assert result == credentials_info


def test_load_google_sheets_credentials_info_from_legacy_env_key(monkeypatch):
    credentials_info = {"type": "service_account", "client_email": "legacy@example.com"}

    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", json.dumps(credentials_info))

    result = google_sheets._load_google_sheets_credentials_info()

    assert result == credentials_info


def test_append_rows_to_google_sheet_warns_and_skips_without_credentials(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet-id")
    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_JSON", raising=False)

    google_sheets.append_rows_to_google_sheet(
        [{"vendor_name": "ExampleCorp", "website": "https://example.com"}]
    )

    assert "Google Sheets credentials are unavailable" in caplog.text


def test_append_rows_to_google_sheet_uses_correct_column_order(monkeypatch, tmp_path: Path):
    rows = [
        {
            "vendor_name": "ExampleCorp",
            "website": "https://example.com",
            "source": "web_search",
            "mission": "Improve customer retention",
            "usp": "reduce churn",
            "use_cases": "SaaS|Mid-market",
            "lifecycle_stages": "Adopt|Support|Renew",
            "pricing": "$99/mo|$199/mo",
            "free_trial": "TRUE",
            "soc2": "TRUE",
            "founded": "2021",
            "confidence": "high",
            "evidence_urls": "https://example.com/proof",
        }
    ]

    monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet-id")
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS_JSON",
        json.dumps({"type": "service_account", "client_email": "test@example.com"}),
    )
    fake_recorder = {}

    def fake_build_google_sheets_service(credentials_info):
        fake_recorder["credentials_info"] = credentials_info
        return FakeSheetsService(fake_recorder)

    monkeypatch.setattr(
        google_sheets,
        "_build_google_sheets_service",
        fake_build_google_sheets_service,
    )

    google_sheets.append_rows_to_google_sheet(rows)

    assert fake_recorder["append_kwargs"] == {
        "spreadsheetId": "sheet-id",
        "range": "vendors!A:M",
        "valueInputOption": "USER_ENTERED",
        "body": {
            "values": [[
                "ExampleCorp",
                "https://example.com",
                "web_search",
                "Improve customer retention",
                "reduce churn",
                "SaaS|Mid-market",
                "Adopt|Support|Renew",
                "$99/mo|$199/mo",
                "TRUE",
                "TRUE",
                "2021",
                "high",
                "https://example.com/proof",
            ]]
        },
    }
    assert fake_recorder["executed"] is True
