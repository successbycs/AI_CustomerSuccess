"""Tests for Supabase configuration and client setup."""

from services.persistence import supabase_client


def test_get_supabase_config_returns_none_when_url_is_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    assert supabase_client.get_supabase_config() is None
    assert supabase_client.is_configured() is False


def test_get_supabase_config_returns_none_when_key_is_missing(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    assert supabase_client.get_supabase_config() is None
    assert supabase_client.is_configured() is False


def test_get_supabase_client_creates_client_when_config_is_present(monkeypatch):
    created = {}

    def fake_create_supabase_client(supabase_url: str, supabase_key: str):
        created["url"] = supabase_url
        created["key"] = supabase_key
        return {"client": "ok"}

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setattr(
        supabase_client,
        "_create_supabase_client",
        fake_create_supabase_client,
    )

    result = supabase_client.get_supabase_client()

    assert result == {"client": "ok"}
    assert created == {
        "url": "https://example.supabase.co",
        "key": "test-key",
    }


def test_get_supabase_client_raises_clean_error_when_config_is_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    try:
        supabase_client.get_supabase_client()
    except RuntimeError as error:
        assert str(error) == "SUPABASE_URL and SUPABASE_KEY must be set"
    else:
        raise AssertionError("Expected RuntimeError when Supabase config is missing")
