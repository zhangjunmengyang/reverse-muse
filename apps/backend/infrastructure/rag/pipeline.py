"""
RAG Pipeline - RAG 流水线编排器

将检索策略、重排器、上下文构建器组合成完整的 RAG 流程。

这是 RAG 模块的入口点，提供统一的接口：

    pipeline = get_default_pipeline()
    output = await pipeline.retrieve(query_text, context)
    memories = output.to_llm_memories()

架构：
    Query
      ↓
    RetrievalStrategy (可插拔)
      ↓
    [候选结果]
      ↓
    Reranker (可选)
      ↓
    [重排结果]
      ↓
    ContextBuilder
      ↓
    [LLM 上下文]
"""

from typing import Any, Dict, List, Optional

import structlog

from apps.backend.app.core.config import get_settings
from apps.backend.infrastructure.rag.context_builder import (
    ContextBuilder,
    DefaultContextBuilder,
)
from apps.backend.infrastructure.rag.reranker import (
    NoOpReranker,
    Reranker,
)
from apps.backend.infrastructure.rag.strategy import (
    DenseRetrievalStrategy,
    RetrievalStrategy,
)
from apps.backend.infrastructure.rag.types import (
    RetrievalConfig,
    RetrievalContext,
    RetrievalMode,
    RetrievalOutput,
)

logger = structlog.get_logger(__name__)


