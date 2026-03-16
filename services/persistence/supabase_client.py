"""Supabase persistence helpers for vendor deduplication and upserts."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from services.extraction.vendor_intel import VendorIntelligence

if TYPE_CHECKING:
    from supabase import Client


def is_configured() -> bool:
    """Return True when the Supabase environment variables are available."""
    return get_supabase_config() is not None


def get_supabase_config() -> dict[str, str] | None:
    """Return Supabase config from environment variables when present."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return None

    return {
        "url": supabase_url,
        "key": supabase_key,
    }


def get_supabase_client() -> "Client":
    """Create a Supabase client from environment variables."""
    config = get_supabase_config()
    if config is None:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

    return _create_supabase_client(config["url"], config["key"])


def _create_supabase_client(supabase_url: str, supabase_key: str) -> "Client":
    """Create the underlying Supabase client instance."""
    from supabase import create_client

    return create_client(supabase_url, supabase_key)


def vendor_exists(website: str, client: "Client | None" = None) -> bool:
    """Return True when a vendor already exists in cs_vendors."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("cs_vendors")
        .select("website")
        .eq("website", website)
        .limit(1)
        .execute()
    )
    return bool(response.data)


def upsert_vendor_result(
    vendor: dict[str, str],
    homepage_payload: dict[str, str | int],
    intelligence: VendorIntelligence,
    client: "Client | None" = None,
) -> dict[str, Any]:
    """Upsert a Phase 2 enriched vendor profile into cs_vendors using website as the conflict key."""
    supabase = client or get_supabase_client()
    row = build_vendor_row(vendor, homepage_payload, intelligence)
    supabase.table("cs_vendors").upsert(row, on_conflict="website").execute()
    return row


def is_persistence_unavailable_error(error: Exception) -> bool:
    """Return True for missing-table or unavailable persistence errors."""
    error_code = getattr(error, "code", "")
    error_message = str(error).lower()

    if error_code == "PGRST205":
        return True

    return all(marker in error_message for marker in ["cs_vendors", "does not exist"]) or any(
        marker in error_message for marker in [
            "could not find the table",
            "public.cs_vendors",
        ]
    )


def build_vendor_row(
    vendor: dict[str, str],
    homepage_payload: dict[str, str | int],
    intelligence: VendorIntelligence,
) -> dict[str, Any]:
    """Build a cs_vendors row payload from an enriched vendor profile."""
    text = str(homepage_payload.get("text", "")).strip()
    raw_description = text or vendor.get("raw_description") or vendor.get("candidate_description")

    return {
        "name": intelligence.vendor_name,
        "website": intelligence.website,
        "source": vendor.get("source"),
        "confidence": intelligence.confidence or None,
        "mission": intelligence.mission or _extract_mission(raw_description or ""),
        "usp": intelligence.usp or (intelligence.value_statements[0] if intelligence.value_statements else None),
        "pricing": "|".join(intelligence.pricing) if intelligence.pricing else None,
        "free_trial": intelligence.free_trial if intelligence.free_trial is not None else _detect_text_boolean(
            raw_description or "",
            ["free trial"],
        ),
        "soc2": intelligence.soc2 if intelligence.soc2 is not None else _detect_text_boolean(
            raw_description or "",
            ["soc 2", "soc2"],
        ),
        "founded": intelligence.founded or None,
        "use_cases": intelligence.use_cases,
        "lifecycle_stages": intelligence.lifecycle_stages,
        "raw_description": raw_description or None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "is_new": True,
    }


def _extract_mission(text: str) -> str | None:
    """Return a short mission-style sentence from homepage text."""
    if not text:
        return None

    normalized_text = text.replace("\n", " ").strip()
    for separator in [". ", "! ", "? "]:
        if separator in normalized_text:
            mission = normalized_text.split(separator, maxsplit=1)[0].strip()
            return mission or None

    return normalized_text or None


def _detect_text_boolean(text: str, phrases: list[str]) -> bool | None:
    lowered_text = text.lower()
    if any(phrase in lowered_text for phrase in phrases):
        return True
    return None
