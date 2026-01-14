"""
RAG Retrieval Strategies - 检索策略

提供可插拔的检索策略接口和实现。

策略模式使得可以轻松切换或组合不同的检索方法：
- DenseRetrievalStrategy: 密集向量检索（当前实现）
- SparseRetrievalStrategy: 稀疏检索 BM25（预留）
- GraphRetrievalStrategy: 图增强检索（预留）
- HybridRetrievalStrategy: 混合检索（预留）
- MultiStageStrategy: 多阶段检索（预留）
"""

import time
from abc import ABC, abstractmethod
from typing import List, Optional

import structlog

from apps.backend.domains.memory_hub.core.entities import MemoryChunk
from apps.backend.infrastructure.db import SurrealMemoryChunkRepository
from apps.backend.infrastructure.embedding import get_embedding_service
from apps.backend.infrastructure.rag.types import (
    RetrievalConfig,
    RetrievalContext,
    RetrievalMode,
    RetrievalOutput,
    RetrievalResult,
)

logger = structlog.get_logger(__name__)


class RetrievalStrategy(ABC):
    """
    检索策略抽象基类

    所有检索策略必须实现此接口。
    便于扩展到 GraphRAG、HyDE、多阶段检索等复杂策略。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称，用于日志和调试"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> RetrievalOutput:
        """
        执行检索

        Args:
            query_text: 查询文本
            context: 检索上下文（用户ID、当前位置等）
            config: 检索配置（阈值、数量限制等）

        Returns:
            RetrievalOutput 包含检索结果和元数据
        """
        pass


class DenseRetrievalStrategy(RetrievalStrategy):
    """
    密集向量检索策略

    使用 embedding 向量进行语义相似度搜索。
    这是当前系统的默认策略，保持原有行为。

    特性：
    - 支持跨论文优先搜索模式（HYBRID）
    - 支持纯跨论文/同论文搜索
    - 阈值过滤
    """

    def __init__(
        self,
        cross_paper_first: bool = True,
    ):
        """
        Args:
            cross_paper_first: 是否优先跨论文搜索（默认 True，保持原有行为）
        """
        self._cross_paper_first = cross_paper_first
        self._embedding_service = get_embedding_service()

    @property
    def name(self) -> str:
        return "dense_retrieval"

    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> RetrievalOutput:
        """
        执行密集向量检索

        实现与原 VectorSearchService.search_similar 相同的逻辑，
        但结构更清晰，便于扩展。
        """
        start_time = time.time()

        # 获取用户的所有 chunks
        repo = SurrealMemoryChunkRepository()
        all_chunks = await repo.list_by_user(user_id=context.user_id)

        if not all_chunks:
            logger.info("No chunks found for user", user_id=context.user_id)
            return self._empty_output(query_text, context, config, start_time)

        # 生成查询 embedding
        try:
            query_embedding = await self._embedding_service.embed(query_text)
        except Exception as e:
            logger.error("Failed to generate query embedding", error=str(e))
            return self._empty_output(query_text, context, config, start_time)

        # 根据模式执行检索
        results = await self._execute_by_mode(
            query_embedding=query_embedding,
            all_chunks=all_chunks,
            context=context,
            config=config,
        )

        # 构建输出
        search_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Dense retrieval completed",
            strategy=self.name,
            query_length=len(query_text),
            total_chunks=len(all_chunks),
            results_found=len(results),
            search_time_ms=f"{search_time_ms:.2f}",
        )

        return RetrievalOutput(
            results=results,
            query_text=query_text,
            context=context,
            config=config,
            total_candidates=len(all_chunks),
            search_time_ms=search_time_ms,
            strategy_name=self.name,
        )

    async def _execute_by_mode(
        self,
        query_embedding: List[float],
        all_chunks: List[MemoryChunk],
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """根据检索模式执行搜索"""

        if config.mode == RetrievalMode.CROSS_PAPER:
            return await self._search_cross_paper(
                query_embedding, all_chunks, context, config
            )

        if config.mode == RetrievalMode.SAME_PAPER:
            return await self._search_same_paper(
                query_embedding, all_chunks, context, config
            )

        if config.mode == RetrievalMode.ALL:
            return await self._search_all(
                query_embedding, all_chunks, context, config
            )

        # HYBRID 模式：先跨论文，无结果再同论文（保持原有行为）
        results = await self._search_cross_paper(
            query_embedding, all_chunks, context, config
        )

        if not results:
            logger.info("No cross-paper results, falling back to same paper")
            results = await self._search_same_paper(
                query_embedding, all_chunks, context, config
            )

        return results

    async def _search_cross_paper(
        self,
        query_embedding: List[float],
        all_chunks: List[MemoryChunk],
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """跨论文搜索"""
        # 过滤：排除当前论文
        filtered_chunks = [
            c for c in all_chunks
            if not c.is_from_same_paper(context.current_paper_id)
        ]

        return self._compute_similarities(
            query_embedding=query_embedding,
            chunks=filtered_chunks,
            threshold=config.cross_paper_threshold,
            limit=config.top_k,
            is_cross_paper=True,
        )

    async def _search_same_paper(
        self,
        query_embedding: List[float],
        all_chunks: List[MemoryChunk],
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """同论文搜索"""
        # 过滤：只保留当前论文的 chunks
        filtered_chunks = [
            c for c in all_chunks
            if c.is_from_same_paper(context.current_paper_id)
        ]

        # 排除当前页
        if config.exclude_current_page:
            filtered_chunks = [
                c for c in filtered_chunks
                if c.metadata.page_number != context.current_page_number
            ]

        return self._compute_similarities(
            query_embedding=query_embedding,
            chunks=filtered_chunks,
            threshold=config.same_paper_threshold,
            limit=config.top_k,
            is_cross_paper=False,
        )

    async def _search_all(
        self,
        query_embedding: List[float],
        all_chunks: List[MemoryChunk],
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> List[RetrievalResult]:
        """全部搜索（不做论文过滤）"""
        # 排除当前页
        filtered_chunks = all_chunks
        if config.exclude_current_page:
            filtered_chunks = [
                c for c in all_chunks
                if not (
                    c.is_from_same_paper(context.current_paper_id)
                    and c.metadata.page_number == context.current_page_number
                )
            ]

        # 使用较低的阈值
        threshold = min(config.cross_paper_threshold, config.same_paper_threshold)

        results = self._compute_similarities(
            query_embedding=query_embedding,
            chunks=filtered_chunks,
            threshold=threshold,
            limit=config.top_k,
            is_cross_paper=False,  # 会在结果中单独标记
        )

        # 标记跨论文结果
        for result in results:
            result.is_cross_paper = not result.chunk.is_from_same_paper(
                context.current_paper_id
            )

        return results

    def _compute_similarities(
        self,
        query_embedding: List[float],
        chunks: List[MemoryChunk],
        threshold: float,
        limit: int,
        is_cross_paper: bool,
    ) -> List[RetrievalResult]:
        """计算相似度并返回结果"""
        results: List[RetrievalResult] = []

        for chunk in chunks:
            if not chunk.has_embedding():
                continue

            similarity = self._embedding_service.cosine_similarity(
                query_embedding, chunk.embedding
            )

            if similarity >= threshold:
                results.append(RetrievalResult(
                    chunk=chunk,
                    similarity_score=similarity,
                    source="dense",
                    is_cross_paper=is_cross_paper,
                ))

        # 按相似度降序排序
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        return results[:limit]

    def _empty_output(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
        start_time: float,
    ) -> RetrievalOutput:
        """生成空结果输出"""
        return RetrievalOutput(
            results=[],
            query_text=query_text,
            context=context,
            config=config,
            total_candidates=0,
            search_time_ms=(time.time() - start_time) * 1000,
            strategy_name=self.name,
        )


# ============================================================================
# 预留策略（便于未来扩展）
# ============================================================================

class SparseRetrievalStrategy(RetrievalStrategy):
    """
    稀疏检索策略（BM25）- 预留

    使用 BM25 算法进行关键词匹配检索。
    适合精确匹配场景。

    TODO: 实现 BM25 索引和检索
    """

    @property
    def name(self) -> str:
        return "sparse_bm25"

    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> RetrievalOutput:
        raise NotImplementedError("BM25 strategy not yet implemented")


class GraphRetrievalStrategy(RetrievalStrategy):
    """
    图增强检索策略 (GraphRAG) - 预留

    利用 MemoryChunk 的 related_chunk_ids 构建知识图谱，
    通过图遍历扩展检索结果。

    TODO: 实现图构建和遍历逻辑
    """

    @property
    def name(self) -> str:
        return "graph_rag"

    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> RetrievalOutput:
        raise NotImplementedError("GraphRAG strategy not yet implemented")


class HybridRetrievalStrategy(RetrievalStrategy):
    """
    混合检索策略 - 预留

    结合密集检索和稀疏检索的结果，
    使用 RRF (Reciprocal Rank Fusion) 或其他融合算法。

    TODO: 实现融合算法
    """

    def __init__(
        self,
        dense_strategy: Optional[DenseRetrievalStrategy] = None,
        sparse_strategy: Optional[SparseRetrievalStrategy] = None,
        dense_weight: float = 0.7,
    ):
        self._dense = dense_strategy or DenseRetrievalStrategy()
        self._sparse = sparse_strategy
        self._dense_weight = dense_weight

    @property
    def name(self) -> str:
        return "hybrid"

    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> RetrievalOutput:
        raise NotImplementedError("Hybrid strategy not yet implemented")


class MultiStageRetrievalStrategy(RetrievalStrategy):
    """
    多阶段检索策略 - 预留

    第一阶段：宽泛召回（低阈值，高数量）
    第二阶段：精细过滤（通过 Reranker）

    TODO: 实现多阶段流程
    """

    @property
    def name(self) -> str:
        return "multi_stage"

    async def retrieve(
        self,
        query_text: str,
        context: RetrievalContext,
        config: RetrievalConfig,
    ) -> RetrievalOutput:
        raise NotImplementedError("Multi-stage strategy not yet implemented")
