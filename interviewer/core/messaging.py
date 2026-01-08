"""Message types and communication structures for multi-agent system."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """Types of messages in the interview system."""

    USER_RESPONSE = "user_response"
    INTERVIEWER_QUESTION = "interviewer_question"
    CODE_SUBMISSION = "code_submission"
    FEEDBACK_REQUEST = "feedback_request"
    SEARCH_REQUEST = "search_request"
    SUMMARY_REQUEST = "summary_request"
    SYSTEM_EVENT = "system_event"


@dataclass
class AgentMessage:
    """Message sent to an agent for processing."""

    content: str
    message_type: MessageType
    metadata: Dict[str, Any]
    sender: str
    timestamp: float
    session_id: str

    @classmethod
    def from_user_input(
        cls, content: str, session_id: str, timestamp: float
    ) -> "AgentMessage":
        """Create a message from user input."""
        return cls(
            content=content,
            message_type=MessageType.USER_RESPONSE,
            metadata={},
            sender="user",
            timestamp=timestamp,
            session_id=session_id,
        )


@dataclass
class AgentResponse:
    """Response from an agent after processing a message."""

    content: str
    confidence: float  # 0.0 to 1.0
    agent_name: str
    requires_followup: bool = False
    metadata: Dict[str, Any] = None
    next_suggested_agents: List[str] = None
    cost_info: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.next_suggested_agents is None:
            self.next_suggested_agents = []


@dataclass
class CombinedResponse:
    """Final response after orchestrator combines multiple agent responses."""

    content: str
    primary_agent: str
    contributing_agents: List[str]
    total_confidence: float
    metadata: Dict[str, Any]
    cost_breakdown: Dict[str, Any]
    feedback_data: Optional[Dict[str, Any]] = None
