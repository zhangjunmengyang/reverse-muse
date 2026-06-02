"""
Tests for OpenAI-compatible provider configuration helpers.
"""

from apps.backend.infrastructure.llm.llm_service import build_llm_default_headers
from apps.backend.infrastructure.openai_compat import normalize_openai_base_url


def test_normalize_openai_base_url_strips_embeddings_endpoint():
    """Embedding endpoint URLs should become SDK base URLs."""
    assert (
        normalize_openai_base_url("https://maas.devops.xiaohongshu.com/v1/embeddings")
        == "https://maas.devops.xiaohongshu.com/v1"
    )


def test_normalize_openai_base_url_keeps_v1_base():
    """Already-normalized base URLs should be unchanged except trailing slash."""
    assert (
        normalize_openai_base_url("https://maas.devops.xiaohongshu.com/v1/")
        == "https://maas.devops.xiaohongshu.com/v1"
    )


def test_build_llm_default_headers_from_maas_fields():
    """MAAS header fields should be attached to OpenAI-compatible LLM calls."""
    headers = build_llm_default_headers(
        user_email="user@example.com",
        app_id="qs-api",
        headers_json=None,
    )

    assert headers == {
        "x-maas-user-email": "user@example.com",
        "x-maas-app-id": "qs-api",
    }


def test_build_llm_default_headers_merges_json_and_maas_fields():
    """Explicit MAAS fields should override JSON header values."""
    headers = build_llm_default_headers(
        user_email="user@example.com",
        app_id="qs-api",
        headers_json='{"x-extra": "1", "x-maas-app-id": "old"}',
    )

    assert headers == {
        "x-extra": "1",
        "x-maas-user-email": "user@example.com",
        "x-maas-app-id": "qs-api",
    }
