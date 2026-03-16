"""Tests for the MVP pipeline orchestration module."""

from services.extraction.llm_extractor import LLMExtractionResult
from services.extraction.vendor_intel import VendorIntelligence
from services.pipeline import run_mvp_pipeline as pipeline_module
from services.pipeline.run_mvp_pipeline import run_mvp_pipeline


def test_run_mvp_pipeline_runs_full_flow(monkeypatch, caplog):
    caplog.set_level("INFO")
    query = "ai customer success platform"
    vendor_candidates = [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com", "source": "web_search"},
        {"vendor_name": "Vitally", "website": "https://vitally.io", "source": "web_search"},
    ]
    homepage_payloads = {
        "Gainsight": _homepage_payload("Gainsight", "https://gainsight.com"),
        "Vitally": _homepage_payload("Vitally", "https://vitally.io"),
    }
    explored_pages = {
        "Gainsight": {"homepage": homepage_payloads["Gainsight"]},
        "Vitally": {"homepage": homepage_payloads["Vitally"]},
    }
    intelligence_objects = {
        "Gainsight": _vendor_intelligence("Gainsight", "https://gainsight.com"),
        "Vitally": _vendor_intelligence("Vitally", "https://vitally.io"),
    }
    sheet_rows = {
        "Gainsight": _sheet_row("Gainsight", "https://gainsight.com"),
        "Vitally": _sheet_row("Vitally", "https://vitally.io"),
    }
    calls = []

    def fake_search_web(received_query: str):
        calls.append(("search_web", received_query))
        return vendor_candidates

    def fake_log_runtime_configuration():
        calls.append(("log_runtime_configuration", None))

    def fake_fetch_vendor_homepage(vendor: dict):
        calls.append(("fetch_vendor_homepage", vendor["vendor_name"]))
        return homepage_payloads[vendor["vendor_name"]]

    def fake_explore_vendor_site(homepage_payload: dict):
        calls.append(("explore_vendor_site", homepage_payload["vendor_name"]))
        return explored_pages[homepage_payload["vendor_name"]]

    def fake_extract_vendor_intelligence(explored_page_payloads: dict):
        vendor_name = explored_page_payloads["homepage"]["vendor_name"]
        calls.append(("extract_vendor_intelligence", vendor_name))
        return intelligence_objects[vendor_name]

    def fake_extract_vendor_intelligence_llm(explored_page_payloads: dict):
        vendor_name = explored_page_payloads["homepage"]["vendor_name"]
        calls.append(("extract_vendor_intelligence_llm", vendor_name))
        return None

    def fake_merge_vendor_intelligence(deterministic: VendorIntelligence, _llm_result: object):
        calls.append(("merge_vendor_intelligence", deterministic.vendor_name))
        return deterministic

    def fake_build_vendor_profile(vendor: dict, _explored_pages: dict, intelligence: VendorIntelligence):
        calls.append(("build_vendor_profile", vendor["vendor_name"]))
        return intelligence

    def fake_vendor_intelligence_to_sheet_row(vendor_intelligence: VendorIntelligence):
        calls.append(("vendor_intelligence_to_sheet_row", vendor_intelligence.vendor_name))
        return sheet_rows[vendor_intelligence.vendor_name]

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: False)
    monkeypatch.setattr(pipeline_module.web_search, "search_web", fake_search_web)
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        fake_fetch_vendor_homepage,
    )
    monkeypatch.setattr(
        pipeline_module.site_explorer,
        "explore_vendor_site",
        fake_explore_vendor_site,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_intel,
        "extract_vendor_intelligence",
        fake_extract_vendor_intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.llm_extractor,
        "log_runtime_configuration",
        fake_log_runtime_configuration,
    )
    monkeypatch.setattr(
        pipeline_module.llm_extractor,
        "extract_vendor_intelligence",
        fake_extract_vendor_intelligence_llm,
    )
    monkeypatch.setattr(
        pipeline_module.merge_results,
        "merge_vendor_intelligence",
        fake_merge_vendor_intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_profile_builder,
        "build_vendor_profile",
        fake_build_vendor_profile,
    )
    monkeypatch.setattr(
        pipeline_module.google_sheets,
        "vendor_intelligence_to_sheet_row",
        fake_vendor_intelligence_to_sheet_row,
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "append_rows_to_google_sheet",
        lambda rows: calls.append(("append_rows_to_google_sheet", len(rows))),
    )

    result = run_mvp_pipeline(query)

    assert result == [
        _sheet_row("Gainsight", "https://gainsight.com"),
        _sheet_row("Vitally", "https://vitally.io"),
    ]
    assert calls == [
        ("log_runtime_configuration", None),
        ("search_web", query),
        ("fetch_vendor_homepage", "Gainsight"),
        ("explore_vendor_site", "Gainsight"),
        ("extract_vendor_intelligence", "Gainsight"),
        ("extract_vendor_intelligence_llm", "Gainsight"),
        ("merge_vendor_intelligence", "Gainsight"),
        ("build_vendor_profile", "Gainsight"),
        ("vendor_intelligence_to_sheet_row", "Gainsight"),
        ("fetch_vendor_homepage", "Vitally"),
        ("explore_vendor_site", "Vitally"),
        ("extract_vendor_intelligence", "Vitally"),
        ("extract_vendor_intelligence_llm", "Vitally"),
        ("merge_vendor_intelligence", "Vitally"),
        ("build_vendor_profile", "Vitally"),
        ("vendor_intelligence_to_sheet_row", "Vitally"),
        ("append_rows_to_google_sheet", 2),
    ]
    assert "Pipeline completed with 2 sheet rows; skipped 0 existing vendors" in caplog.text


