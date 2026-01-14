"""
RAG (Retrieval-Augmented Generation) 模块

提供可插拔的检索策略框架，支持：
- 密集向量检索 (DenseRetrieval)
- 稀疏检索 (BM25) - 预留
- 图增强检索 (GraphRAG) - 预留
- 混合检索策略 - 预留
- 多阶段检索 - 预留

架构设计：
Query → RetrievalStrategy (可插拔) → Reranker → ContextBuilder → LLM

Usage:
    from apps.backend.infrastructure.rag import (
        RAGPipeline,
        get_default_pipeline,
        DenseRetrievalStrategy,
        RetrievalContext,
    )

    # 使用默认 pipeline
    pipeline = get_default_pipeline()
    results = await pipeline.retrieve(query_text, user_id, context)

    # 或自定义策略组合
    pipeline = RAGPipeline(
        strategy=DenseRetrievalStrategy(cross_paper_first=True),
        reranker=LLMReranker(),  # 可选
    )
"""

from apps.backend.infrastructure.rag.types import (
    RetrievalContext,
    RetrievalResult,
    RetrievalConfig,
    RetrievalMode,
    RetrievalOutput,
)
from apps.backend.infrastructure.rag.strategy import (
    RetrievalStrategy,
    DenseRetrievalStrategy,
)
from apps.backend.infrastructure.rag.reranker import (
    Reranker,
    NoOpReranker,
)
from apps.backend.infrastructure.rag.context_builder import (
    ContextBuilder,
    DefaultContextBuilder,
)
from apps.backend.infrastructure.rag.pipeline import (
    RAGPipeline,
    get_default_pipeline,
)

__all__ = [
    # Types
    "RetrievalContext",
    "RetrievalResult",
    "RetrievalConfig",
    "RetrievalMode",
    "RetrievalOutput",
    # Strategy
    "RetrievalStrategy",
    "DenseRetrievalStrategy",
    # Reranker
    "Reranker",
    "NoOpReranker",
    # Context Builder
    "ContextBuilder",
    "DefaultContextBuilder",
    # Pipeline
    "RAGPipeline",
    "get_default_pipeline",
]
