"""Core interview agent for general interview questions and conversation flow.

This agent handles the primary interview conversation, using pydantic-ai for structured interaction.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel

from ..config import InterviewConfig, LLMConfig
from ..core import AgentCapability, AgentMessage, AgentResponse, InterviewContext
from ..prompts import INTERVIEW_TYPE_GUIDANCE
from .base import BaseInterviewAgent


@dataclass
class InterviewDeps:
    interview_type: str
    tone: str
    difficulty: str
    company_name: Optional[str]
    role_title: Optional[str]
    resume_summary: Optional[str]  # Summary/key points from resume
    jd_summary: Optional[str]  # Summary/key points from JD
    custom_instructions: Optional[str]  # Custom instructions from user
    conversation_history: List[Dict[str, Any]]
    current_phase: str


def interview_system_prompt(ctx: RunContext[InterviewDeps]) -> str:
    """Dynamic system prompt generation based on context."""
    deps = ctx.deps

    # Build context about the role/company
    role_context = ""
    if deps.company_name:
        role_context += f"Company: {deps.company_name}\n"
    if deps.role_title:
        role_context += f"Role: {deps.role_title}\n"

    prompt = f"""
You are an expert interviewer conducting a {deps.interview_type} interview.

INTERVIEW CONTEXT:
Tone: {deps.tone}
Difficulty: {deps.difficulty}
{role_context}

YOUR ROLE:
- Conduct a professional, realistic interview.
- Ask relevant follow-up questions based on the candidate's responses.
- Dig deeper into their experience using specific examples they provide.
- Maintain the specified tone throughout.
- If this is a behavioral interview, use STAR method probes.
- If this is a case study, guide them through the problem structuredly.

GUIDELINES:
- Keep your responses concise (usually 1-3 sentences/questions).
- Do NOT repeat yourself.
- Do NOT be overly encouraging or repetitive with praise.
- Move the interview forward with each turn.
- If the user asks for clarification, provide it clearly.
- If the user is stuck, offer a small hint but don't give the answer.

CURRENT PHASE: {deps.current_phase}
"""
    return prompt


class InterviewAgent(BaseInterviewAgent):
    """
    Primary interview agent responsible for conducting the actual interview.

    Uses pydantic-ai to manage the conversation flow and generation.
    """

    def __init__(self, llm_config: LLMConfig, interview_config: InterviewConfig):
        """Initialize the interview agent with LLM and interview configuration."""
        super().__init__(
            name="interview",
            capabilities=[
                AgentCapability.INTERVIEW_QUESTIONS,
                AgentCapability.CONVERSATION_FLOW,
            ],
        )
        self.llm_config = llm_config
        self.interview_config = interview_config
        self.conversation_history = []
        self.pydantic_message_history: List[Any] = []  # For pydantic-ai message history
        self.question_count = 0
        self.current_phase = "introduction"
        self.context_initialized = False  # Track if we've set up the initial context

        # Track interview progress and candidate information
        self.candidate_name = None
        self.interview_start_time = time.time()
        self.last_question_time = None

        # Initialize the LLM model and agent
        self._initialize_agent(llm_config, interview_config)

    def _build_system_prompt(self, interview_type: str) -> str:
        """Build interview-type-specific system prompt."""
        # Get the detailed guidance for this interview type
        type_guidance = INTERVIEW_TYPE_GUIDANCE.get(
            interview_type, INTERVIEW_TYPE_GUIDANCE["behavioral"]
        )

        return f"""You are an expert interviewer conducting a professional interview.

CRITICAL: You will receive context about the role, company, candidate background, and job requirements in your first message. 
Remember this context throughout the ENTIRE interview.

{type_guidance}