def test_run_mvp_pipeline_returns_empty_list_when_no_vendors(monkeypatch):
    def fake_search_web(received_query: str):
        assert received_query == "no results query"
        return []

    def fail_fetch_vendor_homepage(vendor: dict):
        raise AssertionError(f"Unexpected enrichment call for {vendor}")

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: False)
    monkeypatch.setattr(pipeline_module.web_search, "search_web", fake_search_web)
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        fail_fetch_vendor_homepage,
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "append_rows_to_google_sheet",
        lambda rows: None,
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
        "Gainsight": _homepage_payload("Gainsight", "https://gainsight.com"),
        "Vitally": _homepage_payload("Vitally", "https://vitally.io"),
    }
    explored_pages = {
        "Gainsight": {"homepage": homepage_payloads["Gainsight"]},
        "Vitally": {"homepage": homepage_payloads["Vitally"]},
    }
    intelligence_objects = {
        "Gainsight": _vendor_intelligence("Gainsight", "https://gainsight.com"),
        "Vitally": _vendor_intelligence("Vitally", "https://vitally.io"),
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

    def fake_explore_vendor_site(homepage_payload: dict):
        calls.append(("explore_vendor_site", homepage_payload["vendor_name"]))
        return explored_pages[homepage_payload["vendor_name"]]

    def fake_extract_vendor_intelligence(explored_page_payloads: dict):
        vendor_name = explored_page_payloads["homepage"]["vendor_name"]
        calls.append(("extract_vendor_intelligence", vendor_name))
        return intelligence_objects[vendor_name]

    def fake_extract_vendor_intelligence_llm(explored_page_payloads: dict):
        vendor_name = explored_page_payloads["homepage"]["vendor_name"]
        calls.append(("extract_vendor_intelligence_llm", vendor_name))
        return None

    def fake_merge_vendor_intelligence(deterministic: VendorIntelligence, _llm_result: object):
        calls.append(("merge_vendor_intelligence", deterministic.vendor_name))
        return deterministic

    def fake_build_vendor_profile(vendor: dict, _explored_pages: dict, intelligence: VendorIntelligence):
        calls.append(("build_vendor_profile", vendor["vendor_name"]))
        return intelligence

    def fake_vendor_intelligence_to_sheet_row(vendor_intelligence: VendorIntelligence):
        calls.append(("vendor_intelligence_to_sheet_row", vendor_intelligence.vendor_name))
        return _sheet_row(vendor_intelligence.vendor_name, vendor_intelligence.website)

    def fake_vendor_exists(_website: str):
        raise MissingTableError('relation "public.cs_vendors" does not exist')

    monkeypatch.setattr(pipeline_module.web_search, "search_web", fake_search_web)
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        fake_fetch_vendor_homepage,
    )
    monkeypatch.setattr(
        pipeline_module.site_explorer,
        "explore_vendor_site",
        fake_explore_vendor_site,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_intel,
        "extract_vendor_intelligence",
        fake_extract_vendor_intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.llm_extractor,
        "extract_vendor_intelligence",
        fake_extract_vendor_intelligence_llm,
    )
    monkeypatch.setattr(
        pipeline_module.merge_results,
        "merge_vendor_intelligence",
        fake_merge_vendor_intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_profile_builder,
        "build_vendor_profile",
        fake_build_vendor_profile,
    )
    monkeypatch.setattr(
        pipeline_module.google_sheets,
        "vendor_intelligence_to_sheet_row",
        fake_vendor_intelligence_to_sheet_row,
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "append_rows_to_google_sheet",
        lambda rows: calls.append(("append_rows_to_google_sheet", len(rows))),
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
        _sheet_row("Gainsight", "https://gainsight.com"),
        _sheet_row("Vitally", "https://vitally.io"),
    ]
    assert calls == [
        ("search_web", query),
        ("fetch_vendor_homepage", "Gainsight"),
        ("explore_vendor_site", "Gainsight"),
        ("extract_vendor_intelligence", "Gainsight"),
        ("extract_vendor_intelligence_llm", "Gainsight"),
        ("merge_vendor_intelligence", "Gainsight"),
        ("build_vendor_profile", "Gainsight"),
        ("vendor_intelligence_to_sheet_row", "Gainsight"),
        ("fetch_vendor_homepage", "Vitally"),
        ("explore_vendor_site", "Vitally"),
        ("extract_vendor_intelligence", "Vitally"),
        ("extract_vendor_intelligence_llm", "Vitally"),
        ("merge_vendor_intelligence", "Vitally"),
        ("build_vendor_profile", "Vitally"),
        ("vendor_intelligence_to_sheet_row", "Vitally"),
        ("append_rows_to_google_sheet", 2),
    ]


