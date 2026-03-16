"""Tests for repo-level discovery configuration."""

from pathlib import Path

from services.discovery.discovery_config import GoogleSearchConfig, load_google_search_config


def test_load_google_search_config_reads_toml_values(tmp_path: Path):
    config_path = tmp_path / "discovery.toml"
    config_path.write_text(
        "[google_search]\nmax_pages_per_query = 12\nresults_per_page = 10\n",
        encoding="utf-8",
    )

    result = load_google_search_config(config_path)

    assert result == GoogleSearchConfig(max_pages_per_query=12, results_per_page=10)


def test_load_google_search_config_clamps_invalid_values(tmp_path: Path):
    config_path = tmp_path / "discovery.toml"
    config_path.write_text(
        "[google_search]\nmax_pages_per_query = 999\nresults_per_page = -1\n",
        encoding="utf-8",
    )

    result = load_google_search_config(config_path)

    assert result == GoogleSearchConfig(max_pages_per_query=20, results_per_page=1)


def test_load_google_search_config_uses_defaults_when_file_is_missing(tmp_path: Path):
    result = load_google_search_config(tmp_path / "missing.toml")

    assert result == GoogleSearchConfig()


def test_load_google_search_config_warns_when_values_are_invalid(tmp_path: Path, caplog):
    config_path = tmp_path / "discovery.toml"
    config_path.write_text(
        "[google_search]\nmax_pages_per_query = \"many\"\nresults_per_page = 99\n",
        encoding="utf-8",
    )

    result = load_google_search_config(config_path)

    assert result == GoogleSearchConfig(max_pages_per_query=20, results_per_page=10)
    assert "google_search.max_pages_per_query" in caplog.text
    assert "google_search.results_per_page" in caplog.text
