"""Tests for the Supabase persistence client."""

from services.extraction.vendor_intel import VendorIntelligence
from services.persistence import supabase_client


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTableQuery:
    def __init__(self, response_data):
        self.response_data = response_data
        self.operations = []

    def select(self, columns: str):
        self.operations.append(("select", columns))
        return self

    def eq(self, column: str, value: str):
        self.operations.append(("eq", column, value))
        return self

    def limit(self, count: int):
        self.operations.append(("limit", count))
        return self

    def upsert(self, payload, on_conflict: str):
        self.operations.append(("upsert", payload, on_conflict))
        return self

    def execute(self):
        self.operations.append(("execute",))
        return FakeResponse(self.response_data)


class FakeSupabaseClient:
    def __init__(self, response_data):
        self.response_data = response_data
        self.table_calls = []
        self.last_query = None

    def table(self, table_name: str):
        self.table_calls.append(table_name)
        self.last_query = FakeTableQuery(self.response_data)
        return self.last_query


def test_vendor_exists_returns_true_when_website_is_found():
    fake_client = FakeSupabaseClient(
        [
            {
                "website": "https://example.com",
                "directory_fit": "high",
                "directory_category": "customer-success",
                "include_in_directory": True,
            }
        ]
    )

    result = supabase_client.vendor_exists("https://example.com", client=fake_client)

    assert result is True
    assert fake_client.table_calls == ["cs_vendors"]
    assert fake_client.last_query.operations == [
        ("select", "website,directory_fit,directory_category,include_in_directory"),
        ("eq", "website", "https://example.com"),
        ("limit", 1),
        ("execute",),
    ]


def test_vendor_exists_returns_false_when_website_is_missing():
    fake_client = FakeSupabaseClient([])

    result = supabase_client.vendor_exists("https://example.com", client=fake_client)

    assert result is False


def test_vendor_exists_returns_false_when_vendor_row_lacks_review_signal():
    fake_client = FakeSupabaseClient(
        [
            {
                "website": "https://example.com",
                "directory_fit": None,
                "directory_category": None,
                "include_in_directory": None,
            }
        ]
    )

    result = supabase_client.vendor_exists("https://example.com", client=fake_client)

    assert result is False


def test_supports_export_ready_vendor_profiles_returns_true_when_required_columns_are_available(monkeypatch):
    fake_client = FakeSupabaseClient([])

    monkeypatch.setattr(
        supabase_client,
        "_available_vendor_profile_columns",
        lambda _client: tuple(supabase_client.EXPORT_READY_VENDOR_COLUMNS) + ("name", "website"),
    )

    result = supabase_client.supports_export_ready_vendor_profiles(client=fake_client)

    assert result is True


def test_supports_export_ready_vendor_profiles_returns_false_when_required_columns_are_missing(monkeypatch):
    fake_client = FakeSupabaseClient([])

    monkeypatch.setattr(
        supabase_client,
        "_available_vendor_profile_columns",
        lambda _client: ("name", "website", "mission"),
    )

    result = supabase_client.supports_export_ready_vendor_profiles(client=fake_client)

    assert result is False


