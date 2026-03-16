"""Deterministic directory relevance scoring for enriched vendor profiles."""

from __future__ import annotations

from services.config.load_config import DirectoryRelevanceConfig, load_pipeline_config
from services.extraction.vendor_intel import VendorIntelligence


def evaluate_directory_relevance(
    intelligence: VendorIntelligence,
    config: DirectoryRelevanceConfig | None = None,
) -> tuple[str, str, bool]:
    """Return directory fit, category, and include flag from deterministic signals."""
    config = config or load_pipeline_config().directory_relevance

    confidence = intelligence.confidence.strip().lower()
    stages = tuple(stage for stage in intelligence.lifecycle_stages if stage)
    signal_text = _signal_text(intelligence).lower()

    has_core_stage = any(stage in config.core_stages for stage in stages)
    has_support_only_stage = bool(stages) and all(stage in config.support_only_stages for stage in stages)
    has_core_use_case = any(hint in signal_text for hint in config.core_use_case_hints)
    has_adjacent_use_case = any(hint in signal_text for hint in config.adjacent_use_case_hints)
    has_infra_hint = any(hint in signal_text for hint in config.infra_hints)
    has_customer_success_signal = any(
        hint in signal_text
        for hint in (
            "customer success",
            "renewal",
            "onboarding",
            "adoption",
            "retention",
            "customer health",
            "churn",
            "voice of customer",
            "advocacy",
        )
    )
    has_generic_cx_hint = any(
        hint in signal_text
        for hint in (
            "customer experience",
            "cx platform",
            "contact center",
            "call center",
            "help desk",
        )
    )

    if has_infra_hint and not (has_core_stage or has_core_use_case or has_adjacent_use_case):
        return "low", "infra", False

    if has_core_stage or has_core_use_case:
        include = confidence in config.include_confidence_levels
        fit = "high" if confidence == "high" else "medium"
        return fit, "cs_core", include

    if has_support_only_stage:
        include = confidence in config.include_confidence_levels
        fit = "medium" if include else "low"
        return fit, "support_only", include

    if has_adjacent_use_case or has_customer_success_signal:
        include = confidence in config.include_confidence_levels
        fit = "medium" if include else "low"
        return fit, "cs_adjacent", include

    if has_generic_cx_hint:
        return "low", "generic_cx", False

    include = confidence in config.include_confidence_levels and bool(
        intelligence.mission.strip() or intelligence.usp.strip() or intelligence.use_cases
    )
    return ("medium" if include else "low"), ("cs_adjacent" if include else "infra"), include


def _signal_text(intelligence: VendorIntelligence) -> str:
    parts = [
        intelligence.mission,
        intelligence.usp,
        *intelligence.icp,
        *intelligence.use_cases,
        *intelligence.value_statements,
        *intelligence.case_studies,
        *intelligence.customers,
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())
