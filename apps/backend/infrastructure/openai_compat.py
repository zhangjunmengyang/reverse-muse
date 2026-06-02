"""
Helpers for OpenAI-compatible provider configuration.
"""

from typing import Optional

OPENAI_ENDPOINT_SUFFIXES = (
    "/chat/completions",
    "/embeddings",
    "/completions",
)


def normalize_openai_base_url(base_url: Optional[str]) -> Optional[str]:
    """
    Normalize a full endpoint URL into an OpenAI SDK base URL.

    The SDK expects a base such as ``https://host/v1`` and appends endpoint
    paths internally. Users often paste full URLs like ``.../v1/embeddings``.
    """
    if not base_url:
        return None

    normalized = base_url.rstrip("/")
    for suffix in OPENAI_ENDPOINT_SUFFIXES:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized
