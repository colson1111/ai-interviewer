"""
Tests for interviewer/agents/interview.py

Tests InterviewAgent functionality with mocked LLM calls.
Optional live LLM tests can be run with RUN_LIVE_LLM_TESTS=1.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from interviewer.agents.interview import (
    InterviewAgent,
    InterviewDeps,
)
from interviewer.config import (
    Difficulty,
    InterviewConfig,
    InterviewType,
    LLMConfig,
    LLMProvider,
    Tone,
)
from interviewer.core import (
    AgentCapability,
    AgentMessage,
    AgentResponse,
    MessageType,
)

# ============================================================================
# Test InterviewDeps
# ============================================================================


class TestInterviewDeps:
    """Tests for InterviewDeps dataclass."""

    def test_create_deps_minimal(self):
        """Test creating deps with minimal info."""
        deps = InterviewDeps(
            interview_type="behavioral",
            tone="professional",
            difficulty="medium",
            company_name=None,
            role_title=None,
            resume_summary=None,
            jd_summary=None,
            custom_instructions=None,
            conversation_history=[],
            current_phase="introduction",
        )

        assert deps.interview_type == "behavioral"
        assert deps.company_name is None

    def test_create_deps_full(self):
        """Test creating deps with full info."""
        deps = InterviewDeps(
            interview_type="case_study",
            tone="challenging",
            difficulty="hard",
            company_name="TechCorp",
            role_title="Senior Engineer",
            resume_summary="5 years experience in Python",
            jd_summary="Looking for senior engineer",
            custom_instructions="Focus on leadership",
            conversation_history=[{"content": "Hello"}],
            current_phase="behavioral",
        )

        assert deps.company_name == "TechCorp"
        assert deps.role_title == "Senior Engineer"
        assert len(deps.conversation_history) == 1


# ============================================================================
# Test InterviewAgent Initialization
# ============================================================================


class TestInterviewAgentInit:
    """Tests for InterviewAgent initialization."""

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_init_openai(self, mock_agent_class, mock_openai_model):
        """Test initializing with OpenAI provider."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o")
        interview_config = InterviewConfig()

        agent = InterviewAgent(llm_config, interview_config)

        assert agent.name == "interview"
        assert AgentCapability.INTERVIEW_QUESTIONS in agent.capabilities
        assert AgentCapability.CONVERSATION_FLOW in agent.capabilities
        mock_openai_model.assert_called_once_with("gpt-4o")

    @patch("interviewer.agents.interview.AnthropicModel")
    @patch("interviewer.agents.interview.Agent")
    def test_init_anthropic(self, mock_agent_class, mock_anthropic_model):
        """Test initializing with Anthropic provider."""
        llm_config = LLMConfig(
            provider=LLMProvider.ANTHROPIC, model="claude-sonnet-4-20250514"
        )
        interview_config = InterviewConfig()

        agent = InterviewAgent(llm_config, interview_config)

        assert agent.name == "interview"
        mock_anthropic_model.assert_called_once_with("claude-sonnet-4-20250514")

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_init_state(self, mock_agent_class, mock_openai_model):
        """Test initial state of agent."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()

        agent = InterviewAgent(llm_config, interview_config)

        assert agent.conversation_history == []
        assert agent.pydantic_message_history == []
        assert agent.question_count == 0
        assert agent.current_phase == "introduction"
        assert agent.context_initialized is False


# ============================================================================
# Test can_handle Method
# ============================================================================


class TestInterviewAgentCanHandle:
    """Tests for can_handle method."""

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_can_handle_user_message(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_user_message,
    ):
        """Test high confidence for user messages."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        score = agent.can_handle(sample_user_message, interview_context)

        assert score == 0.9

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_can_handle_system_message(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_system_message,
    ):
        """Test medium confidence for system messages."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        score = agent.can_handle(sample_system_message, interview_context)

        assert score == 0.7

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_can_handle_other_sender(
        self, mock_agent_class, mock_openai_model, interview_context
    ):
        """Test low confidence for other senders."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        message = AgentMessage(
            content="Test",
            message_type=MessageType.USER_RESPONSE,
            metadata={},
            sender="other_agent",
            timestamp=0,
            session_id="test",
        )

        score = agent.can_handle(message, interview_context)

        assert score == 0.3


# ============================================================================
# Test process Method (Mocked)
# ============================================================================


