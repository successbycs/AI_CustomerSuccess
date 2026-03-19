"""Vendor intelligence extraction schema.

This module defines the schema used to represent extracted vendor intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any
from urllib.parse import urlparse

CANONICAL_LIFECYCLE_STAGES = [
    "Sign",
    "Onboard",
    "Activate",
    "Adopt",
    "Support",
    "Expand",
    "Renew",
    "Advocate",
]

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

ICP_RULES = [
    (["for saas companies", "saas companies", "for modern saas teams"], "SaaS companies"),
    (["for b2b startups", "b2b startups", "for b2b software teams"], "B2B startups"),
    (["for product-led teams", "product-led teams", "for product led teams", "product led teams"], "product-led teams"),
    (["for customer success teams", "customer success teams", "built for customer success teams"], "customer success teams"),
    (["for support teams", "support teams", "built for support teams"], "support teams"),
    (["for revenue teams", "revenue teams", "for revenue operations teams"], "revenue teams"),
]

PRICING_RULES = [
    (["per seat"], "per seat"),
    (["per user"], "per user"),
    (["per month", "/month", "monthly"], "per month"),
    (["per year", "/year", "annually"], "per year"),
    (["contact sales", "custom pricing"], "contact sales"),
]

CASE_STUDY_RULES = [
    (["case study", "case studies"], "case study"),
    (["customer story", "customer stories"], "customer story"),
]

INTEGRATION_CATEGORY_RULES = [
    (["salesforce", "hubspot"], "crm"),
    (["slack", "microsoft teams", "teams"], "communication"),
    (["zendesk", "intercom", "freshdesk"], "support"),
    (["segment", "snowflake", "bigquery"], "data"),
    (["jira", "asana"], "project management"),
]

KNOWN_INTEGRATIONS = [
    "Asana",
    "BigQuery",
    "Freshdesk",
    "HubSpot",
    "Intercom",
    "Jira",
    "Microsoft Teams",
    "Salesforce",
    "Segment",
    "Slack",
    "Snowflake",
    "Zendesk",
]

SUPPORT_SIGNAL_RULES = [
    (["help center", "help centre", "help-center"], "help center"),
    (["knowledge base", "knowledge-base"], "knowledge base"),
    (["support portal", "support center", "support-centre"], "support portal"),
    (["community forum", "community support"], "community"),
    (["academy", "training"], "training"),
]

CUSTOMER_PATTERNS = [
    r"trusted by ([A-Z][A-Za-z0-9&.-]+(?:,\s*[A-Z][A-Za-z0-9&.-]+){0,4})",
    r"customers include ([A-Z][A-Za-z0-9&.-]+(?:,\s*[A-Z][A-Za-z0-9&.-]+){0,4})",
    r"used by ([A-Z][A-Za-z0-9&.-]+(?:,\s*[A-Z][A-Za-z0-9&.-]+){0,4})",
    r"how ([A-Z][A-Za-z0-9&.-]+) uses",
]
STRONG_CS_RELEVANCE_HINTS = [
    "customer success",
    "customer success teams",
    "customer onboarding",
    "customer health",
    "health score",
    "health scoring",
    "implementation portal",
    "implementation portals",
    "in-app guidance",
    "onboarding automation",
    "playbook automation",
    "renewal automation",
    "sales to cs handoff",
    "sales-to-cs handoff",
    "stakeholder mapping",
    "support automation",
    "ticket triage",
    "time to value",
    "time-to-value",
    "usage analytics",
    "voice of customer",
]


@dataclass
class VendorIntelligence:
    vendor_name: str
    website: str
    source: str = ""
    mission: str = ""
    usp: str = ""
    icp: list[str] = field(default_factory=list)
    icp_buyer: list[dict[str, Any]] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    lifecycle_stages: list[str] = field(default_factory=list)
    pricing: list[str] = field(default_factory=list)
    free_trial: bool | None = None
    soc2: bool | None = None
    founded: str = ""
    products: list[dict[str, Any]] = field(default_factory=list)
    leadership: list[dict[str, Any]] = field(default_factory=list)
    company_hq: str = ""
    contact_email: str = ""
    contact_page_url: str = ""
    demo_url: str = ""
    help_center_url: str = ""
    support_url: str = ""
    about_url: str = ""
    team_url: str = ""
    integration_categories: list[str] = field(default_factory=list)
    integrations: list[str] = field(default_factory=list)
    support_signals: list[str] = field(default_factory=list)
    case_studies: list[str] = field(default_factory=list)
    case_study_details: list[dict[str, Any]] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    value_statements: list[str] = field(default_factory=list)
    confidence: str = ""
    evidence_urls: list[str] = field(default_factory=list)
    directory_fit: str = ""
    directory_category: str = ""
    include_in_directory: bool | None = None

    def __post_init__(self) -> None:
        """Normalize structured buyer-persona enrichment into a stable list-of-dicts shape."""
        self.website = normalize_website_url(self.website)
        self.icp_buyer = normalize_icp_buyer_profiles(self.icp_buyer)
        self.products = normalize_product_profiles(self.products)
        self.leadership = normalize_leadership_profiles(self.leadership)
        self.contact_email = normalize_email_address(self.contact_email)
        self.contact_page_url = normalize_website_url(self.contact_page_url)
        self.demo_url = normalize_website_url(self.demo_url)
        self.help_center_url = normalize_website_url(self.help_center_url)
        self.support_url = normalize_website_url(self.support_url)
        self.about_url = normalize_website_url(self.about_url)
        self.team_url = normalize_website_url(self.team_url)
        self.integration_categories = _normalize_string_list(self.integration_categories)
        self.integrations = _normalize_string_list(self.integrations)
        self.support_signals = _normalize_string_list(self.support_signals)
        self.case_study_details = normalize_case_study_details(self.case_study_details)
        self.evidence_urls = [url for url in (normalize_website_url(url) for url in self.evidence_urls) if url]

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
            "source",
            "mission",
            "usp",
            "founded",
            "confidence",
            "directory_fit",
            "directory_category",
            "company_hq",
            "contact_email",
            "contact_page_url",
            "demo_url",
            "help_center_url",
            "support_url",
            "about_url",
            "team_url",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")

        for field_name in [
            "icp",
            "use_cases",
            "lifecycle_stages",
            "pricing",
            "integration_categories",
            "integrations",
            "support_signals",
            "case_studies",
            "customers",
            "value_statements",
            "evidence_urls",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise TypeError(f"{field_name} must be a list")
            if not all(isinstance(item, str) for item in value):
                raise TypeError(f"All items in {field_name} must be strings")

        if not isinstance(self.icp_buyer, list):
            raise TypeError("icp_buyer must be a list")
        if not all(isinstance(item, dict) for item in self.icp_buyer):
            raise TypeError("All items in icp_buyer must be objects")
        if not isinstance(self.products, list):
            raise TypeError("products must be a list")
        if not all(isinstance(item, dict) for item in self.products):
            raise TypeError("All items in products must be objects")
        if not isinstance(self.leadership, list):
            raise TypeError("leadership must be a list")
        if not all(isinstance(item, dict) for item in self.leadership):
            raise TypeError("All items in leadership must be objects")
        if not isinstance(self.case_study_details, list):
            raise TypeError("case_study_details must be a list")
        if not all(isinstance(item, dict) for item in self.case_study_details):
            raise TypeError("All items in case_study_details must be objects")

        for field_name in ["free_trial", "soc2", "include_in_directory"]:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a bool or None")

        invalid_lifecycle_stages = [
            lifecycle_stage
            for lifecycle_stage in self.lifecycle_stages
            if lifecycle_stage not in CANONICAL_LIFECYCLE_STAGES
        ]
        if invalid_lifecycle_stages:
            raise TypeError(
                "lifecycle_stages must only contain canonical stage names: "
                + ", ".join(invalid_lifecycle_stages)
            )


def normalize_icp_buyer_profiles(value: object) -> list[dict[str, Any]]:
    """Return a normalized buyer-persona enrichment payload."""
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []
        return normalize_icp_buyer_profiles(parsed)

    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen_personas: set[str] = set()
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue

        persona = str(raw_item.get("persona") or "").strip()
        if not persona:
            continue
        lowered_persona = persona.lower()
        if lowered_persona in seen_personas:
            continue

        confidence = _normalize_confidence_label(raw_item.get("confidence"))
        google_queries = _normalize_query_list(raw_item.get("google_queries"))
        geo_queries = _normalize_query_list(raw_item.get("geo_queries"))
        evidence = _normalize_string_list(raw_item.get("evidence"))

        normalized.append(
            {
                "persona": persona,
                "confidence": confidence,
                "evidence": evidence,
                "google_queries": google_queries,
                "geo_queries": geo_queries,
            }
        )
        seen_personas.add(lowered_persona)

    return normalized


def normalize_product_profiles(value: object) -> list[dict[str, Any]]:
    """Return normalized structured product metadata."""
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []
        return normalize_product_profiles(parsed)

    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for raw_item in value:
        if isinstance(raw_item, str):
            raw_item = {"name": raw_item}
        if not isinstance(raw_item, dict):
            continue

        name = str(raw_item.get("name") or "").strip()
        if not name:
            continue

        key = name.lower()
        if key in seen_keys:
            continue

        normalized.append(
            {
                "name": name,
                "category": str(raw_item.get("category") or "").strip(),
                "description": str(raw_item.get("description") or "").strip(),
                "source_url": normalize_website_url(raw_item.get("source_url")),
            }
        )
        seen_keys.add(key)
    return normalized


def normalize_leadership_profiles(value: object) -> list[dict[str, Any]]:
    """Return normalized structured leadership metadata."""
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []
        return normalize_leadership_profiles(parsed)

    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue

        name = str(raw_item.get("name") or "").strip()
        title = str(raw_item.get("title") or "").strip()
        if not name:
            continue

        key = (name.lower(), title.lower())
        if key in seen_keys:
            continue

        normalized.append(
            {
                "name": name,
                "title": title,
                "source_url": normalize_website_url(raw_item.get("source_url")),
            }
        )
        seen_keys.add(key)
    return normalized


def normalize_case_study_details(value: object) -> list[dict[str, Any]]:
    """Return normalized structured case-study metadata."""
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []
        return normalize_case_study_details(parsed)

    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue

        client = str(raw_item.get("client") or "").strip()
        title = str(raw_item.get("title") or "").strip()
        use_case = str(raw_item.get("use_case") or "").strip()
        value_realized = str(raw_item.get("value_realized") or "").strip()
        if not any((client, title, use_case, value_realized)):
            continue

        key = (client.lower(), title.lower(), value_realized.lower())
        if key in seen_keys:
            continue

        normalized.append(
            {
                "client": client,
                "title": title,
                "use_case": use_case,
                "value_realized": value_realized,
                "source_url": normalize_website_url(raw_item.get("source_url")),
            }
        )
        seen_keys.add(key)
    return normalized


def summarize_icp_buyer_profiles(profiles: list[dict[str, Any]]) -> str:
    """Return a readable summary of buyer personas for flat review surfaces."""
    personas = [str(item.get("persona") or "").strip() for item in profiles if isinstance(item, dict)]
    personas = [persona for persona in personas if persona]
    return ", ".join(personas)


def normalize_website_url(value: object) -> str:
    """Return a canonical website URL suitable for persistence."""
    text = str(value or "").strip()
    if not text:
        return ""

    if "://" not in text and re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(/.*)?$", text, flags=re.IGNORECASE):
        text = f"https://{text}"

    parsed = urlparse(text)
    if not parsed.netloc:
        return ""

    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if path == "/":
        path = ""

    scheme = parsed.scheme.lower() or "https"
    return f"{scheme}://{domain}{path}"


def normalize_email_address(value: object) -> str:
    """Return a canonical email address suitable for persistence."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if not re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", text):
        return ""
    return text


