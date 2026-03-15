"""Small CLI runner for the MVP pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.pipeline.run_mvp_pipeline import run_mvp_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the MVP vendor intelligence pipeline for a search query.",
    )
    parser.add_argument("query", help="Search query used for vendor discovery")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output",
    )
    return parser


def main() -> int:
    """Run the CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()
    rows = run_mvp_pipeline(args.query)

    if args.pretty:
        print(json.dumps(rows, indent=2))
    else:
        print(json.dumps(rows))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