class RAGPipeline:
    """
    RAG 流水线

    组合检索策略、重排器和上下文构建器，
    提供端到端的 RAG 功能。

    Usage:
        # 使用默认配置
        pipeline = RAGPipeline()

        # 或自定义组件
        pipeline = RAGPipeline(
            strategy=DenseRetrievalStrategy(),
            reranker=LLMReranker(),
            context_builder=StructuredContextBuilder(),
        )

        # 执行检索
        output = await pipeline.retrieve(
            query_text="transformer attention mechanism",
            context=RetrievalContext(
                user_id="user123",
                current_paper_id="paper456",
                current_page_number=10,
            ),
        )

        # 获取 LLM 上下文
        memories = output.to_llm_memories()
    """

    def __init__(
        self,
        strategy: Optional[RetrievalStrategy] = None,
        reranker: Optional[Reranker] = None,
        context_builder: Optional[ContextBuilder] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        """
        初始化 RAG Pipeline

        Args:
            strategy: 检索策略（默认 DenseRetrievalStrategy）
            reranker: 重排器（默认 NoOpReranker）
            context_builder: 上下文构建器（默认 DefaultContextBuilder）
            config: 检索配置（默认从 settings 读取）
        """
        self._strategy = strategy or DenseRetrievalStrategy()
        self._reranker = reranker or NoOpReranker()
        self._context_builder = context_builder or DefaultContextBuilder()
        self._config = config or self._default_config()

        logger.info(
            "RAG Pipeline initialized",
            strategy=self._strategy.name,
            reranker=self._reranker.name,
            context_builder=self._context_builder.name,
        )

    @staticmethod
    def _default_config() -> RetrievalConfig:
        """从 settings 创建默认配置"""
        settings = get_settings()
        return RetrievalConfig(
            cross_paper_threshold=settings.cross_paper_similarity_threshold,
            same_paper_threshold=settings.same_paper_similarity_threshold,
            top_k=5,
            mode=RetrievalMode.HYBRID,
        )

    @property
    def strategy(self) -> RetrievalStrategy:
        """当前使用的检索策略"""
        return self._strategy

    @property
    def reranker(self) -> Reranker:
        """当前使用的重排器"""
        return self._reranker

    @property
    def context_builder(self) -> ContextBuilder:
        """当前使用的上下文构建器"""
        return self._context_builder

    @property
    def config(self) -> RetrievalConfig:
        """当前配置"""
        return self._config

    def with_strategy(self, strategy: RetrievalStrategy) -> "RAGPipeline":
        """
        创建使用新策略的 Pipeline 副本

        支持链式调用：
            pipeline = get_default_pipeline().with_strategy(GraphRAGStrategy())
        """
        return RAGPipeline(
            strategy=strategy,
            reranker=self._reranker,
            context_builder=self._context_builder,
            config=self._config,
        )

    def with_reranker(self, reranker: Reranker) -> "RAGPipeline":
        """创建使用新重排器的 Pipeline 副本"""
        return RAGPipeline(
            strategy=self._strategy,
            reranker=reranker,
            context_builder=self._context_builder,
            config=self._config,
        )

    def with_context_builder(self, builder: ContextBuilder) -> "RAGPipeline":
        """创建使用新上下文构建器的 Pipeline 副本"""
        return RAGPipeline(
            strategy=self._strategy,
            reranker=self._reranker,
            context_builder=builder,
            config=self._config,
        )

    def with_config(self, config: RetrievalConfig) -> "RAGPipeline":
        """创建使用新配置的 Pipeline 副本"""
        return RAGPipeline(
            strategy=self._strategy,
            reranker=self._reranker,
            context_builder=self._context_builder,
            config=config,
        )

    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config_override: Optional[RetrievalConfig] = None,
    ) -> RetrievalOutput:
        """
        执行完整的 RAG 检索流程

        Args:
            query_text: 查询文本
            context: 检索上下文
            config_override: 可选的配置覆盖

        Returns:
            RetrievalOutput 包含检索结果和元数据
        """
        config = config_override or self._config

        # 1. 执行检索
        output = await self._strategy.retrieve(
            query_text=query_text,
            context=context,
            config=config,
        )

        # 2. 重排（如果有结果且配置了重排）
        if output.results and config.enable_reranking:
            reranked_results = await self._reranker.rerank(
                query_text=query_text,
                results=output.results,
                top_k=config.top_k,
            )
            output.results = reranked_results

        logger.info(
            "RAG pipeline completed",
            strategy=self._strategy.name,
            reranker=self._reranker.name,
            results_count=len(output.results),
            has_cross_paper=output.has_cross_paper_results(),
        )

        return output

    async def retrieve_and_build_context(
        self,
        query_text: str,
        context: RetrievalContext,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        执行检索并构建 LLM 上下文

        便捷方法，一步完成检索和上下文构建。

        Args:
            query_text: 查询文本
            context: 检索上下文
            max_tokens: 最大 token 数限制

        Returns:
            LLM 可用的上下文列表
        """
        output = await self.retrieve(query_text, context)
        return self._context_builder.build(output, max_tokens=max_tokens)


# ============================================================================
# 工厂函数和单例
# ============================================================================

_default_pipeline: Optional[RAGPipeline] = None


def get_default_pipeline() -> RAGPipeline:
    """
    获取默认的 RAG Pipeline 单例

    使用：
    - DenseRetrievalStrategy（密集向量检索）
    - NoOpReranker（无重排）
    - DefaultContextBuilder（默认上下文格式）
    """
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = RAGPipeline()
    return _default_pipeline


def create_pipeline(
    strategy: str = "dense",
    reranker: str = "none",
    context_builder: str = "default",
    **kwargs,
) -> RAGPipeline:
    """
    根据名称创建 RAG Pipeline

    便捷的工厂方法，通过字符串配置创建 Pipeline。

    Args:
        strategy: 策略名称 ("dense", "sparse", "graph", "hybrid")
        reranker: 重排器名称 ("none", "llm", "cross_encoder", "cohere")
        context_builder: 构建器名称 ("default", "structured", "condensed")
        **kwargs: 传递给组件的额外参数

    Returns:
        配置好的 RAGPipeline

    Example:
        pipeline = create_pipeline(
            strategy="dense",
            reranker="llm",
            context_builder="structured",
        )
    """
    from apps.backend.infrastructure.rag.context_builder import (
        CondensedContextBuilder,
        StructuredContextBuilder,
    )
    from apps.backend.infrastructure.rag.reranker import LLMReranker
    from apps.backend.infrastructure.rag.strategy import (
        GraphRetrievalStrategy,
        HybridRetrievalStrategy,
        SparseRetrievalStrategy,
    )

    # 策略映射
    strategy_map = {
        "dense": DenseRetrievalStrategy,
        "sparse": SparseRetrievalStrategy,
        "graph": GraphRetrievalStrategy,
        "hybrid": HybridRetrievalStrategy,
    }

    # 重排器映射
    reranker_map = {
        "none": NoOpReranker,
        "llm": LLMReranker,
    }

    # 上下文构建器映射
    builder_map = {
        "default": DefaultContextBuilder,
        "structured": StructuredContextBuilder,
        "condensed": CondensedContextBuilder,
    }

    # 创建组件
    strategy_cls = strategy_map.get(strategy, DenseRetrievalStrategy)
    reranker_cls = reranker_map.get(reranker, NoOpReranker)
    builder_cls = builder_map.get(context_builder, DefaultContextBuilder)

    return RAGPipeline(
        strategy=strategy_cls(),
        reranker=reranker_cls(),
        context_builder=builder_cls(),
    )
