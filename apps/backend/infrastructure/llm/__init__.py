"""
LLM Infrastructure Package
"""

from apps.backend.infrastructure.llm.llm_service import LLMService, get_llm_service

__all__ = ["LLMService", "get_llm_service"]
