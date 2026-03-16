"""Helpers for loading repo-level discovery configuration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import tomllib

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_CONFIG_PATH = PROJECT_ROOT / "config" / "discovery.toml"
DEFAULT_GOOGLE_SEARCH_PAGES = 20
DEFAULT_GOOGLE_RESULTS_PER_PAGE = 10
MIN_GOOGLE_SEARCH_PAGES = 1
MIN_GOOGLE_RESULTS_PER_PAGE = 1
MAX_GOOGLE_SEARCH_PAGES = 20
MAX_GOOGLE_RESULTS_PER_PAGE = 10


@dataclass(frozen=True)
class GoogleSearchConfig:
    """Configurable limits for Apify Google Search discovery."""

    max_pages_per_query: int = DEFAULT_GOOGLE_SEARCH_PAGES
    results_per_page: int = DEFAULT_GOOGLE_RESULTS_PER_PAGE


def load_google_search_config(
    config_path: Path | None = None,
) -> GoogleSearchConfig:
    """Load Google Search discovery settings from TOML."""
    config_path = config_path or DISCOVERY_CONFIG_PATH
    if not config_path.exists():
        return GoogleSearchConfig()

    try:
        with config_path.open("rb") as config_file:
            raw_config = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        logger.warning("Could not load discovery config at %s: %s", config_path, error)
        return GoogleSearchConfig()

    google_search_config = raw_config.get("google_search", {})
    if not isinstance(google_search_config, dict):
        logger.warning("Discovery config at %s is missing [google_search]", config_path)
        return GoogleSearchConfig()

    return GoogleSearchConfig(
        max_pages_per_query=_bounded_int(
            google_search_config.get("max_pages_per_query"),
            setting_name="google_search.max_pages_per_query",
            config_path=config_path,
            default=GoogleSearchConfig.max_pages_per_query,
            minimum=MIN_GOOGLE_SEARCH_PAGES,
            maximum=MAX_GOOGLE_SEARCH_PAGES,
        ),
        results_per_page=_bounded_int(
            google_search_config.get("results_per_page"),
            setting_name="google_search.results_per_page",
            config_path=config_path,
            default=GoogleSearchConfig.results_per_page,
            minimum=MIN_GOOGLE_RESULTS_PER_PAGE,
            maximum=MAX_GOOGLE_RESULTS_PER_PAGE,
        ),
    )


def _bounded_int(
    value: object,
    *,
    setting_name: str,
    config_path: Path,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Return an integer kept within a safe range."""
    if not isinstance(value, int):
        logger.warning(
            "Invalid %s in %s; expected an integer and using default %s",
            setting_name,
            config_path,
            default,
        )
        return default
    if value < minimum:
        logger.warning(
            "%s in %s was below the minimum %s; using %s",
            setting_name,
            config_path,
            minimum,
            minimum,
        )
        return minimum
    if value > maximum:
        logger.warning(
            "%s in %s exceeded the maximum %s; using %s",
            setting_name,
            config_path,
            maximum,
            maximum,
        )
        return maximum
    return value