class TestInterviewAgentProcess:
    """Tests for process method with mocked LLM."""

    @pytest.mark.asyncio
    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    async def test_process_returns_response(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_user_message,
    ):
        """Test that process returns a valid AgentResponse."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.output = (
            "That's interesting! Can you tell me more about that experience?"
        )
        mock_result.all_messages = MagicMock(return_value=[])

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_pydantic_agent

        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)
        agent.pydantic_agent = mock_pydantic_agent

        response = await agent.process(sample_user_message, interview_context)

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "interview"
        assert response.confidence == 0.9
        assert (
            "interesting" in response.content.lower()
            or "tell me more" in response.content.lower()
        )

    @pytest.mark.asyncio
    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    async def test_process_start_interview(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_system_message,
    ):
        """Test processing a start_interview system message."""
        mock_result = MagicMock()
        mock_result.output = (
            "Welcome! Let's begin. Tell me about yourself and your background."
        )
        mock_result.all_messages = MagicMock(return_value=[])

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_pydantic_agent

        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)
        agent.pydantic_agent = mock_pydantic_agent

        response = await agent.process(sample_system_message, interview_context)

        assert isinstance(response, AgentResponse)
        assert agent.context_initialized is True
        assert agent.current_phase == "introduction"

    @pytest.mark.asyncio
    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    async def test_process_updates_history(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_user_message,
    ):
        """Test that process updates conversation history."""
        mock_result = MagicMock()
        mock_result.output = "Great answer!"
        mock_result.all_messages = MagicMock(return_value=[])

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_pydantic_agent

        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)
        agent.pydantic_agent = mock_pydantic_agent

        assert len(agent.conversation_history) == 0

        await agent.process(sample_user_message, interview_context)

        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0]["sender"] == "user"

    @pytest.mark.asyncio
    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    async def test_process_handles_error(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_user_message,
    ):
        """Test that process handles errors gracefully."""
        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = AsyncMock(side_effect=Exception("LLM API error"))
        mock_agent_class.return_value = mock_pydantic_agent

        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)
        agent.pydantic_agent = mock_pydantic_agent

        response = await agent.process(sample_user_message, interview_context)

        assert isinstance(response, AgentResponse)
        assert response.confidence == 0.0
        assert "error" in response.metadata


# ============================================================================
# Test Context Building
# ============================================================================


class TestInterviewAgentContext:
    """Tests for context building in process method."""

    @pytest.mark.asyncio
    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    async def test_context_includes_company_role(
        self,
        mock_agent_class,
        mock_openai_model,
        interview_context,
        sample_system_message,
    ):
        """Test that initial context includes company and role."""
        captured_user_content = None

        async def capture_run(user_content, **kwargs):
            nonlocal captured_user_content
            captured_user_content = user_content
            mock_result = MagicMock()
            mock_result.output = "Welcome to the interview!"
            mock_result.all_messages = MagicMock(return_value=[])
            return mock_result

        mock_pydantic_agent = MagicMock()
        mock_pydantic_agent.run = capture_run
        mock_agent_class.return_value = mock_pydantic_agent

        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)
        agent.pydantic_agent = mock_pydantic_agent

        await agent.process(sample_system_message, interview_context)

        # Check that context was built with company/role info
        assert captured_user_content is not None
        assert "TechCorp" in captured_user_content
        assert "Senior ML Engineer" in captured_user_content


# ============================================================================
# Test _build_system_prompt Method
# ============================================================================


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt method."""

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_system_prompt_includes_no_markdown_rule(
        self, mock_agent_class, mock_openai_model
    ):
        """Test that system prompt includes no-markdown rule."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        prompt = agent._build_system_prompt("behavioral")

        assert "markdown" in prompt.lower()
        assert "never" in prompt.lower() or "no" in prompt.lower()

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_system_prompt_behavioral_includes_star(
        self, mock_agent_class, mock_openai_model
    ):
        """Test that behavioral system prompt includes STAR method."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        prompt = agent._build_system_prompt("behavioral")

        assert "STAR" in prompt

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_system_prompt_case_study_includes_scenario(
        self, mock_agent_class, mock_openai_model
    ):
        """Test that case study system prompt includes scenario guidance."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        prompt = agent._build_system_prompt("case_study")

        assert "scenario" in prompt.lower()
        assert "brief" in prompt.lower()


# ============================================================================
# Test _build_initial_context Method
# ============================================================================


class TestBuildInitialContext:
    """Tests for _build_initial_context method."""

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_behavioral_context_mentions_resume(
        self, mock_agent_class, mock_openai_model
    ):
        """Test that behavioral initial context references resume."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig(interview_type=InterviewType.BEHAVIORAL)
        agent = InterviewAgent(llm_config, interview_config)

        deps = InterviewDeps(
            interview_type="behavioral",
            tone="professional",
            difficulty="medium",
            company_name="TestCorp",
            role_title="Data Scientist",
            resume_summary="5 years of Python experience",
            jd_summary="Looking for ML engineer",
            custom_instructions=None,
            conversation_history=[],
            current_phase="introduction",
        )

        context = agent._build_initial_context(deps)

        assert "BEHAVIORAL" in context
        assert "resume" in context.lower() or "past" in context.lower()
        assert "TestCorp" in context
        assert "Data Scientist" in context

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_case_study_context_emphasizes_brevity(
        self, mock_agent_class, mock_openai_model
    ):
        """Test that case study initial context emphasizes brevity."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig(interview_type=InterviewType.CASE_STUDY)
        agent = InterviewAgent(llm_config, interview_config)

        deps = InterviewDeps(
            interview_type="case_study",
            tone="professional",
            difficulty="medium",
            company_name="TestCorp",
            role_title="Data Scientist",
            resume_summary=None,
            jd_summary="Customer churn modeling",
            custom_instructions=None,
            conversation_history=[],
            current_phase="introduction",
        )

        context = agent._build_initial_context(deps)

        assert "CASE STUDY" in context
        # Should emphasize keeping it short
        assert "brief" in context.lower() or "short" in context.lower()
        # Should NOT ask about resume
        assert "DO NOT ask about" in context or "don't ask about" in context.lower()

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_case_study_context_no_markdown_rule(
        self, mock_agent_class, mock_openai_model
    ):
        """Test that case study context includes no-markdown rule."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig(interview_type=InterviewType.CASE_STUDY)
        agent = InterviewAgent(llm_config, interview_config)

        deps = InterviewDeps(
            interview_type="case_study",
            tone="professional",
            difficulty="medium",
            company_name="TestCorp",
            role_title="Data Scientist",
            resume_summary=None,
            jd_summary=None,
            custom_instructions=None,
            conversation_history=[],
            current_phase="introduction",
        )

        context = agent._build_initial_context(deps)

        assert "markdown" in context.lower()


