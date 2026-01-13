"""
Request/Response schemas
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


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
    created_at: datetime
    updated_at: Optional[datetime] = None
