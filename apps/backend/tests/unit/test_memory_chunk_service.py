"""
Tests for MemoryChunkService domain service
"""

from apps.backend.domains.memory_hub.core.entities import MemorySource
from apps.backend.domains.memory_hub.services.domain_service import (
    MemoryChunkService,
)


def test_create_chunk(sample_user_id, sample_paper_id):
    """Test creating a new memory chunk via service"""
    service = MemoryChunkService()

    chunk = service.create_chunk(
        user_id=sample_user_id,
        content="test content",
        paper_id=sample_paper_id,
        paper_title="Test Paper",
        page_number=5,
        source=MemorySource.PDF_TEXT,
        embedding=[0.1, 0.2, 0.3],
    )

    assert chunk.user_id == sample_user_id
    assert chunk.content == "test content"
    assert chunk.metadata.paper_id == sample_paper_id
    assert chunk.metadata.page_number == 5


def test_update_embedding(memory_chunk):
    """Test updating chunk embedding"""
    service = MemoryChunkService()

    new_embedding = [0.5, 0.6, 0.7]

    service.update_embedding(memory_chunk, new_embedding)

    assert memory_chunk.embedding == new_embedding


def test_mark_accessed(memory_chunk):
    """Test marking chunk as accessed via service"""
    service = MemoryChunkService()

    initial_count = memory_chunk.metadata.access_count

    service.mark_accessed(memory_chunk)

    assert memory_chunk.metadata.access_count == initial_count + 1


def test_filter_by_paper(sample_paper_id):
    """Test filtering chunks by paper ID"""
    service = MemoryChunkService()

    from apps.backend.domains.memory_hub.core.entities import MemoryMetadata

    chunks = [
        MemoryChunk(
            id="1",
            user_id="user1",
            content="content1",
            metadata=MemoryMetadata(
                paper_id=sample_paper_id,
                paper_title="Paper 1",
                page_number=1,
            ),
        ),
        MemoryChunk(
            id="2",
            user_id="user1",
            content="content2",
            metadata=MemoryMetadata(
                paper_id="other_paper",
                paper_title="Paper 2",
                page_number=1,
            ),
        ),
    ]

    filtered = service.filter_by_paper(chunks, sample_paper_id)

    assert len(filtered) == 1
    assert filtered[0].metadata.paper_id == sample_paper_id


def test_filter_has_embedding():
    """Test filtering chunks that have embeddings"""
    service = MemoryChunkService()

    from apps.backend.domains.memory_hub.core.entities import MemoryMetadata

    chunks = [
        MemoryChunk(
            id="1",
            user_id="user1",
            content="content1",
            embedding=[0.1, 0.2],
            metadata=MemoryMetadata(paper_id="paper1", paper_title="P1", page_number=1),
        ),
        MemoryChunk(
            id="2",
            user_id="user1",
            content="content2",
            embedding=None,
            metadata=MemoryMetadata(paper_id="paper2", paper_title="P2", page_number=1),
        ),
    ]

    filtered = service.filter_has_embedding(chunks)

    assert len(filtered) == 1
    assert filtered[0].has_embedding()


def test_get_top_accessed():
    """Test getting most frequently accessed chunks"""
    service = MemoryChunkService()

    from apps.backend.domains.memory_hub.core.entities import MemoryMetadata

    chunks = [
        MemoryChunk(
            id="1",
            user_id="user1",
            content="content1",
            metadata=MemoryMetadata(
                paper_id="paper1", paper_title="P1", page_number=1, access_count=10
            ),
        ),
        MemoryChunk(
            id="2",
            user_id="user1",
            content="content2",
            metadata=MemoryMetadata(
                paper_id="paper2", paper_title="P2", page_number=1, access_count=5
            ),
        ),
        MemoryChunk(
            id="3",
            user_id="user1",
            content="content3",
            metadata=MemoryMetadata(
                paper_id="paper3", paper_title="P3", page_number=1, access_count=15
            ),
        ),
    ]

    top_chunks = service.get_top_accessed(chunks, limit=2)

    assert len(top_chunks) == 2
    assert top_chunks[0].metadata.access_count >= top_chunks[1].metadata.access_count
