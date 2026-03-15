"""Vendor intelligence extraction schema.

This module defines the schema used to represent extracted vendor intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LIFECYCLE_STAGE_RULES = [
    (
        "Sign",
        [
            "conversational intelligence",
            "ai notetaker",
            "ai notetakers",
            "notetaker",
            "meeting summary",
            "meeting summaries",
            "sales-to-cs handoff",
            "sales to cs handoff",
            "handoff",
        ],
    ),
    (
        "Onboard",
        [
            "implementation portal",
            "implementation portals",
            "psa",
            "professional services automation",
            "onboarding automation",
            "time to value",
            "time-to-value",
            "implementation",
        ],
    ),
    (
        "Activate",
        [
            "in-app guidance",
            "user education",
            "product walkthrough",
            "product walkthroughs",
            "walkthrough",
            "walkthroughs",
            "adoption nudge",
            "adoption nudges",
        ],
    ),
    (
        "Adopt",
        [
            "health scoring",
            "usage analytics",
            "sentiment analysis",
            "signal-to-playbook",
            "signal to playbook",
            "customer health",
        ],
    ),
    (
        "Expand",
        [
            "upsell",
            "cross-sell",
            "cross sell",
            "expansion revenue",
            "stakeholder mapping",
        ],
    ),
    (
        "Renew",
        [
            "churn prediction",
            "renewal automation",
            "risk alert",
            "risk alerts",
            "forecasting",
            "renewal",
            "renewals",
            "churn",
        ],
    ),
    (
        "Advocate",
        [
            "nps",
            "voice of customer",
            "voc",
            "reference management",
            "case study tool",
            "case study tools",
            "case study",
            "case studies",
        ],
    ),
]

USE_CASE_KEYWORDS = [
    (["onboarding"], "onboarding"),
    (["churn"], "churn"),
    (["retention"], "retention"),
    (["support"], "support"),
    (["automation", "automate"], "automation"),
    (["health"], "health"),
    (["adoption"], "adoption"),
    (["renewal", "renewals"], "renewal"),
    (["expansion"], "expansion"),
]

VALUE_STATEMENT_RULES = [
    (["reduce churn"], "reduce churn"),
    (["improve adoption", "improves adoption"], "improve adoption"),
    (["automate workflows", "automates workflows"], "automate workflows"),
    (["improve customer health", "improving customer health"], "improve customer health"),
    (["increase retention", "increasing retention"], "increase retention"),
    (["reduce support workload"], "reduce support workload"),
    (["speed time to value", "speeds time to value"], "speed time to value"),
]


@dataclass
class VendorIntelligence:
    vendor_name: str
    website: str
    icp: list[str] = field(default_factory=list)
    lifecycle_stages: list[str] = field(default_factory=list)
    case_studies: list[str] = field(default_factory=list)
    value_statements: list[str] = field(default_factory=list)
    pricing: list[str] = field(default_factory=list)

    def validate(self) -> None:
        """Validate the schema structure and types.

        Raises:
            TypeError: If any field is missing or has an unexpected type.
        """
        if not isinstance(self.vendor_name, str):
            raise TypeError("vendor_name must be a string")
        if not isinstance(self.website, str):
            raise TypeError("website must be a string")

        for field_name in [
            "icp",
            "lifecycle_stages",
            "case_studies",
            "value_statements",
            "pricing",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise TypeError(f"{field_name} must be a list")
            if not all(isinstance(item, str) for item in value):
                raise TypeError(f"All items in {field_name} must be strings")


def extract_vendor_intelligence(
    homepage_payload: dict[str, str | int],
) -> VendorIntelligence:
    """Convert a homepage payload into a VendorIntelligence object.

    This MVP implementation uses simple rule-based keyword matching on
    homepage text to populate a few useful fields deterministically.
    """
    text = str(homepage_payload.get("text", "")).lower()
    use_cases = _extract_use_cases(text)
    lifecycle_stages = _extract_lifecycle_stages(text)
    value_statements = _extract_value_statements(text)

    return VendorIntelligence(
        vendor_name=str(homepage_payload["vendor_name"]),
        website=str(homepage_payload["website"]),
        icp=use_cases,
        lifecycle_stages=lifecycle_stages,
        value_statements=value_statements,
    )


def _extract_lifecycle_stages(text: str) -> list[str]:
    """Return lifecycle stages detected from homepage text."""
    lifecycle_stages: list[str] = []

    for stage_name, keywords in LIFECYCLE_STAGE_RULES:
        if any(keyword in text for keyword in keywords):
            lifecycle_stages.append(stage_name)

    return lifecycle_stages


def _extract_use_cases(text: str) -> list[str]:
    """Return use cases detected from homepage text."""
    use_cases: list[str] = []

    for keywords, label in USE_CASE_KEYWORDS:
        if any(keyword in text for keyword in keywords) and label not in use_cases:
            use_cases.append(label)

    return use_cases


def _extract_value_statements(text: str) -> list[str]:
    """Return value statements detected from homepage text."""
    value_statements: list[str] = []

    for phrases, label in VALUE_STATEMENT_RULES:
        if any(phrase in text for phrase in phrases):
            value_statements.append(label)

    return value_statements
