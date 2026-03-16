"""Tests for merging deterministic and LLM extraction."""

from services.extraction.llm_extractor import LLMExtractionResult
from services.extraction.merge_results import merge_vendor_intelligence
from services.extraction.vendor_intel import VendorIntelligence


def test_merge_vendor_intelligence_keeps_deterministic_result_without_llm():
    deterministic = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        mission="Improve retention for customer success teams.",
        use_cases=["health scoring"],
        lifecycle_stages=["Adopt"],
        confidence="medium",
    )

    merged = merge_vendor_intelligence(deterministic, None)

    assert merged == deterministic


def test_merge_vendor_intelligence_prefers_valid_llm_fields_and_keeps_deterministic_stages():
    deterministic = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        source="google_search",
        mission="Baseline mission",
        usp="Baseline usp",
        use_cases=["health scoring"],
        lifecycle_stages=["Adopt"],
        pricing=["contact sales"],
        free_trial=None,
        soc2=None,
        founded="",
        value_statements=["improve customer health"],
        confidence="medium",
        evidence_urls=["https://example.com"],
    )
    llm_result = LLMExtractionResult(
        is_cs_relevant=True,
        mission="AI customer success platform that reduces churn and automates onboarding.",
        usp="Predict churn and speed time to value.",
        use_cases=["churn prediction", "onboarding automation"],
        pricing="per seat",
        free_trial=True,
        soc2=True,
        founded="2024",
        confidence="high",
    )

    merged = merge_vendor_intelligence(deterministic, llm_result)

    assert merged.vendor_name == "ExampleCorp"
    assert merged.website == "https://example.com"
    assert merged.mission == "AI customer success platform that reduces churn and automates onboarding."
    assert merged.usp == "Predict churn and speed time to value."
    assert merged.use_cases == ["health scoring", "churn prediction", "onboarding automation"]
    assert merged.lifecycle_stages == ["Adopt"]
    assert merged.pricing == ["contact sales", "per seat"]
    assert merged.free_trial is True
    assert merged.soc2 is True
    assert merged.founded == "2024"
    assert merged.confidence == "high"
    assert merged.evidence_urls == ["https://example.com"]


def test_merge_vendor_intelligence_keeps_stronger_deterministic_signals():
    deterministic = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        mission="Customer success platform for onboarding and renewals.",
        usp="Reduce churn for CS teams.",
        use_cases=["renewal forecasting"],
        lifecycle_stages=["Renew"],
        pricing=["contact sales"],
        free_trial=True,
        soc2=True,
        founded="2020",
        value_statements=["reduce churn"],
        confidence="medium",
        evidence_urls=["https://example.com"],
    )
    llm_result = LLMExtractionResult(
        is_cs_relevant=True,
        mission="Short summary.",
        usp="Short usp.",
        use_cases=["onboarding automation"],
        pricing="per seat",
        free_trial=False,
        soc2=False,
        founded="",
        confidence="low",
    )

    merged = merge_vendor_intelligence(deterministic, llm_result)

    assert merged.mission == deterministic.mission
    assert merged.usp == deterministic.usp
    assert merged.use_cases == ["renewal forecasting", "onboarding automation"]
    assert merged.pricing == ["contact sales", "per seat"]
    assert merged.free_trial is True
    assert merged.soc2 is True
    assert merged.founded == "2020"
    assert merged.confidence == "medium"
