"""
Use Case: Generate Insight with LLM

Orchestrates the generation of AI insights using LLM service.

Phase 1 核心特性：
- 语义搜索：使用 OpenAI Embedding 查找相关记忆
- 沉默决策：当 LLM 返回 [SILENCE] 时，不生成洞察
- 置信度阈值：只有超过 0.85 的置信度才触发显示

Phase 2 重构：
- 使用 RAGPipeline 进行检索，支持策略切换
- 检索逻辑与业务逻辑分离
- 易于扩展到 GraphRAG 等复杂策略
"""

import asyncio
from typing import TYPE_CHECKING, List, Optional

import structlog

from apps.backend.app.core.config import get_settings
from apps.backend.domains.insight_hub.core.entities import (
    BubbleInsight,
    InsightContext,
    InsightType,
)
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.domains.insight_hub.services.domain_service import (
    InsightGenerationService,
)
from apps.backend.infrastructure.llm import get_llm_service
from apps.backend.infrastructure.rag import (
    RAGPipeline,
    RetrievalConfig,
    RetrievalContext,
    RetrievalMode,
    RetrievalOutput,
    get_default_pipeline,
)

if TYPE_CHECKING:
    from apps.backend.domains.memory_hub.core.entities import MemoryChunk
    from apps.backend.domains.reading_hub.core.entities import UserAction

logger = structlog.get_logger(__name__)


