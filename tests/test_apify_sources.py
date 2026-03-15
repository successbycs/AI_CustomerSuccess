"""Tests for the Apify Google Search discovery adapter."""

from services.discovery import apify_sources


class FakeDatasetItems:
    def __init__(self, items):
        self.items = items


class FakeDataset:
    def __init__(self, items):
        self.items = items

    def list_items(self):
        return FakeDatasetItems(self.items)


class FakeActor:
    def __init__(self, dataset_id: str, calls: list[tuple[str, dict[str, object]]]):
        self.dataset_id = dataset_id
        self.calls = calls

    def call(self, run_input: dict[str, object]):
        self.calls.append((apify_sources.GOOGLE_SEARCH_ACTOR, run_input))
        return {"defaultDatasetId": self.dataset_id}


class FakeApifyClient:
    def __init__(self, datasets: dict[str, list[dict[str, object]]]):
        self.datasets = datasets
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.actor_ids: list[str] = []

    def actor(self, actor_id: str):
        self.actor_ids.append(actor_id)
        dataset_id = f"dataset_{len(self.actor_ids)}"
        return FakeActor(dataset_id, self.calls)

    def dataset(self, dataset_id: str):
        return FakeDataset(self.datasets[dataset_id])


def test_fetch_google_search_normalizes_candidates_and_deduplicates(monkeypatch):
    fake_client = FakeApifyClient(
        {
            "dataset_1": [
                {
                    "title": "RenewAI",
                    "url": "https://www.renewai.com/pricing",
                    "description": "Renewal automation for customer success teams",
                },
                {
                    "title": "RenewAI Duplicate",
                    "url": "https://renewai.com/customers",
                    "description": "Duplicate domain should be skipped",
                },
            ],
            "dataset_2": [
                {
                    "title": "OnboardFlow",
                    "url": "https://onboardflow.io",
                    "description": "Onboarding automation for SaaS teams",
                }
            ],
        }
    )

    monkeypatch.setattr(apify_sources, "get_apify_client", lambda: fake_client)

    results = apify_sources.fetch_google_search(["query one", "query two"])

    assert fake_client.actor_ids == [
        apify_sources.GOOGLE_SEARCH_ACTOR,
        apify_sources.GOOGLE_SEARCH_ACTOR,
    ]
    assert fake_client.calls == [
        (
            apify_sources.GOOGLE_SEARCH_ACTOR,
            {
                "queries": "query one",
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10,
            },
        ),
        (
            apify_sources.GOOGLE_SEARCH_ACTOR,
            {
                "queries": "query two",
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10,
            },
        ),
    ]
    assert results == [
        {
            "company_name": "RenewAI",
            "website": "https://renewai.com",
            "raw_description": "Renewal automation for customer success teams",
            "source": "google_search",
        },
        {
            "company_name": "OnboardFlow",
            "website": "https://onboardflow.io",
            "raw_description": "Onboarding automation for SaaS teams",
            "source": "google_search",
        },
    ]


def test_fetch_google_search_returns_empty_list_for_empty_queries():
    assert apify_sources.fetch_google_search([]) == []
