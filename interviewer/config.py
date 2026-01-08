"""Configuration for the interviewer application."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class LLMProvider(str, Enum):
    """Available LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class InterviewType(str, Enum):
    """Available interview types."""

    BEHAVIORAL = "behavioral"  # Past experiences, project walkthroughs, STAR method
    CASE_STUDY = "case_study"  # Hypothetical problem-solving scenarios


class Tone(str, Enum):
    """Available interviewer tones."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CHALLENGING = "challenging"
    SUPPORTIVE = "supportive"


class Difficulty(str, Enum):
    """Available difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# Available models for each provider
PROVIDER_MODELS: Dict[LLMProvider, List[str]] = {
    LLMProvider.OPENAI: [
        # Latest models
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ],
    LLMProvider.ANTHROPIC: [
        # Latest models
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ],
}

# Default models for each provider
DEFAULT_MODELS: Dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
}


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    provider: LLMProvider = LLMProvider.OPENAI
    api_key: Optional[str] = None
    model: str = Field(default="gpt-3.5-turbo")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)

    @model_validator(mode="after")
    def set_default_model(self) -> "LLMConfig":
        """Set default model for provider if not specified."""
        if self.model == "gpt-3.5-turbo" and self.provider != LLMProvider.OPENAI:
            self.model = DEFAULT_MODELS[self.provider]
        return self


class InterviewConfig(BaseModel):
    """Configuration for interview behavior."""

    interview_type: InterviewType = InterviewType.BEHAVIORAL
    tone: Tone = Tone.PROFESSIONAL
    difficulty: Difficulty = Difficulty.MEDIUM


def get_available_models(provider: LLMProvider) -> List[str]:
    """Get available models for a provider."""
    return PROVIDER_MODELS.get(provider, [])


def validate_model_for_provider(provider: LLMProvider, model: str) -> bool:
    """Check if model is valid for the given provider."""
    return model in PROVIDER_MODELS.get(provider, [])
