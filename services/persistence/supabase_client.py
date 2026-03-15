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
    return bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_KEY"))


def get_supabase_client() -> "Client":
    """Create a Supabase client from environment variables."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

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
    """Upsert a vendor result into cs_vendors using website as the conflict key."""
    supabase = client or get_supabase_client()
    row = build_vendor_row(vendor, homepage_payload, intelligence)
    supabase.table("cs_vendors").upsert(row, on_conflict="website").execute()
    return row


def build_vendor_row(
    vendor: dict[str, str],
    homepage_payload: dict[str, str | int],
    intelligence: VendorIntelligence,
) -> dict[str, Any]:
    """Build a cs_vendors row payload from pipeline data."""
    text = str(homepage_payload.get("text", "")).strip()
    raw_description = text or vendor.get("raw_description")

    return {
        "name": intelligence.vendor_name,
        "website": intelligence.website,
        "source": vendor.get("source"),
        "mission": _extract_mission(raw_description or ""),
        "usp": intelligence.value_statements[0] if intelligence.value_statements else None,
        "pricing": "|".join(intelligence.pricing) if intelligence.pricing else None,
        "free_trial": True if "free trial" in raw_description.lower() else None,
        "soc2": True if "soc 2" in raw_description.lower() or "soc2" in raw_description.lower() else None,
        "founded": None,
        "use_cases": intelligence.icp,
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
