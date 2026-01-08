"""
Cost tracking for LLM API usage during interviews.
Helps monitor spending on OpenAI, Anthropic, and other services.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class APICall:
    """Record of a single API call."""

    timestamp: datetime
    provider: str  # 'openai', 'anthropic'
    service: str  # 'gpt-4', 'claude-3', 'whisper', 'tts'
    input_tokens: int = 0
    output_tokens: int = 0
    audio_seconds: float = 0.0
    characters: int = 0
    cost_usd: float = 0.0


@dataclass
class CostTracker:
    """Track costs across an interview session."""

    session_id: str
    calls: List[APICall] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)

    # Current pricing (as of 2024 - these should be updated periodically)
    PRICING = {
        "openai": {
            "gpt-4o": {"input": 0.0025, "output": 0.01},  # per 1K tokens
            "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},  # per 1K tokens
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},  # per 1K tokens
            "whisper-1": 0.006,  # per minute
            "tts-1": 0.015,  # per 1K characters
            "tts-1-hd": 0.030,  # per 1K characters
        },
        "anthropic": {
            "claude-3-5-sonnet-20241022": {
                "input": 0.003,
                "output": 0.015,
            },  # per 1K tokens
            "claude-3-5-haiku-20241022": {
                "input": 0.001,
                "output": 0.005,
            },  # per 1K tokens
            "claude-3-opus-20240229": {
                "input": 0.015,
                "output": 0.075,
            },  # per 1K tokens
        },
    }

    def add_text_call(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Add a text generation API call and return estimated cost."""
        cost = self._calculate_text_cost(provider, model, input_tokens, output_tokens)

        call = APICall(
            timestamp=datetime.now(),
            provider=provider,
            service=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self.calls.append(call)
        return cost

    def add_whisper_call(self, audio_seconds: float) -> float:
        """Add a Whisper transcription call and return estimated cost."""
        audio_minutes = audio_seconds / 60
        cost = audio_minutes * self.PRICING["openai"]["whisper-1"]

        call = APICall(
            timestamp=datetime.now(),
            provider="openai",
            service="whisper-1",
            audio_seconds=audio_seconds,
            cost_usd=cost,
        )
        self.calls.append(call)
        return cost

    def add_tts_call(self, characters: int, model: str = "tts-1") -> float:
        """Add a TTS synthesis call and return estimated cost."""
        cost = (characters / 1000) * self.PRICING["openai"][model]

        call = APICall(
            timestamp=datetime.now(),
            provider="openai",
            service=model,
            characters=characters,
            cost_usd=cost,
        )
        self.calls.append(call)
        return cost

    def _calculate_text_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost for text generation."""
        if provider not in self.PRICING or model not in self.PRICING[provider]:
            return 0.0  # Unknown model, can't calculate

        pricing = self.PRICING[provider][model]
        if isinstance(pricing, dict):
            input_cost = (input_tokens / 1000) * pricing["input"]
            output_cost = (output_tokens / 1000) * pricing["output"]
            return input_cost + output_cost
        else:
            # Flat rate pricing
            return (input_tokens + output_tokens) / 1000 * pricing

    def get_total_cost(self) -> float:
        """Get total estimated cost for the session."""
        return sum(call.cost_usd for call in self.calls)

    def get_cost_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Get cost breakdown by provider and service."""
        breakdown = {}

        for call in self.calls:
            if call.provider not in breakdown:
                breakdown[call.provider] = {}
            if call.service not in breakdown[call.provider]:
                breakdown[call.provider][call.service] = 0.0
            breakdown[call.provider][call.service] += call.cost_usd

        return breakdown

    def get_token_stats(self) -> Dict[str, int]:
        """Get total token usage statistics."""
        total_input = sum(call.input_tokens for call in self.calls)
        total_output = sum(call.output_tokens for call in self.calls)
        total_audio_minutes = sum(call.audio_seconds for call in self.calls) / 60
        total_characters = sum(call.characters for call in self.calls)

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "audio_minutes": round(total_audio_minutes, 2),
            "tts_characters": total_characters,
        }

    def get_summary(self) -> Dict:
        """Get a complete summary for display."""
        duration = datetime.now() - self.start_time

        return {
            "session_id": self.session_id,
            "duration_minutes": round(duration.total_seconds() / 60, 1),
            "total_cost_usd": round(self.get_total_cost(), 4),
            "total_calls": len(self.calls),
            "token_stats": self.get_token_stats(),
            "cost_breakdown": self.get_cost_breakdown(),
            "last_updated": datetime.now().isoformat(),
        }


# Simple token estimation (rough approximation)
def estimate_tokens(text: str) -> int:
    """
    Rough token estimation for text.
    Real token counting would require tiktoken or similar,
    but this gives a reasonable approximation.
    """
    # Rough approximation: 1 token ≈ 0.75 words ≈ 4 characters
    # This is a simplification but good enough for cost estimation
    return max(1, len(text) // 4)


def estimate_tokens_detailed(text: str) -> int:
    """
    More detailed token estimation.
    Still an approximation but closer to actual tokenization.
    """
    import re

    # Split on word boundaries and count
    words = re.findall(r"\w+|[^\w\s]", text)

    # Rough conversion: most words are 1 token, punctuation is often 1 token
    # Special tokens, numbers, etc. might be multiple tokens
    token_count = 0
    for word in words:
        if word.isalpha():
            # Regular words: usually 1 token, longer words might be 2+
            if len(word) <= 4:
                token_count += 1
            elif len(word) <= 8:
                token_count += 1.3
            else:
                token_count += 1.6
        elif word.isdigit():
            # Numbers can be multiple tokens
            token_count += max(1, len(word) // 3)
        else:
            # Punctuation, symbols
            token_count += 1

    return max(1, int(token_count))
