"""Tests for the VendorIntelligence schema."""

from services.extraction.vendor_intel import VendorIntelligence


def test_vendor_intelligence_schema_fields_and_types():
    vendor = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        source="web_search",
        mission="Improve retention",
        usp="reduce churn",
        icp=["SaaS", "Mid-market"],
        use_cases=["health scoring", "renewal management"],
        lifecycle_stages=["Adopt", "Support", "Renew"],
        case_studies=["Increased retention by 20%", "Reduced churn"],
        customers=["Acme"],
        value_statements=["Increases retention", "Boosts ARR"],
        pricing=["$99/mo", "$199/mo"],
        free_trial=True,
        soc2=True,
        founded="2022",
        confidence="high",
        evidence_urls=["https://example.com/proof"],
        directory_fit="strong",
        directory_category="Renew",
        include_in_directory=True,
    )

    # Validate schema structure and type enforcement
    vendor.validate()

    assert vendor.vendor_name == "ExampleCorp"
    assert vendor.website == "https://example.com"
    assert vendor.source == "web_search"
    assert isinstance(vendor.icp, list)
    assert isinstance(vendor.use_cases, list)
    assert isinstance(vendor.lifecycle_stages, list)
    assert isinstance(vendor.case_studies, list)
    assert isinstance(vendor.customers, list)
    assert isinstance(vendor.value_statements, list)
    assert isinstance(vendor.pricing, list)
    assert isinstance(vendor.evidence_urls, list)
    assert vendor.directory_fit == "strong"
    assert vendor.directory_category == "Renew"
    assert vendor.include_in_directory is True
