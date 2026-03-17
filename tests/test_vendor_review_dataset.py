"""Tests for the slim vendor review dataset and HTML export."""

from pathlib import Path

from services.export import vendor_review_dataset
from services.extraction.vendor_intel import VendorIntelligence


def test_build_vendor_review_dataset_normalizes_and_sorts_rows(monkeypatch):
    monkeypatch.setattr(vendor_review_dataset.supabase_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        vendor_review_dataset.supabase_client,
        "list_vendor_profiles",
        lambda limit=500, client=None: [
            {
                "name": "Zeta",
                "website": "https://zeta.example.com",
                "source": "google_search",
                "mission": "Zeta helps teams reduce churn and improve adoption with AI guidance.",
                "use_cases": ["health scoring", "renewal management"],
                "pricing": "contact sales|per seat",
                "lifecycle_stages": ["Adopt", "Renew"],
                "directory_category": "cs_core",
                "directory_fit": "high",
                "include_in_directory": True,
                "confidence": "high",
                "free_trial": "false",
                "soc2": True,
                "founded": "2022",
                "evidence_urls": ["https://zeta.example.com", "https://zeta.example.com/pricing"],
                "last_updated": "2026-03-17T00:00:00+00:00",
            },
            {
                "name": "Alpha",
                "website": "https://alpha.example.com",
                "source": "google_search",
                "mission": "Alpha onboarding platform",
                "use_cases": [],
                "pricing": [],
                "lifecycle_stages": ["Onboard"],
                "directory_category": "cs_core",
                "directory_fit": "medium",
                "include_in_directory": False,
                "confidence": "medium",
                "free_trial": True,
                "soc2": None,
                "founded": "",
                "evidence_urls": [],
                "last_updated": "2026-03-16T00:00:00+00:00",
            },
        ],
    )

    dataset = vendor_review_dataset.build_vendor_review_dataset()

    assert [item["vendor_name"] for item in dataset] == ["Alpha", "Zeta"]
    assert dataset[1]["pricing_summary"] == "contact sales, per seat"
    assert dataset[1]["evidence_url_count"] == 2
    assert dataset[0]["include_in_directory"] is False


def test_build_vendor_review_dataset_falls_back_to_current_profiles_when_supabase_is_unavailable(monkeypatch):
    monkeypatch.setattr(vendor_review_dataset.supabase_client, "is_configured", lambda: False)

    dataset = vendor_review_dataset.build_vendor_review_dataset(
        fallback_profiles=[
            VendorIntelligence(
                vendor_name="Bravo",
                website="https://bravo.example.com",
                mission="Renewal automation for SaaS teams",
                use_cases=["renewal management", "churn prevention"],
                pricing=["contact sales"],
                lifecycle_stages=["Renew"],
                directory_category="cs_core",
                directory_fit="high",
                include_in_directory=True,
                confidence="high",
                free_trial=True,
                soc2=True,
                founded="2024",
                evidence_urls=["https://bravo.example.com"],
            )
        ]
    )

    assert dataset == [
        {
            "vendor_name": "Bravo",
            "website": "https://bravo.example.com",
            "source": "",
            "mission_summary": "Renewal automation for SaaS teams",
            "use_case_summary": "renewal management, churn prevention",
            "pricing_summary": "contact sales",
            "lifecycle_stages": ["Renew"],
            "directory_category": "cs_core",
            "directory_fit": "high",
            "include_in_directory": True,
            "confidence": "high",
            "free_trial": True,
            "soc2": True,
            "founded": "2024",
            "evidence_url_count": 1,
            "last_updated": "",
        }
    ]


def test_export_vendor_review_artifacts_writes_json_and_html(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        vendor_review_dataset,
        "build_vendor_review_dataset",
        lambda client=None, fallback_profiles=None: [
            {
                "vendor_name": "Alpha",
                "website": "https://alpha.example.com",
                "source": "google_search",
                "mission_summary": "Alpha onboarding platform",
                "use_case_summary": "onboarding",
                "pricing_summary": "contact sales",
                "lifecycle_stages": ["Onboard"],
                "directory_category": "cs_core",
                "directory_fit": "high",
                "include_in_directory": True,
                "confidence": "high",
                "free_trial": True,
                "soc2": False,
                "founded": "2023",
                "evidence_url_count": 2,
                "last_updated": "2026-03-17T00:00:00+00:00",
            }
        ],
    )

    dataset_path = tmp_path / "vendor_review_dataset.json"
    html_path = tmp_path / "vendor_review.html"
    dataset = vendor_review_dataset.export_vendor_review_artifacts(
        dataset_output_path=dataset_path,
        html_output_path=html_path,
    )

    assert dataset[0]["vendor_name"] == "Alpha"
    assert dataset_path.exists()
    assert html_path.exists()
    assert '"vendor_name": "Alpha"' in dataset_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")
    assert "Vendor review report" in html
    assert "Alpha" in html
