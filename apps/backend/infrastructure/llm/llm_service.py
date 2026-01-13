"""
LLM Service Integration

Provides OpenAI and Anthropic client integrations.
"""

import os
from typing import Optional, List, Dict, Any

import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from apps.backend.app.core.config import get_settings

logger = structlog.get_logger(__name__)


class LLMService:
    """Unified LLM service for multiple providers"""

    def __init__(self):
        self.settings = get_settings()
        self.openai_client: Optional[AsyncOpenAI] = None
        self.anthropic_client: Optional[AsyncAnthropic] = None

        # Initialize clients based on API keys
        if self.settings.openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or None,
            )
            logger.info("OpenAI client initialized")

        if self.settings.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(
                api_key=self.settings.anthropic_api_key,
            )
            logger.info("Anthropic client initialized")

    async def generate_insight(
        self,
        user_id: str,
        selected_text: str,
        context_text: str,
        related_memories: List[Dict[str, Any]],
        reading_position: Dict[str, Any],
    ) -> tuple[str, float]:
        """
        Generate an AI insight based on user action and context.

        Returns (insight_content, confidence)
        """
        # Build the prompt
        prompt = self._build_insight_prompt(
            selected_text=selected_text,
            context_text=context_text,
            related_memories=related_memories,
            reading_position=reading_position,
        )

        # Choose provider based on settings
        if self.settings.default_llm_provider == "openai" and self.openai_client:
            return await self._generate_with_openai(prompt)
        elif self.settings.default_llm_provider == "anthropic" and self.anthropic_client:
            return await self._generate_with_anthropic(prompt)
        else:
            logger.warning(f"LLM provider {self.settings.default_llm_provider} not available")
            # Fallback to mock insight for MVP
            return self._generate_mock_insight(selected_text, related_memories)

    def _build_insight_prompt(
        self,
        selected_text: str,
        context_text: str,
        related_memories: List[Dict[str, Any]],
        reading_position: Dict[str, Any],
    ) -> str:
        """Build the prompt for insight generation"""
        memory_context = ""
        if related_memories:
            memory_context = "\n\nRelated knowledge from previous readings:\n"
            for i, memory in enumerate(related_memories[:5], 1):
                memory_context += f"{i}. {memory.get('content', '')}\n"

        prompt = f"""You are an AI reading assistant. The user is reading a research paper and has just selected some text.

**Selected Text:**
{selected_text}

**Context around selection:**
{context_text}

{memory_context}

**Instructions:**
Generate a brief, helpful insight (maximum 200 characters) about this selection. Consider:
1. Does this contradict or connect to other papers they've read?
2. Are there important related concepts?
3. Is there a simpler explanation for this technical content?

Your insight should be:
- Concise (under 200 characters)
- Helpful and educational
- Conversational and friendly
- Mention specific connections if found

Return your insight as a single paragraph.
"""
        return prompt

    async def _generate_with_openai(self, prompt: str) -> tuple[str, float]:
        """Generate insight using OpenAI"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.settings.default_llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI reading assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=200,
            )

            insight = response.choices[0].message.content or ""
            confidence = 0.85  # Base confidence for OpenAI

            logger.info("Generated insight with OpenAI", length=len(insight))
            return insight, confidence

        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e))
            raise

    async def _generate_with_anthropic(self, prompt: str) -> tuple[str, float]:
        """Generate insight using Anthropic"""
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            insight = response.content[0].text or ""
            confidence = 0.88  # Slightly higher for Claude

            logger.info("Generated insight with Anthropic", length=len(insight))
            return insight, confidence

        except Exception as e:
            logger.error("Anthropic generation failed", error=str(e))
            raise

    def _generate_mock_insight(
        self,
        selected_text: str,
        related_memories: List[Dict[str, Any]],
    ) -> tuple[str, float]:
        """Generate a mock insight for MVP/demo purposes"""
        insights = [
            f"This reminds me of similar concepts in {len(related_memories)} other papers you've studied.",
            f"This concept appears frequently in research on {selected_text[:20]}...",
            "Consider reviewing the related work section for deeper understanding.",
        ]

        import random
        insight = random.choice(insights)
        confidence = 0.75

        logger.info("Generated mock insight")
        return insight, confidence


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
