"""Helpers for loading repo-level enrichment configuration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import tomllib

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENRICHMENT_CONFIG_PATH = PROJECT_ROOT / "config" / "enrichment.toml"
DEFAULT_MAX_NON_HOMEPAGE_PAGES = 5
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_PAGE_PRIORITY = (
    "pricing_page",
    "product_page",
    "case_studies_page",
    "security_page",
    "about_page",
    "integrations_page",
)
DEFAULT_PAGE_PATTERNS = {
    "pricing_page": ("pricing",),
    "product_page": ("product", "platform", "features", "solutions"),
    "case_studies_page": (
        "case studies",
        "case-study",
        "case-studies",
        "customer stories",
        "customer-story",
        "customers",
    ),
    "about_page": ("about", "company"),
    "security_page": ("security", "trust", "compliance"),
    "integrations_page": ("integrations", "integration", "apps", "marketplace"),
}
DEFAULT_JUNK_HINTS = (
    "careers",
    "cookie",
    "docs",
    "documentation",
    "legal",
    "login",
    "privacy",
    "signin",
    "sign-in",
    "support",
    "terms",
)


@dataclass(frozen=True)
class SiteExplorerConfig:
    """Configurable limits and matching rules for site exploration."""

    max_non_homepage_pages: int = DEFAULT_MAX_NON_HOMEPAGE_PAGES
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    page_priority: tuple[str, ...] = DEFAULT_PAGE_PRIORITY
    page_patterns: dict[str, tuple[str, ...]] | None = None
    junk_hints: tuple[str, ...] = DEFAULT_JUNK_HINTS

    def resolved_page_patterns(self) -> dict[str, tuple[str, ...]]:
        """Return the effective page-pattern map."""
        return self.page_patterns or DEFAULT_PAGE_PATTERNS


def load_site_explorer_config(config_path: Path | None = None) -> SiteExplorerConfig:
    """Load site exploration settings from TOML."""
    config_path = config_path or ENRICHMENT_CONFIG_PATH
    if not config_path.exists():
        return SiteExplorerConfig(page_patterns=DEFAULT_PAGE_PATTERNS)

    try:
        with config_path.open("rb") as config_file:
            raw_config = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        logger.warning("Could not load enrichment config at %s: %s", config_path, error)
        return SiteExplorerConfig(page_patterns=DEFAULT_PAGE_PATTERNS)

    explorer_config = raw_config.get("site_explorer", {})
    if not isinstance(explorer_config, dict):
        logger.warning("Enrichment config at %s is missing [site_explorer]", config_path)
        return SiteExplorerConfig(page_patterns=DEFAULT_PAGE_PATTERNS)

    raw_patterns = explorer_config.get("page_patterns", {})
    return SiteExplorerConfig(
        max_non_homepage_pages=_bounded_int(
            explorer_config.get("max_non_homepage_pages", explorer_config.get("max_pages_per_vendor")),
            setting_name="site_explorer.max_non_homepage_pages",
            config_path=config_path,
            default=DEFAULT_MAX_NON_HOMEPAGE_PAGES,
            minimum=1,
            maximum=10,
        ),
        request_timeout_seconds=_bounded_int(
            explorer_config.get("request_timeout_seconds"),
            setting_name="site_explorer.request_timeout_seconds",
            config_path=config_path,
            default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
            minimum=1,
            maximum=60,
        ),
        page_priority=_normalized_page_priority(
            explorer_config.get("page_priority"),
            config_path=config_path,
        ),
        page_patterns=_normalized_page_patterns(raw_patterns, config_path=config_path),
        junk_hints=_normalized_string_tuple(
            explorer_config.get("junk_hints"),
            setting_name="site_explorer.junk_hints",
            config_path=config_path,
            default=DEFAULT_JUNK_HINTS,
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
    if not isinstance(value, int):
        if value is not None:
            logger.warning(
                "Invalid %s in %s; expected an integer and using default %s",
                setting_name,
                config_path,
                default,
            )
        return default
    if value < minimum:
        logger.warning("%s in %s was below %s; using %s", setting_name, config_path, minimum, minimum)
        return minimum
    if value > maximum:
        logger.warning("%s in %s exceeded %s; using %s", setting_name, config_path, maximum, maximum)
        return maximum
    return value


def _normalized_page_priority(value: object, *, config_path: Path) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_PAGE_PRIORITY
    if not isinstance(value, list):
        logger.warning(
            "Invalid site_explorer.page_priority in %s; using defaults",
            config_path,
        )
        return DEFAULT_PAGE_PRIORITY

    cleaned = [str(item).strip() for item in value if str(item).strip() in DEFAULT_PAGE_PATTERNS]
    if not cleaned:
        logger.warning(
            "Invalid site_explorer.page_priority in %s; using defaults",
            config_path,
        )
        return DEFAULT_PAGE_PRIORITY
    return tuple(cleaned)


def _normalized_page_patterns(value: object, *, config_path: Path) -> dict[str, tuple[str, ...]]:
    if value is None:
        return DEFAULT_PAGE_PATTERNS
    if not isinstance(value, dict):
        logger.warning(
            "Invalid site_explorer.page_patterns in %s; using defaults",
            config_path,
        )
        return DEFAULT_PAGE_PATTERNS

    normalized_patterns: dict[str, tuple[str, ...]] = {}
    for page_key, default_patterns in DEFAULT_PAGE_PATTERNS.items():
        raw_patterns = value.get(page_key, default_patterns)
        if isinstance(raw_patterns, list):
            cleaned_patterns = tuple(str(item).strip().lower() for item in raw_patterns if str(item).strip())
            normalized_patterns[page_key] = cleaned_patterns or default_patterns
        else:
            normalized_patterns[page_key] = default_patterns
    return normalized_patterns


def _normalized_string_tuple(
    value: object,
    *,
    setting_name: str,
    config_path: Path,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list):
        logger.warning("Invalid %s in %s; using defaults", setting_name, config_path)
        return default

    cleaned = tuple(str(item).strip().lower() for item in value if str(item).strip())
    if not cleaned:
        logger.warning("Invalid %s in %s; using defaults", setting_name, config_path)
        return default
    return cleaned
