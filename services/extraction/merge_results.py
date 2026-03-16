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

    merged_mission = llm_result.mission or deterministic.mission
    merged_usp = llm_result.usp or deterministic.usp
    merged_use_cases = _merge_unique_strings(deterministic.use_cases, llm_result.use_cases)
    merged_pricing = _merge_unique_strings(deterministic.pricing, llm_result.pricing)
    merged_value_statements = _merge_unique_strings(
        deterministic.value_statements,
        vendor_intel._extract_value_statements(_build_signal_text(  # noqa: SLF001
            mission=merged_mission,
            usp=merged_usp,
            use_cases=merged_use_cases,
        ).lower()),
    )
    merged_lifecycle_stages = _merge_unique_strings(
        deterministic.lifecycle_stages,
        vendor_intel._extract_lifecycle_stages(_build_signal_text(  # noqa: SLF001
            mission=merged_mission,
            usp=merged_usp,
            use_cases=merged_use_cases,
            value_statements=merged_value_statements,
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
        lifecycle_stages=merged_lifecycle_stages,
        pricing=merged_pricing,
        free_trial=llm_result.free_trial if llm_result.free_trial is not None else deterministic.free_trial,
        soc2=llm_result.soc2 if llm_result.soc2 is not None else deterministic.soc2,
        founded=llm_result.founded or deterministic.founded,
        case_studies=deterministic.case_studies,
        customers=deterministic.customers,
        value_statements=merged_value_statements,
        confidence=llm_result.confidence or deterministic.confidence,
        evidence_urls=deterministic.evidence_urls,
    )


def _merge_unique_strings(*collections: list[str]) -> list[str]:
    merged: list[str] = []
    for collection in collections:
        for value in collection:
            cleaned_value = value.strip()
            if cleaned_value and cleaned_value not in merged:
                merged.append(cleaned_value)
    return merged


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
