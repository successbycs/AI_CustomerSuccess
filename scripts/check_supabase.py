"""Manual Supabase connectivity check."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.persistence import supabase_client


def main() -> int:
    """Run a manual Supabase connectivity check."""
    load_dotenv(PROJECT_ROOT / ".env")

    if not supabase_client.is_configured():
        print("Supabase config missing: set SUPABASE_URL and SUPABASE_KEY.")
        return 1

    try:
        client = supabase_client.get_supabase_client()
        response = client.table("cs_vendors").select("website").limit(1).execute()
    except Exception as error:
        print(f"Supabase connectivity check failed: {error}")
        return 1

    row_count = len(response.data or [])
    print(f"Supabase connectivity check succeeded. Retrieved {row_count} row(s) from cs_vendors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
