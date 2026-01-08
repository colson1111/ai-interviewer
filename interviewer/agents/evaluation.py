"""Evaluation agent for post-interview analysis and reporting.

This agent uses pydantic-ai to generate a comprehensive report card
after the interview concludes.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel

from .base import BaseInterviewAgent
from ..config import LLMConfig
from ..core import InterviewContext, AgentMessage, AgentResponse, AgentCapability


class InterviewReport(BaseModel):
    """Structured evaluation report for an interview session."""
    score: int = Field(description="Overall score from 0 to 10")
    summary: str = Field(description="Executive summary of the interview performance")
    strengths: List[str] = Field(description="List of candidate's demonstrated strengths")
    improvements: List[str] = Field(description="List of areas for improvement")
    technical_assessment: Optional[str] = Field(description="Assessment of technical knowledge (if applicable)", default=None)
    communication_assessment: str = Field(description="Assessment of communication skills")
    cultural_fit_assessment: str = Field(description="Assessment of cultural fit and behavioral traits")


class EvaluationAgent(BaseInterviewAgent):
    """
    Agent responsible for generating the final interview report.
    """
    
    def __init__(self, llm_config: LLMConfig):
        super().__init__(
            name="evaluation",
            capabilities=[AgentCapability.PERFORMANCE_SCORING, AgentCapability.FEEDBACK_ANALYSIS]
        )
        self.llm_config = llm_config
        
        # Initialize model
        if llm_config.provider.value == "openai":
            model = OpenAIModel(llm_config.model)
        elif llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            raise ValueError(f"Unsupported provider: {llm_config.provider}")
            
        # Create Pydantic-AI agent with structured result type
        # Note: In pydantic-ai 1.x, structured outputs are handled differently
        # We'll use a static system prompt and parse the response manually
        self.pydantic_agent = Agent(
            model,
            system_prompt="""
You are an expert interview evaluator.
Your task is to analyze a full interview transcript and generate a structured evaluation report.

EVALUATION CRITERIA:
1. **Score (0-10)**: 
   - 9-10: Exceptional (Hired immediately)
   - 7-8: Strong (Likely hired)
   - 5-6: Average (Borderline)
   - <5: Weak (Not hired)

2. **Analysis**:
   - Identify concrete strengths (what they did well).
   - Identify specific improvements (what was missing or weak).
   - Assess communication clarity, conciseness, and structure (STAR method).
   - Assess cultural fit (attitude, enthusiasm, professionalism).

3. **Output Format** (JSON):
{
  "score": <0-10>,
  "summary": "<executive summary>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "improvements": ["<improvement 1>", "<improvement 2>", ...],
  "technical_assessment": "<optional technical assessment>",
  "communication_assessment": "<communication assessment>",
  "cultural_fit_assessment": "<cultural fit assessment>"
}

Provide a fair, constructive, and detailed report using professional language.
"""
        )

    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Evaluation agent is typically triggered manually or at end of session."""
        if "evaluate_session" in message.content:
            return 1.0
        return 0.0

    async def generate_report(self, context: InterviewContext) -> InterviewReport:
        """
        Generate a report from the interview context.
        """
        # Format transcript
        transcript = []
        for turn in context.conversation_history:
            speaker = turn.get("speaker", "unknown")
            content = turn.get("content", "")
            transcript.append(f"{speaker.upper()}: {content}")
        
        full_transcript = "\n\n".join(transcript)
        
        interview_type = context.interview_config.interview_type.value
        role = getattr(context.candidate_info, 'role_title', 'Candidate')
        
        prompt = f"""
Analyze this {interview_type} interview for the role of {role}.

TRANSCRIPT:
{full_transcript}
"""
        
        result = await self.pydantic_agent.run(prompt)
        # Extract the response content
        response_text = result.output if hasattr(result, 'output') else str(result)
        
        # Parse JSON response
        import json
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                report_data = json.loads(json_str)
                return InterviewReport(**report_data)
            else:
                # Fallback: create a basic report
                return InterviewReport(
                    score=5,
                    summary=response_text[:200],
                    strengths=["Unable to parse structured feedback"],
                    improvements=["Unable to parse structured feedback"],
                    communication_assessment="Unable to parse structured feedback",
                    cultural_fit_assessment="Unable to parse structured feedback"
                )
        except Exception as e:
            print(f"Error parsing evaluation report: {e}")
            return InterviewReport(
                score=5,
                summary="Error generating evaluation",
                strengths=["Error parsing response"],
                improvements=["Error parsing response"],
                communication_assessment="Error parsing response",
                cultural_fit_assessment="Error parsing response"
            )

    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """Process wrapper to conform to BaseInterviewAgent interface."""
        # This method might not be used if we call generate_report directly, 
        # but implementing it for consistency.
        try:
            report = await self.generate_report(context)
            return self._create_response(
                content="Evaluation complete.",
                confidence=1.0,
                metadata={"report": report.model_dump()}
            )
        except Exception as e:
            return self._create_response(
                content=f"Evaluation failed: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