def test_upsert_vendor_result_uses_website_conflict_key():
    fake_client = FakeSupabaseClient([])
    vendor = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "source": "web_search",
    }
    homepage_payload = {
        "vendor_name": "ExampleCorp",
        "website": "https://example.com",
        "text": "Reduce churn with customer health visibility. Free trial available. SOC 2 compliant.",
    }
    intelligence = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://example.com",
        icp=["churn", "health"],
        use_cases=["health scoring", "churn prevention"],
        lifecycle_stages=["Adopt", "Renew"],
        value_statements=["reduce churn"],
    )

    row = supabase_client.upsert_vendor_result(
        vendor,
        homepage_payload,
        intelligence,
        client=fake_client,
    )

    assert fake_client.table_calls == ["cs_vendors"]
    assert fake_client.last_query.operations[0][0] == "upsert"
    assert fake_client.last_query.operations[0][2] == "website"
    assert fake_client.last_query.operations[1] == ("execute",)
    assert row["name"] == "ExampleCorp"
    assert row["website"] == "https://example.com"
    assert row["source"] == "web_search"
    assert row["mission"] == "Reduce churn with customer health visibility"
    assert row["usp"] == "reduce churn"
    assert row["free_trial"] is True
    assert row["soc2"] is True
    assert row["use_cases"] == ["health scoring", "churn prevention"]
    assert row["lifecycle_stages"] == ["Adopt", "Renew"]
    assert row["raw_description"] == (
        "Reduce churn with customer health visibility. Free trial available. SOC 2 compliant."
    )
    assert row["is_new"] is True


def test_upsert_vendor_result_normalizes_richer_m18_fields():
    fake_client = FakeSupabaseClient([])
    vendor = {
        "vendor_name": "ExampleCorp",
        "website": "https://www.example.com/",
        "source": "web_search",
    }
    homepage_payload = {
        "vendor_name": "ExampleCorp",
        "website": "https://www.example.com/",
        "text": "Homepage text.",
    }
    intelligence = VendorIntelligence(
        vendor_name="ExampleCorp",
        website="https://www.example.com/",
        contact_email="INFO@EXAMPLE.COM",
        contact_page_url="https://www.example.com/contact/",
        demo_url="example.com/demo",
        help_center_url="https://www.example.com/help/",
        support_url="https://www.example.com/support/",
        about_url="https://www.example.com/about/",
        team_url="https://www.example.com/team/",
        company_hq="Austin, Texas",
        products=[
            {
                "name": "Journey Hub",
                "category": "platform",
                "description": "Guided onboarding",
                "source_url": "https://www.example.com/products/journey-hub/",
            }
        ],
        leadership=[
            {
                "name": "Jane Doe",
                "title": "CEO",
                "source_url": "https://www.example.com/team/",
            }
        ],
        integration_categories=["crm"],
        integrations=["Salesforce"],
        support_signals=["help center"],
        case_study_details=[
            {
                "client": "Acme",
                "title": "Acme case study",
                "use_case": "onboarding",
                "value_realized": "reduced churn by 20%",
                "source_url": "https://www.example.com/customers/acme/",
            }
        ],
        evidence_urls=["https://www.example.com/contact/"],
    )

    row = supabase_client.upsert_vendor_result(
        vendor,
        homepage_payload,
        intelligence,
        client=fake_client,
    )

    assert row["website"] == "https://example.com"
    assert row["contact_email"] == "info@example.com"
    assert row["contact_page_url"] == "https://example.com/contact"
    assert row["demo_url"] == "https://example.com/demo"
    assert row["help_center_url"] == "https://example.com/help"
    assert row["support_url"] == "https://example.com/support"
    assert row["about_url"] == "https://example.com/about"
    assert row["team_url"] == "https://example.com/team"
    assert row["company_hq"] == "Austin, Texas"
    assert row["products"] == [
        {
            "name": "Journey Hub",
            "category": "platform",
            "description": "Guided onboarding",
            "source_url": "https://example.com/products/journey-hub",
        }
    ]
    assert row["leadership"] == [
        {
            "name": "Jane Doe",
            "title": "CEO",
            "source_url": "https://example.com/team",
        }
    ]
    assert row["integration_categories"] == ["crm"]
    assert row["integrations"] == ["Salesforce"]
    assert row["support_signals"] == ["help center"]
    assert row["case_study_details"] == [
        {
            "client": "Acme",
            "title": "Acme case study",
            "use_case": "onboarding",
            "value_realized": "reduced churn by 20%",
            "source_url": "https://example.com/customers/acme",
        }
    ]
    assert row["evidence_urls"] == ["https://example.com/contact"]
