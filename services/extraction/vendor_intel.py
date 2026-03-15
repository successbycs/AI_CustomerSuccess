"""Vendor intelligence extraction schema.

This module defines the schema used to represent extracted vendor intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

LIFECYCLE_STAGE_RULES = [
    (
        "Sign",
        [
            "call summary",
            "call summaries",
            "conversational intelligence",
            "conversation intelligence",
            "handoff",
            "meeting note",
            "meeting notes",
            "meeting summary",
            "meeting summaries",
            "notetaker",
            "sales to cs handoff",
            "sales-to-cs handoff",
        ],
    ),
    (
        "Onboard",
        [
            "implementation portal",
            "implementation portals",
            "onboarding automation",
            "professional services automation",
            "psa",
            "time to value",
            "time-to-value",
        ],
    ),
    (
        "Activate",
        [
            "adoption nudge",
            "adoption nudges",
            "guided onboarding",
            "in app guidance",
            "in-app guidance",
            "product walkthrough",
            "product walkthroughs",
            "user education",
            "walkthrough",
            "walkthroughs",
        ],
    ),
    (
        "Adopt",
        [
            "customer health",
            "health score",
            "health scoring",
            "playbook automation",
            "sentiment analysis",
            "signal to playbook",
            "signal-to-playbook",
            "usage analytics",
            "usage signals",
        ],
    ),
    (
        "Support",
        [
            "agent assist",
            "case deflection",
            "case routing",
            "help desk",
            "knowledge base",
            "support automation",
            "support copilot",
            "support platform",
            "ticket triage",
        ],
    ),
    (
        "Expand",
        [
            "cross sell",
            "cross-sell",
            "expansion revenue",
            "stakeholder mapping",
            "upsell",
        ],
    ),
    (
        "Renew",
        [
            "churn",
            "churn prediction",
            "forecasting",
            "renewal",
            "renewal automation",
            "renewals",
            "risk alert",
            "risk alerts",
        ],
    ),
    (
        "Advocate",
        [
            "case studies",
            "case study",
            "nps",
            "reference management",
            "reference program",
            "voice of customer",
            "voc",
        ],
    ),
]

USE_CASE_RULES = [
    (["sales to cs handoff", "sales-to-cs handoff", "meeting summary", "meeting summaries"], "sales-to-cs handoff"),
    (["conversational intelligence", "conversation intelligence", "call summary", "call summaries"], "meeting intelligence"),
    (["onboarding automation", "implementation portal", "implementation portals"], "onboarding"),
    (["time to value", "time-to-value"], "time to value"),
    (["in-app guidance", "in app guidance", "user education", "product walkthrough", "product walkthroughs"], "product activation"),
    (["adoption nudge", "adoption nudges", "guided onboarding"], "adoption guidance"),
    (["health score", "health scoring", "customer health"], "health scoring"),
    (["usage analytics", "usage signals"], "usage analytics"),
    (["sentiment analysis"], "sentiment analysis"),
    (["signal to playbook", "signal-to-playbook", "playbook automation"], "playbook automation"),
    (["support automation", "support platform", "help desk", "agent assist"], "support automation"),
    (["ticket triage", "case routing", "case deflection"], "ticket triage"),
    (["knowledge base"], "knowledge base"),
    (["upsell", "cross-sell", "cross sell", "expansion revenue"], "expansion"),
    (["stakeholder mapping"], "stakeholder mapping"),
    (["renewal automation", "renewal", "renewals"], "renewal management"),
    (["churn", "churn prediction", "risk alert", "risk alerts"], "churn prevention"),
    (["nps", "voice of customer", "voc"], "voice of customer"),
    (["reference management", "reference program", "case study", "case studies"], "customer advocacy"),
]

VALUE_STATEMENT_RULES = [
    (["sales to cs handoff", "sales-to-cs handoff", "meeting summaries", "meeting summary"], "improve handoff"),
    (["speed time to value", "speeds time to value", "time to value", "time-to-value"], "speed time to value"),
    (["reduce churn", "reduces churn", "churn prediction", "risk alert", "risk alerts"], "reduce churn"),
    (["improve adoption", "improves adoption", "in-app guidance", "in app guidance", "user education", "product walkthrough", "product walkthroughs"], "improve adoption"),
    (["improve customer health", "improving customer health", "customer health", "health score", "health scoring"], "improve customer health"),
    (["support automation", "help desk", "agent assist", "ticket triage", "case deflection"], "reduce support workload"),
    (["automate workflows", "automates workflows", "signal to playbook", "signal-to-playbook", "playbook automation"], "automate workflows"),
    (["onboarding automation", "implementation portal", "implementation portals"], "automate onboarding"),
    (["increase retention", "increasing retention", "renewal automation", "renewal", "renewals"], "increase retention"),
    (["upsell", "cross-sell", "cross sell", "expansion revenue"], "grow expansion revenue"),
    (["forecasting", "renewal automation", "risk alert", "risk alerts"], "improve renewal forecasting"),
    (["nps", "voice of customer", "voc", "reference management", "case study", "case studies"], "strengthen customer advocacy"),
]


@dataclass
class VendorIntelligence:
    vendor_name: str
    website: str
    source: str = ""
    mission: str = ""
    usp: str = ""
    icp: list[str] = field(default_factory=list)
    lifecycle_stages: list[str] = field(default_factory=list)
    case_studies: list[str] = field(default_factory=list)
    value_statements: list[str] = field(default_factory=list)
    pricing: list[str] = field(default_factory=list)
    free_trial: bool | None = None
    soc2: bool | None = None
    founded: str = ""
    confidence: str = ""
    evidence_urls: list[str] = field(default_factory=list)

    def validate(self) -> None:
        """Validate the schema structure and types.

        Raises:
            TypeError: If any field is missing or has an unexpected type.
        """
        if not isinstance(self.vendor_name, str):
            raise TypeError("vendor_name must be a string")
        if not isinstance(self.website, str):
            raise TypeError("website must be a string")
        for field_name in ["source", "mission", "usp", "founded", "confidence"]:
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")

        for field_name in [
            "icp",
            "lifecycle_stages",
            "case_studies",
            "value_statements",
            "pricing",
            "evidence_urls",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise TypeError(f"{field_name} must be a list")
            if not all(isinstance(item, str) for item in value):
                raise TypeError(f"All items in {field_name} must be strings")

        for field_name in ["free_trial", "soc2"]:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a bool or None")


def extract_vendor_intelligence(
    homepage_payload: dict[str, str | int],
) -> VendorIntelligence:
    """Convert a homepage payload into a VendorIntelligence object.

    This MVP implementation uses simple rule-based keyword matching on
    homepage text to populate a few useful fields deterministically.
    """
    raw_text = str(homepage_payload.get("text", "")).strip()
    text = raw_text.lower()
    use_cases = _extract_use_cases(text)
    lifecycle_stages = _extract_lifecycle_stages(text)
    value_statements = _extract_value_statements(text)

    return VendorIntelligence(
        vendor_name=str(homepage_payload["vendor_name"]),
        website=str(homepage_payload["website"]),
        source=str(homepage_payload.get("source", "")),
        mission=_extract_mission(raw_text),
        usp=value_statements[0] if value_statements else "",
        icp=use_cases,
        lifecycle_stages=lifecycle_stages,
        value_statements=value_statements,
        free_trial=_detect_boolean_signal(text, ["free trial"]),
        soc2=_detect_boolean_signal(text, ["soc 2", "soc2"]),
        founded=_extract_founded(raw_text),
        confidence=_determine_confidence(use_cases, lifecycle_stages, value_statements),
    )


def _extract_lifecycle_stages(text: str) -> list[str]:
    """Return lifecycle stages detected from homepage text."""
    lifecycle_stages: list[str] = []

    for stage_name, keywords in LIFECYCLE_STAGE_RULES:
        if _contains_any(text, keywords):
            lifecycle_stages.append(stage_name)

    return lifecycle_stages


def _extract_use_cases(text: str) -> list[str]:
    """Return use cases detected from homepage text."""
    use_cases: list[str] = []

    for keywords, label in USE_CASE_RULES:
        if _contains_any(text, keywords) and label not in use_cases:
            use_cases.append(label)

    return use_cases


def _extract_value_statements(text: str) -> list[str]:
    """Return value statements detected from homepage text."""
    value_statements: list[str] = []

    for phrases, label in VALUE_STATEMENT_RULES:
        if _contains_any(text, phrases):
            value_statements.append(label)

    return value_statements


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Return True when the text contains any keyword or phrase."""
    return any(keyword in text for keyword in keywords)


def _extract_mission(text: str) -> str:
    """Return a short mission-like sentence from homepage text."""
    if not text:
        return ""

    normalized_text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
    for sentence in sentences:
        cleaned_sentence = sentence.strip(" -")
        if cleaned_sentence:
            return cleaned_sentence[:200]

    return ""


def _extract_founded(text: str) -> str:
    """Return a founded year when the homepage text mentions one."""
    match = re.search(r"\b(?:founded|since)\s+(?:in\s+)?((?:19|20)\d{2})\b", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1)


def _detect_boolean_signal(text: str, keywords: list[str]) -> bool | None:
    """Return True when a signal is present, else None."""
    if _contains_any(text, keywords):
        return True
    return None


def _determine_confidence(
    use_cases: list[str],
    lifecycle_stages: list[str],
    value_statements: list[str],
) -> str:
    """Return a simple deterministic confidence label."""
    signal_score = (len(lifecycle_stages) * 2) + len(use_cases) + len(value_statements)
    if signal_score >= 10:
        return "high"
    if signal_score >= 4:
        return "medium"
    return "low"
