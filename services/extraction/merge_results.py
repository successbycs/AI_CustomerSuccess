"""Merge deterministic and LLM extraction into one vendor profile."""

from __future__ import annotations

from services.extraction import vendor_intel
from services.extraction.llm_extractor import LLMExtractionResult
from services.extraction.vendor_intel import VendorIntelligence


def merge_vendor_intelligence(
    deterministic: VendorIntelligence,
    llm_result: LLMExtractionResult | None,
) -> VendorIntelligence:
    """Merge deterministic extraction with optional LLM output."""
    if llm_result is None:
        return deterministic

    merged_mission = _prefer_text_value(deterministic.mission, llm_result.mission)
    merged_usp = _prefer_text_value(deterministic.usp, llm_result.usp)
    merged_use_cases = _merge_unique_strings(deterministic.use_cases, llm_result.use_cases)
    merged_pricing = _merge_unique_strings(deterministic.pricing, _pricing_to_signals(llm_result.pricing))
    merged_value_statements = _merge_unique_strings(
        deterministic.value_statements,
        vendor_intel._extract_value_statements(_build_signal_text(  # noqa: SLF001
            mission=merged_mission,
            usp=merged_usp,
            use_cases=merged_use_cases,
        ).lower()),
    )

    return VendorIntelligence(
        vendor_name=deterministic.vendor_name,
        website=deterministic.website,
        source=deterministic.source,
        mission=merged_mission,
        usp=merged_usp,
        icp=deterministic.icp,
        use_cases=merged_use_cases,
        lifecycle_stages=deterministic.lifecycle_stages,
        pricing=merged_pricing,
        free_trial=_prefer_optional_bool(deterministic.free_trial, llm_result.free_trial),
        soc2=_prefer_optional_bool(deterministic.soc2, llm_result.soc2),
        founded=_prefer_text_value(deterministic.founded, llm_result.founded),
        case_studies=deterministic.case_studies,
        customers=deterministic.customers,
        value_statements=merged_value_statements,
        confidence=_prefer_confidence(deterministic.confidence, llm_result.confidence),
        evidence_urls=deterministic.evidence_urls,
        directory_fit=deterministic.directory_fit,
        directory_category=deterministic.directory_category,
        include_in_directory=deterministic.include_in_directory,
    )


def _merge_unique_strings(*collections: list[str]) -> list[str]:
    merged: list[str] = []
    for collection in collections:
        for value in collection:
            cleaned_value = value.strip()
            if cleaned_value and cleaned_value not in merged:
                merged.append(cleaned_value)
    return merged


def _prefer_text_value(deterministic_value: str, llm_value: str) -> str:
    """Prefer deterministic text unless the LLM output is materially richer."""
    cleaned_deterministic = deterministic_value.strip()
    cleaned_llm = llm_value.strip()

    if not cleaned_deterministic:
        return cleaned_llm
    if not cleaned_llm:
        return cleaned_deterministic
    if len(cleaned_llm) >= len(cleaned_deterministic) + 20:
        return cleaned_llm
    return cleaned_deterministic


def _prefer_optional_bool(deterministic_value: bool | None, llm_value: bool | None) -> bool | None:
    """Prefer known positive deterministic signals over weaker LLM negatives."""
    if deterministic_value is True:
        return True
    if llm_value is not None:
        return llm_value
    return deterministic_value


def _prefer_confidence(deterministic_confidence: str, llm_confidence: str) -> str:
    """Keep the strongest non-empty confidence label."""
    confidence_order = {"": 0, "low": 1, "medium": 2, "high": 3}
    cleaned_deterministic = deterministic_confidence.strip().lower()
    cleaned_llm = llm_confidence.strip().lower()

    if confidence_order.get(cleaned_llm, 0) > confidence_order.get(cleaned_deterministic, 0):
        return cleaned_llm
    return cleaned_deterministic


def _build_signal_text(
    *,
    mission: str = "",
    usp: str = "",
    use_cases: list[str] | None = None,
    value_statements: list[str] | None = None,
) -> str:
    parts = [mission, usp]
    parts.extend(use_cases or [])
    parts.extend(value_statements or [])
    return " ".join(part for part in parts if part).strip()


def _pricing_to_signals(pricing: str) -> list[str]:
    """Convert a short LLM pricing summary into deterministic signal strings."""
    if not pricing.strip():
        return []

    normalized = pricing.replace("\n", "|").replace(",", "|")
    return [segment.strip() for segment in normalized.split("|") if segment.strip()]