class GenerateInsightUseCase:
    """
    Use case for generating AI insights with LLM.

    Phase 1 设计哲学：
    "宁可错过，不可打扰" - 只在真正有价值时才生成洞察

    Phase 2 增强：
    - 可插拔的 RAG 策略（通过 pipeline 参数）
    - 更清晰的检索与生成分离
    """

    def __init__(
        self,
        insight_repo: InsightRepository,
        insight_service: InsightGenerationService,
        rag_pipeline: Optional[RAGPipeline] = None,
    ):
        """
        初始化 UseCase

        Args:
            insight_repo: 洞察仓储
            insight_service: 洞察领域服务
            rag_pipeline: 可选的 RAG Pipeline，默认使用全局单例
        """
        self.insight_repo = insight_repo
        self.insight_service = insight_service
        self._pipeline = rag_pipeline

    @property
    def pipeline(self) -> RAGPipeline:
        """获取 RAG Pipeline"""
        if self._pipeline is None:
            self._pipeline = get_default_pipeline()
        return self._pipeline

    async def execute(
        self,
        user_id: str,
        context_id: str,
        action: "UserAction",
        related_memories: List["MemoryChunk"],
        confidence_threshold: Optional[float] = None,
    ) -> Optional[BubbleInsight]:
        """
        Execute the use case with LLM integration.

        Phase 2 流程：
        1. 使用 RAGPipeline 执行检索（可插拔策略）
        2. 调用 LLM 生成洞察（带沉默决策）
        3. 检查置信度阈值
        4. 去重并保存

        Args:
            user_id: 用户 ID
            context_id: 阅读上下文 ID
            action: 用户操作
            related_memories: 相关记忆（可能为空，将通过语义搜索补充）
            confidence_threshold: 置信度阈值（默认 0.85）

        Returns:
            生成的洞察，如果 AI 决定沉默则返回 None
        """
        settings = get_settings()

        # Use configured threshold or default
        if confidence_threshold is None:
            confidence_threshold = settings.confidence_threshold

        # 获取查询文本
        query_text = action.selected_text or action.context_text or ""
        if not query_text.strip():
            logger.info("No text to search for, skipping insight generation")
            return None

        # 使用 RAGPipeline 执行检索
        retrieval_output = await self._execute_retrieval(
            query_text=query_text,
            user_id=user_id,
            action=action,
            settings=settings,
        )

        # 转换搜索结果为 LLM 格式
        memories_for_llm = retrieval_output.to_llm_memories()
        top_memories = retrieval_output.get_top_chunks()

        logger.info(
            "RAG retrieval completed for insight generation",
            strategy=self.pipeline.strategy.name,
            query_length=len(query_text),
            results_found=len(memories_for_llm),
            has_cross_paper=retrieval_output.has_cross_paper_results(),
        )

        # 调用 LLM 生成洞察（带沉默决策）
        try:
            insight_content, confidence = await asyncio.wait_for(
                get_llm_service().generate_insight(
                    user_id=user_id,
                    selected_text=action.selected_text or "",
                    context_text=action.context_text or "",
                    related_memories=memories_for_llm,
                    reading_position={
                        "paper_id": action.reading_position.paper_id,
                        "page_number": action.reading_position.page_number,
                    },
                    trigger_type=action.trigger_type.value,
                ),
                timeout=settings.llm_timeout_seconds,
            )
        except TimeoutError as error:
            logger.warning(
                "LLM insight generation timed out",
                timeout_seconds=settings.llm_timeout_seconds,
                trigger_type=action.trigger_type.value,
            )
            raise TimeoutError("Request timed out.") from error

        # Phase 1 核心：检测沉默决策
        if insight_content == "[SILENCE]":
            logger.info(
                "AI decided to stay silent",
                trigger_type=action.trigger_type.value,
                has_related_memories=len(memories_for_llm) > 0,
            )
            return None

        # 检查置信度阈值
        if confidence < confidence_threshold:
            logger.info(
                "Insight below confidence threshold",
                confidence=confidence,
                threshold=confidence_threshold,
            )
            return None

        # 洞察内容为空
        if not insight_content or not insight_content.strip():
            logger.info("Empty insight content, skipping")
            return None

        # 创建洞察上下文
        insight_context = InsightContext(
            trigger_type=action.trigger_type.value,
            paper_id=action.reading_position.paper_id,
            page_number=action.reading_position.page_number,
            selected_text=action.selected_text,
            context_text=action.context_text,
            related_memory_ids=[m.id for m in top_memories if m.id],
            related_paper_titles=[
                m.metadata.paper_title
                for m in top_memories
                if not m.is_from_same_paper(action.reading_position.paper_id)
            ],
        )

        # 创建洞察实体
        insight = self.insight_service.create_insight(
            user_id=user_id,
            reading_context_id=context_id,
            insight_type=self._determine_insight_type(action, top_memories),
            content=insight_content,
            confidence=confidence,
            context=insight_context,
        )

        # 检查重复
        existing_insights = await self.insight_repo.list_by_context(context_id)
        if self.insight_service.is_duplicate_insight(insight, existing_insights):
            logger.info("Skipping duplicate insight")
            return None

        # 保存洞察
        await self.insight_repo.save(insight)

        logger.info(
            "Insight generated and saved",
            insight_id=insight.id,
            insight_type=insight.insight_type.value,
            confidence=confidence,
            related_papers=len(insight_context.related_paper_titles),
        )

        return insight

    async def _execute_retrieval(
        self,
        query_text: str,
        user_id: str,
        action: "UserAction",
        settings,
    ) -> RetrievalOutput:
        """
        执行 RAG 检索

        默认行为（HYBRID 模式）：
        1. 首先尝试跨论文搜索
        2. 如果没有结果，搜索同论文其他页面

        可通过替换 pipeline 的 strategy 切换到其他策略。
        """
        # 构建检索上下文
        retrieval_context = RetrievalContext(
            user_id=user_id,
            current_paper_id=action.reading_position.paper_id,
            current_page_number=action.reading_position.page_number,
        )

        # 使用默认 HYBRID 模式配置
        config = RetrievalConfig(
            cross_paper_threshold=settings.cross_paper_similarity_threshold,
            same_paper_threshold=settings.same_paper_similarity_threshold,
            top_k=5,
            mode=RetrievalMode.HYBRID,
            exclude_current_page=True,
        )

        # 执行检索
        return await self.pipeline.retrieve(
            query_text=query_text,
            context=retrieval_context,
            config_override=config,
        )

    def _determine_insight_type(
        self, action: "UserAction", related_memories: List["MemoryChunk"]
    ) -> InsightType:
        """
        Determine insight type based on action and context.

        Phase 1 分类：
        - 有跨论文关联 → CONNECTION（最有价值）
        - 同论文内关联 → SIMILARITY
        - 选中文本 → EXPLANATION
        - 其他 → CUSTOM
        """
        # 检查是否有跨论文关联
        has_cross_paper_relation = any(
            not m.is_from_same_paper(action.reading_position.paper_id)
            for m in related_memories
        )

        if has_cross_paper_relation:
            return InsightType.CONNECTION

        if action.trigger_type.value == "selection":
            return InsightType.EXPLANATION

        if related_memories:
            return InsightType.SIMILARITY

        return InsightType.CUSTOM
