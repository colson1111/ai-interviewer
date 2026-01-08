"""
Multi-agent interview system for conducting AI-powered mock interviews.

This module orchestrates multiple specialized agents to conduct comprehensive interviews:
- InterviewAgent: Primary conversation and question generation
- SearchAgent: Real-time information lookup and fact-checking
- FeedbackAgent: Real-time response analysis and feedback
- SummaryAgent: Session summary and final assessment

The system coordinates these agents to provide a realistic, comprehensive interview experience
with live feedback, search capabilities, and detailed analysis.
"""

import time
from typing import Any, Dict

from .agents import InterviewAgent, SearchAgent, SummaryAgent
from .agents.orchestrator import OrchestratorAgent
from .agents.registry import AgentRegistry
from .config import InterviewConfig, LLMConfig
from .core import AgentMessage, AgentResponse, ConversationTurn, InterviewContext
from .core.messaging import MessageType


class MultiAgentInterviewSystem:
    """
    Orchestrates multiple specialized agents for comprehensive interview sessions.

    This system:
    - Coordinates multiple agents with different capabilities
    - Routes messages to appropriate agents based on content and context
    - Combines responses from multiple agents into coherent responses
    - Manages conversation flow and agent interactions
    - Provides real-time feedback and analysis

    Agent Responsibilities:
    - InterviewAgent: Primary conversation, question generation, interview flow
    - SearchAgent: Real-time information lookup, fact-checking, research
    - FeedbackAgent: Response analysis, performance scoring, improvement suggestions
    - SummaryAgent: Session summaries, final assessments, performance trends
    - OrchestratorAgent: Agent coordination, response combination, routing decisions
    """

    def __init__(self, llm_config: LLMConfig, interview_config: InterviewConfig):
        """
        Initialize the multi-agent interview system.

        Args:
            llm_config: Configuration for LLM providers and models
            interview_config: Interview type, tone, difficulty settings
        """
        self.llm_config = llm_config
        self.interview_config = interview_config

        # Initialize agent registry
        self.agent_registry = AgentRegistry()

        # Create and register specialized agents
        self._create_agents()
        self._register_agents()

        # Create orchestrator for agent coordination
        self.orchestrator = OrchestratorAgent(self.agent_registry)

        # Track system state
        self.session_start_time = time.time()
        self.message_count = 0
        self.agent_responses = []

    def _create_agents(self):
        """Create and configure all specialized agents."""
        # Primary interview agents
        self.interview_agent = InterviewAgent(self.llm_config, self.interview_config)

        # Search agent for real-time information lookup
        self.search_agent = SearchAgent(self.llm_config)

        # Summary agent for session analysis
        self.summary_agent = SummaryAgent()

    def _register_agents(self):
        """Register all agents with the agent registry."""
        self.agent_registry.register_agent(self.interview_agent)
        self.agent_registry.register_agent(self.search_agent)
        self.agent_registry.register_agent(self.summary_agent)

    async def get_initial_message(self, context: InterviewContext) -> AgentResponse:
        """
        Generate the initial welcome message and first question.

        This method:
        1. Creates the interview context with initial setup
        2. Generates a personalized welcome message
        3. Creates the first interview question
        4. Sets up the conversation flow

        Args:
            context: Interview context with candidate info and configuration

        Returns:
            AgentResponse with the initial message
        """
        # Choose the correct primary agent based on interview type
        primary_agent = self.interview_agent

        # Create initial message from the selected agent
        initial_message = await primary_agent.process(
            AgentMessage(
                sender="system",
                content="start_interview",
                message_type=MessageType.SYSTEM_EVENT,
                metadata={"action": "start_interview"},
                timestamp=time.time(),
                session_id=context.session_id,
            ),
            context,
        )

        # Add the initial message to conversation history
        context.add_turn(
            ConversationTurn(
                timestamp=time.time(),
                speaker="interviewer",
                content=initial_message.content,
                message_type="welcome",
                metadata={"phase": "introduction"},
            )
        )

        return initial_message

    async def process_message(
        self, user_message: str, context: InterviewContext
    ) -> Dict[str, Any]:
        """
        Process a user message through the multi-agent system.

        This method:
        1. Routes the message to appropriate agents based on content and context
        2. Collects responses from multiple agents
        3. Combines responses into a coherent response
        4. Generates real-time feedback
        5. Updates conversation context and history

        Args:
            user_message: The user's message to process
            context: Current interview context

        Returns:
            Dictionary containing combined response and metadata
        """
        try:
            # Create agent message
            agent_message = AgentMessage(
                sender="user",
                content=user_message,
                message_type=MessageType.USER_RESPONSE,
                metadata={"timestamp": time.time()},
                timestamp=time.time(),
                session_id=context.session_id,
            )

            # Add user message to conversation history
            context.add_turn(
                ConversationTurn(
                    timestamp=time.time(),
                    speaker="user",
                    content=user_message,
                    message_type="user_response",
                    metadata={},
                )
            )

            # Process through orchestrator to coordinate multiple agents
            combined_response = await self.orchestrator.process(agent_message, context)

            # Add interviewer response to conversation history
            if combined_response.content:
                context.add_turn(
                    ConversationTurn(
                        timestamp=time.time(),
                        speaker="interviewer",
                        content=combined_response.content,
                        message_type="interviewer_response",
                        metadata={
                            "agent": combined_response.primary_agent,
                            "confidence": combined_response.total_confidence,
                        },
                    )
                )

            # Update system state
            self.message_count += 1
            self.agent_responses.append(
                {
                    "timestamp": time.time(),
                    "user_message": user_message,
                    "combined_response": combined_response,
                }
            )

            return {
                "primary_response": AgentResponse(
                    content=combined_response.content,
                    confidence=combined_response.total_confidence,
                    agent_name=combined_response.primary_agent,
                    metadata=combined_response.metadata,
                ),
                "feedback_data": combined_response.feedback_data,
                "search_data": None,  # Search data is embedded in content
                "metadata": {
                    "message_count": self.message_count,
                    "session_duration": time.time() - self.session_start_time,
                    "agents_used": combined_response.contributing_agents,
                },
            }

        except Exception as e:
            # Fallback response on error
            fallback_response = AgentResponse(
                content="I apologize, but I'm having trouble processing that. Could you please repeat your question?",
                confidence=0.1,
                agent_name="orchestrator",
                metadata={"error": str(e), "fallback": True},
            )

            return {
                "primary_response": fallback_response,
                "feedback_data": None,
                "search_data": None,
                "metadata": {"error": str(e), "fallback": True},
            }

    async def get_session_summary(self, context: InterviewContext) -> Dict[str, Any]:
        """
        Generate a comprehensive session summary.

        This method:
        1. Analyzes the entire conversation history
        2. Generates performance metrics and trends
        3. Provides improvement recommendations
        4. Creates a final assessment

        Args:
            context: Interview context with full conversation history

        Returns:
            Dictionary containing session summary and analysis
        """
        try:
            # Get summary from summary agent
            summary_response = await self.summary_agent.process(
                AgentMessage(
                    sender="system",
                    content="generate_session_summary",
                    message_type=MessageType.SYSTEM_EVENT,
                    metadata={"action": "generate_summary"},
                    timestamp=time.time(),
                    session_id=context.session_id,
                ),
                context,
            )

            # Get feedback summary
            # feedback_summary = self.feedback_agent.get_session_summary(context) # This line was removed

            return {
                "summary": summary_response.content,
                "feedback_summary": None,  # feedback_summary, # This line was removed
                "session_metrics": {
                    "total_messages": self.message_count,
                    "session_duration": time.time() - self.session_start_time,
                    "agents_used": len(self.agent_responses),
                },
            }

        except Exception as e:
            return {
                "summary": "Session summary unavailable",
                "error": str(e),
                "session_metrics": {
                    "total_messages": self.message_count,
                    "session_duration": time.time() - self.session_start_time,
                },
            }

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status and metrics.

        Returns:
            Dictionary with system status information
        """
        return {
            "session_duration": time.time() - self.session_start_time,
            "message_count": self.message_count,
            "active_agents": len(self.agent_registry.get_agents()),
            "system_health": "healthy",
        }


def create_multi_agent_interview_system(
    llm_config: LLMConfig, interview_config: InterviewConfig
) -> MultiAgentInterviewSystem:
    """
    Factory function to create a multi-agent interview system.

    This function:
    1. Creates the multi-agent system with provided configurations
    2. Initializes all specialized agents
    3. Sets up agent coordination and routing
    4. Returns the configured system ready for interviews

    Args:
        llm_config: Configuration for LLM providers and models
        interview_config: Interview type, tone, difficulty settings

    Returns:
        Configured MultiAgentInterviewSystem instance
    """
    return MultiAgentInterviewSystem(llm_config, interview_config)
