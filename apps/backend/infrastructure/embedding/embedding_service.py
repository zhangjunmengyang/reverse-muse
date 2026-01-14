"""
Embedding Service

Provides semantic embedding using OpenAI's embedding models.
Following Phase 1's philosophy: "告别 Jaccard，拥抱语义"
"""

from typing import List, Optional

import structlog
from openai import AsyncOpenAI

from apps.backend.app.core.config import get_settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    OpenAI Embedding 服务

    使用 text-embedding-3-small 模型，性价比之选。
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None
        self._model = self.settings.default_embedding_model
        self._dimension = 1536  # text-embedding-3-small 的默认维度

        if self.settings.openai_api_key:
            self._client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                timeout=60.0,
            )
            logger.info(
                "Embedding service initialized",
                model=self._model,
                base_url=self.settings.openai_base_url,
            )

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    async def embed(self, text: str) -> List[float]:
        """
        为单个文本生成 embedding 向量。

        Args:
            text: 要嵌入的文本

        Returns:
            embedding 向量 (List[float])
        """
        if not self._client:
            raise RuntimeError(
                "Embedding service not configured. Please set OPENAI_API_KEY in .env"
            )

        # 清理文本
        text = text.strip()
        if not text:
            return [0.0] * self._dimension

        try:
            response = await self._client.embeddings.create(
                input=text,
                model=self._model,
            )
            embedding = response.data[0].embedding
            logger.debug("Generated embedding", text_length=len(text), dim=len(embedding))
            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        批量生成 embedding 向量。

        为了效率，将文本分批处理。

        Args:
            texts: 文本列表
            batch_size: 每批处理的文本数量

        Returns:
            embedding 向量列表
        """
        if not self._client:
            raise RuntimeError(
                "Embedding service not configured. Please set OPENAI_API_KEY in .env"
            )

        # 清理空文本
        cleaned_texts = [t.strip() if t else "" for t in texts]

        all_embeddings: List[List[float]] = []

        for i in range(0, len(cleaned_texts), batch_size):
            batch = cleaned_texts[i:i + batch_size]

            # 跳过全空的批次
            if all(not t for t in batch):
                all_embeddings.extend([[0.0] * self._dimension] * len(batch))
                continue

            try:
                response = await self._client.embeddings.create(
                    input=batch,
                    model=self._model,
                )

                # 按索引排序结果
                batch_embeddings = [None] * len(batch)
                for item in response.data:
                    batch_embeddings[item.index] = item.embedding

                # 处理空文本的情况
                for j, text in enumerate(batch):
                    if not text:
                        batch_embeddings[j] = [0.0] * self._dimension

                all_embeddings.extend(batch_embeddings)

                logger.debug(
                    "Batch embedding completed",
                    batch_index=i // batch_size,
                    batch_size=len(batch),
                )

            except Exception as e:
                logger.error("Batch embedding failed", error=str(e), batch_index=i)
                raise

        return all_embeddings

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度。

        Args:
            vec1: 第一个向量
            vec2: 第二个向量

        Returns:
            相似度分数 (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # 计算模长
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# 单例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
