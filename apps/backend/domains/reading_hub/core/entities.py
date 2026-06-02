"""
Reading Hub Domain - Core Entities

Defines the reading context and user actions that trigger AI insights.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class TriggerType(Enum):
    """Trigger type for AI insights"""

    SELECTION = "selection"  # User selected text
    LINGER = "linger"  # User stayed at a location (gaze detection)
    BACKTRACK = "backtrack"  # User scrolled back up (回溯检测)
    SCROLL_STOP = "scroll_stop"  # User stopped scrolling
    MANUAL = "manual"  # Explicit request


@dataclass
class ReadingPosition:
    """Position in a PDF document"""

    paper_id: str
    page_number: int
    # Optional bounding box for precise location
    bbox: Optional[Dict[str, float]] = None  # {x, y, width, height}
    text_snippet: Optional[str] = None


@dataclass
class UserAction:
    """User action that may trigger an insight"""

    trigger_type: TriggerType
    reading_position: ReadingPosition
    selected_text: Optional[str] = None
    context_text: Optional[str] = None
    # For linger trigger
    duration_seconds: Optional[float] = None
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReadingContext:
    """Current reading state (aggregate root)"""

    id: Optional[str] = None
    user_id: str = ""
    paper_id: str = ""

    # Current reading position
    current_position: Optional[ReadingPosition] = None

    # Recent actions (for context)
    recent_actions: List[UserAction] = field(default_factory=list)

    # Reading session metadata
    session_id: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    reading_progress: float = 0.0  # 0.0 to 1.0

    def add_action(self, action: UserAction, max_history: int = 10) -> None:
        """Add a new user action to the context"""
        self.recent_actions.append(action)
        # Keep only recent actions
        if len(self.recent_actions) > max_history:
            self.recent_actions = self.recent_actions[-max_history:]
        self.last_activity_at = datetime.utcnow()

    def get_current_position(self) -> Optional[ReadingPosition]:
        """Get the current reading position"""
        return self.current_position

    def update_position(
        self,
        position: Optional[ReadingPosition] = None,
        *,
        paper_id: Optional[str] = None,
        page_number: Optional[int] = None,
        bbox: Optional[Dict[str, float]] = None,
        text_snippet: Optional[str] = None,
    ) -> None:
        """Update the current reading position."""
        if position is None:
            if paper_id is None or page_number is None:
                raise ValueError("paper_id and page_number are required")
            position = ReadingPosition(
                paper_id=paper_id,
                page_number=page_number,
                bbox=bbox,
                text_snippet=text_snippet,
            )

        self.current_position = position
        self.last_activity_at = datetime.utcnow()

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if reading context is stale (no activity for timeout)"""
        if not self.last_activity_at:
            return True
        delta = datetime.utcnow() - self.last_activity_at
        return delta.total_seconds() > timeout_seconds
