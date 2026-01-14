"""
Tests for MemoryChunk domain entity
"""

from apps.backend.domains.memory_hub.core.entities import (
    MemoryChunk,
    MemoryMetadata,
)


def test_create_memory_chunk(memory_chunk):
    """Test creating a new memory chunk"""
    assert memory_chunk.user_id == "user_test_123"
    assert memory_chunk.content == "This is a sample memory chunk content"
    assert memory_chunk.embedding == [0.1, 0.2, 0.3]
    assert memory_chunk.metadata.paper_id == "paper_test_456"
    assert memory_chunk.metadata.page_number == 5


def test_mark_accessed(memory_chunk):
    """Test marking a memory chunk as accessed"""
    initial_count = memory_chunk.metadata.access_count

    memory_chunk.mark_accessed()

    assert memory_chunk.metadata.access_count == initial_count + 1
    assert memory_chunk.metadata.last_accessed_at is not None


def test_is_from_same_paper_true(memory_chunk, sample_paper_id):
    """Test checking if chunk is from same paper - true case"""
    assert memory_chunk.is_from_same_paper(sample_paper_id)


def test_is_from_same_paper_false(memory_chunk):
    """Test checking if chunk is from same paper - false case"""
    assert not memory_chunk.is_from_same_paper("other_paper_id")


def test_has_embedding_true(memory_chunk):
    """Test checking if chunk has embedding - true case"""
    assert memory_chunk.has_embedding()


def test_has_embedding_false():
    """Test checking if chunk has embedding - false case"""

    chunk = MemoryChunk(
        user_id="user_1",
        content="content",
        embedding=None,
        metadata=MemoryMetadata(
            paper_id="paper_1",
            paper_title="Test",
            page_number=1,
        ),
    )

    assert not chunk.has_embedding()
