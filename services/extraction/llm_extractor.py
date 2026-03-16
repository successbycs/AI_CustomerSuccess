"""Optional Level 2 LLM extraction for richer vendor intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from typing import Any, Callable

import requests

from services.config.load_config import load_pipeline_config

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = load_pipeline_config().llm.model
MAX_PAGE_TEXT_CHARS = load_pipeline_config().llm.max_page_text_chars
MAX_SITE_TEXT_CHARS = load_pipeline_config().llm.max_site_text_chars
MAX_ERROR_BODY_CHARS = load_pipeline_config().llm.max_error_body_chars
_llm_is_disabled_for_run = False
_runtime_config_logged_for_run = False

PagePayload = dict[str, object]
ExploredPages = dict[str, PagePayload]
RequestPost = Callable[..., requests.Response]

LLM_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_cs_relevant": {"type": "boolean"},
        "mission": {"type": "string"},
        "usp": {"type": "string"},
        "use_cases": {
            "type": "array",
            "items": {"type": "string"},
        },
        "pricing": {"type": "string"},
        "free_trial": {"type": ["boolean", "null"]},
        "soc2": {"type": ["boolean", "null"]},
        "founded": {"type": "string"},
        "confidence": {"type": "string"},
    },
    "required": [
        "is_cs_relevant",
        "mission",
        "usp",
        "use_cases",
        "pricing",
        "free_trial",
        "soc2",
        "founded",
        "confidence",
    ],
    "additionalProperties": False,
}


@dataclass
class LLMExtractionResult:
    """Structured vendor intelligence returned by the LLM."""

    is_cs_relevant: bool = True
    mission: str = ""
    usp: str = ""
    use_cases: list[str] = field(default_factory=list)
    pricing: str = ""
    free_trial: bool | None = None
    soc2: bool | None = None
    founded: str = ""
    confidence: str = ""


def is_configured() -> bool:
    """Return True when OpenAI configuration is available."""
    return load_pipeline_config().llm.enabled and bool(os.getenv("OPENAI_API_KEY", "").strip())


def get_configured_model() -> str:
    """Return the configured OpenAI model name."""
    configured_model = os.getenv("OPENAI_MODEL", "").strip()
    return configured_model or load_pipeline_config().llm.model


def get_missing_configuration() -> list[str]:
    """Return required OpenAI configuration keys that are missing."""
    missing: list[str] = []
    if not os.getenv("OPENAI_API_KEY", "").strip():
        missing.append("OPENAI_API_KEY")
    return missing


def start_pipeline_run() -> None:
    """Reset LLM runtime state for a new pipeline run."""
    global _llm_is_disabled_for_run
    global _runtime_config_logged_for_run

    _llm_is_disabled_for_run = False
    _runtime_config_logged_for_run = False


def log_runtime_configuration() -> None:
    """Log the effective OpenAI runtime configuration once per pipeline run."""
    global _runtime_config_logged_for_run

    if _runtime_config_logged_for_run:
        return

    logger.info(
        "OpenAI LLM extraction config: enabled=%s endpoint=%s model=%s timeout=%ss max_site_text_chars=%s missing=%s",
        is_configured(),
        OPENAI_API_URL,
        get_configured_model(),
        load_pipeline_config().llm.request_timeout_seconds,
        load_pipeline_config().llm.max_site_text_chars,
        ",".join(get_missing_configuration()) or "none",
    )
    _runtime_config_logged_for_run = True


def extract_vendor_intelligence(
    page_payload: dict[str, object],
    *,
    request_post: RequestPost | None = None,
) -> LLMExtractionResult | None:
    """Extract richer vendor intelligence with the OpenAI API when configured."""
    global _llm_is_disabled_for_run

    if not is_configured() or _llm_is_disabled_for_run:
        return None

    site_text = _build_site_text(page_payload)
    if not site_text:
        return None

    request_post = request_post or requests.post
    llm_config = load_pipeline_config().llm
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": get_configured_model(),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "vendor_intelligence",
                "schema": LLM_RESULT_SCHEMA,
                "strict": True,
            }
        },
        "input": [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You extract vendor-level commercial intelligence for an AI Customer Success vendor directory. "
                            "Be conservative. Mark is_cs_relevant false unless the company clearly sells software or "
                            "AI-enabled products relevant to the customer success lifecycle. "
                            'Confidence must be one of "low", "medium", or "high". '
                            "Do not include lifecycle stages."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract vendor intelligence from this website text.\n"
                            "Return the structured result using the provided schema.\n"
                            "Requirements:\n"
                            "- use_cases must be an array of short strings\n"
                            "- pricing must be a short pricing summary string capturing signals like contact sales, per seat, per user, or annual pricing\n"
                            "- founded should be a year or short founded string if present, else empty string\n"
                            "- booleans should be true, false, or null\n"
                            "- confidence should reflect certainty that this is a relevant AI-enabled Customer Success vendor\n\n"
                            f"Website text:\n{site_text}"
                        ),
                    }
                ],
            },
        ],
    }

    try:
        response = request_post(
            OPENAI_API_URL,
            headers=headers,
            json=payload,
            timeout=llm_config.request_timeout_seconds,
        )
        if 400 <= response.status_code < 500 and response.status_code != 429:
            error_body = _response_body_snippet(response)
            logger.warning(
                "Disabling LLM extraction for the rest of this pipeline run after OpenAI returned %s: %s",
                response.status_code,
                error_body,
            )
            _llm_is_disabled_for_run = True
            return None
        response.raise_for_status()
        response_payload = response.json()
        content = _extract_response_text(response_payload)
        return _parse_result(content)
    except (requests.RequestException, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        logger.warning("LLM extraction unavailable, falling back to deterministic extraction: %s", error)
        return None


def _response_body_snippet(response: requests.Response) -> str:
    """Return a short response body snippet for error logging."""
    response_text = getattr(response, "text", "")
    if not isinstance(response_text, str):
        return ""
    response_text = response_text.strip().replace("\n", " ")
    return response_text[: load_pipeline_config().llm.max_error_body_chars]


def _build_site_text(page_payload: dict[str, object]) -> str:
    """Build a compact vendor-level text bundle from explored pages."""
    page_payloads = _coerce_page_payloads(page_payload)
    text_sections: list[str] = []

    ordered_page_keys = [
        "homepage",
        "product_page",
        "pricing_page",
        "case_studies_page",
        "about_page",
        "security_page",
        "integrations_page",
    ]
    ordered_page_keys.extend(
        page_key for page_key in page_payloads if page_key.startswith("extra_page_")
    )

    for page_key in ordered_page_keys:
        section_text = _truncate_page_text(str(page_payloads.get(page_key, {}).get("text", "")).strip())
        section_url = str(
            page_payloads.get(page_key, {}).get("website")
            or page_payloads.get(page_key, {}).get("url")
            or ""
        ).strip()
        if not section_text:
            continue

        label = page_key.replace("_", " ")
        if section_url:
            text_sections.append(f"[{label}] {section_url}\n{section_text}")
        else:
            text_sections.append(f"[{label}]\n{section_text}")

    combined_text = "\n\n".join(text_sections).strip()
    return combined_text[: load_pipeline_config().llm.max_site_text_chars]


def _truncate_page_text(text: str) -> str:
    """Return deterministic page text truncated to a bounded size."""
    return text[: load_pipeline_config().llm.max_page_text_chars].strip()


def _coerce_page_payloads(page_payload: dict[str, object]) -> ExploredPages:
    if "homepage" in page_payload and isinstance(page_payload["homepage"], dict):
        page_payloads = {
            page_name: page_value
            for page_name, page_value in page_payload.items()
            if isinstance(page_value, dict)
        }
        extra_pages = page_payload.get("extra_pages", [])
        if isinstance(extra_pages, list):
            for index, extra_page in enumerate(extra_pages, start=1):
                if isinstance(extra_page, dict):
                    page_payloads[f"extra_page_{index}"] = extra_page
        return page_payloads
    return {"homepage": page_payload}


def _extract_response_text(response_payload: dict[str, Any]) -> str:
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output_items = response_payload.get("output")
    if not isinstance(output_items, list):
        raise ValueError("OpenAI response did not include output text")

    for item in output_items:
        if not isinstance(item, dict):
            continue

        content_parts = item.get("content")
        if not isinstance(content_parts, list):
            continue

        for part in content_parts:
            if not isinstance(part, dict):
                continue

            if part.get("type") != "output_text":
                continue

            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise ValueError("OpenAI response did not include output text")


def _parse_result(content: str) -> LLMExtractionResult:
    raw_result = json.loads(content)
    if not isinstance(raw_result, dict):
        raise ValueError("LLM extraction response was not a JSON object")

    confidence = str(raw_result.get("confidence", "")).strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = ""

    return LLMExtractionResult(
        is_cs_relevant=_normalize_required_bool(raw_result.get("is_cs_relevant"), default=True),
        mission=_clean_string(raw_result.get("mission")),
        usp=_clean_string(raw_result.get("usp")),
        use_cases=_normalize_string_list(raw_result.get("use_cases")),
        pricing=_normalize_pricing(raw_result.get("pricing")),
        free_trial=_normalize_optional_bool(raw_result.get("free_trial")),
        soc2=_normalize_optional_bool(raw_result.get("soc2")),
        founded=_clean_string(raw_result.get("founded")),
        confidence=confidence,
    )


def _clean_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        candidates = [segment.strip() for segment in value.replace("\n", ",").replace("|", ",").split(",")]
        return [candidate for candidate in candidates if candidate]

    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            cleaned_item = _clean_string(item)
            if cleaned_item and cleaned_item not in normalized:
                normalized.append(cleaned_item)
        return normalized

    return []


def _normalize_pricing(value: object) -> str:
    if isinstance(value, list):
        return " | ".join(_normalize_string_list(value))
    return _clean_string(value)


def _normalize_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in {"true", "yes"}:
        return True
    if normalized in {"false", "no"}:
        return False
    return None


def _normalize_required_bool(value: object, *, default: bool) -> bool:
    normalized_value = _normalize_optional_bool(value)
    if normalized_value is None:
        return default
    return normalized_value
