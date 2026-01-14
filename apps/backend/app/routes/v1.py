"""
API V1 Routes

Routes for reading sessions, insights, and PDF management.
"""

from pathlib import Path
from typing import Optional

import fitz
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from apps.backend.app.core.config import get_settings
from apps.backend.app.schemas.common import (
    InsightResponse,
    InsightsListResponse,
    LoadPaperRequest,
    LoadPaperResponse,
    PaperContentResponse,
    PaperInfo,
    PaperLibraryResponse,
    PDFMetadata,
    PDFUploadResponse,
    ReadingContextResponse,
    StartReadingSessionRequest,
    UserActionCreate,
    UserActionResponse,
)
from apps.backend.domains.insight_hub.services.domain_service import (
    InsightGenerationService,
)
from apps.backend.domains.insight_hub.use_cases.generate_insight import (
    GenerateInsightUseCase,
)
from apps.backend.domains.memory_hub.core.entities import MemoryChunk, MemoryMetadata
from apps.backend.domains.reading_hub.core.entities import (
    ReadingPosition as DomainReadingPosition,
    TriggerType,
    UserAction,
)
from apps.backend.domains.reading_hub.services.domain_service import (
    ReadingContextService,
)
from apps.backend.domains.reading_hub.use_cases.record_user_action import (
    RecordUserActionUseCase,
)
from apps.backend.domains.reading_hub.use_cases.start_reading_session import (
    StartReadingSessionUseCase,
)
from apps.backend.infrastructure.db import (
    SurrealInsightRepository,
    SurrealMemoryChunkRepository,
    SurrealReadingContextRepository,
)
from apps.backend.infrastructure.embedding import get_embedding_service
from apps.backend.infrastructure.llm import get_llm_service
from apps.backend.infrastructure.pdf import get_pdf_service

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()

# Paper Library path from settings
PAPER_LIBRARY_PATH = settings.paper_library_dir


def get_library_pdf_path(paper_id: str) -> Path:
    """Get the PDF path for a library paper, raising 404 if not found."""
    if not PAPER_LIBRARY_PATH:
        raise HTTPException(status_code=404, detail="Paper library not configured")
    pdf_path = PAPER_LIBRARY_PATH / f"{paper_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found in library")
    return pdf_path


def read_pdf_metadata(pdf_path: Path) -> dict:
    """Read PDF metadata from a file path."""
    doc = fitz.open(pdf_path)
    metadata = {
        "title": doc.metadata.get("title") or pdf_path.stem,
        "author": doc.metadata.get("author"),
        "page_count": len(doc),
    }
    doc.close()
    return metadata


async def get_dependencies():
    """
    Dependency injection for use cases and repositories.

    This is a simplified version that doesn't properly handle async dependencies,
    but works for MVP purposes.
    """
    # Repositories (they get DB connection internally)
    context_repo = SurrealReadingContextRepository()
    memory_repo = SurrealMemoryChunkRepository()
    insight_repo = SurrealInsightRepository()

    # Services
    llm_service = get_llm_service()
    pdf_service = get_pdf_service()
    embedding_service = get_embedding_service()

    # Domain services
    context_service = ReadingContextService()

    # Use cases
    insight_use_case = GenerateInsightUseCase(
        insight_repo=insight_repo,
        insight_service=InsightGenerationService(),
    )
    start_reading_use_case = StartReadingSessionUseCase(
        context_repo=context_repo,
        context_service=context_service,
    )
    record_action_use_case = RecordUserActionUseCase(
        context_repo=context_repo,
        context_service=context_service,
        memory_repo=memory_repo,
        insight_use_case=insight_use_case,
    )

    return {
        "context_repo": context_repo,
        "memory_repo": memory_repo,
        "insight_repo": insight_repo,
        "llm_service": llm_service,
        "pdf_service": pdf_service,
        "embedding_service": embedding_service,
        "context_service": context_service,
        "insight_use_case": insight_use_case,
        "start_reading_use_case": start_reading_use_case,
        "record_action_use_case": record_action_use_case,
    }


