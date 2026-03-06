"""Core interview agent for general interview questions and conversation flow.

This agent handles the primary interview conversation, using pydantic-ai for structured interaction.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from ..config import InterviewConfig, LLMConfig
from ..core import AgentCapability, AgentMessage, AgentResponse, InterviewContext
from ..prompts import build_system_prompt
from .base import BaseInterviewAgent


@dataclass
class InterviewDeps:
    interview_type: str
    tone: str
    difficulty: str
    company_name: Optional[str]
    role_title: Optional[str]
    resume_summary: Optional[str]  # Summary/key points from resume (first 1500 chars)
    jd_summary: Optional[str]  # Full job description when provided; used as primary evaluation lens
    custom_instructions: Optional[str]  # Custom instructions from user
    conversation_history: List[Dict[str, Any]]
    current_phase: str
    custom_interview_plan: Optional[str] = None  # LLM-expanded plan for custom type
    wrap_up_triggered: bool = False  # Recording time limit reached; start wrapping up


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
- Ask ONE question per turn. At most two if they are tightly related. Never more.
- Keep your responses concise (usually 1-3 sentences total).
- Do NOT repeat yourself.
- Do NOT be overly encouraging or repetitive with praise.
- Move the interview forward with each turn.
- If the user asks for clarification, provide it clearly.
- If the user is stuck, offer a small hint but don't give the answer.
- When the candidate checks in mid-response ("Does that make sense?", "Am I on track?") or asks a quick question: answer briefly and invite them to continue. Do NOT ask a follow-up question—let them finish their thought.

CURRENT PHASE: {deps.current_phase}
"""
    if deps.wrap_up_triggered:
        prompt += """
WRAP-UP PHASE: We've reached the recording time limit. Give a brief final response to what the candidate just said, then transition to asking "Do you have any questions for me?" Keep the conversation open—answer their questions naturally. They will end the interview when ready. Do not force-close; let them wrap up on their own terms.
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

    def _build_system_prompt(
        self, interview_type: str, tone: str, difficulty: str
    ) -> str:
        """Build interview-type-specific system prompt using prompts module."""
        return build_system_prompt(interview_type, tone, difficulty)

    def _build_initial_context(self, deps: InterviewDeps) -> str:
        """Build the initial context message based on interview type and available docs (JD / resume / neither)."""
        company = deps.company_name or "the company"
        role = deps.role_title or "this role"
        has_jd = bool(deps.jd_summary)
        has_resume = bool(deps.resume_summary)

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
            context_parts.append("\n=== BEHAVIORAL INTERVIEW INSTRUCTIONS ===")
            context_parts.append(
                "This is a BEHAVIORAL interview. Focus ONLY on the candidate's "
                "PAST experiences and work history."
            )
            context_parts.append(
                "- Probe past experiences using varied phrasings; don't rely on a single question template."
            )
            context_parts.append(
                "- DO NOT present hypothetical scenarios or case studies"
            )

            if has_jd:
                # JD present: treat JD as primary; probe JD focus areas even when resume is thin
                context_parts.append(
                    "\n=== JOB-DESCRIPTION PRIORITY ==="
                )
                context_parts.append(
                    "The job description below is the PRIMARY source for what you are evaluating."
                )
                context_parts.append(
                    "Identify key skills, focus areas, and requirements from the JD. "
                    "Proactively ask about the candidate's experience and depth in those areas, "
                    "especially where the resume is thin or silent (e.g. if the JD emphasizes "
                    "A/B testing and product work, probe that even if the resume is ML-heavy)."
                )
                context_parts.append(
                    f"\n=== JOB DESCRIPTION (full) ===\n{deps.jd_summary}"
                )
                if has_resume:
                    context_parts.append(
                        f"\n=== CANDIDATE RESUME (secondary context) ===\n{deps.resume_summary}"
                    )
                context_parts.append("\n=== YOUR TASK ===")
                context_parts.append(
                    f"Begin the behavioral interview for {role} at {company}. "
                    "Start with a warm introduction. Ask about their background, then "
                    "probe their experience in the key areas from the job description; "
                    "seek out their actual familiarity with what the role requires."
                )
            elif has_resume:
                # Resume only: resume-driven questions
                context_parts.append(
                    "- Reference their resume to ask about specific projects"
                )
                context_parts.append(
                    "- Probe how their experience aligns with this role"
                )
                context_parts.append(
                    f"\n=== CANDIDATE RESUME (use this to ask specific questions) ===\n"
                    f"{deps.resume_summary}"
                )
                context_parts.append("\n=== YOUR TASK ===")
                context_parts.append(
                    f"Begin the behavioral interview for {role} at {company}. "
                    "Start with a warm introduction and ask about their background or "
                    "a specific experience from their resume that's relevant to this role."
                )
            else:
                # Neither: default
                context_parts.append("\n=== YOUR TASK ===")
                context_parts.append(
                    "Begin the interview with an appropriate opening question."
                )

        elif deps.interview_type == "case_study":
            context_parts.append("\n=== CASE STUDY INTERVIEW INSTRUCTIONS ===")
            context_parts.append(
                "This is a CASE STUDY interview. Present a brief hypothetical problem."
            )
            context_parts.append(
                "CRITICAL: Keep your opening SHORT - just 2-3 sentences!"
            )
            context_parts.append(
                "DO NOT list all available data or constraints upfront."
            )
            context_parts.append(
                "Let details emerge as the candidate asks clarifying questions."
            )
            context_parts.append("DO NOT ask about their past projects or resume.")
            context_parts.append("NEVER use markdown, bullets, or formatting.")

            if has_jd:
                context_parts.append(
                    f"\n=== JOB DESCRIPTION (full, for scenario design; don't recite) ===\n"
                    f"{deps.jd_summary}"
                )
            scenario_hint = self._generate_case_study_hint(
                deps.jd_summary, company, role
            )
            context_parts.append(
                f"\n=== SCENARIO THEME (pick one, keep it brief) ===\n{scenario_hint}"
            )

            context_parts.append("\n=== YOUR TASK ===")
            context_parts.append(
                f"Start with a brief, conversational setup for {role} at {company}. "
                "Vary your opening style—brief scenario, question, or constraint—and "
                "WAIT for their response. Don't prescribe one format."
            )

        elif deps.interview_type == "custom":
            context_parts.append("\n=== CUSTOM INTERVIEW ===")
            context_parts.append(
                "This interview is structured by the INTERVIEW PLAN below. "
                "Follow it closely. Do NOT default to behavioral or case study patterns "
                "unless the plan explicitly asks for them."
            )
            plan = (deps.custom_interview_plan or "").strip()
            if plan:
                context_parts.append(
                    f"\n=== INTERVIEW PLAN (follow this) ===\n{plan}"
                )
            if has_jd:
                context_parts.append(
                    f"\n=== JOB DESCRIPTION ===\n{deps.jd_summary}"
                )
            if has_resume:
                context_parts.append(
                    f"\n=== CANDIDATE RESUME ===\n{deps.resume_summary}"
                )
            context_parts.append("\n=== YOUR TASK ===")
            if plan:
                context_parts.append(
                    f"Begin the custom interview for {role} at {company} per the plan. "
                    "Start with a brief welcome and first question."
                )
            else:
                context_parts.append(
                    "Begin the interview with an appropriate opening question."
                )

        else:
            context_parts.append("\n=== YOUR TASK ===")
            context_parts.append(
                "Begin the interview with an appropriate opening question."
            )

        # Add special instructions only for non-custom types (custom uses the plan above)
        if deps.custom_instructions and deps.interview_type != "custom":
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
        if llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            raise ValueError(f"Unsupported provider: {llm_config.provider}")

        # Build interview-type-specific system prompt
        system_prompt = self._build_system_prompt(
            interview_config.interview_type.value,
            interview_config.tone.value,
            interview_config.difficulty.value,
        )

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
            else None,  # First 1500 chars for token economy
            jd_summary=context.candidate_info.job_description.strip() or None,  # Full JD when present
            custom_instructions=context.candidate_info.custom_instructions,
            conversation_history=self.conversation_history,
            current_phase=self.current_phase,
            custom_interview_plan=getattr(
                context.candidate_info, "custom_interview_plan", None
            ),
            wrap_up_triggered=context.session_metadata.get("wrap_up_triggered", False),
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
