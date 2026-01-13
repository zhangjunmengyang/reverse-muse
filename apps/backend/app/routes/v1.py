"""
API V1 Routes

Routes for reading sessions, insights, and PDF management.
"""

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from typing import Optional

from apps.backend.app.schemas.common import (
    InsightResponse,
    InsightsListResponse,
    PDFMetadata,
    PDFUploadResponse,
    ReadingContextResponse,
    StartReadingSessionRequest,
    UserActionCreate,
    UserActionResponse,
)
from apps.backend.app.core.config import get_settings
from apps.backend.domains.insight_hub.use_cases.generate_insight import (
    GenerateInsightUseCase,
)
from apps.backend.domains.insight_hub.port.repository import InsightRepository
from apps.backend.domains.memory_hub.port.repository import MemoryChunkRepository
from apps.backend.domains.memory_hub.core.entities import MemoryChunk
from apps.backend.domains.reading_hub.core.entities import (
    ReadingContext,
    TriggerType,
    UserAction,
)
from apps.backend.domains.reading_hub.use_cases.record_user_action import (
    RecordUserActionUseCase,
)
from apps.backend.domains.reading_hub.use_cases.start_reading_session import (
    StartReadingSessionUseCase,
)
from apps.backend.domains.reading_hub.port.repository import (
    ReadingContextRepository,
)
from apps.backend.domains.reading_hub.services.domain_service import (
    ReadingContextService,
)
from apps.backend.domains.insight_hub.services.domain_service import (
    InsightGenerationService,
)
from apps.backend.infrastructure.db import (
    SurrealReadingContextRepository,
    SurrealMemoryChunkRepository,
    SurrealInsightRepository,
)
from apps.backend.infrastructure.llm import get_llm_service
from apps.backend.infrastructure.pdf import get_pdf_service
from apps.backend.infrastructure.db.connection import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


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

        # Create UserAction domain object
        action = UserAction(
            trigger_type=trigger_type,
            reading_position=action_request.reading_position,
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
        logger.error("Failed to record user action", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
    Upload a PDF file and extract metadata.

    Args:
        file: PDF file to upload
        user_id: User ID (optional)

    Returns:
        PDFUploadResponse with paper_id, filename, page_count, chunk_count
    """
    pdf_service = deps["pdf_service"]
    memory_repo = deps["memory_repo"]

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

        # Save chunks to repository
        for chunk_data in chunks_data:
            chunk = MemoryChunk(
                user_id=actual_user_id,
                paper_id=paper_id,
                content=chunk_data["content"],
                paper_title=metadata.get("title", file.filename),
                metadata={
                    "page_number": chunk_data["page_number"],
                    "chunk_index": chunk_data["chunk_index"],
                    "start_char": chunk_data["start_char"],
                    "end_char": chunk_data["end_char"],
                },
            )
            await memory_repo.save(chunk)

        logger.info(
            "PDF uploaded and processed",
            paper_id=paper_id,
            page_count=metadata.get("page_count", 0),
            chunk_count=len(chunks_data),
        )

        return PDFUploadResponse(
            paper_id=paper_id,
            filename=file.filename,
            page_count=metadata.get("page_count", 0),
            chunk_count=len(chunks_data),
            message=f"PDF uploaded successfully. Extracted {len(chunks_data)} text chunks.",
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
    """
    Get metadata for a PDF by paper_id.

    Args:
        paper_id: Paper ID

    Returns:
        PDFMetadata with title, author, page_count, created_at
    """
    pdf_service = deps["pdf_service"]
    logger.info("Getting PDF metadata", paper_id=paper_id)

    try:
        pdf_path = pdf_service.get_pdf_path(paper_id)
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF not found")

        import fitz
        doc = fitz.open(pdf_path)
        metadata = {
            "title": doc.metadata.get("title"),
            "author": doc.metadata.get("author"),
            "page_count": len(doc),
            "created_at": None,  # Would need to fetch from repository
        }
        doc.close()

        return PDFMetadata(
            title=metadata["title"],
            author=metadata["author"],
            page_count=metadata["page_count"],
            created_at=metadata["created_at"] or "Unknown",
            updated_at=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get PDF metadata", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
