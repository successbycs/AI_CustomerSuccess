"""Tests for the explicit Phase 2 enrichment runner."""

from services.extraction.llm_extractor import LLMExtractionResult
from services.extraction.vendor_intel import VendorIntelligence
from services.pipeline.enrichment_runner import run_enrichment_phase


def test_run_enrichment_phase_builds_profiles_and_rows():
    queued_vendor_candidates = [
        {"vendor_name": "SignalAI", "website": "https://signal.example.com", "candidate_domain": "signal.example.com"}
    ]
    homepage_payload = {"vendor_name": "SignalAI", "website": "https://signal.example.com", "text": "Homepage text"}
    explored_pages = {"homepage": homepage_payload, "extra_pages": []}
    deterministic = VendorIntelligence(vendor_name="SignalAI", website="https://signal.example.com", confidence="medium")
    profile = VendorIntelligence(vendor_name="SignalAI", website="https://signal.example.com", confidence="high")

    rows, enrichment_results, llm_success_count, llm_fallback_count = run_enrichment_phase(
        queued_vendor_candidates,
        fetch_vendor_homepage_fn=lambda vendor: homepage_payload,
        explore_vendor_site_fn=lambda payload: explored_pages,
        extract_vendor_intelligence_fn=lambda pages: deterministic,
        extract_vendor_intelligence_llm_fn=lambda pages: LLMExtractionResult(is_cs_relevant=True, confidence="high"),
        merge_vendor_intelligence_fn=lambda deterministic, _llm_result: deterministic,
        build_vendor_profile_fn=lambda vendor, pages, intelligence: profile,
        vendor_intelligence_to_sheet_row_fn=lambda intelligence: {"vendor_name": intelligence.vendor_name},
        upsert_vendor_result_fn=None,
        drop_reason_fn=lambda _profile, _llm_result: "",
    )

    assert rows == [{"vendor_name": "SignalAI"}]
    assert enrichment_results == [
        {
            "candidate_domain": "signal.example.com",
            "status": "enriched",
            "drop_reason": "",
            "profile": profile,
        }
    ]
    assert llm_success_count == 1
    assert llm_fallback_count == 0


def test_run_enrichment_phase_marks_failed_vendors_without_crashing():
    queued_vendor_candidates = [
        {"vendor_name": "WeakAI", "website": "https://weak.example.com", "candidate_domain": "weak.example.com"}
    ]
    homepage_payload = {"vendor_name": "WeakAI", "website": "https://weak.example.com", "text": "Homepage text"}
    deterministic = VendorIntelligence(vendor_name="WeakAI", website="https://weak.example.com", confidence="low")

    rows, enrichment_results, llm_success_count, llm_fallback_count = run_enrichment_phase(
        queued_vendor_candidates,
        fetch_vendor_homepage_fn=lambda vendor: homepage_payload,
        explore_vendor_site_fn=lambda payload: (_ for _ in ()).throw(RuntimeError("timeout")),
        extract_vendor_intelligence_fn=lambda pages: deterministic,
        extract_vendor_intelligence_llm_fn=lambda pages: None,
        merge_vendor_intelligence_fn=lambda deterministic, _llm_result: deterministic,
        build_vendor_profile_fn=lambda vendor, pages, intelligence: intelligence,
        vendor_intelligence_to_sheet_row_fn=lambda intelligence: {"vendor_name": intelligence.vendor_name},
        upsert_vendor_result_fn=None,
        drop_reason_fn=lambda _profile, _llm_result: "low_confidence",
    )

    assert rows == []
    assert enrichment_results[0]["candidate_domain"] == "weak.example.com"
    assert enrichment_results[0]["status"] == "failed"
    assert enrichment_results[0]["drop_reason"] == "low_confidence"
    assert llm_success_count == 0
    assert llm_fallback_count == 1
