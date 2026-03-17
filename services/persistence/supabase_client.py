"""Supabase persistence helpers for vendor deduplication and upserts."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from services.extraction.vendor_intel import VendorIntelligence

if TYPE_CHECKING:
    from supabase import Client


VENDOR_PROFILE_SELECT = ",".join(
    [
        "name",
        "website",
        "source",
        "mission",
        "usp",
        "icp",
        "use_cases",
        "lifecycle_stages",
        "pricing",
        "free_trial",
        "soc2",
        "founded",
        "case_studies",
        "customers",
        "value_statements",
        "confidence",
        "evidence_urls",
        "directory_fit",
        "directory_category",
        "include_in_directory",
        "last_updated",
        "is_new",
    ]
)


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


def list_directory_vendors(client: "Client | None" = None) -> list[dict[str, Any]]:
    """Return vendors currently marked for public directory inclusion."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("cs_vendors")
        .select(VENDOR_PROFILE_SELECT)
        .eq("include_in_directory", True)
        .execute()
    )
    return list(response.data or [])


def list_vendor_profiles(*, limit: int = 200, client: "Client | None" = None) -> list[dict[str, Any]]:
    """Return enriched vendor profiles for read-only admin visibility."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("cs_vendors")
        .select(VENDOR_PROFILE_SELECT)
        .order("last_updated", desc=True)
        .limit(limit)
        .execute()
    )
    return list(response.data or [])


def update_vendor_admin_fields(
    vendor_lookup: str,
    *,
    include_in_directory: bool | None = None,
    directory_fit: str | None = None,
    directory_category: str | None = None,
    client: "Client | None" = None,
) -> dict[str, Any]:
    """Apply thin admin overrides for public-directory controls."""
    supabase = client or get_supabase_client()
    record = find_vendor_by_lookup(vendor_lookup, client=supabase)
    if not record:
        raise LookupError(f"Vendor {vendor_lookup!r} was not found")

    updates: dict[str, Any] = {"last_updated": datetime.now(timezone.utc).isoformat()}
    if include_in_directory is not None:
        updates["include_in_directory"] = include_in_directory
    if directory_fit:
        updates["directory_fit"] = directory_fit
    if directory_category:
        updates["directory_category"] = directory_category

    if len(updates) == 1:
        raise ValueError("No admin override fields were provided")

    website = str(record.get("website", "")).strip()
    response = (
        supabase.table("cs_vendors")
        .update(updates)
        .eq("website", website)
        .execute()
    )
    updated_rows = list(response.data or [])
    return updated_rows[0] if updated_rows else {**record, **updates}


def find_vendor_by_lookup(vendor_lookup: str, client: "Client | None" = None) -> dict[str, Any] | None:
    """Find one vendor by website or case-insensitive name match."""
    supabase = client or get_supabase_client()
    lookup = vendor_lookup.strip()
    if not lookup:
        return None

    website_matches = (
        supabase.table("cs_vendors")
        .select(VENDOR_PROFILE_SELECT)
        .eq("website", lookup if lookup.startswith("http") else f"https://{lookup}")
        .limit(1)
        .execute()
    )
    if website_matches.data:
        return website_matches.data[0]

    exact_name_matches = (
        supabase.table("cs_vendors")
        .select(VENDOR_PROFILE_SELECT)
        .ilike("name", lookup)
        .limit(1)
        .execute()
    )
    if exact_name_matches.data:
        return exact_name_matches.data[0]

    return None


def is_persistence_unavailable_error(error: Exception) -> bool:
    """Return True for missing-table or unavailable persistence errors."""
    error_code = getattr(error, "code", "")
    error_message = str(error).lower()

    if error_code == "PGRST205":
        return True

    if "column cs_vendors." in error_message and "does not exist" in error_message:
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
        "icp": intelligence.icp or [],
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
        "case_studies": intelligence.case_studies or [],
        "customers": intelligence.customers or [],
        "value_statements": intelligence.value_statements or [],
        "evidence_urls": intelligence.evidence_urls or [],
        "directory_fit": intelligence.directory_fit or None,
        "directory_category": intelligence.directory_category or None,
        "include_in_directory": intelligence.include_in_directory,
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
