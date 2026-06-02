"""
Request/Response schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ReadingPosition(BaseModel):
    paper_id: str
    page_number: int
    bbox: Optional[dict] = None
    text_snippet: Optional[str] = None


class UserActionCreate(BaseModel):
    trigger_type: str
    selected_text: Optional[str] = None
    context_text: Optional[str] = None
    reading_position: ReadingPosition
    duration_seconds: Optional[float] = None


class StartReadingSessionRequest(BaseModel):
    user_id: str
    paper_id: str
    session_id: str


class ReadingContextResponse(BaseModel):
    context_id: str
    paper_id: str


class InsightResponse(BaseModel):
    id: str
    content: str
    insight_type: str
    confidence: float
    status: str


class InsightsListResponse(BaseModel):
    insights: List[InsightResponse]


class UserActionResponse(BaseModel):
    action_recorded: bool
    insight: Optional[InsightResponse] = None


class PDFUploadResponse(BaseModel):
    paper_id: str
    filename: str
    page_count: int
    chunk_count: int
    message: str


class PDFMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaperInfo(BaseModel):
    """Information about a paper in the library"""
    paper_id: str
    filename: str
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: int = 0
    file_path: str


class PaperLibraryResponse(BaseModel):
    """Response for paper library listing"""
    papers: List[PaperInfo]
    total: int


class LoadPaperRequest(BaseModel):
    """Request to load a paper from the library"""
    paper_id: str
    user_id: str


class LoadPaperResponse(BaseModel):
    """Response after loading a paper"""
    paper_id: str
    title: str
    page_count: int
    chunk_count: int
    message: str


class PaperContentResponse(BaseModel):
    """Response with paper content for reading"""
    paper_id: str
    title: str
    page_count: int
    pages: List[dict]  # List of {page_number, content}