def test_run_mvp_pipeline_drops_vendor_when_llm_marks_non_cs_relevant(monkeypatch, caplog):
    caplog.set_level("INFO")
    calls = []
    vendor = {"vendor_name": "OtherTool", "website": "https://other.example.com", "source": "web_search"}
    homepage_payload = _homepage_payload("OtherTool", "https://other.example.com")
    deterministic = _vendor_intelligence("OtherTool", "https://other.example.com", confidence="medium")

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: False)
    monkeypatch.setattr(pipeline_module.web_search, "search_web", lambda _query: [vendor])
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        lambda _vendor: homepage_payload,
    )
    monkeypatch.setattr(
        pipeline_module.site_explorer,
        "explore_vendor_site",
        lambda _payload: {"homepage": homepage_payload},
    )
    monkeypatch.setattr(
        pipeline_module.vendor_intel,
        "extract_vendor_intelligence",
        lambda _pages: deterministic,
    )
    monkeypatch.setattr(
        pipeline_module.llm_extractor,
        "extract_vendor_intelligence",
        lambda _pages: LLMExtractionResult(is_cs_relevant=False, confidence="medium"),
    )
    monkeypatch.setattr(
        pipeline_module.merge_results,
        "merge_vendor_intelligence",
        lambda deterministic, _llm_result: deterministic,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_profile_builder,
        "build_vendor_profile",
        lambda _vendor, _pages, intelligence: intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.google_sheets,
        "vendor_intelligence_to_sheet_row",
        lambda _intelligence: (_ for _ in ()).throw(AssertionError("Unexpected export row build")),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "append_rows_to_google_sheet",
        lambda rows: calls.append(("append_rows_to_google_sheet", len(rows))),
    )

    result = run_mvp_pipeline("query")

    assert result == []
    assert calls == [("append_rows_to_google_sheet", 0)]
    assert "Dropping vendor OtherTool: llm_marked_non_cs_relevant" in caplog.text


