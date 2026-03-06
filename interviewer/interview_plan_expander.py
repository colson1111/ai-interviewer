"""
Interview plan expander for the Custom interview type.

Expands user-provided custom instructions (e.g., interviewer overviews) into a fuller
executable interview plan using an LLM. Considers persona, tangential directions,
and resume/JD context.
"""

import logging
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

from .config import LLMConfig
from .cost_tracker import CostTracker, estimate_tokens_detailed
from .prompts import CUSTOM_INTERVIEW_EXPANSION_PROMPT

logger = logging.getLogger(__name__)

# Truncation limits for expansion prompt (keeps cost and latency predictable)
RESUME_MAX_CHARS = 1500
JD_MAX_CHARS = 2000


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding ellipsis if cut."""
    if not text or len(text) <= max_chars:
        return (text or "").strip()
    return text[: max_chars - 3].rstrip() + "..."


async def expand_custom_interview_plan(
    custom_instructions: str,
    resume_text: str,
    job_description: str,
    company_name: Optional[str],
    role_title: Optional[str],
    llm_config: LLMConfig,
    cost_tracker: Optional[CostTracker] = None,
) -> str:
    """
    Expand custom interview instructions into a fuller executable plan.

    Roleplays as the interviewer described, considers tangential directions,
    and personalizes to resume/JD when provided.

    Args:
        custom_instructions: User's raw instructions (e.g., interviewer overview)
        resume_text: Candidate resume (truncated to RESUME_MAX_CHARS)
        job_description: Job description (truncated to JD_MAX_CHARS)
        company_name: Optional company name
        role_title: Optional role title
        llm_config: LLM provider and model configuration
        cost_tracker: Optional; when provided, tracks expansion cost

    Returns:
        Expanded interview plan as plain text. On any expansion failure, returns
        custom_instructions (or "" if empty) so the interview can proceed.
    """
    instructions = (custom_instructions or "").strip()
    if not instructions:
        return ""

    resume = _truncate(resume_text or "", RESUME_MAX_CHARS)
    jd = _truncate(job_description or "", JD_MAX_CHARS)

    user_prompt = f"""INTERVIEWER OVERVIEW (expand this into a fuller plan):
{instructions}
"""

    if company_name:
        user_prompt += f"\nCompany: {company_name}"
    if role_title:
        user_prompt += f"\nRole: {role_title}"

    if resume:
        user_prompt += f"""

CANDIDATE RESUME (use to personalize the plan):
{resume}
"""

    if jd:
        user_prompt += f"""

JOB DESCRIPTION (use to align focus areas):
{jd}
"""

    user_prompt += """

Expand the above into a detailed interview plan. Output plain prose only, no markdown."""

    try:
        if llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            raise ValueError(f"Unsupported provider: {llm_config.provider}")

        agent = Agent(
            model,
            system_prompt=CUSTOM_INTERVIEW_EXPANSION_PROMPT,
        )

        result = await agent.run(user_prompt)
        output = result.output if hasattr(result, "output") else str(result)
        plan = (output or "").strip()

        if cost_tracker:
            input_tokens = estimate_tokens_detailed(user_prompt)
            output_tokens = estimate_tokens_detailed(plan)
            cost_tracker.add_text_call(
                llm_config.provider.value,
                llm_config.model,
                input_tokens,
                output_tokens,
            )

        return plan if plan else instructions

    except Exception as e:
        logger.warning(
            "Interview plan expansion failed, using raw instructions: %s",
            e,
            exc_info=True,
        )
        return instructions
