"""
RAG Types - 核心类型定义

定义 RAG 模块中使用的所有数据类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from apps.backend.domains.memory_hub.core.entities import MemoryChunk


class RetrievalMode(Enum):
    """检索模式"""
    CROSS_PAPER = "cross_paper"       # 跨论文搜索（优先）
    SAME_PAPER = "same_paper"         # 同论文搜索
    ALL = "all"                       # 全部搜索
    HYBRID = "hybrid"                 # 混合模式（先跨论文，无结果再同论文）


@dataclass
class RetrievalConfig:
    """
    检索配置

    控制检索行为的所有参数，便于实验和调优。
    """
    # 相似度阈值
    cross_paper_threshold: float = 0.75
    same_paper_threshold: float = 0.85

    # 检索数量限制
    top_k: int = 5
    max_candidates: int = 20  # 重排前的候选数量

    # 检索模式
    mode: RetrievalMode = RetrievalMode.HYBRID

    # 过滤选项
    exclude_current_page: bool = True

    # 高级选项（预留）
    enable_reranking: bool = False
    reranker_model: Optional[str] = None

    # 图检索选项（预留）
    graph_depth: int = 2
    graph_min_weight: float = 0.5


@dataclass
class RetrievalContext:
    """
    检索上下文

    包含执行检索所需的所有上下文信息。
    """
    # 用户信息
    user_id: str

    # 当前阅读位置
    current_paper_id: str
    current_page_number: int

    # 可选：论文标题（用于日志和调试）
    current_paper_title: Optional[str] = None

    # 可选：额外的元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetrievalResult:
    """
    单个检索结果

    封装检索到的 MemoryChunk 及其相关评分。
    """
    chunk: MemoryChunk
    similarity_score: float

    # 可选：重排后的分数（如果启用重排）
    rerank_score: Optional[float] = None

    # 来源标记
    source: str = "dense"  # "dense", "sparse", "graph", "hybrid"

    # 是否跨论文
    is_cross_paper: bool = False

    # 调试信息
    debug_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def final_score(self) -> float:
        """获取最终排序分数"""
        return self.rerank_score if self.rerank_score is not None else self.similarity_score

    def to_llm_format(self) -> Dict[str, Any]:
        """转换为 LLM 输入格式"""
        return {
            "content": self.chunk.content,
            "paper_id": self.chunk.metadata.paper_id,
            "paper_title": self.chunk.metadata.paper_title,
            "page_number": self.chunk.metadata.page_number,
            "similarity": self.final_score,
            "is_cross_paper": self.is_cross_paper,
        }


@dataclass
class RetrievalOutput:
    """
    检索输出

    包含检索结果和相关元数据。
    """
    results: List[RetrievalResult]

    # 检索元数据
    query_text: str
    context: RetrievalContext
    config: RetrievalConfig

    # 统计信息
    total_candidates: int = 0
    search_time_ms: float = 0.0

    # 使用的策略
    strategy_name: str = "unknown"

    def get_top_chunks(self) -> List[MemoryChunk]:
        """获取排序后的 chunk 列表"""
        return [r.chunk for r in self.results]

    def to_llm_memories(self) -> List[Dict[str, Any]]:
        """转换为 LLM 所需的 memories 格式"""
        return [r.to_llm_format() for r in self.results]

    def has_cross_paper_results(self) -> bool:
        """是否包含跨论文结果"""
        return any(r.is_cross_paper for r in self.results)
