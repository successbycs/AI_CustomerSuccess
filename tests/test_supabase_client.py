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
    fake_client = FakeSupabaseClient([{"website": "https://example.com"}])

    result = supabase_client.vendor_exists("https://example.com", client=fake_client)

    assert result is True
    assert fake_client.table_calls == ["cs_vendors"]
    assert fake_client.last_query.operations == [
        ("select", "website"),
        ("eq", "website", "https://example.com"),
        ("limit", 1),
        ("execute",),
    ]


def test_vendor_exists_returns_false_when_website_is_missing():
    fake_client = FakeSupabaseClient([])

    result = supabase_client.vendor_exists("https://example.com", client=fake_client)

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
