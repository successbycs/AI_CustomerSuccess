"""Tests for the two-phase MVP pipeline orchestration module."""

from services.pipeline import run_mvp_pipeline as pipeline_module
from services.pipeline.run_mvp_pipeline import run_mvp_pipeline


def test_run_mvp_pipeline_runs_discovery_and_enrichment_phases(monkeypatch, caplog):
    caplog.set_level("INFO")
    calls = []
    candidate_records = [
        {"candidate_domain": "gainsight.com", "candidate_status": "queued_for_enrichment", "status": "queued_for_enrichment"},
        {"candidate_domain": "vitally.io", "candidate_status": "queued_for_enrichment", "status": "queued_for_enrichment"},
    ]
    queued_vendor_candidates = [
        {"vendor_name": "Gainsight", "website": "https://gainsight.com", "candidate_domain": "gainsight.com"},
        {"vendor_name": "Vitally", "website": "https://vitally.io", "candidate_domain": "vitally.io"},
    ]
    sheet_rows = [
        _sheet_row("Gainsight", "https://gainsight.com"),
        _sheet_row("Vitally", "https://vitally.io"),
    ]

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: False)
    monkeypatch.setattr(pipeline_module.llm_extractor, "start_pipeline_run", lambda: calls.append(("start", None)))
    monkeypatch.setattr(
        pipeline_module.llm_extractor,
        "log_runtime_configuration",
        lambda: calls.append(("log", None)),
    )
    monkeypatch.setattr(pipeline_module.orchestrator, "_persist_run_record", lambda run_record: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_write_run_snapshot", lambda run_record: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_write_candidate_review_snapshot", lambda candidate_records: None)
    monkeypatch.setattr(
        pipeline_module.orchestrator.discovery_runner,
        "run_discovery_phase",
        lambda query, **kwargs: (
            calls.append(("discovery", query)) or (candidate_records, queued_vendor_candidates, 0)
        ),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.enrichment_runner,
        "run_enrichment_phase",
        lambda queued_vendor_candidates, **kwargs: (
            calls.append(("enrichment", len(queued_vendor_candidates))) or (sheet_rows, [], 1, 1)
        ),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "publish_ops_review_export",
        lambda **kwargs: calls.append(("review_export", kwargs["run_record"]["run_status"])),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator,
        "_export_directory_dataset",
        lambda enrichment_results: calls.append(("directory_export", len(enrichment_results))) or [],
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator,
        "_export_vendor_review_dataset",
        lambda enrichment_results: calls.append(("review_dataset_export", len(enrichment_results))) or [],
    )

    result = run_mvp_pipeline("ai customer success platform")

    assert result == sheet_rows
    assert calls == [
        ("start", None),
        ("log", None),
        ("discovery", "ai customer success platform"),
        ("enrichment", 2),
        ("review_export", "completed"),
        ("directory_export", 0),
        ("review_dataset_export", 0),
    ]
    assert "Phase 1 discovery produced 2 candidate domains and queued 2 vendors for enrichment" in caplog.text
    assert "LLM stage summary: successes=1 fallback_or_skipped=1" in caplog.text


