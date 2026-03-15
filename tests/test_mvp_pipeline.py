"""Tests for the MVP pipeline orchestration module."""

from services.pipeline.run_mvp_pipeline import run_mvp_pipeline
from services.pipeline import run_mvp_pipeline as pipeline_module


def test_run_mvp_pipeline_runs_full_flow(monkeypatch):
    query = "ai customer success platform"
    vendor_candidates = [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com", "source": "web_search"},
        {"vendor_name": "Vitally", "website": "https://vitally.io", "source": "web_search"},
    ]
    homepage_payloads = {
        "Gainsight": {
            "vendor_name": "Gainsight",
            "website": "https://gainsight.com",
            "page_type": "homepage",
            "status_code": 200,
            "html": "<html>Gainsight</html>",
            "text": "Gainsight homepage",
        },
        "Vitally": {
            "vendor_name": "Vitally",
            "website": "https://vitally.io",
            "page_type": "homepage",
            "status_code": 200,
            "html": "<html>Vitally</html>",
            "text": "Vitally homepage",
        },
    }
    intelligence_objects = {
        "Gainsight": {"vendor_name": "Gainsight", "website": "https://gainsight.com"},
        "Vitally": {"vendor_name": "Vitally", "website": "https://vitally.io"},
    }
    sheet_rows = {
        "Gainsight": {"vendor_name": "Gainsight", "website": "https://gainsight.com"},
        "Vitally": {"vendor_name": "Vitally", "website": "https://vitally.io"},
    }
    calls = []

    def fake_search_web(received_query: str):
        calls.append(("search_web", received_query))
        return vendor_candidates

    def fake_fetch_vendor_homepage(vendor: dict):
        calls.append(("fetch_vendor_homepage", vendor["vendor_name"]))
        return homepage_payloads[vendor["vendor_name"]]

    def fake_extract_vendor_intelligence(homepage_payload: dict):
        calls.append(("extract_vendor_intelligence", homepage_payload["vendor_name"]))
        return intelligence_objects[homepage_payload["vendor_name"]]

    def fake_vendor_intelligence_to_sheet_row(vendor_intelligence: dict):
        calls.append(("vendor_intelligence_to_sheet_row", vendor_intelligence["vendor_name"]))
        return sheet_rows[vendor_intelligence["vendor_name"]]

    monkeypatch.setattr(pipeline_module.web_search, "search_web", fake_search_web)
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        fake_fetch_vendor_homepage,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_intel,
        "extract_vendor_intelligence",
        fake_extract_vendor_intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.google_sheets,
        "vendor_intelligence_to_sheet_row",
        fake_vendor_intelligence_to_sheet_row,
    )

    result = run_mvp_pipeline(query)

    assert result == [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com"},
        {"vendor_name": "Vitally", "website": "https://vitally.io"},
    ]
    assert calls == [
        ("search_web", query),
        ("fetch_vendor_homepage", "Gainsight"),
        ("extract_vendor_intelligence", "Gainsight"),
        ("vendor_intelligence_to_sheet_row", "Gainsight"),
        ("fetch_vendor_homepage", "Vitally"),
        ("extract_vendor_intelligence", "Vitally"),
        ("vendor_intelligence_to_sheet_row", "Vitally"),
    ]


def test_run_mvp_pipeline_returns_empty_list_when_no_vendors(monkeypatch):
    def fake_search_web(received_query: str):
        assert received_query == "no results query"
        return []

    def fail_fetch_vendor_homepage(vendor: dict):
        raise AssertionError(f"Unexpected enrichment call for {vendor}")

    monkeypatch.setattr(pipeline_module.web_search, "search_web", fake_search_web)
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        fail_fetch_vendor_homepage,
    )

    result = run_mvp_pipeline("no results query")

    assert result == []


def test_run_mvp_pipeline_continues_when_persistence_is_unavailable(monkeypatch):
    query = "ai customer success platform"
    vendor_candidates = [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com", "source": "web_search"},
        {"vendor_name": "Vitally", "website": "https://vitally.io", "source": "web_search"},
    ]
    homepage_payloads = {
        "Gainsight": {
            "vendor_name": "Gainsight",
            "website": "https://gainsight.com",
            "page_type": "homepage",
            "status_code": 200,
            "html": "<html>Gainsight</html>",
            "text": "Gainsight homepage",
        },
        "Vitally": {
            "vendor_name": "Vitally",
            "website": "https://vitally.io",
            "page_type": "homepage",
            "status_code": 200,
            "html": "<html>Vitally</html>",
            "text": "Vitally homepage",
        },
    }
    intelligence_objects = {
        "Gainsight": {"vendor_name": "Gainsight", "website": "https://gainsight.com"},
        "Vitally": {"vendor_name": "Vitally", "website": "https://vitally.io"},
    }
    sheet_rows = {
        "Gainsight": {"vendor_name": "Gainsight", "website": "https://gainsight.com"},
        "Vitally": {"vendor_name": "Vitally", "website": "https://vitally.io"},
    }
    calls = []

    class MissingTableError(Exception):
        pass

    def fake_search_web(received_query: str):
        calls.append(("search_web", received_query))
        return vendor_candidates

    def fake_fetch_vendor_homepage(vendor: dict):
        calls.append(("fetch_vendor_homepage", vendor["vendor_name"]))
        return homepage_payloads[vendor["vendor_name"]]

    def fake_extract_vendor_intelligence(homepage_payload: dict):
        calls.append(("extract_vendor_intelligence", homepage_payload["vendor_name"]))
        return intelligence_objects[homepage_payload["vendor_name"]]

    def fake_vendor_intelligence_to_sheet_row(vendor_intelligence: dict):
        calls.append(("vendor_intelligence_to_sheet_row", vendor_intelligence["vendor_name"]))
        return sheet_rows[vendor_intelligence["vendor_name"]]

    def fake_vendor_exists(_website: str):
        raise MissingTableError('relation "public.cs_vendors" does not exist')

    monkeypatch.setattr(pipeline_module.web_search, "search_web", fake_search_web)
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        fake_fetch_vendor_homepage,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_intel,
        "extract_vendor_intelligence",
        fake_extract_vendor_intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.google_sheets,
        "vendor_intelligence_to_sheet_row",
        fake_vendor_intelligence_to_sheet_row,
    )
    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: True)
    monkeypatch.setattr(pipeline_module.supabase_client, "vendor_exists", fake_vendor_exists)
    monkeypatch.setattr(
        pipeline_module.supabase_client,
        "upsert_vendor_result",
        lambda *_args: (_ for _ in ()).throw(AssertionError("Unexpected upsert call")),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.supabase_client,
        "is_persistence_unavailable_error",
        lambda error: "does not exist" in str(error),
    )

    result = run_mvp_pipeline(query)

    assert result == [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com"},
        {"vendor_name": "Vitally", "website": "https://vitally.io"},
    ]
    assert calls == [
        ("search_web", query),
        ("fetch_vendor_homepage", "Gainsight"),
        ("extract_vendor_intelligence", "Gainsight"),
        ("vendor_intelligence_to_sheet_row", "Gainsight"),
        ("fetch_vendor_homepage", "Vitally"),
        ("extract_vendor_intelligence", "Vitally"),
        ("vendor_intelligence_to_sheet_row", "Vitally"),
    ]