# ============================================================================
# Test _generate_case_study_hint Method
# ============================================================================


class TestGenerateCaseStudyHint:
    """Tests for _generate_case_study_hint method."""

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_hint_with_churn_keyword(self, mock_agent_class, mock_openai_model):
        """Test that churn in JD generates churn-related hint."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        hint = agent._generate_case_study_hint(
            "We need someone to work on customer churn prediction models",
            "TestCorp",
            "Data Scientist",
        )

        assert "churn" in hint.lower()

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_hint_with_forecast_keyword(self, mock_agent_class, mock_openai_model):
        """Test that forecast in JD generates forecasting hint."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        hint = agent._generate_case_study_hint(
            "Experience with demand forecasting and time series",
            "RetailCo",
            "ML Engineer",
        )

        assert "forecast" in hint.lower()

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_hint_with_no_jd(self, mock_agent_class, mock_openai_model):
        """Test hint generation when no JD is provided."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        hint = agent._generate_case_study_hint(None, "TestCorp", "Data Scientist")

        # Should still generate a reasonable hint
        assert "Data Scientist" in hint or "TestCorp" in hint
        assert len(hint) > 20

    @patch("interviewer.agents.interview.OpenAIModel")
    @patch("interviewer.agents.interview.Agent")
    def test_hint_with_multiple_keywords(self, mock_agent_class, mock_openai_model):
        """Test hint with multiple relevant keywords."""
        llm_config = LLMConfig(provider=LLMProvider.OPENAI)
        interview_config = InterviewConfig()
        agent = InterviewAgent(llm_config, interview_config)

        hint = agent._generate_case_study_hint(
            "Work on customer segmentation, A/B testing, and recommendation systems",
            "TechCorp",
            "Senior DS",
        )

        # Should detect multiple themes
        hint_lower = hint.lower()
        keywords_found = sum(
            [
                "segment" in hint_lower,
                "a/b" in hint_lower or "experiment" in hint_lower,
                "recommend" in hint_lower,
            ]
        )
        assert keywords_found >= 2  # Should detect at least 2 themes


# ============================================================================
# Live LLM Tests (Optional)
# ============================================================================


@pytest.mark.live_llm
class TestInterviewAgentLive:
    """
    Live LLM tests - only run when RUN_LIVE_LLM_TESTS=1.

    These tests make actual API calls and consume credits.
    """

    @pytest.mark.asyncio
    async def test_live_openai_response(self, interview_context, sample_system_message):
        """Test actual OpenAI API response."""
        # Skip if no API key
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",  # Use cheaper model for tests
            max_tokens=150,
        )
        interview_config = InterviewConfig(
            interview_type=InterviewType.BEHAVIORAL,
            tone=Tone.PROFESSIONAL,
            difficulty=Difficulty.MEDIUM,
        )

        agent = InterviewAgent(llm_config, interview_config)
        response = await agent.process(sample_system_message, interview_context)

        assert isinstance(response, AgentResponse)
        assert response.confidence > 0
        assert len(response.content) > 10  # Should have meaningful content

    @pytest.mark.asyncio
    async def test_live_conversation_flow(
        self, interview_context, sample_system_message
    ):
        """Test a multi-turn conversation with live LLM."""
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI, model="gpt-4o-mini", max_tokens=150
        )
        interview_config = InterviewConfig()

        agent = InterviewAgent(llm_config, interview_config)

        # Start interview
        response1 = await agent.process(sample_system_message, interview_context)
        assert response1.confidence > 0

        # User response
        user_message = AgentMessage(
            content="I have 5 years of experience as a software engineer, primarily working with Python and machine learning.",
            message_type=MessageType.USER_RESPONSE,
            metadata={},
            sender="user",
            timestamp=0,
            session_id="test",
        )

        response2 = await agent.process(user_message, interview_context)
        assert response2.confidence > 0
        assert len(response2.content) > 10

        # Verify conversation history is maintained
        assert len(agent.conversation_history) == 2
