"""Tests for the VendorIntelligence schema."""

from services.extraction.vendor_intel import VendorIntelligence


def test_vendor_intelligence_schema_fields_and_types():
    vendor = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        icp=["SaaS", "Mid-market"],
        lifecycle_stages=["Adopt", "Renew"],
        case_studies=["Increased retention by 20%", "Reduced churn"],
        value_statements=["Increases retention", "Boosts ARR"],
        pricing=["$99/mo", "$199/mo"]
    )

    # Validate schema structure and type enforcement
    vendor.validate()

    assert vendor.vendor_name == "ExampleCorp"
    assert vendor.website == "https://example.com"
    assert isinstance(vendor.icp, list)
    assert isinstance(vendor.lifecycle_stages, list)
    assert isinstance(vendor.case_studies, list)
    assert isinstance(vendor.value_statements, list)
    assert isinstance(vendor.pricing, list)
