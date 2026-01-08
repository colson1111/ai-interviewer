"""Core interview agent for general interview questions and conversation flow.

This agent handles the primary interview conversation, using pydantic-ai for structured interaction.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import re

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel

from .base import BaseInterviewAgent
from ..config import LLMConfig, InterviewConfig
from ..core import InterviewContext, AgentMessage, AgentResponse, AgentCapability


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
                AgentCapability.CONVERSATION_FLOW
            ]
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
    
        # Initialize the LLM model
        if llm_config.provider.value == "openai":
            model = OpenAIModel(llm_config.model)
        elif llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            raise ValueError(f"Unsupported provider: {llm_config.provider}")
            
        # Create Pydantic-AI agent with a STATIC system prompt
        # Dynamic prompts with functions are causing serialization issues
        self.pydantic_agent = Agent(
            model,
            deps_type=InterviewDeps,
            system_prompt="""
You are an expert interviewer conducting a professional interview.

CRITICAL: You will receive context about the role, company, candidate background, and job requirements in your first message. 
Remember this context throughout the ENTIRE interview. When the candidate asks about the role or company, refer to this context.

YOUR ROLE:
- Conduct a professional, realistic interview for the specific role and company provided.
- Ask relevant follow-up questions based on the candidate's responses.
- Dig deeper into their experience using specific examples they provide.
- React naturally - question mismatches, probe vague claims, show curiosity about strengths.
- If this is a behavioral interview, use STAR method probes.
- If this is a case study, guide them through the problem structuredly.

GUIDELINES:
- Keep your responses concise (usually 1-3 sentences/questions).
- Do NOT repeat yourself.
- Do NOT be overly encouraging or repetitive with praise.
- Move the interview forward with each turn.
- If the candidate asks for clarification about the role/company, refer to the context you were given.
- Question irrelevant experience directly (e.g., if they mention botany for an ML role, ask about the connection).

Adapt your questioning style based on the interview context and candidate responses.
"""
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
    
    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """Process the message using Pydantic AI agent."""
        
        # Update conversation history
        self.conversation_history.append({
            "timestamp": time.time(),
            "sender": message.sender,
            "content": message.content
        })
        
        # Prepare dependencies with simple types
        deps = InterviewDeps(
            interview_type=context.interview_config.interview_type.value,
            tone=context.interview_config.tone.value,
            difficulty=context.interview_config.difficulty.value,
            company_name=context.candidate_info.company_name,
            role_title=context.candidate_info.role_title,
            resume_summary=context.candidate_info.resume_text[:1500] if context.candidate_info.resume_text else None,  # First 1500 chars
            jd_summary=context.candidate_info.job_description[:1500] if context.candidate_info.job_description else None,  # First 1500 chars
            custom_instructions=context.candidate_info.custom_instructions,
            conversation_history=self.conversation_history,
            current_phase=self.current_phase
        )
        
        try:
            # Handle system messages (start interview) specially - build comprehensive context
            user_content = message.content
            
            if message.sender == "system" and "start_interview" in message.content.lower() and not self.context_initialized:
                # Build rich initial context that will be remembered throughout the interview
                context_parts = [
                    "=== INTERVIEW CONTEXT ===",
                    f"Company: {deps.company_name or 'Not specified'}",
                    f"Role: {deps.role_title or 'Not specified'}",
                    f"Interview Type: {deps.interview_type}",
                    f"Tone: {deps.tone}",
                    f"Difficulty: {deps.difficulty}"
                ]
                
                if deps.resume_summary:
                    context_parts.append(f"\n=== CANDIDATE BACKGROUND ===\n{deps.resume_summary}")
                
                if deps.jd_summary:
                    context_parts.append(f"\n=== JOB REQUIREMENTS ===\n{deps.jd_summary}")
                
                if deps.custom_instructions:
                    context_parts.append(f"\n=== SPECIAL INSTRUCTIONS ===\n{deps.custom_instructions}")
                
                context_parts.append("\n=== YOUR TASK ===")
                context_parts.append("Begin the interview with an appropriate opening question for this specific role and company.")
                context_parts.append("Remember this context for the entire interview - if the candidate asks about the role or company, refer to this information.")
                
                user_content = "\n".join(context_parts)
                self.current_phase = "introduction"
                self.context_initialized = True
            
            # Run the agent with full message history to maintain context
            result = await self.pydantic_agent.run(
                user_content, 
                deps=deps,
                message_history=self.pydantic_message_history if self.pydantic_message_history else None
            )
            
            # Extract the response content
            response_content = result.output if hasattr(result, 'output') else str(result)
            
            # Update pydantic-ai message history to maintain context for next turn
            # The result contains the full message exchange
            if hasattr(result, 'all_messages'):
                self.pydantic_message_history = result.all_messages()
            elif hasattr(result, 'messages'):
                self.pydantic_message_history = result.messages
            
            # Update our internal context
            context.add_turn({
                "timestamp": time.time(),
                "speaker": "interviewer",
                "content": response_content,
                "message_type": "question"
            })
            
            return self._create_response(
                content=response_content,
                confidence=0.9,
                metadata={"phase": self.current_phase}
            )
            
        except Exception as e:
            print(f"Error in InterviewAgent: {e}")
            import traceback
            traceback.print_exc()
            return self._create_response(
                content="I apologize, but I encountered an error. Could you please repeat that?",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def update_configuration(self, llm_config: LLMConfig, interview_config: InterviewConfig):
        """Update LLM and interview configuration."""
        self.llm_config = llm_config
        self.interview_config = interview_config
        if llm_config.provider.value == "openai":
            model = OpenAIModel(llm_config.model)
        elif llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            return

        # Reset message history when reconfiguring
        self.pydantic_message_history = []
        self.context_initialized = False
        
        self.pydantic_agent = Agent(
            model,
            deps_type=InterviewDeps,
            system_prompt="""
You are an expert interviewer conducting a professional interview.

CRITICAL: You will receive context about the role, company, candidate background, and job requirements in your first message. 
Remember this context throughout the ENTIRE interview. When the candidate asks about the role or company, refer to this context.

YOUR ROLE:
- Conduct a professional, realistic interview for the specific role and company provided.
- Ask relevant follow-up questions based on the candidate's responses.
- Dig deeper into their experience using specific examples they provide.
- React naturally - question mismatches, probe vague claims, show curiosity about strengths.
- If this is a behavioral interview, use STAR method probes.
- If this is a case study, guide them through the problem structuredly.

GUIDELINES:
- Keep your responses concise (usually 1-3 sentences/questions).
- Do NOT repeat yourself.
- Do NOT be overly encouraging or repetitive with praise.
- Move the interview forward with each turn.
- If the candidate asks for clarification about the role/company, refer to the context you were given.
- Question irrelevant experience directly (e.g., if they mention botany for an ML role, ask about the connection).

Adapt your questioning style based on the interview context and candidate responses.
"""
        )

