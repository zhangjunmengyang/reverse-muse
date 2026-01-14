"""
Vector Search Service

向量搜索服务 - 提供语义搜索功能。

Phase 2 重构：
- 核心检索逻辑已迁移到 infrastructure/rag/strategy.py
- 本服务保留向后兼容的接口
- 内部使用 RAGPipeline 执行实际检索

"告别 Jaccard，拥抱语义" - Phase 1 设计哲学
"拥抱策略模式，易于扩展" - Phase 2 设计哲学
"""

from typing import List, Optional, Tuple

import structlog

from apps.backend.app.core.config import get_settings
from apps.backend.domains.memory_hub.core.entities import MemoryChunk
from apps.backend.infrastructure.rag import (
    RAGPipeline,
    RetrievalConfig,
    RetrievalContext,
    RetrievalMode,
    get_default_pipeline,
)

logger = structlog.get_logger(__name__)


class VectorSearchService:
    """
    语义向量搜索服务。

    提供向后兼容的接口，内部使用 RAGPipeline 执行检索。

    推荐使用方式（新代码）：
        from apps.backend.infrastructure.rag import get_default_pipeline

        pipeline = get_default_pipeline()
        output = await pipeline.retrieve(query_text, context)

    向后兼容方式（保留原有调用）：
        service = get_vector_search_service()
        results = await service.search_similar(query_text, user_id, ...)
    """

    def __init__(self, pipeline: Optional[RAGPipeline] = None):
        """
        初始化向量搜索服务

        Args:
            pipeline: 可选的 RAGPipeline 实例，默认使用全局单例
        """
        self._pipeline = pipeline

    @property
    def pipeline(self) -> RAGPipeline:
        """获取底层的 RAG Pipeline"""
        if self._pipeline is None:
            self._pipeline = get_default_pipeline()
        return self._pipeline

    async def search_similar(
        self,
        query_text: str,
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        exclude_page_number: Optional[int] = None,
        only_paper_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[MemoryChunk, float]]:
        """
        使用语义相似度搜索相关的记忆块。

        这是向后兼容的接口，内部委托给 RAGPipeline。

        Args:
            query_text: 查询文本
            user_id: 用户 ID
            exclude_paper_id: 排除的论文 ID（跨论文搜索时使用）
            exclude_page_number: 排除的页码（同论文搜索时排除当前页）
            only_paper_id: 只搜索特定论文（同论文搜索时使用）
            limit: 返回结果数量限制
            threshold: 相似度阈值 (默认 0.85)

        Returns:
            (MemoryChunk, similarity_score) 元组列表，按相似度降序排列
        """
        settings = get_settings()

        # 确定检索模式和参数
        if only_paper_id:
            # 同论文搜索
            mode = RetrievalMode.SAME_PAPER
            current_paper_id = only_paper_id
            current_page_number = exclude_page_number or 0
            same_paper_threshold = threshold
            cross_paper_threshold = settings.cross_paper_similarity_threshold
        elif exclude_paper_id:
            # 跨论文搜索
            mode = RetrievalMode.CROSS_PAPER
            current_paper_id = exclude_paper_id
            current_page_number = 0
            cross_paper_threshold = threshold
            same_paper_threshold = settings.same_paper_similarity_threshold
        else:
            # 全部搜索
            mode = RetrievalMode.ALL
            current_paper_id = ""
            current_page_number = 0
            cross_paper_threshold = threshold
            same_paper_threshold = threshold

        # 构建检索上下文
        context = RetrievalContext(
            user_id=user_id,
            current_paper_id=current_paper_id,
            current_page_number=current_page_number,
        )

        # 构建配置
        config = RetrievalConfig(
            cross_paper_threshold=cross_paper_threshold,
            same_paper_threshold=same_paper_threshold,
            top_k=limit,
            mode=mode,
            exclude_current_page=exclude_page_number is not None,
        )

        # 执行检索
        output = await self.pipeline.retrieve(
            query_text=query_text,
            context=context,
            config_override=config,
        )

        # 转换为原有格式
        return [
            (result.chunk, result.similarity_score)
            for result in output.results
        ]

    async def find_connections(
        self,
        query_text: str,
        user_id: str,
        exclude_paper_id: Optional[str] = None,
        min_similarity: float = 0.85,
    ) -> List[dict]:
        """
        寻找与查询文本相关的知识连接。

        这是 Phase 1 "看见"能力的核心：
        发现用户当前阅读内容与过往知识的联系。

        Args:
            query_text: 用户选中或关注的文本
            user_id: 用户 ID
            exclude_paper_id: 当前论文 ID
            min_similarity: 最小相似度阈值

        Returns:
            知识连接列表，每个包含 content, paper_title, page_number, similarity
        """
        similar_chunks = await self.search_similar(
            query_text=query_text,
            user_id=user_id,
            exclude_paper_id=exclude_paper_id,
            limit=5,
            threshold=min_similarity,
        )

        connections = []
        for chunk, similarity in similar_chunks:
            connections.append({
                "content": chunk.content,
                "paper_id": chunk.metadata.paper_id,
                "paper_title": chunk.metadata.paper_title,
                "page_number": chunk.metadata.page_number,
                "similarity": similarity,
            })

        return connections


_vector_search_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Get or create vector search service singleton."""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service
