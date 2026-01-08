"""
Shared test fixtures and configuration for the AI Interviewer test suite.
"""

import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from interviewer.config import (
    Difficulty,
    InterviewConfig,
    InterviewType,
    LLMConfig,
    LLMProvider,
    Tone,
)
from interviewer.core import (
    AgentMessage,
    AgentResponse,
    CandidateInfo,
    InterviewContext,
    MessageType,
)

# ============================================================================
# Markers
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "live_llm: marks tests that require live LLM API calls"
    )


def pytest_collection_modifyitems(config, items):
    """Skip live_llm tests unless RUN_LIVE_LLM_TESTS=1 is set."""
    if os.environ.get("RUN_LIVE_LLM_TESTS", "0") != "1":
        skip_live = pytest.mark.skip(
            reason="Set RUN_LIVE_LLM_TESTS=1 to run live LLM tests"
        )
        for item in items:
            if "live_llm" in item.keywords:
                item.add_marker(skip_live)


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def openai_llm_config():
    """Create an OpenAI LLM configuration."""
    return LLMConfig(
        provider=LLMProvider.OPENAI, model="gpt-4o", temperature=0.7, max_tokens=1000
    )


@pytest.fixture
def anthropic_llm_config():
    """Create an Anthropic LLM configuration."""
    return LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        temperature=0.7,
        max_tokens=1000,
    )


@pytest.fixture
def interview_config():
    """Create a standard interview configuration."""
    return InterviewConfig(
        interview_type=InterviewType.BEHAVIORAL,
        tone=Tone.PROFESSIONAL,
        difficulty=Difficulty.MEDIUM,
    )


# ============================================================================
# Context Fixtures
# ============================================================================


@pytest.fixture
def candidate_info():
    """Create sample candidate information."""
    return CandidateInfo(
        resume_text="Software engineer with 5 years experience in Python and ML.",
        job_description="Looking for a Senior ML Engineer to join our team.",
        custom_instructions="Focus on leadership experience.",
        company_name="TechCorp",
        role_title="Senior ML Engineer",
        skills_mentioned=["Python", "Machine Learning", "TensorFlow"],
        companies_mentioned=["Previous Corp"],
        technologies_mentioned=["Python", "TensorFlow", "Docker"],
    )


@pytest.fixture
def interview_context(openai_llm_config, interview_config, candidate_info):
    """Create a complete interview context."""
    return InterviewContext(
        session_id="test_session_123",
        llm_config=openai_llm_config,
        interview_config=interview_config,
        candidate_info=candidate_info,
    )


# ============================================================================
# Message Fixtures
# ============================================================================


@pytest.fixture
def sample_user_message():
    """Create a sample user message."""
    return AgentMessage(
        content="In my previous role, I led a team of 5 engineers.",
        message_type=MessageType.USER_RESPONSE,
        metadata={},
        sender="user",
        timestamp=time.time(),
        session_id="test_session_123",
    )


@pytest.fixture
def sample_system_message():
    """Create a sample system message to start interview."""
    return AgentMessage(
        content="start_interview",
        message_type=MessageType.SYSTEM_EVENT,
        metadata={},
        sender="system",
        timestamp=time.time(),
        session_id="test_session_123",
    )


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_pydantic_agent():
    """Create a mock pydantic-ai agent."""
    mock_agent = MagicMock()

    # Mock the run method to return a mock result
    mock_result = MagicMock()
    mock_result.output = "That's an interesting experience! Can you tell me more about a specific challenge you faced while leading that team?"
    mock_result.all_messages = []

    mock_agent.run = AsyncMock(return_value=mock_result)

    return mock_agent


@pytest.fixture
def mock_agent_response():
    """Create a sample agent response."""
    return AgentResponse(
        content="Tell me about a time you led a project.",
        confidence=0.95,
        agent_name="interview",
        requires_followup=False,
        metadata={"phase": "behavioral"},
        next_suggested_agents=[],
        cost_info={"tokens": 100},
    )
