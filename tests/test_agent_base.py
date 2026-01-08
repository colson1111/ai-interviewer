"""
Tests for interviewer/agents/base.py

Tests BaseInterviewAgent functionality including response creation,
performance metrics, and status management.
"""

import time
from typing import List

import pytest

from interviewer.agents.base import BaseInterviewAgent
from interviewer.core import (
    AgentCapability,
    AgentMessage,
    AgentResponse,
    InterviewContext,
)

# ============================================================================
# Concrete Implementation for Testing
# ============================================================================


class MockAgent(BaseInterviewAgent):
    """Concrete implementation of BaseInterviewAgent for testing."""

    def __init__(
        self, name: str = "mock_agent", capabilities: List[AgentCapability] = None
    ):
        caps = capabilities or [AgentCapability.INTERVIEW_QUESTIONS]
        super().__init__(name=name, capabilities=caps)
        self._can_handle_return = 0.8
        self._process_response = "Mock response"

    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Return configurable confidence score."""
        return self._can_handle_return

    async def process(
        self, message: AgentMessage, context: InterviewContext
    ) -> AgentResponse:
        """Return a mock response."""
        return self._create_response(
            content=self._process_response,
            confidence=0.9,
            requires_followup=False,
            metadata={"mock": True},
        )


# ============================================================================
# Test Classes
# ============================================================================


class TestBaseAgentInitialization:
    """Tests for agent initialization."""

    def test_agent_creation(self):
        """Test basic agent creation."""
        agent = MockAgent(name="test_agent")

        assert agent.name == "test_agent"
        assert agent.is_enabled is True
        assert agent.usage_count == 0
        assert agent.last_used == 0.0

    def test_agent_with_capabilities(self):
        """Test agent creation with multiple capabilities."""
        caps = [AgentCapability.INTERVIEW_QUESTIONS, AgentCapability.CONVERSATION_FLOW]
        agent = MockAgent(name="multi_cap", capabilities=caps)

        assert len(agent.capabilities) == 2
        assert AgentCapability.INTERVIEW_QUESTIONS in agent.capabilities
        assert AgentCapability.CONVERSATION_FLOW in agent.capabilities

    def test_agent_initial_metrics(self):
        """Test that initial performance metrics are zero."""
        agent = MockAgent()

        assert agent.performance_metrics["total_requests"] == 0
        assert agent.performance_metrics["successful_responses"] == 0
        assert agent.performance_metrics["average_confidence"] == 0.0
        assert agent.performance_metrics["average_response_time"] == 0.0


class TestAgentCapabilities:
    """Tests for capability management."""

    def test_get_capabilities(self):
        """Test getting agent capabilities."""
        caps = [AgentCapability.INTERVIEW_QUESTIONS, AgentCapability.FEEDBACK_ANALYSIS]
        agent = MockAgent(capabilities=caps)

        returned_caps = agent.get_capabilities()

        assert len(returned_caps) == 2
        assert AgentCapability.INTERVIEW_QUESTIONS in returned_caps
        assert AgentCapability.FEEDBACK_ANALYSIS in returned_caps

    def test_get_capabilities_returns_copy(self):
        """Test that get_capabilities returns a copy, not the original list."""
        agent = MockAgent()

        caps1 = agent.get_capabilities()
        caps2 = agent.get_capabilities()

        # Modifying one should not affect the other
        caps1.append(AgentCapability.WEB_SEARCH)
        assert AgentCapability.WEB_SEARCH not in caps2
        assert AgentCapability.WEB_SEARCH not in agent.capabilities

    def test_has_capability_true(self):
        """Test has_capability returns True for existing capability."""
        agent = MockAgent(capabilities=[AgentCapability.INTERVIEW_QUESTIONS])

        assert agent.has_capability(AgentCapability.INTERVIEW_QUESTIONS) is True

    def test_has_capability_false(self):
        """Test has_capability returns False for missing capability."""
        agent = MockAgent(capabilities=[AgentCapability.INTERVIEW_QUESTIONS])

        assert agent.has_capability(AgentCapability.WEB_SEARCH) is False


class TestCreateResponse:
    """Tests for the _create_response helper method."""

    def test_create_basic_response(self):
        """Test creating a basic response."""
        agent = MockAgent(name="responder")

        response = agent._create_response(content="Test content", confidence=0.85)

        assert response.content == "Test content"
        assert response.confidence == 0.85
        assert response.agent_name == "responder"
        assert response.requires_followup is False
        assert response.metadata == {}
        assert response.next_suggested_agents == []

    def test_create_response_with_metadata(self):
        """Test creating a response with metadata."""
        agent = MockAgent()

        response = agent._create_response(
            content="Content",
            confidence=0.9,
            metadata={"key": "value", "phase": "intro"},
        )

        assert response.metadata == {"key": "value", "phase": "intro"}

    def test_create_response_with_followup(self):
        """Test creating a response that requires followup."""
        agent = MockAgent()

        response = agent._create_response(
            content="Need more info", confidence=0.7, requires_followup=True
        )

        assert response.requires_followup is True

    def test_create_response_with_suggested_agents(self):
        """Test creating a response with suggested next agents."""
        agent = MockAgent()

        response = agent._create_response(
            content="Content",
            confidence=0.8,
            next_suggested_agents=["feedback", "summary"],
        )

        assert response.next_suggested_agents == ["feedback", "summary"]

    def test_create_response_with_cost_info(self):
        """Test creating a response with cost information."""
        agent = MockAgent()

        cost_info = {"tokens": 150, "cost": 0.003}
        response = agent._create_response(
            content="Content", confidence=0.8, cost_info=cost_info
        )

        assert response.cost_info == cost_info


class TestPerformanceMetrics:
    """Tests for performance metric tracking."""

    def test_update_metrics_first_request(self):
        """Test updating metrics after first request."""
        agent = MockAgent()

        response = AgentResponse(content="Test", confidence=0.8, agent_name="mock")

        agent.update_performance_metrics(response, response_time=0.5)

        assert agent.performance_metrics["total_requests"] == 1
        assert agent.performance_metrics["successful_responses"] == 1
        assert agent.performance_metrics["average_confidence"] == 0.8
        assert agent.performance_metrics["average_response_time"] == 0.5
        assert agent.usage_count == 1

    def test_update_metrics_multiple_requests(self):
        """Test updating metrics after multiple requests."""
        agent = MockAgent()

        # First request
        response1 = AgentResponse(content="Test", confidence=0.8, agent_name="mock")
        agent.update_performance_metrics(response1, response_time=0.4)

        # Second request
        response2 = AgentResponse(content="Test", confidence=0.6, agent_name="mock")
        agent.update_performance_metrics(response2, response_time=0.6)

        assert agent.performance_metrics["total_requests"] == 2
        assert agent.performance_metrics["average_confidence"] == 0.7  # (0.8 + 0.6) / 2
        assert (
            agent.performance_metrics["average_response_time"] == 0.5
        )  # (0.4 + 0.6) / 2
        assert agent.usage_count == 2

    def test_update_metrics_low_confidence_not_successful(self):
        """Test that low confidence responses are not counted as successful."""
        agent = MockAgent()

        # Low confidence response (< 0.5)
        response = AgentResponse(content="Test", confidence=0.3, agent_name="mock")
        agent.update_performance_metrics(response, response_time=0.5)

        assert agent.performance_metrics["total_requests"] == 1
        assert agent.performance_metrics["successful_responses"] == 0

    def test_update_metrics_updates_last_used(self):
        """Test that last_used timestamp is updated."""
        agent = MockAgent()

        before = time.time()
        response = AgentResponse(content="Test", confidence=0.8, agent_name="mock")
        agent.update_performance_metrics(response, response_time=0.5)
        after = time.time()

        assert before <= agent.last_used <= after

    def test_reset_metrics(self):
        """Test resetting performance metrics."""
        agent = MockAgent()

        # Add some metrics
        response = AgentResponse(content="Test", confidence=0.8, agent_name="mock")
        agent.update_performance_metrics(response, response_time=0.5)

        assert agent.performance_metrics["total_requests"] == 1

        # Reset
        agent.reset_metrics()

        assert agent.performance_metrics["total_requests"] == 0
        assert agent.performance_metrics["successful_responses"] == 0
        assert agent.performance_metrics["average_confidence"] == 0.0
        assert agent.performance_metrics["average_response_time"] == 0.0
        assert agent.usage_count == 0


class TestAgentEnableDisable:
    """Tests for enable/disable functionality."""

    def test_agent_starts_enabled(self):
        """Test that agents start enabled."""
        agent = MockAgent()
        assert agent.is_enabled is True

    def test_disable_agent(self):
        """Test disabling an agent."""
        agent = MockAgent()
        agent.disable()
        assert agent.is_enabled is False

    def test_enable_agent(self):
        """Test enabling a disabled agent."""
        agent = MockAgent()
        agent.disable()
        agent.enable()
        assert agent.is_enabled is True


class TestAgentStatus:
    """Tests for get_status method."""

    def test_get_status_basic(self):
        """Test basic status retrieval."""
        agent = MockAgent(
            name="status_test", capabilities=[AgentCapability.INTERVIEW_QUESTIONS]
        )

        status = agent.get_status()

        assert status["name"] == "status_test"
        assert status["is_enabled"] is True
        assert status["usage_count"] == 0
        assert "performance_metrics" in status
        assert "capabilities" in status

    def test_get_status_capabilities_as_strings(self):
        """Test that capabilities are returned as string values."""
        agent = MockAgent(capabilities=[AgentCapability.INTERVIEW_QUESTIONS])

        status = agent.get_status()

        assert "interview_questions" in status["capabilities"]

    def test_get_status_after_usage(self):
        """Test status after agent has been used."""
        agent = MockAgent()

        response = AgentResponse(content="Test", confidence=0.8, agent_name="mock")
        agent.update_performance_metrics(response, response_time=0.5)

        status = agent.get_status()

        assert status["usage_count"] == 1
        assert status["last_used"] > 0
        assert status["performance_metrics"]["total_requests"] == 1


class TestAgentStringRepresentation:
    """Tests for string representation methods."""

    def test_str_representation(self):
        """Test __str__ method."""
        agent = MockAgent(
            name="string_test", capabilities=[AgentCapability.INTERVIEW_QUESTIONS]
        )

        str_repr = str(agent)

        assert "MockAgent" in str_repr
        assert "string_test" in str_repr
        assert "capabilities=1" in str_repr

    def test_repr_representation(self):
        """Test __repr__ method."""
        agent = MockAgent(name="repr_test")

        repr_str = repr(agent)

        assert "MockAgent" in repr_str
        assert "repr_test" in repr_str


class TestAgentProcessing:
    """Tests for the async process method."""

    @pytest.mark.asyncio
    async def test_process_returns_response(
        self, interview_context, sample_user_message
    ):
        """Test that process returns a valid AgentResponse."""
        agent = MockAgent()

        response = await agent.process(sample_user_message, interview_context)

        assert isinstance(response, AgentResponse)
        assert response.content == "Mock response"
        assert response.confidence == 0.9
        assert response.agent_name == "mock_agent"

    def test_can_handle_returns_float(self, interview_context, sample_user_message):
        """Test that can_handle returns a float."""
        agent = MockAgent()

        score = agent.can_handle(sample_user_message, interview_context)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
