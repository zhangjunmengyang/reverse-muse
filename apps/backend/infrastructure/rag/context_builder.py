"""
RAG Context Builder - 上下文构建器

负责将检索结果转换为 LLM 可用的上下文格式。

这是 RAG 流程中的关键步骤，决定了：
1. 如何组织检索到的内容
2. 如何添加元数据
3. 如何处理长上下文截断
4. 如何去重和合并相似内容
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog

from apps.backend.infrastructure.rag.types import (
    RetrievalOutput,
    RetrievalResult,
)

logger = structlog.get_logger(__name__)


class ContextBuilder(ABC):
    """
    上下文构建器抽象基类

    将检索结果转换为 LLM 所需的格式。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """构建器名称"""
        pass

    @abstractmethod
    def build(
        self,
        retrieval_output: RetrievalOutput,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        构建上下文

        Args:
            retrieval_output: 检索输出
            max_tokens: 最大 token 数限制（可选）

        Returns:
            LLM 可用的上下文列表
        """
        pass


class DefaultContextBuilder(ContextBuilder):
    """
    默认上下文构建器

    保持原有的上下文格式，直接使用 RetrievalResult.to_llm_format()。
    """

    @property
    def name(self) -> str:
        return "default"

    def build(
        self,
        retrieval_output: RetrievalOutput,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        构建默认格式的上下文

        格式：
        [
            {
                "content": "...",
                "paper_id": "...",
                "paper_title": "...",
                "page_number": ...,
                "similarity": ...,
                "is_cross_paper": ...
            },
            ...
        ]
        """
        return retrieval_output.to_llm_memories()


class StructuredContextBuilder(ContextBuilder):
    """
    结构化上下文构建器 - 预留

    将检索结果按论文分组，添加层次结构。

    输出格式示例：
    [
        {
            "paper_title": "Paper A",
            "is_cross_paper": true,
            "excerpts": [
                {"page": 5, "content": "...", "similarity": 0.9},
                {"page": 12, "content": "...", "similarity": 0.85}
            ]
        },
        ...
    ]
    """

    @property
    def name(self) -> str:
        return "structured"

    def build(
        self,
        retrieval_output: RetrievalOutput,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """按论文分组构建结构化上下文"""
        # 按论文分组
        papers: Dict[str, Dict[str, Any]] = {}

        for result in retrieval_output.results:
            paper_id = result.chunk.metadata.paper_id
            if paper_id not in papers:
                papers[paper_id] = {
                    "paper_id": paper_id,
                    "paper_title": result.chunk.metadata.paper_title,
                    "is_cross_paper": result.is_cross_paper,
                    "excerpts": [],
                }

            papers[paper_id]["excerpts"].append({
                "page": result.chunk.metadata.page_number,
                "content": result.chunk.content,
                "similarity": result.final_score,
            })

        # 转换为列表，跨论文优先
        result_list = list(papers.values())
        result_list.sort(key=lambda x: (not x["is_cross_paper"], -x["excerpts"][0]["similarity"]))

        return result_list


class CondensedContextBuilder(ContextBuilder):
    """
    精简上下文构建器 - 预留

    对检索到的内容进行去重和摘要，
    减少冗余，提高上下文利用效率。

    特性：
    - 相似内容合并
    - 长文本摘要
    - Token 限制控制
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,  # 去重阈值
        max_content_length: int = 500,        # 单条最大长度
    ):
        self._similarity_threshold = similarity_threshold
        self._max_content_length = max_content_length

    @property
    def name(self) -> str:
        return "condensed"

    def build(
        self,
        retrieval_output: RetrievalOutput,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """构建精简上下文"""
        # 去重
        unique_results = self._deduplicate(retrieval_output.results)

        # 截断长内容
        contexts = []
        for result in unique_results:
            content = result.chunk.content
            if len(content) > self._max_content_length:
                content = content[:self._max_content_length] + "..."

            contexts.append({
                "content": content,
                "paper_title": result.chunk.metadata.paper_title,
                "page_number": result.chunk.metadata.page_number,
                "similarity": result.final_score,
                "is_cross_paper": result.is_cross_paper,
            })

        # Token 限制（简单实现，按字符估算）
        if max_tokens:
            total_chars = 0
            limited_contexts = []
            for ctx in contexts:
                ctx_chars = len(ctx["content"]) + 50  # 估算元数据
                if total_chars + ctx_chars > max_tokens * 4:  # 假设 1 token ≈ 4 chars
                    break
                total_chars += ctx_chars
                limited_contexts.append(ctx)
            return limited_contexts

        return contexts

    def _deduplicate(
        self,
        results: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        """简单去重：基于内容前缀"""
        seen_prefixes: set = set()
        unique: List[RetrievalResult] = []

        for result in results:
            # 使用前 100 个字符作为去重键
            prefix = result.chunk.content[:100].strip().lower()
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                unique.append(result)

        return unique


class GraphContextBuilder(ContextBuilder):
    """
    图增强上下文构建器 - 预留

    利用知识图谱关系丰富上下文，
    添加实体关系、概念链接等信息。

    适用于 GraphRAG 策略。
    """

    @property
    def name(self) -> str:
        return "graph"

    def build(
        self,
        retrieval_output: RetrievalOutput,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("Graph context builder not yet implemented")