@router.post("/reading/start", response_model=ReadingContextResponse)
async def start_reading_session(
    request: StartReadingSessionRequest,
    deps: dict = Depends(get_dependencies),
):
    """
    Start a new reading session or return existing active context.

    Args:
        request: StartReadingSessionRequest with user_id, paper_id, session_id

    Returns:
        ReadingContextResponse with context_id and paper_id
    """
    use_case = deps["start_reading_use_case"]
    logger.info("Starting reading session", user_id=request.user_id, paper_id=request.paper_id)

    try:
        context = await use_case.execute(
            user_id=request.user_id,
            paper_id=request.paper_id,
            session_id=request.session_id,
        )

        if not context:
            raise HTTPException(status_code=500, detail="Failed to create reading context")

        return ReadingContextResponse(
            context_id=context.id or "",
            paper_id=context.paper_id,
        )
    except Exception as e:
        logger.error("Failed to start reading session", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reading/action", response_model=UserActionResponse)
async def record_user_action(
    action_request: UserActionCreate,
    context_id: Optional[str] = None,
    deps: dict = Depends(get_dependencies),
):
    """
    Record a user action (selection, linger, etc.) and possibly trigger insight.

    Args:
        action_request: UserActionCreate with trigger_type, reading_position, etc.
        context_id: Reading context ID (optional, extracted from query param)

    Returns:
        UserActionResponse with action_recorded and optional insight
    """
    use_case = deps["record_action_use_case"]
    logger.info("Recording user action", trigger_type=action_request.trigger_type)

    try:
        # Convert trigger_type string to enum
        trigger_type = TriggerType(action_request.trigger_type)

        # Convert schema ReadingPosition to domain ReadingPosition
        domain_reading_position = DomainReadingPosition(
            paper_id=action_request.reading_position.paper_id,
            page_number=action_request.reading_position.page_number,
            bbox=action_request.reading_position.bbox,
            text_snippet=action_request.reading_position.text_snippet,
        )

        # Create UserAction domain object
        action = UserAction(
            trigger_type=trigger_type,
            reading_position=domain_reading_position,
            selected_text=action_request.selected_text,
            context_text=action_request.context_text,
            duration_seconds=action_request.duration_seconds,
        )

        # Execute use case
        insight = await use_case.execute(
            context_id=context_id,
            action=action,
        )

        # Convert insight to response if exists
        insight_response = None
        if insight:
            insight_response = InsightResponse(
                id=insight.id or "",
                content=insight.content,
                insight_type=insight.insight_type.value if insight.insight_type else "",
                confidence=insight.confidence,
                status=insight.status.value if insight.status else "",
            )

        return UserActionResponse(
            action_recorded=True,
            insight=insight_response,
        )
    except ValueError as e:
        logger.error("Invalid trigger type", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid trigger type: {e}")
    except Exception as e:
        error_str = str(e)
        logger.error("Failed to record user action", error=error_str)

        # Handle rate limit errors gracefully - return success without insight
        if "429" in error_str or "rate" in error_str.lower() or "limit" in error_str.lower():
            logger.warning("Rate limited, returning without insight")
            return UserActionResponse(action_recorded=True, insight=None)

        raise HTTPException(status_code=500, detail=error_str)


@router.get("/insights/{context_id}", response_model=InsightsListResponse)
async def get_insights(
    context_id: str,
    deps: dict = Depends(get_dependencies),
):
    """
    Get all insights for a reading context.

    Args:
        context_id: Reading context ID

    Returns:
        InsightsListResponse with list of InsightResponse
    """
    insight_repo = deps["insight_repo"]
    logger.info("Getting insights", context_id=context_id)

    try:
        insights = await insight_repo.list_by_context(context_id)

        insight_responses = [
            InsightResponse(
                id=insight.id or "",
                content=insight.content,
                insight_type=insight.insight_type.value if insight.insight_type else "",
                confidence=insight.confidence,
                status=insight.status.value if insight.status else "",
            )
            for insight in insights
        ]

        return InsightsListResponse(insights=insight_responses)
    except Exception as e:
        logger.error("Failed to get insights", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    deps: dict = Depends(get_dependencies),
):
    """
    Upload a PDF file, extract text, and generate embeddings.

    Phase 1 升级：为每个文本块生成 OpenAI Embedding，支持语义搜索。

    Args:
        file: PDF file to upload
        user_id: User ID (optional)

    Returns:
        PDFUploadResponse with paper_id, filename, page_count, chunk_count
    """
    pdf_service = deps["pdf_service"]
    memory_repo = deps["memory_repo"]
    embedding_service = deps["embedding_service"]

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    logger.info("Uploading PDF", filename=file.filename, user_id=user_id)

    try:
        # Read file content
        file_content = await file.read()

        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.max_pdf_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.max_pdf_size_mb}MB"
            )

        # Save PDF and extract metadata
        actual_user_id = user_id or "anonymous"
        paper_id, metadata = pdf_service.save_pdf(
            filename=file.filename,
            file_content=file_content,
            user_id=actual_user_id,
        )

        # Get PDF path and extract text chunks
        pdf_path = pdf_service.get_pdf_path(paper_id)
        if not pdf_path:
            raise HTTPException(status_code=500, detail="Failed to save PDF file")

        chunks_data = pdf_service.extract_text_and_chunk(
            pdf_path=pdf_path,
            paper_id=paper_id,
            paper_title=metadata.get("title", file.filename),
            user_id=actual_user_id,
        )

        # Generate embeddings for all chunks (batch processing)
        logger.info("Generating embeddings for chunks", count=len(chunks_data))
        chunk_texts = [c["content"] for c in chunks_data]
        embeddings = await embedding_service.embed_batch(chunk_texts)

        # Save chunks with embeddings to repository
        for i, chunk_data in enumerate(chunks_data):
            chunk_metadata = MemoryMetadata(
                paper_id=paper_id,
                paper_title=metadata.get("title", file.filename),
                page_number=chunk_data["page_number"],
            )
            chunk = MemoryChunk(
                user_id=actual_user_id,
                content=chunk_data["content"],
                embedding=embeddings[i],
                metadata=chunk_metadata,
            )
            await memory_repo.save(chunk)

        logger.info(
            "PDF uploaded with embeddings",
            paper_id=paper_id,
            page_count=metadata.get("page_count", 0),
            chunk_count=len(chunks_data),
        )

        return PDFUploadResponse(
            paper_id=paper_id,
            filename=file.filename,
            page_count=metadata.get("page_count", 0),
            chunk_count=len(chunks_data),
            message=f"PDF uploaded successfully. Extracted {len(chunks_data)} text chunks with embeddings.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload PDF", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf/{paper_id}/metadata", response_model=PDFMetadata)
async def get_pdf_metadata(
    paper_id: str,
    deps: dict = Depends(get_dependencies),
):
    """Get metadata for a PDF by paper_id."""
    pdf_service = deps["pdf_service"]
    logger.info("Getting PDF metadata", paper_id=paper_id)

    try:
        pdf_path = pdf_service.get_pdf_path(paper_id)
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF not found")

        metadata = read_pdf_metadata(pdf_path)
        return PDFMetadata(
            title=metadata["title"],
            author=metadata["author"],
            page_count=metadata["page_count"],
            created_at=None,
            updated_at=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get PDF metadata", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library/papers", response_model=PaperLibraryResponse)
async def list_library_papers():
    """List all papers available in the paper library folder."""
    if not PAPER_LIBRARY_PATH or not PAPER_LIBRARY_PATH.exists():
        logger.warning("Paper library path not configured or does not exist")
        return PaperLibraryResponse(papers=[], total=0)

    papers = []
    for pdf_file in PAPER_LIBRARY_PATH.glob("*.pdf"):
        try:
            metadata = read_pdf_metadata(pdf_file)
            papers.append(PaperInfo(
                paper_id=pdf_file.stem,
                filename=pdf_file.name,
                title=metadata["title"],
                author=metadata["author"],
                page_count=metadata["page_count"],
                file_path=str(pdf_file),
            ))
        except Exception as e:
            logger.warning("Failed to read PDF", file=str(pdf_file), error=str(e))

    logger.info("Listed library papers", count=len(papers))
    return PaperLibraryResponse(papers=papers, total=len(papers))


@router.post("/library/load", response_model=LoadPaperResponse)
async def load_library_paper(
    request: LoadPaperRequest,
    deps: dict = Depends(get_dependencies),
):
    """
    Load a paper from the library, extract text chunks, and generate embeddings.

    Phase 1 升级：为每个文本块生成 OpenAI Embedding，支持语义搜索。
    """
    memory_repo = deps["memory_repo"]
    embedding_service = deps["embedding_service"]
    pdf_path = get_library_pdf_path(request.paper_id)

    logger.info("Loading paper from library", paper_id=request.paper_id, user_id=request.user_id)

    try:
        doc = fitz.open(pdf_path)
        title = doc.metadata.get("title") or request.paper_id
        page_count = len(doc)

        # Extract text from all pages
        chunk_texts = []
        chunk_pages = []
        for page_num in range(page_count):
            text = doc[page_num].get_text().replace('\x00', '').strip()
            if not text:
                continue
            # Limit to 2000 chars per page
            chunk_texts.append(text[:2000])
            chunk_pages.append(page_num + 1)

        doc.close()

        if not chunk_texts:
            return LoadPaperResponse(
                paper_id=request.paper_id,
                title=title,
                page_count=page_count,
                chunk_count=0,
                message=f"No text content found in {title}.",
            )

        # Generate embeddings for all chunks (batch processing)
        logger.info("Generating embeddings for library paper", count=len(chunk_texts))
        embeddings = await embedding_service.embed_batch(chunk_texts)

        # Save chunks with embeddings
        chunks_created = 0
        for i, text in enumerate(chunk_texts):
            chunk = MemoryChunk(
                user_id=request.user_id,
                content=text,
                embedding=embeddings[i],
                metadata=MemoryMetadata(
                    paper_id=request.paper_id,
                    paper_title=title,
                    page_number=chunk_pages[i],
                ),
            )
            await memory_repo.save(chunk)
            chunks_created += 1

        logger.info(
            "Paper loaded with embeddings",
            paper_id=request.paper_id,
            page_count=page_count,
            chunks=chunks_created,
        )

        return LoadPaperResponse(
            paper_id=request.paper_id,
            title=title,
            page_count=page_count,
            chunk_count=chunks_created,
            message=f"Successfully loaded {title} with {chunks_created} text chunks and embeddings.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load paper", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library/paper/{paper_id}/content", response_model=PaperContentResponse)
async def get_paper_content(paper_id: str):
    """Get the text content of a paper for reading."""
    pdf_path = get_library_pdf_path(paper_id)

    try:
        doc = fitz.open(pdf_path)
        title = doc.metadata.get("title") or paper_id
        page_count = len(doc)

        pages = [
            {"page_number": page_num + 1, "content": doc[page_num].get_text()}
            for page_num in range(page_count)
        ]
        doc.close()

        return PaperContentResponse(
            paper_id=paper_id,
            title=title,
            page_count=page_count,
            pages=pages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get paper content", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library/paper/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str):
    """Get the PDF file for viewing in the frontend."""
    pdf_path = get_library_pdf_path(paper_id)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{paper_id}.pdf",
        headers={"Access-Control-Expose-Headers": "Content-Disposition"},
    )
