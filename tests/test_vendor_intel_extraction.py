"""Tests for rule-based vendor intelligence extraction."""

from services.extraction.vendor_intel import extract_vendor_intelligence


def test_extract_vendor_intelligence_populates_use_cases_and_value_statements():
    homepage_payload = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "text": (
            "Our platform improves adoption, speeds time to value, and helps teams "
            "reduce churn. We automate workflows for onboarding and support, "
            "while improving customer health and increasing retention with "
            "usage analytics and renewal automation."
        ),
    }

    result = extract_vendor_intelligence(homepage_payload)

    assert result.vendor_name == "ExampleCorp"
    assert result.website == "https://example.com"
    assert result.icp == [
        "onboarding",
        "churn",
        "retention",
        "support",
        "automation",
        "health",
        "adoption",
        "renewal",
    ]
    assert result.value_statements == [
        "reduce churn",
        "improve adoption",
        "automate workflows",
        "improve customer health",
        "increase retention",
        "speed time to value",
    ]
    assert result.lifecycle_stages == ["Onboard", "Adopt", "Renew"]
    assert result.case_studies == []
    assert result.pricing == []


def test_extract_vendor_intelligence_returns_empty_lists_when_no_keywords_match():
    homepage_payload = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "text": "Customer success platform for modern SaaS teams.",
    }

    result = extract_vendor_intelligence(homepage_payload)

    assert result.icp == []
    assert result.value_statements == []
    assert result.lifecycle_stages == []


def test_extract_vendor_intelligence_supports_multiple_exact_lifecycle_stages():
    homepage_payload = {
        "vendor_name": "LifecycleAI",
        "website": "https://lifecycle.example.com",
        "text": (
            "Conversational intelligence and meeting summaries improve sales-to-cs handoff. "
            "Our onboarding automation and time-to-value tooling support implementation teams. "
            "In-app guidance and product walkthroughs boost activation. "
            "Usage analytics and health scoring help customer health teams. "
            "Stakeholder mapping drives expansion revenue. "
            "Churn prediction and risk alerts improve renewals. "
            "NPS and voice of customer programs help advocacy."
        ),
    }

    result = extract_vendor_intelligence(homepage_payload)

    assert result.lifecycle_stages == [
        "Sign",
        "Onboard",
        "Activate",
        "Adopt",
        "Expand",
        "Renew",
        "Advocate",
    ]
