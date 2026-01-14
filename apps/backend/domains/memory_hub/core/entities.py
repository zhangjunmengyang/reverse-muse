"""
Memory Hub Domain - Core Entities

Defines memory chunks and their relationships to user's reading history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MemorySource(Enum):
    """Source of the memory chunk"""

    PDF_TEXT = "pdf_text"
    USER_NOTE = "user_note"
    AI_INSIGHT = "ai_insight"
    WEB_ARTICLE = "web_article"


@dataclass
class MemoryMetadata:
    """Metadata for a memory chunk"""

    paper_id: str
    paper_title: str
    page_number: int
    # Context information
    section: Optional[str] = None
    chapter: Optional[str] = None
    # Source
    source: MemorySource = MemorySource.PDF_TEXT
    # Usage tracking
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None


@dataclass
class MemoryChunk:
    """A chunk of content stored in vector memory (aggregate root)"""

    id: Optional[str] = None
    user_id: str = ""
    content: str = ""
    embedding: Optional[List[float]] = None  # Vector representation

    # Metadata
    metadata: MemoryMetadata = field(default_factory=lambda: MemoryMetadata(
        paper_id="", paper_title="", page_number=0
    ))

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Optional: links to related chunks
    related_chunk_ids: List[str] = field(default_factory=list)

    def mark_accessed(self) -> None:
        """Mark this memory chunk as accessed"""
        self.metadata.access_count += 1
        self.metadata.last_accessed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def is_from_same_paper(self, paper_id: str) -> bool:
        """Check if this chunk is from the same paper"""
        return self.metadata.paper_id == paper_id

    def has_embedding(self) -> bool:
        """Check if this chunk has been vectorized"""
        return self.embedding is not None and len(self.embedding) > 0
