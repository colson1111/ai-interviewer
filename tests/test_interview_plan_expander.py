"""
Tests for interviewer/interview_plan_expander.py

Tests the custom interview plan expansion with mocked LLM.
"""

import pytest
from unittest.mock import AsyncMock, patch

from interviewer.config import LLMConfig, LLMProvider
from interviewer.cost_tracker import CostTracker
from interviewer.interview_plan_expander import (
    RESUME_MAX_CHARS,
    JD_MAX_CHARS,
    expand_custom_interview_plan,
)


@pytest.fixture
def llm_config():
    """Standard LLM config for tests."""
    return LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o")


@pytest.fixture
def cost_tracker():
    """Cost tracker for testing."""
    return CostTracker(session_id="test_session")


class TestExpandCustomInterviewPlan:
    """Tests for expand_custom_interview_plan."""

    @pytest.mark.asyncio
    @patch("interviewer.interview_plan_expander.Agent")
    @patch("interviewer.interview_plan_expander.OpenAIModel")
    async def test_expansion_returns_plan(
        self, mock_openai_model, mock_agent_class, llm_config, cost_tracker
    ):
        """Test that expansion returns the LLM-generated plan."""
        mock_result = AsyncMock()
        mock_result.output = "Interview plan: Focus on metrics, A/B tests, and product thinking."
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        plan = await expand_custom_interview_plan(
            custom_instructions="Ravi assesses product growth and metrics",
            resume_text="5 years as data scientist",
            job_description="ML Engineer at TechCo",
            company_name="TechCo",
            role_title="ML Engineer",
            llm_config=llm_config,
            cost_tracker=cost_tracker,
        )

        assert "metrics" in plan.lower() or "A/B" in plan
        mock_agent_instance.run.assert_called_once()
        assert len(cost_tracker.calls) == 1

    @pytest.mark.asyncio
    async def test_empty_instructions_returns_empty(self, llm_config):
        """Test that empty instructions return empty string without LLM call."""
        with patch("interviewer.interview_plan_expander.Agent") as mock_agent:
            plan = await expand_custom_interview_plan(
                custom_instructions="",
                resume_text="",
                job_description="",
                company_name=None,
                role_title=None,
                llm_config=llm_config,
            )

            assert plan == ""
            mock_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_empty(self, llm_config):
        """Test that whitespace-only instructions return empty without LLM call."""
        with patch("interviewer.interview_plan_expander.Agent") as mock_agent:
            plan = await expand_custom_interview_plan(
                custom_instructions="   \n\t  ",
                resume_text="",
                job_description="",
                company_name=None,
                role_title=None,
                llm_config=llm_config,
            )

            assert plan == ""
            mock_agent.assert_not_called()

    @pytest.mark.asyncio
    @patch("interviewer.interview_plan_expander.Agent")
    @patch("interviewer.interview_plan_expander.OpenAIModel")
    async def test_fallback_on_error(
        self, mock_openai_model, mock_agent_class, llm_config
    ):
        """Test that expansion falls back to raw instructions on LLM failure."""
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("Rate limit"))
        mock_agent_class.return_value = mock_agent_instance

        raw = "Ravi will assess your product growth skills"
        plan = await expand_custom_interview_plan(
            custom_instructions=raw,
            resume_text="",
            job_description="",
            company_name=None,
            role_title=None,
            llm_config=llm_config,
        )

        assert plan == raw

    @pytest.mark.asyncio
    @patch("interviewer.interview_plan_expander.Agent")
    @patch("interviewer.interview_plan_expander.OpenAIModel")
    async def test_truncates_long_resume(
        self, mock_openai_model, mock_agent_class, llm_config
    ):
        """Test that long resume is truncated before passing to LLM."""
        mock_result = AsyncMock()
        mock_result.output = "Plan"
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        long_resume = "x" * (RESUME_MAX_CHARS + 500)
        await expand_custom_interview_plan(
            custom_instructions="Assess metrics",
            resume_text=long_resume,
            job_description="",
            company_name=None,
            role_title=None,
            llm_config=llm_config,
        )

        call_args = mock_agent_instance.run.call_args[0][0]
        assert "..." in call_args or len(call_args) < len(long_resume) + 500

    @pytest.mark.asyncio
    @patch("interviewer.interview_plan_expander.Agent")
    @patch("interviewer.interview_plan_expander.OpenAIModel")
    async def test_works_without_cost_tracker(
        self, mock_openai_model, mock_agent_class, llm_config
    ):
        """Test that expansion works when cost_tracker is not provided."""
        mock_result = AsyncMock()
        mock_result.output = "Generated plan"
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        plan = await expand_custom_interview_plan(
            custom_instructions="Test",
            resume_text="",
            job_description="",
            company_name=None,
            role_title=None,
            llm_config=llm_config,
            cost_tracker=None,
        )

        assert plan == "Generated plan"


class TestExpansionConstants:
    """Tests for expansion module constants."""

    def test_resume_max_chars_reasonable(self):
        """Test that resume truncation limit is reasonable."""
        assert RESUME_MAX_CHARS >= 1000
        assert RESUME_MAX_CHARS <= 5000

    def test_jd_max_chars_reasonable(self):
        """Test that JD truncation limit is reasonable."""
        assert JD_MAX_CHARS >= 1000
        assert JD_MAX_CHARS <= 5000
