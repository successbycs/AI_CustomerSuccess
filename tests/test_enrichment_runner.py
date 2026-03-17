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
    profile = VendorIntelligence(
        vendor_name="SignalAI",
        website="https://signal.example.com",
        confidence="high",
        include_in_directory=True,
    )

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
            "completed_at": enrichment_results[0]["completed_at"],
        }
    ]
    assert llm_success_count == 1
    assert llm_fallback_count == 0


def test_run_enrichment_phase_persists_non_directory_vendor_but_skips_sheet_row():
    queued_vendor_candidates = [
        {"vendor_name": "WeakFit", "website": "https://weakfit.example.com", "candidate_domain": "weakfit.example.com"}
    ]
    homepage_payload = {"vendor_name": "WeakFit", "website": "https://weakfit.example.com", "text": "Homepage text"}
    deterministic = VendorIntelligence(vendor_name="WeakFit", website="https://weakfit.example.com", confidence="medium")
    profile = VendorIntelligence(
        vendor_name="WeakFit",
        website="https://weakfit.example.com",
        confidence="medium",
        include_in_directory=False,
    )
    upserted = []

    rows, enrichment_results, llm_success_count, llm_fallback_count = run_enrichment_phase(
        queued_vendor_candidates,
        fetch_vendor_homepage_fn=lambda vendor: homepage_payload,
        explore_vendor_site_fn=lambda payload: {"homepage": homepage_payload, "extra_pages": []},
        extract_vendor_intelligence_fn=lambda pages: deterministic,
        extract_vendor_intelligence_llm_fn=lambda pages: None,
        merge_vendor_intelligence_fn=lambda deterministic, _llm_result: deterministic,
        build_vendor_profile_fn=lambda vendor, pages, intelligence: profile,
        vendor_intelligence_to_sheet_row_fn=lambda intelligence: {"vendor_name": intelligence.vendor_name},
        upsert_vendor_result_fn=lambda vendor, homepage_payload, profile: upserted.append(profile.vendor_name),
        drop_reason_fn=lambda _profile, _llm_result: "",
    )

    assert rows == []
    assert upserted == ["WeakFit"]
    assert enrichment_results[0]["status"] == "enriched"
    assert llm_success_count == 0
    assert llm_fallback_count == 1


def test_run_enrichment_phase_marks_dropped_vendors_without_crashing():
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
    assert enrichment_results[0]["status"] == "dropped_low_confidence"
    assert enrichment_results[0]["drop_reason"] == "low_confidence"
    assert llm_success_count == 0
    assert llm_fallback_count == 1


def test_run_enrichment_phase_marks_fetch_failures_without_crashing():
    queued_vendor_candidates = [
        {"vendor_name": "MissingAI", "website": "https://missing.example.com", "candidate_domain": "missing.example.com"}
    ]

    rows, enrichment_results, llm_success_count, llm_fallback_count = run_enrichment_phase(
        queued_vendor_candidates,
        fetch_vendor_homepage_fn=lambda vendor: (_ for _ in ()).throw(RuntimeError("network timeout")),
        explore_vendor_site_fn=lambda payload: {"homepage": payload, "extra_pages": []},
        extract_vendor_intelligence_fn=lambda pages: VendorIntelligence(vendor_name="MissingAI", website="https://missing.example.com"),
        extract_vendor_intelligence_llm_fn=lambda pages: None,
        merge_vendor_intelligence_fn=lambda deterministic, _llm_result: deterministic,
        build_vendor_profile_fn=lambda vendor, pages, intelligence: intelligence,
        vendor_intelligence_to_sheet_row_fn=lambda intelligence: {"vendor_name": intelligence.vendor_name},
        upsert_vendor_result_fn=None,
        drop_reason_fn=lambda _profile, _llm_result: "",
    )

    assert rows == []
    assert enrichment_results == [
        {
            "candidate_domain": "missing.example.com",
            "status": "failed_fetch",
            "drop_reason": "homepage_fetch_failed",
        }
    ]
    assert llm_success_count == 0
    assert llm_fallback_count == 0