def test_run_mvp_pipeline_retries_discovery_when_persistence_is_unavailable(monkeypatch, caplog):
    caplog.set_level("INFO")
    calls = []

    class MissingTableError(Exception):
        pass

    def fake_run_discovery_phase(query, **kwargs):
        calls.append(("discovery", kwargs.get("vendor_exists_fn") is not None))
        if kwargs.get("vendor_exists_fn") is not None:
            raise MissingTableError('relation "public.cs_vendors" does not exist')
        return ([], [], 0)

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: True)
    monkeypatch.setattr(pipeline_module.supabase_client, "vendor_exists", lambda _website: False)
    monkeypatch.setattr(pipeline_module.supabase_client, "upsert_vendor_result", lambda *_args: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_persist_run_record", lambda run_record: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_write_run_snapshot", lambda run_record: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_write_candidate_review_snapshot", lambda candidate_records: None)
    monkeypatch.setattr(
        pipeline_module.orchestrator.supabase_client,
        "is_persistence_unavailable_error",
        lambda error: "does not exist" in str(error),
    )
    monkeypatch.setattr(pipeline_module.llm_extractor, "start_pipeline_run", lambda: None)
    monkeypatch.setattr(pipeline_module.llm_extractor, "log_runtime_configuration", lambda: None)
    monkeypatch.setattr(
        pipeline_module.orchestrator.discovery_runner,
        "run_discovery_phase",
        fake_run_discovery_phase,
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.enrichment_runner,
        "run_enrichment_phase",
        lambda queued_vendor_candidates, **kwargs: ([], [], 0, 0),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "publish_ops_review_export",
        lambda **kwargs: calls.append(("review_export", kwargs["run_record"]["run_status"])),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator,
        "_export_directory_dataset",
        lambda enrichment_results: calls.append(("directory_export", len(enrichment_results))) or [],
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator,
        "_export_vendor_review_dataset",
        lambda enrichment_results: calls.append(("review_dataset_export", len(enrichment_results))) or [],
    )

    result = run_mvp_pipeline("query")

    assert result == []
    assert calls == [
        ("discovery", True),
        ("discovery", False),
        ("review_export", "completed"),
        ("directory_export", 0),
        ("review_dataset_export", 0),
    ]
    assert "Persistence unavailable, continuing without deduplication" in caplog.text


def test_run_mvp_pipeline_updates_candidate_statuses_from_enrichment_results(monkeypatch):
    candidate_records = [
        {"candidate_domain": "signal.example.com", "candidate_status": "queued_for_enrichment", "status": "queued_for_enrichment"},
        {"candidate_domain": "weak.example.com", "candidate_status": "queued_for_enrichment", "status": "queued_for_enrichment"},
    ]
    queued_vendor_candidates = [
        {"vendor_name": "SignalAI", "website": "https://signal.example.com", "candidate_domain": "signal.example.com"},
        {"vendor_name": "WeakAI", "website": "https://weak.example.com", "candidate_domain": "weak.example.com"},
    ]
    enrichment_results = [
        {"candidate_domain": "signal.example.com", "status": "enriched"},
        {"candidate_domain": "weak.example.com", "status": "failed"},
    ]

    monkeypatch.setattr(pipeline_module.supabase_client, "is_configured", lambda: False)
    monkeypatch.setattr(pipeline_module.llm_extractor, "start_pipeline_run", lambda: None)
    monkeypatch.setattr(pipeline_module.llm_extractor, "log_runtime_configuration", lambda: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_persist_run_record", lambda run_record: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_write_run_snapshot", lambda run_record: None)
    monkeypatch.setattr(pipeline_module.orchestrator, "_write_candidate_review_snapshot", lambda candidate_records: None)
    monkeypatch.setattr(
        pipeline_module.orchestrator.discovery_runner,
        "run_discovery_phase",
        lambda query, **kwargs: (candidate_records, queued_vendor_candidates, 0),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.enrichment_runner,
        "run_enrichment_phase",
        lambda queued_vendor_candidates, **kwargs: (
            [_sheet_row("SignalAI", "https://signal.example.com")],
            enrichment_results,
            0,
            1,
        ),
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator.google_sheets,
        "publish_ops_review_export",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator,
        "_export_directory_dataset",
        lambda enrichment_results: [],
    )
    monkeypatch.setattr(
        pipeline_module.orchestrator,
        "_export_vendor_review_dataset",
        lambda enrichment_results: [],
    )

    result = run_mvp_pipeline("query")

    assert result == [_sheet_row("SignalAI", "https://signal.example.com")]
    assert candidate_records == [
        {"candidate_domain": "signal.example.com", "candidate_status": "enriched", "status": "enriched"},
        {"candidate_domain": "weak.example.com", "candidate_status": "failed", "status": "failed"},
    ]


def _sheet_row(vendor_name: str, website: str) -> dict[str, str]:
    return {
        "vendor_name": vendor_name,
        "website": website,
        "source": "",
        "mission": "",
        "usp": "",
        "icp": "",
        "use_cases": "",
        "lifecycle_stages": "",
        "pricing": "",
        "free_trial": "",
        "soc2": "",
        "founded": "",
        "case_studies": "",
        "customers": "",
        "value_statements": "",
        "confidence": "",
        "evidence_urls": "",
        "directory_fit": "",
        "directory_category": "",
        "include_in_directory": "",
    }
