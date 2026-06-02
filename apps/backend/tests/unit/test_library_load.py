"""
Tests for library loading route behavior.
"""

import asyncio

import fitz

from apps.backend.app.routes import v1
from apps.backend.app.schemas.common import LoadPaperRequest
from apps.backend.domains.memory_hub.core.entities import MemoryChunk, MemoryMetadata


class ExistingChunkRepository:
    def __init__(self, chunk: MemoryChunk):
        self.chunk = chunk
        self.saved_chunks = 0

    async def list_by_paper(self, user_id: str, paper_id: str):
        return [self.chunk]

    async def save(self, chunk: MemoryChunk) -> None:
        self.saved_chunks += 1


class FailingEmbeddingService:
    async def embed_batch(self, texts):
        raise AssertionError("existing library papers should not be re-embedded")


def test_load_library_paper_reuses_existing_chunks(tmp_path, monkeypatch):
    async def run_test():
        paper_id = "paper_existing"
        pdf_path = tmp_path / f"{paper_id}.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Existing PDF text.")
        doc.save(pdf_path)
        doc.close()

        monkeypatch.setattr(v1, "PDF_DIR", tmp_path)

        chunk = MemoryChunk(
            user_id="demo_user",
            content="Existing PDF text.",
            embedding=[1.0, 0.0],
            metadata=MemoryMetadata(
                paper_id=paper_id,
                paper_title="Existing Paper",
                page_number=1,
            ),
        )
        memory_repo = ExistingChunkRepository(chunk)

        response = await v1.load_library_paper(
            LoadPaperRequest(paper_id=paper_id, user_id="demo_user"),
            deps={
                "memory_repo": memory_repo,
                "embedding_service": FailingEmbeddingService(),
            },
        )

        assert response.paper_id == paper_id
        assert response.title == "Existing Paper"
        assert response.chunk_count == 1
        assert "already loaded" in response.message
        assert memory_repo.saved_chunks == 0

    asyncio.run(run_test())
