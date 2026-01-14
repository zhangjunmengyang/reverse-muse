"""
Insight Hub Domain - Core Entities

Defines AI-generated insights that appear as bubbles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class InsightType(Enum):
    """Type of AI insight"""

    EXPLANATION = "explanation"  # Explain the selected text
    CONNECTION = "connection"  # Connect to previous knowledge
    CONTRADICTION = "contradiction"  # Point out contradictions
    HYPOTHESIS = "hypothesis"  # Suggest hypotheses
    QUESTION = "question"  # Prompt a question
    SIMILARITY = "similarity"  # Similar content found
    CUSTOM = "custom"  # Other types


class InsightStatus(Enum):
    """Status of an insight"""

    GENERATING = "generating"
    GENERATED = "generated"
    DISPLAYED = "displayed"
    DISMISSED = "dismissed"
    PINNED = "pinned"


@dataclass
class InsightContext:
    """Context that led to this insight"""

    trigger_type: str
    paper_id: str
    page_number: int
    selected_text: Optional[str] = None
    context_text: Optional[str] = None
    # Related memories that influenced this insight
    related_memory_ids: List[str] = field(default_factory=list)
    related_paper_titles: List[str] = field(default_factory=list)


@dataclass
class BubbleInsight:
    """AI-generated insight displayed as a bubble (aggregate root)"""

    id: Optional[str] = None
    user_id: str = ""
    reading_context_id: str = ""

    # Insight content
    insight_type: InsightType = InsightType.CUSTOM
    content: str = ""
    confidence: float = 0.0  # 0.0 to 1.0

    # Context
    context: InsightContext = field(default_factory=lambda: InsightContext(
        trigger_type="", paper_id="", page_number=0
    ))

    # State
    status: InsightStatus = InsightStatus.GENERATING
    is_ai_generated: bool = True

    # Display settings
    max_display_length: int = 200
    display_duration_seconds: int = 5

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    displayed_at: Optional[datetime] = None

    def mark_displayed(self) -> None:
        """Mark this insight as displayed"""
        self.status = InsightStatus.DISPLAYED
        self.displayed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_dismissed(self) -> None:
        """Mark this insight as dismissed by user"""
        self.status = InsightStatus.DISMISSED
        self.updated_at = datetime.utcnow()

    def mark_pinned(self) -> None:
        """Pin this insight for later review"""
        self.status = InsightStatus.PINNED
        self.updated_at = datetime.utcnow()

    def should_display(self, confidence_threshold: float = 0.8) -> bool:
        """Check if this insight should be displayed"""
        return bool(
            self.confidence >= confidence_threshold
            and self.status == InsightStatus.GENERATED
            and self.content
        )

    def get_display_content(self) -> str:
        """Get content suitable for display in bubble"""
        if len(self.content) <= self.max_display_length:
            return self.content
        return self.content[: self.max_display_length - 3] + "..."
