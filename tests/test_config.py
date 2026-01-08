"""
Tests for interviewer/config.py

Tests configuration validation for LLMConfig and InterviewConfig.
"""

import pytest
from pydantic import ValidationError

from interviewer.config import (
    DEFAULT_MODELS,
    PROVIDER_MODELS,
    Difficulty,
    InterviewConfig,
    InterviewType,
    LLMConfig,
    LLMProvider,
    Tone,
    get_available_models,
    validate_model_for_provider,
)


class TestLLMConfig:
    """Tests for LLMConfig validation and defaults."""

    def test_default_openai_config(self):
        """Test that default config uses OpenAI."""
        config = LLMConfig()
        assert config.provider == LLMProvider.OPENAI
        assert config.temperature == 0.7
        assert config.max_tokens == 1000

    def test_openai_config_with_model(self, openai_llm_config):
        """Test OpenAI config with specified model."""
        assert openai_llm_config.provider == LLMProvider.OPENAI
        assert openai_llm_config.model == "gpt-4o"

    def test_anthropic_config_with_model(self, anthropic_llm_config):
        """Test Anthropic config with specified model."""
        assert anthropic_llm_config.provider == LLMProvider.ANTHROPIC
        assert anthropic_llm_config.model == "claude-sonnet-4-20250514"

    def test_anthropic_default_model_assignment(self):
        """Test that Anthropic provider gets correct default model when gpt-3.5-turbo is specified."""
        config = LLMConfig(provider=LLMProvider.ANTHROPIC)
        # When provider is anthropic but model is default gpt-3.5-turbo, it should switch
        assert config.model == DEFAULT_MODELS[LLMProvider.ANTHROPIC]

    def test_temperature_bounds_valid(self):
        """Test valid temperature values."""
        config = LLMConfig(temperature=0.0)
        assert config.temperature == 0.0

        config = LLMConfig(temperature=2.0)
        assert config.temperature == 2.0

        config = LLMConfig(temperature=1.0)
        assert config.temperature == 1.0

    def test_temperature_bounds_invalid_low(self):
        """Test that temperature below 0 raises validation error."""
        with pytest.raises(ValidationError):
            LLMConfig(temperature=-0.1)

    def test_temperature_bounds_invalid_high(self):
        """Test that temperature above 2 raises validation error."""
        with pytest.raises(ValidationError):
            LLMConfig(temperature=2.1)

    def test_max_tokens_positive(self):
        """Test valid max_tokens values."""
        config = LLMConfig(max_tokens=1)
        assert config.max_tokens == 1

        config = LLMConfig(max_tokens=4000)
        assert config.max_tokens == 4000

    def test_max_tokens_invalid(self):
        """Test that max_tokens <= 0 raises validation error."""
        with pytest.raises(ValidationError):
            LLMConfig(max_tokens=0)

        with pytest.raises(ValidationError):
            LLMConfig(max_tokens=-100)


class TestInterviewConfig:
    """Tests for InterviewConfig validation."""

    def test_default_interview_config(self):
        """Test default interview configuration."""
        config = InterviewConfig()
        assert config.interview_type == InterviewType.BEHAVIORAL
        assert config.tone == Tone.PROFESSIONAL
        assert config.difficulty == Difficulty.MEDIUM

    def test_custom_interview_config(self, interview_config):
        """Test custom interview configuration."""
        assert interview_config.interview_type == InterviewType.BEHAVIORAL
        assert interview_config.tone == Tone.PROFESSIONAL
        assert interview_config.difficulty == Difficulty.MEDIUM

    def test_all_interview_types(self):
        """Test all interview type values."""
        for interview_type in InterviewType:
            config = InterviewConfig(interview_type=interview_type)
            assert config.interview_type == interview_type

    def test_all_tones(self):
        """Test all tone values."""
        for tone in Tone:
            config = InterviewConfig(tone=tone)
            assert config.tone == tone

    def test_all_difficulties(self):
        """Test all difficulty values."""
        for difficulty in Difficulty:
            config = InterviewConfig(difficulty=difficulty)
            assert config.difficulty == difficulty

    def test_case_study_config(self):
        """Test case study interview configuration."""
        config = InterviewConfig(
            interview_type=InterviewType.CASE_STUDY,
            tone=Tone.CHALLENGING,
            difficulty=Difficulty.HARD,
        )
        assert config.interview_type == InterviewType.CASE_STUDY
        assert config.tone == Tone.CHALLENGING
        assert config.difficulty == Difficulty.HARD


class TestProviderModels:
    """Tests for provider model utilities."""

    def test_openai_models_exist(self):
        """Test that OpenAI has models defined."""
        models = PROVIDER_MODELS[LLMProvider.OPENAI]
        assert len(models) > 0
        assert "gpt-4o" in models

    def test_anthropic_models_exist(self):
        """Test that Anthropic has models defined."""
        models = PROVIDER_MODELS[LLMProvider.ANTHROPIC]
        assert len(models) > 0

    def test_get_available_models_openai(self):
        """Test get_available_models for OpenAI."""
        models = get_available_models(LLMProvider.OPENAI)
        assert isinstance(models, list)
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models

    def test_get_available_models_anthropic(self):
        """Test get_available_models for Anthropic."""
        models = get_available_models(LLMProvider.ANTHROPIC)
        assert isinstance(models, list)
        assert len(models) > 0

    def test_validate_model_for_provider_valid(self):
        """Test model validation with valid model."""
        assert validate_model_for_provider(LLMProvider.OPENAI, "gpt-4o") is True

    def test_validate_model_for_provider_invalid(self):
        """Test model validation with invalid model."""
        assert (
            validate_model_for_provider(LLMProvider.OPENAI, "nonexistent-model")
            is False
        )

    def test_validate_model_wrong_provider(self):
        """Test model validation with model from wrong provider."""
        # OpenAI model should not be valid for Anthropic
        assert validate_model_for_provider(LLMProvider.ANTHROPIC, "gpt-4o") is False


class TestDefaultModels:
    """Tests for default model configuration."""

    def test_default_models_defined(self):
        """Test that default models are defined for all providers."""
        for provider in LLMProvider:
            assert provider in DEFAULT_MODELS
            assert DEFAULT_MODELS[provider] in PROVIDER_MODELS[provider]

    def test_openai_default_model(self):
        """Test OpenAI default model."""
        assert DEFAULT_MODELS[LLMProvider.OPENAI] == "gpt-4o"

    def test_anthropic_default_model(self):
        """Test Anthropic default model."""
        assert DEFAULT_MODELS[LLMProvider.ANTHROPIC] == "claude-sonnet-4-20250514"