GENERAL GUIDELINES:
- Keep your responses concise (usually 1-3 sentences/questions).
- Do NOT repeat yourself.
- Do NOT be overly encouraging or repetitive with praise.
- Move the interview forward with each turn.
- React naturally - question mismatches, probe vague claims, show curiosity about strengths.
"""

    def _build_initial_context(self, deps: InterviewDeps) -> str:
        """Build the initial context message based on interview type."""
        company = deps.company_name or "the company"
        role = deps.role_title or "this role"

        # Common context header
        context_parts = [
            "=== INTERVIEW CONTEXT ===",
            f"Company: {deps.company_name or 'Not specified'}",
            f"Role: {deps.role_title or 'Not specified'}",
            f"Interview Type: {deps.interview_type}",
            f"Tone: {deps.tone}",
            f"Difficulty: {deps.difficulty}",
        ]

        if deps.interview_type == "behavioral":
            # BEHAVIORAL: Focus on resume and past experiences
            context_parts.append("\n=== BEHAVIORAL INTERVIEW INSTRUCTIONS ===")
            context_parts.append(
                "This is a BEHAVIORAL interview. Focus ONLY on the candidate's "
                "PAST experiences and work history."
            )
            context_parts.append("- Ask 'Tell me about a time when...' questions")
            context_parts.append(
                "- Reference their resume to ask about specific projects"
            )
            context_parts.append(
                "- Probe how their experience aligns with the job requirements"
            )
            context_parts.append(
                "- DO NOT present hypothetical scenarios or case studies"
            )

            if deps.resume_summary:
                context_parts.append(
                    f"\n=== CANDIDATE RESUME (use this to ask specific questions) ===\n"
                    f"{deps.resume_summary}"
                )

            if deps.jd_summary:
                context_parts.append(
                    f"\n=== JOB REQUIREMENTS (align questions to these) ===\n"
                    f"{deps.jd_summary}"
                )

            context_parts.append("\n=== YOUR TASK ===")
            context_parts.append(
                f"Begin the behavioral interview for {role} at {company}. "
                "Start with a warm introduction and ask about their background or "
                "a specific experience from their resume that's relevant to this role."
            )

        elif deps.interview_type == "case_study":
            # CASE STUDY: Generate hypothetical scenario
            context_parts.append("\n=== CASE STUDY INTERVIEW INSTRUCTIONS ===")
            context_parts.append(
                "This is a CASE STUDY interview. Present a HYPOTHETICAL business "
                "problem for the candidate to solve."
            )
            context_parts.append(
                "- DO NOT ask about the candidate's past projects or resume"
            )
            context_parts.append("- Create a scenario relevant to the company and role")
            context_parts.append("- Guide them through structured problem-solving")
            context_parts.append("- Probe their analytical thinking and approach")

            if deps.jd_summary:
                context_parts.append(
                    f"\n=== JOB REQUIREMENTS (design case study around these) ===\n"
                    f"{deps.jd_summary}"
                )

            # Generate case study scenario hints based on JD keywords
            scenario_hint = self._generate_case_study_hint(
                deps.jd_summary, company, role
            )
            context_parts.append(
                f"\n=== SUGGESTED SCENARIO THEMES ===\n{scenario_hint}"
            )

            context_parts.append("\n=== YOUR TASK ===")
            context_parts.append(
                f"Begin the case study interview for {role} at {company}. "
                "Present a realistic hypothetical scenario relevant to the role. "
                "For example: 'Imagine you're a [role] at [company]. "
                "You've been asked to [specific business problem]...'"
            )

        else:
            # Fallback to behavioral
            context_parts.append("\n=== YOUR TASK ===")
            context_parts.append(
                "Begin the interview with an appropriate opening question."
            )

        if deps.custom_instructions:
            context_parts.append(
                f"\n=== SPECIAL INSTRUCTIONS ===\n{deps.custom_instructions}"
            )

        return "\n".join(context_parts)

    def _generate_case_study_hint(
        self, jd_summary: Optional[str], company: str, role: str
    ) -> str:
        """Generate case study scenario hints based on JD keywords."""
        if not jd_summary:
            return (
                f"Design a case study relevant to a {role} at {company}. "
                "Consider common challenges in this domain."
            )

        jd_lower = jd_summary.lower()
        hints = []

        # Detect keywords and suggest relevant case studies
        if any(kw in jd_lower for kw in ["churn", "retention", "customer lifetime"]):
            hints.append("Customer churn prediction or retention strategy")
        if any(kw in jd_lower for kw in ["segment", "cluster", "persona"]):
            hints.append("Customer segmentation or targeting")
        if any(kw in jd_lower for kw in ["forecast", "predict", "demand"]):
            hints.append("Demand forecasting or sales prediction")
        if any(kw in jd_lower for kw in ["recommend", "personalization"]):
            hints.append("Recommendation system or personalization")
        if any(kw in jd_lower for kw in ["a/b test", "experiment", "causal"]):
            hints.append("Experiment design or A/B testing analysis")
        if any(kw in jd_lower for kw in ["fraud", "anomaly", "detection"]):
            hints.append("Fraud detection or anomaly identification")
        if any(kw in jd_lower for kw in ["marketing", "campaign", "attribution"]):
            hints.append("Marketing campaign optimization or attribution")
        if any(kw in jd_lower for kw in ["pricing", "revenue", "optimization"]):
            hints.append("Pricing strategy or revenue optimization")
        if any(kw in jd_lower for kw in ["nlp", "text", "sentiment"]):
            hints.append("Text analysis or sentiment classification")
        if any(kw in jd_lower for kw in ["supply chain", "inventory", "logistics"]):
            hints.append("Supply chain optimization or inventory management")

        if hints:
            return (
                f"Based on the job description, consider these case study themes:\n"
                + "\n".join(f"- {h}" for h in hints[:3])
            )
        else:
            return (
                f"Design a realistic business problem that a {role} at {company} "
                "might encounter. Focus on data-driven problem solving."
            )

    def _initialize_agent(
        self, llm_config: LLMConfig, interview_config: InterviewConfig
    ):
        """Initialize or reinitialize the pydantic-ai agent."""
        if llm_config.provider.value == "openai":
            model = OpenAIModel(llm_config.model)
        elif llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            raise ValueError(f"Unsupported provider: {llm_config.provider}")

        # Build interview-type-specific system prompt
        system_prompt = self._build_system_prompt(interview_config.interview_type.value)

        # Create Pydantic-AI agent with interview-type-specific prompt
        self.pydantic_agent = Agent(
            model,
            deps_type=InterviewDeps,
            system_prompt=system_prompt,
        )

    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Determine if this agent can handle the message."""
        # High confidence for user messages (candidate responses)
        if message.sender == "user":
            return 0.9
        # Medium confidence for system messages (interview setup)
        if message.sender == "system":
            return 0.7
        return 0.3

    async def process(
        self, message: AgentMessage, context: InterviewContext
    ) -> AgentResponse:
        """Process the message using Pydantic AI agent."""

        # Update conversation history
        self.conversation_history.append(
            {
                "timestamp": time.time(),
                "sender": message.sender,
                "content": message.content,
            }
        )

        # Prepare dependencies with simple types
        deps = InterviewDeps(
            interview_type=context.interview_config.interview_type.value,
            tone=context.interview_config.tone.value,
            difficulty=context.interview_config.difficulty.value,
            company_name=context.candidate_info.company_name,
            role_title=context.candidate_info.role_title,
            resume_summary=context.candidate_info.resume_text[:1500]
            if context.candidate_info.resume_text
            else None,  # First 1500 chars
            jd_summary=context.candidate_info.job_description[:1500]
            if context.candidate_info.job_description
            else None,  # First 1500 chars
            custom_instructions=context.candidate_info.custom_instructions,
            conversation_history=self.conversation_history,
            current_phase=self.current_phase,
        )

        try:
            # Handle system messages (start interview) specially - build comprehensive context
            user_content = message.content

            if (
                message.sender == "system"
                and "start_interview" in message.content.lower()
                and not self.context_initialized
            ):
                # Build rich initial context based on interview type
                user_content = self._build_initial_context(deps)
                self.current_phase = "introduction"
                self.context_initialized = True

            # Run the agent with full message history to maintain context
            result = await self.pydantic_agent.run(
                user_content,
                deps=deps,
                message_history=self.pydantic_message_history
                if self.pydantic_message_history
                else None,
            )

            # Extract the response content
            response_content = (
                result.output if hasattr(result, "output") else str(result)
            )

            # Update pydantic-ai message history to maintain context for next turn
            # The result contains the full message exchange
            if hasattr(result, "all_messages"):
                self.pydantic_message_history = result.all_messages()
            elif hasattr(result, "messages"):
                self.pydantic_message_history = result.messages

            # Update our internal context
            context.add_turn(
                {
                    "timestamp": time.time(),
                    "speaker": "interviewer",
                    "content": response_content,
                    "message_type": "question",
                }
            )

            return self._create_response(
                content=response_content,
                confidence=0.9,
                metadata={"phase": self.current_phase},
            )

        except Exception as e:
            print(f"Error in InterviewAgent: {e}")
            import traceback

            traceback.print_exc()
            return self._create_response(
                content="I apologize, but I encountered an error. Could you please repeat that?",
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def update_configuration(
        self, llm_config: LLMConfig, interview_config: InterviewConfig
    ):
        """Update LLM and interview configuration."""
        self.llm_config = llm_config
        self.interview_config = interview_config

        # Reset message history when reconfiguring
        self.pydantic_message_history = []
        self.context_initialized = False

        # Reinitialize agent with new configuration
        self._initialize_agent(llm_config, interview_config)