def test_run_mvp_pipeline_drops_low_confidence_vendor(monkeypatch, caplog):
    caplog.set_level("INFO")
    calls = []
    vendor = {"vendor_name": "WeakSignal", "website": "https://weak.example.com", "source": "web_search"}
    homepage_payload = _homepage_payload("WeakSignal", "https://weak.example.com")
    low_confidence_profile = _vendor_intelligence("WeakSignal", "https://weak.example.com", confidence="low")

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: False)
    monkeypatch.setattr(pipeline_module.web_search, "search_web", lambda _query: [vendor])
    monkeypatch.setattr(
        pipeline_module.vendor_fetcher,
        "fetch_vendor_homepage",
        lambda _vendor: homepage_payload,
    )
    monkeypatch.setattr(
        pipeline_module.site_explorer,
        "explore_vendor_site",
        lambda _payload: {"homepage": homepage_payload},
    )
    monkeypatch.setattr(
        pipeline_module.vendor_intel,
        "extract_vendor_intelligence",
        lambda _pages: low_confidence_profile,
    )
    monkeypatch.setattr(
        pipeline_module.llm_extractor,
        "extract_vendor_intelligence",
        lambda _pages: None,
    )
    monkeypatch.setattr(
        pipeline_module.merge_results,
        "merge_vendor_intelligence",
        lambda deterministic, _llm_result: deterministic,
    )
    monkeypatch.setattr(
        pipeline_module.vendor_profile_builder,
        "build_vendor_profile",
        lambda _vendor, _pages, intelligence: intelligence,
    )
    monkeypatch.setattr(
        pipeline_module.google_sheets,
        "vendor_intelligence_to_sheet_row",
        lambda _intelligence: (_ for _ in ()).throw(AssertionError("Unexpected export row build")),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "append_rows_to_google_sheet",
        lambda rows: calls.append(("append_rows_to_google_sheet", len(rows))),
    )

    result = run_mvp_pipeline("query")

    assert result == []
    assert calls == [("append_rows_to_google_sheet", 0)]
    assert "Dropping vendor WeakSignal: low_confidence" in caplog.text


def _homepage_payload(vendor_name: str, website: str) -> dict[str, str | int]:
    return {
        "vendor_name": vendor_name,
        "website": website,
        "source": "web_search",
        "page_type": "homepage",
        "status_code": 200,
        "html": f"<html>{vendor_name}</html>",
        "text": f"{vendor_name} homepage",
    }


def _vendor_intelligence(
    vendor_name: str,
    website: str,
    *,
    confidence: str = "medium",
) -> VendorIntelligence:
    return VendorIntelligence(
        vendor_name=vendor_name,
        website=website,
        source="web_search",
        confidence=confidence,
    )


def _sheet_row(vendor_name: str, website: str) -> dict[str, str]:
    return {
        "vendor_name": vendor_name,
        "website": website,
        "mission": "",
        "usp": "",
        "icp": "",
        "use_cases": "",
        "lifecycle_stages": "",
        "pricing": "",
        "free_trial": "",
        "soc2": "",
        "founded": "",
        "case_studies": "",
        "customers": "",
        "value_statements": "",
        "confidence": "",
        "evidence_urls": "",
    }
