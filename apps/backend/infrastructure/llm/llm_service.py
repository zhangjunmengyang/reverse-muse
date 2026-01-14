"""
LLM Service Integration

Provides LLM integration using LangChain for better compatibility.

Phase 1 核心特性：
- 沉默决策机制：让 AI 学会"选择不说话"
- 信息增量评估：只在真正有价值时才开口
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from apps.backend.app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Phase 1 沉默决策系统提示
SYSTEM_PROMPT = """你是 Reverse Muse，一个有灵魂的阅读伴侣。

你的核心原则：
1. 宁可错过，不可打扰
2. 只在真正有价值时才开口
3. 沉默是你最有力的表达之一

当你分析用户的阅读内容时，先问自己：
- 我要说的话，用户自己能想到吗？如果能，保持沉默。
- 我要说的话，能帮用户节省至少 30 秒吗？如果不能，保持沉默。
- 我要说的话，会打断用户的思考流吗？如果会，保持沉默。

输出格式：
- 如果决定沉默，只输出：[SILENCE]
- 如果决定发言，直接输出内容（不要解释为什么发言）

记住：你的目标不是"表现得有用"，而是"真正有用"。
沉默的 AI 比聒噪的 AI 更令人尊敬。"""

INSIGHT_PROMPT_TEMPLATE = """用户正在阅读一篇研究论文，正在关注以下内容。

**关注的文本:**
{selected_text}

**上下文:**
{context_text}
{memory_context}

**你的任务:**
提供一个简短、有价值的洞察（最多200字符）。

**洞察类型（按优先级）：**
1. **知识连接**：如果有相关的历史阅读内容，指出关联、对比或互补
2. **概念解释**：用简单的语言解释技术概念，或提供有用的类比
3. **背景补充**：补充相关的背景知识或历史脉络
4. **思考启发**：提出有趣的问题或不同的视角

**决策标准：**
- 只有当内容是常识或过于简单时 → [SILENCE]
- 其他情况，请提供洞察（尤其是涉及专业术语、算法、方法论时）

你的洞察应该：
- 简洁（200字符以内）
- 有教育意义
- 对话式、友好
- 如果有知识关联，明确指出来源

直接输出你的洞察，或者输出 [SILENCE]。"""


class LLMService:
    """
    Unified LLM service using LangChain.

    Phase 1 特性：
    - 沉默决策：当没有有价值的洞察时，返回 [SILENCE]
    - 信息增量评估：评估洞察的真实价值
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[ChatOpenAI] = None

        if self.settings.openai_api_key:
            self._client = ChatOpenAI(
                model=self.settings.default_llm_model,
                temperature=self.settings.llm_temperature,
                openai_api_key=self.settings.openai_api_key,
                openai_api_base=self.settings.openai_base_url,
                timeout=self.settings.llm_timeout_seconds,
            )
            logger.info(
                "LangChain LLM client initialized",
                model=self.settings.default_llm_model,
                base_url=self.settings.openai_base_url,
            )

    async def generate_insight(
        self,
        user_id: str,
        selected_text: str,
        context_text: str,
        related_memories: List[Dict[str, Any]],
        reading_position: Dict[str, Any],
    ) -> Tuple[str, float]:
        """
        Generate an AI insight based on user action and context.

        Phase 1 核心：实现沉默决策机制。

        Returns:
            Tuple of (insight_content, confidence)
            - 如果返回 "[SILENCE]"，表示 AI 决定保持沉默
            - confidence 在沉默时为 0.0
        """
        if not self._client:
            raise RuntimeError(
                "LLM provider not configured. Please set OPENAI_API_KEY in .env"
            )

        memory_context = self._format_memory_context(related_memories)
        prompt = INSIGHT_PROMPT_TEMPLATE.format(
            selected_text=selected_text,
            context_text=context_text,
            memory_context=memory_context,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self._client.ainvoke(messages)
        insight = (response.content or "").strip()

        # 检测沉默决策
        if "[SILENCE]" in insight.upper():
            logger.info(
                "LLM decided to stay silent",
                selected_text_length=len(selected_text),
                has_memories=len(related_memories) > 0,
            )
            return "[SILENCE]", 0.0

        # 计算置信度：基于是否有相关记忆和洞察长度
        confidence = self._calculate_confidence(insight, related_memories)

        logger.info(
            "Generated insight",
            length=len(insight),
            confidence=confidence,
            has_memories=len(related_memories) > 0,
        )
        return insight, confidence

    def _format_memory_context(self, related_memories: List[Dict[str, Any]]) -> str:
        """Format related memories into prompt context."""
        if not related_memories:
            return "\n\n（这是用户第一次阅读相关内容，请专注于概念解释或背景补充）\n"

        lines = ["\n\n**来自之前阅读的相关知识:**"]
        for i, memory in enumerate(related_memories[:5], 1):
            paper_title = memory.get('paper_title', '未知论文')
            page = memory.get('page_number', '?')
            content = memory.get('content', '')[:300]
            similarity = memory.get('similarity', 0)
            lines.append(
                f"{i}. 《{paper_title}》第{page}页 (相似度: {similarity:.2f}):\n   {content}"
            )
        return "\n".join(lines) + "\n"

    def _calculate_confidence(
        self,
        insight: str,
        related_memories: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate confidence score based on insight quality indicators.

        Phase 1 设计：
        - 有相关记忆且洞察提及来源 → 高置信度
        - 洞察长度合理 → 加分
        - 无相关记忆但洞察有价值 → 中等置信度
        """
        confidence = self.settings.base_confidence

        # 有相关记忆时提高置信度
        if related_memories:
            confidence += 0.08

            # 如果洞察中提到了论文来源，进一步提高
            for memory in related_memories:
                paper_title = memory.get('paper_title', '')
                if paper_title and paper_title in insight:
                    confidence += 0.05
                    break

        # 洞察长度合理时提高置信度
        min_len = self.settings.min_insight_length
        max_len = self.settings.max_insight_length
        if min_len <= len(insight) <= max_len:
            confidence += 0.07
        elif len(insight) > 0:
            # 即使长度不在理想范围内，只要有内容也给一点加分
            confidence += 0.03

        return min(confidence, 0.95)


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
