"""Tests for the read-only admin API."""

from io import BytesIO
from pathlib import Path

from services.admin import admin_api


def test_admin_api_returns_candidates_endpoint():
    app = admin_api.build_admin_app(
        list_candidates_fn=lambda: [{"candidate_domain": "renewai.com"}],
        list_vendors_fn=lambda: [],
        list_runs_fn=lambda: [],
    )
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    response_body = b"".join(app({"PATH_INFO": "/admin/candidates", "QUERY_STRING": ""}, start_response))

    assert status_headers["status"] == "200 OK"
    assert b'"candidate_domain": "renewai.com"' in response_body


def test_admin_api_returns_not_found_for_unknown_path():
    app = admin_api.build_admin_app(
        list_candidates_fn=lambda: [],
        list_vendors_fn=lambda: [],
        list_runs_fn=lambda: [],
    )
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    response_body = b"".join(app({"PATH_INFO": "/admin/unknown", "QUERY_STRING": ""}, start_response))

    assert status_headers["status"] == "404 Not Found"
    assert b'"error": "not_found"' in response_body


def test_admin_api_returns_empty_items_when_candidates_backend_fails():
    app = admin_api.build_admin_app(
        list_candidates_fn=lambda: (_ for _ in ()).throw(RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")),
        list_vendors_fn=lambda: [],
        list_runs_fn=lambda: [],
    )
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    response_body = b"".join(app({"PATH_INFO": "/admin/candidates", "QUERY_STRING": ""}, start_response))

    assert status_headers["status"] == "200 OK"
    assert b'"items": []' in response_body
    assert b'"error": "candidates_unavailable"' in response_body


def test_admin_api_include_action_endpoint():
    app = admin_api.build_admin_app(
        list_candidates_fn=lambda: [],
        list_vendors_fn=lambda: [],
        list_runs_fn=lambda: [],
        include_vendor_fn=lambda vendor: {"ok": True, "action": "include", "vendor": vendor},
    )
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    response_body = b"".join(
        app(
            {
                "PATH_INFO": "/admin/vendor/include",
                "QUERY_STRING": "",
                "REQUEST_METHOD": "POST",
                "CONTENT_LENGTH": "22",
                "wsgi.input": BytesIO(b'{"vendor":"gainsight"}'),
            },
            start_response,
        )
    )

    assert status_headers["status"] == "200 OK"
    assert b'"action": "include"' in response_body


def test_admin_api_returns_runs_endpoint_with_status_fields():
    app = admin_api.build_admin_app(
        list_candidates_fn=lambda: [],
        list_vendors_fn=lambda: [],
        list_runs_fn=lambda: [{"run_id": "run-1", "run_status": "completed_with_warnings", "error_summary": ""}],
    )
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    response_body = b"".join(app({"PATH_INFO": "/admin/runs", "QUERY_STRING": ""}, start_response))

    assert status_headers["status"] == "200 OK"
    assert b'"run_status": "completed_with_warnings"' in response_body


def test_admin_api_rerun_action_requires_vendor_lookup():
    app = admin_api.build_admin_app(
        list_candidates_fn=lambda: [],
        list_vendors_fn=lambda: [],
        list_runs_fn=lambda: [],
    )
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    response_body = b"".join(
        app(
            {
                "PATH_INFO": "/admin/vendor/rerun-enrichment",
                "QUERY_STRING": "",
                "REQUEST_METHOD": "POST",
                "CONTENT_LENGTH": "2",
                "wsgi.input": BytesIO(b"{}"),
            },
            start_response,
        )
    )

    assert status_headers["status"] == "400 Bad Request"
    assert b'"vendor_lookup_required"' in response_body


def test_list_vendor_records_falls_back_to_local_review_output(monkeypatch, tmp_path: Path):
    results_path = tmp_path / "vendor_review_dataset.json"
    results_path.write_text('[{"vendor_name": "ExampleCorp", "website": "https://example.com"}]', encoding="utf-8")

    monkeypatch.setattr(admin_api.supabase_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        admin_api.supabase_client,
        "list_vendor_profiles",
        lambda limit=200: (_ for _ in ()).throw(RuntimeError("column cs_vendors.icp does not exist")),
    )
    monkeypatch.setattr(admin_api.supabase_client, "is_persistence_unavailable_error", lambda error: "does not exist" in str(error))
    monkeypatch.setattr(admin_api, "DEFAULT_VENDOR_RESULTS_PATH", results_path)

    result = admin_api.list_vendor_records(limit=50)
    fallback = admin_api.read_vendor_review_results(results_path)

    assert fallback == [{"vendor_name": "ExampleCorp", "website": "https://example.com"}]
    assert result == [{"vendor_name": "ExampleCorp", "website": "https://example.com"}]


def test_list_candidate_records_falls_back_to_local_review_output(monkeypatch, tmp_path: Path):
    results_path = tmp_path / "candidate_review_dataset.json"
    results_path.write_text('[{"candidate_domain": "renewai.com", "candidate_status": "enriched"}]', encoding="utf-8")

    monkeypatch.setattr(admin_api.supabase_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        admin_api.discovery_store,
        "list_candidate_records",
        lambda limit=200: (_ for _ in ()).throw(RuntimeError("public.discovery_candidates does not exist")),
    )
    monkeypatch.setattr(admin_api.discovery_store, "is_discovery_store_unavailable_error", lambda error: "does not exist" in str(error))
    monkeypatch.setattr(admin_api, "DEFAULT_CANDIDATE_RESULTS_PATH", results_path)

    result = admin_api.list_candidate_records(limit=50)

    assert result == [{"candidate_domain": "renewai.com", "candidate_status": "enriched"}]