def _normalize_query_list(value: object) -> list[str]:
    queries = _normalize_string_list(value)
    return queries[:5]


def _normalize_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        candidates = [segment.strip() for segment in value.replace("\n", ",").replace("|", ",").split(",")]
        normalized: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in normalized:
                normalized.append(candidate)
        return normalized

    if isinstance(value, list):
        normalized = []
        for item in value:
            cleaned_item = str(item).strip()
            if cleaned_item and cleaned_item not in normalized:
                normalized.append(cleaned_item)
        return normalized

    return []


def _normalize_confidence_label(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in {"low", "medium", "high"}:
        return cleaned
    return ""


def extract_vendor_intelligence(
    page_payload: dict[str, object],
) -> VendorIntelligence:
    """Convert explored vendor page payloads into a VendorIntelligence object.

    This implementation uses simple rule-based keyword matching on
    homepage and high-signal vendor pages to populate directory fields.
    """
    page_payloads = _coerce_page_payloads(page_payload)
    homepage_payload = page_payloads.get("homepage", {})
    homepage_text = str(homepage_payload.get("text", "")).strip()
    combined_text = _combine_page_texts(page_payloads)
    combined_text_lower = combined_text.lower()
    relevance_text = _combine_relevance_texts(page_payloads).lower()
    pricing_text = _page_text(page_payloads, "pricing_page").lower()
    case_studies_text = _page_text(page_payloads, "case_studies_page")
    case_studies_text_lower = case_studies_text.lower()
    product_text = _page_text(page_payloads, "product_page")
    about_text = _page_text(page_payloads, "about_page")
    team_text = _page_text(page_payloads, "team_page")
    contact_text = _page_text(page_payloads, "contact_page")
    demo_text = _page_text(page_payloads, "demo_page")
    help_text = _page_text(page_payloads, "help_page")
    support_text = _page_text(page_payloads, "support_page")
    integrations_text = _page_text(page_payloads, "integrations_page")
    security_text = _page_text(page_payloads, "security_page").lower()
    all_evidence_urls = _collect_page_urls(page_payloads)
    canonical_website = normalize_website_url(
        homepage_payload.get("website") or homepage_payload.get("url") or ""
    )

    icp = _extract_icp(combined_text_lower)
    use_cases = _extract_use_cases(combined_text_lower)
    lifecycle_stages = _extract_lifecycle_stages(combined_text_lower)
    value_statements = _extract_value_statements(combined_text_lower)
    case_studies = _extract_case_studies(case_studies_text_lower or combined_text_lower)
    customers = _extract_customers(combined_text)
    pricing = _extract_pricing(pricing_text or combined_text_lower)
    case_study_details = _extract_case_study_details(
        case_studies_text or "",
        source_url=_page_url(page_payloads, "case_studies_page"),
    )
    free_trial = _detect_boolean_signal(combined_text_lower, ["free trial", "start free", "try free"])
    soc2 = _detect_boolean_signal(security_text or combined_text_lower, ["soc 2", "soc2", "iso 27001", "iso27001"])

    return VendorIntelligence(
        vendor_name=str(homepage_payload.get("vendor_name", "")),
        website=canonical_website,
        source=str(homepage_payload.get("source", "")),
        mission=_extract_mission(homepage_text or combined_text),
        usp=_extract_usp(value_statements, combined_text),
        icp=icp,
        use_cases=use_cases,
        lifecycle_stages=lifecycle_stages,
        pricing=pricing,
        free_trial=free_trial,
        soc2=soc2,
        founded=_extract_founded(combined_text),
        products=_extract_products(
            product_text or homepage_text,
            source_url=_page_url(page_payloads, "product_page") or canonical_website,
        ),
        leadership=_extract_leadership(
            f"{about_text} {team_text}".strip(),
            source_url=_page_url(page_payloads, "team_page") or _page_url(page_payloads, "about_page"),
        ),
        company_hq=_extract_company_hq(f"{about_text} {contact_text}".strip()),
        contact_email=_extract_contact_email(contact_text or combined_text),
        contact_page_url=_page_url(page_payloads, "contact_page"),
        demo_url=_page_url(page_payloads, "demo_page"),
        help_center_url=_page_url(page_payloads, "help_page"),
        support_url=_page_url(page_payloads, "support_page"),
        about_url=_page_url(page_payloads, "about_page"),
        team_url=_page_url(page_payloads, "team_page"),
        integration_categories=_extract_integration_categories(integrations_text or combined_text),
        integrations=_extract_integrations(integrations_text),
        support_signals=_extract_support_signals(
            f"{help_text} {support_text} {contact_text} {demo_text}".strip().lower()
        ),
        case_studies=case_studies,
        case_study_details=case_study_details,
        customers=customers,
        value_statements=value_statements,
        confidence=_determine_confidence(
            icp=icp,
            use_cases=use_cases,
            lifecycle_stages=lifecycle_stages,
            value_statements=value_statements,
            case_studies=case_studies,
            pricing=pricing,
            strong_cs_relevance=_has_strong_cs_relevance(relevance_text),
        ),
        evidence_urls=all_evidence_urls,
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


def _extract_icp(text: str) -> list[str]:
    """Return simple ICP labels detected from vendor text."""
    icp: list[str] = []

    for keywords, label in ICP_RULES:
        if _contains_any(text, keywords) and label not in icp:
            icp.append(label)

    return icp


def _extract_value_statements(text: str) -> list[str]:
    """Return value statements detected from homepage text."""
    value_statements: list[str] = []

    for phrases, label in VALUE_STATEMENT_RULES:
        if _contains_any(text, phrases):
            value_statements.append(label)

    return value_statements


def _extract_pricing(text: str) -> list[str]:
    """Return simple pricing signals from vendor text."""
    pricing: list[str] = []

    if "$" in text and "$" not in pricing:
        pricing.append("$")

    for keywords, label in PRICING_RULES:
        if _contains_any(text, keywords) and label not in pricing:
            pricing.append(label)

    return pricing


def _extract_case_studies(text: str) -> list[str]:
    """Return case-study style proof signals from vendor text."""
    case_studies: list[str] = []

    for keywords, label in CASE_STUDY_RULES:
        if _contains_any(text, keywords) and label not in case_studies:
            case_studies.append(label)

    if re.search(r"how [a-z0-9&.-]+ uses", text) and "how customers use the product" not in case_studies:
        case_studies.append("how customers use the product")

    return case_studies


def _extract_case_study_details(text: str, *, source_url: str) -> list[dict[str, str]]:
    """Return structured case-study rows when the page exposes customer outcomes."""
    normalized_text = re.sub(r"\s+", " ", text).strip()
    if not normalized_text:
        return []

    details: list[dict[str, str]] = []
    patterns = [
        re.compile(
            r"(?P<client>[A-Z][A-Za-z0-9&.\-]+)\s+(?:used|uses|using)\s+.+?\s+to\s+(?P<value_realized>[^.]+)",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"(?P<client>[A-Z][A-Za-z0-9&.\-]+)\s+(?P<value_realized>(?:reduced|increased|improved|cut)\s+[^.]+)",
            flags=re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(normalized_text):
            client = match.group("client").strip()
            value_realized = match.group("value_realized").strip(" .")
            detail = {
                "client": client,
                "title": f"{client} case study",
                "use_case": _infer_case_study_use_case(value_realized),
                "value_realized": value_realized,
                "source_url": normalize_website_url(source_url),
            }
            if detail not in details:
                details.append(detail)
    return details


def _extract_customers(text: str) -> list[str]:
    """Return simple named-customer signals from vendor text."""
    customers: list[str] = []

    for pattern in CUSTOMER_PATTERNS:
        for match in re.finditer(pattern, text):
            for customer_name in re.split(r",|\band\b", match.group(1)):
                cleaned_name = customer_name.strip().strip(".")
                if cleaned_name and cleaned_name not in customers:
                    customers.append(cleaned_name)

    return customers


def _extract_products(text: str, *, source_url: str) -> list[dict[str, str]]:
    """Return simple structured product rows for vendors with named products."""
    normalized_text = re.sub(r"\s+", " ", text).strip()
    if not normalized_text:
        return []

    products: list[dict[str, str]] = []
    product_match = re.search(
        r"(?:products?|platforms?)\s+(?:include|includes|are|:)\s*([^.]+)",
        normalized_text,
        flags=re.IGNORECASE,
    )
    if not product_match:
        return products

    raw_names = re.split(r",|\band\b", product_match.group(1))
    for raw_name in raw_names:
        name = raw_name.strip().strip(".")
        if not name:
            continue
        products.append(
            {
                "name": name,
                "category": "platform",
                "description": normalized_text[:200],
                "source_url": normalize_website_url(source_url),
            }
        )
    return normalize_product_profiles(products)


def _extract_leadership(text: str, *, source_url: str) -> list[dict[str, str]]:
    """Return structured founder and executive evidence."""
    normalized_text = re.sub(r"\s+", " ", text).strip()
    if not normalized_text:
        return []

    profiles: list[dict[str, str]] = []
    patterns = [
        re.compile(
            r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),\s*(?P<title>CEO|Founder|Co-Founder|Chief Executive Officer|Chief Customer Officer)",
        ),
        re.compile(
            r"(?P<title>CEO|Founder|Co-Founder|Chief Executive Officer|Chief Customer Officer)\s+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ),
        re.compile(
            r"founded by\s+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            flags=re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(normalized_text):
            title = str(match.groupdict().get("title") or "Founder").strip()
            name = str(match.groupdict().get("name") or "").strip()
            if not name:
                continue
            profiles.append(
                {
                    "name": name,
                    "title": title,
                    "source_url": normalize_website_url(source_url),
                }
            )
    return normalize_leadership_profiles(profiles)


def _extract_company_hq(text: str) -> str:
    """Return a headquarters/location string when the site states it explicitly."""
    match = re.search(
        r"(?:headquartered in|based in)\s+([A-Z][A-Za-z\s,.-]+?)(?:\.|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return match.group(1).strip()


def _extract_contact_email(text: str) -> str:
    """Return the first canonical contact email found in the supplied text."""
    match = re.search(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return normalize_email_address(match.group(0))


def _extract_integration_categories(text: str) -> list[str]:
    """Return high-level integration buckets inferred from the integrations surface."""
    lowered_text = text.lower()
    categories: list[str] = []
    for keywords, label in INTEGRATION_CATEGORY_RULES:
        if _contains_any(lowered_text, keywords) and label not in categories:
            categories.append(label)
    return categories


def _extract_integrations(text: str) -> list[str]:
    """Return specific integration names from the integrations surface."""
    integrations: list[str] = []
    lowered_text = text.lower()
    for integration_name in KNOWN_INTEGRATIONS:
        if integration_name.lower() in lowered_text and integration_name not in integrations:
            integrations.append(integration_name)
    return integrations


def _extract_support_signals(text: str) -> list[str]:
    """Return support-surface capabilities discovered from help and support pages."""
    signals: list[str] = []
    for keywords, label in SUPPORT_SIGNAL_RULES:
        if _contains_any(text, keywords) and label not in signals:
            signals.append(label)
    return signals


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Return True when the text contains any keyword or phrase."""
    return any(keyword in text for keyword in keywords)


def _page_url(page_payloads: dict[str, dict[str, str | int]], page_key: str) -> str:
    page_payload = page_payloads.get(page_key, {})
    return normalize_website_url(page_payload.get("website") or page_payload.get("url") or "")


def _extract_mission(text: str) -> str:
    """Return a short mission-like sentence from homepage text."""
    if not text:
        return ""

    normalized_text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
    for sentence in sentences:
        cleaned_sentence = sentence.strip(" -")
        if _looks_like_mission_sentence(cleaned_sentence):
            return cleaned_sentence[:200]

    return sentences[0][:200].strip(" -") if sentences else ""


def _extract_usp(value_statements: list[str], combined_text: str) -> str:
    """Return the most useful deterministic USP signal available."""
    if value_statements:
        return value_statements[0]

    normalized_text = re.sub(r"\s+", " ", combined_text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
    for sentence in sentences:
        lowered_sentence = sentence.lower()
        if any(
            keyword in lowered_sentence
            for keyword in ("reduce", "increase", "improve", "faster", "accelerate", "automate")
        ):
            return sentence[:120].strip(" -")

    return ""


def _extract_founded(text: str) -> str:
    """Return a founded year when the homepage text mentions one."""
    match = re.search(r"\b(?:founded|since)\s+(?:in\s+)?((?:19|20)\d{2})\b", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1)


def _infer_case_study_use_case(value_realized: str) -> str:
    lowered = value_realized.lower()
    for keywords, label in USE_CASE_RULES:
        if _contains_any(lowered, keywords):
            return label
    return ""


def _detect_boolean_signal(text: str, keywords: list[str]) -> bool | None:
    """Return True when a signal is present, else None."""
    if _contains_any(text, keywords):
        return True
    return None


def _determine_confidence(
    *,
    icp: list[str],
    use_cases: list[str],
    lifecycle_stages: list[str],
    value_statements: list[str],
    case_studies: list[str],
    pricing: list[str],
    strong_cs_relevance: bool,
) -> str:
    """Return a simple deterministic confidence label."""
    if not strong_cs_relevance:
        return "low"

    signal_score = (
        (len(lifecycle_stages) * 2)
        + len(use_cases)
        + len(icp)
        + len(value_statements)
        + len(case_studies)
        + len(pricing)
    )
    if signal_score >= 12:
        return "high"
    if signal_score >= 4:
        return "medium"
    return "low"


def _coerce_page_payloads(page_payload: dict[str, object]) -> dict[str, dict[str, str | int]]:
    """Accept either a single homepage payload or explored page payloads."""
    if "homepage" in page_payload and isinstance(page_payload["homepage"], dict):
        page_payloads = {
            page_name: page_value
            for page_name, page_value in page_payload.items()
            if isinstance(page_value, dict)
        }
        extra_pages = page_payload.get("extra_pages", [])
        if isinstance(extra_pages, list):
            for index, extra_page in enumerate(extra_pages, start=1):
                if isinstance(extra_page, dict):
                    page_payloads[f"extra_page_{index}"] = extra_page
        return page_payloads

    return {"homepage": page_payload}  # type: ignore[return-value]


def _combine_page_texts(page_payloads: dict[str, dict[str, str | int]]) -> str:
    """Return the combined text from explored vendor pages."""
    texts: list[str] = []
    ordered_page_keys = [
        "homepage",
        "product_page",
        "pricing_page",
        "case_studies_page",
        "about_page",
        "team_page",
        "contact_page",
        "demo_page",
        "help_page",
        "support_page",
        "security_page",
        "integrations_page",
    ]
    ordered_page_keys.extend(
        page_key for page_key in page_payloads if page_key.startswith("extra_page_")
    )
    for page_key in ordered_page_keys:
        page_text = _page_text(page_payloads, page_key)
        if page_text:
            texts.append(page_text)
    return " ".join(texts).strip()


def _combine_relevance_texts(page_payloads: dict[str, dict[str, str | int]]) -> str:
    """Return text from the highest-signal relevance pages only."""
    texts: list[str] = []
    for page_key in [
        "homepage",
        "product_page",
        "about_page",
        "team_page",
        "contact_page",
        "demo_page",
        "help_page",
        "support_page",
        "integrations_page",
    ]:
        page_text = _page_text(page_payloads, page_key)
        if page_text:
            texts.append(page_text)
    for page_key in page_payloads:
        if page_key.startswith("extra_page_"):
            page_text = _page_text(page_payloads, page_key)
            if page_text:
                texts.append(page_text)
    return " ".join(texts).strip()


def _page_text(page_payloads: dict[str, dict[str, str | int]], page_key: str) -> str:
    page_payload = page_payloads.get(page_key, {})
    return str(page_payload.get("text", "")).strip()


def _collect_page_urls(page_payloads: dict[str, dict[str, str | int]]) -> list[str]:
    """Return URLs used as evidence for extracted signals."""
    evidence_urls: list[str] = []
    for page_payload in page_payloads.values():
        page_url = str(page_payload.get("website") or page_payload.get("url") or "").strip()
        if page_url and page_url not in evidence_urls:
            evidence_urls.append(page_url)
    return evidence_urls


def _has_strong_cs_relevance(text: str) -> bool:
    """Return True when vendor text shows direct Customer Success relevance."""
    return _contains_any(text, STRONG_CS_RELEVANCE_HINTS)


def _looks_like_mission_sentence(sentence: str) -> bool:
    lowered_sentence = sentence.lower()
    return any(
        hint in lowered_sentence
        for hint in (
            "help",
            "helps",
            "platform",
            "software",
            "product",
            "improve",
            "increase",
            "reduce",
            "enable",
            "enables",
            "built for",
        )
    )
