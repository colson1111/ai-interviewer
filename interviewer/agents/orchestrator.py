"""Orchestrator agent that manages and coordinates other agents."""

import time
from typing import List, Dict, Any, Optional
import asyncio

from .base import BaseInterviewAgent
from .registry import AgentRegistry
from ..core import (
    InterviewContext, AgentMessage, AgentResponse, CombinedResponse,
    MessageType, AgentCapability, InterviewPhase, ConversationTurn
)
from ..core.routing import AgentSelector, RoutingDecision


class OrchestratorAgent(BaseInterviewAgent):
    """
    Main orchestrator that routes messages to appropriate specialist agents
    and combines their responses.
    """
    
    def __init__(self, registry: AgentRegistry):
        super().__init__(
            name="orchestrator",
            capabilities=[AgentCapability.CONVERSATION_FLOW]
        )
        self.registry = registry
        self.agent_selector = AgentSelector()
        self.routing_history: List[RoutingDecision] = []
    
    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Orchestrator can handle any message by routing to appropriate agents."""
        return 1.0  # Always can handle by delegating
    
    async def process(self, message: AgentMessage, context: InterviewContext) -> CombinedResponse:
        """
        Process a message by routing to appropriate agents and combining responses.
        
        Args:
            message: The message to process
            context: Current interview context
            
        Returns:
            CombinedResponse: Combined response from multiple agents
        """
        start_time = time.time()
        
        try:
            print(f"########## ORCHESTRATOR: Starting to process message: {message.content[:50]}...")
            
            # Step 1: Analyze message and determine routing
            routing_decision = self._route_message(message, context)
            self.routing_history.append(routing_decision)
            print(f"########## ORCHESTRATOR: Routing decision made: {routing_decision}")
            
            # Log when SearchAgent is being used
            if routing_decision.primary_agent == "search" or "search" in routing_decision.supporting_agents:
                print(f"########## ORCHESTRATOR: SearchAgent selected - primary: {routing_decision.primary_agent}, supporting: {routing_decision.supporting_agents}")
            
            # Step 2: Execute agents
            agent_responses = await self._execute_agents(message, context, routing_decision)
            print(f"########## ORCHESTRATOR: Agent responses collected: {len(agent_responses)}")
            
            # Step 3: Combine responses
            combined_response = self._combine_responses(agent_responses, routing_decision, context)
            print(f"########## ORCHESTRATOR: Combined response: {combined_response.content[:50]}...")
            
            # Step 4: Update context
            print("########## ORCHESTRATOR: Updating context...")
            self._update_context(context, message, combined_response.content)
            print("########## ORCHESTRATOR: Context updated successfully")
            
            response_time = time.time() - start_time
            
            # Update our own metrics
            temp_response = self._create_response(
                content=combined_response.content,
                confidence=combined_response.total_confidence
            )
            self.update_performance_metrics(temp_response, response_time)
            
            print(f"########## ORCHESTRATOR: Returning combined response: {combined_response.content[:50]}...")
            return combined_response
            
        except Exception as e:
            print(f"########## ORCHESTRATOR: Exception caught: {e}")
            import traceback
            traceback.print_exc()
            # Fallback response on error
            error_response = AgentResponse(
                content=f"I apologize, but I encountered an issue processing your message. Let's continue with the interview.",
                confidence=0.1,
                agent_name="orchestrator",
                metadata={"error": str(e)}
            )
            
            return CombinedResponse(
                content=error_response.content,
                primary_agent="orchestrator",
                contributing_agents=[],
                total_confidence=0.1,
                metadata={"error": str(e)},
                cost_breakdown={}
            )
    
    def _route_message(self, message: AgentMessage, context: InterviewContext) -> RoutingDecision:
        """Determine which agents should handle the message."""
        
        # Use the correct AgentSelector method
        routing_decision = self.agent_selector.select_agents(message, context)
        
        # Enhance the routing decision based on context
        self._enhance_routing_decision(routing_decision, message, context)
        
        return routing_decision
    
    def _enhance_routing_decision(
        self, 
        routing_decision: RoutingDecision, 
        message: AgentMessage, 
        context: InterviewContext
    ):
        """Enhance routing decision based on context and message."""
        
        # Always include feedback agent for user responses
        if (message.message_type.value == "user_response" and 
            "feedback" not in routing_decision.supporting_agents and
            "feedback" != routing_decision.primary_agent):
            routing_decision.supporting_agents.append("feedback")
        
        # Ensure we have at least one agent
        if not routing_decision.primary_agent:
            routing_decision.primary_agent = "interview"
    
    async def _execute_agents(
        self, 
        message: AgentMessage, 
        context: InterviewContext, 
        routing_decision: RoutingDecision
    ) -> List[AgentResponse]:
        """Execute the selected agents and collect their responses."""
        
        responses = []
        
        print(f"########## ORCHESTRATOR: Executing agents")
        print(f"########## ORCHESTRATOR: primary={routing_decision.primary_agent}, supporting={routing_decision.supporting_agents}")
        
        # Execute primary agent
        primary_agent = self.registry.get_agent(routing_decision.primary_agent)
        print(f"########## ORCHESTRATOR: Primary agent found: {primary_agent is not None}")
        if primary_agent and primary_agent.is_enabled:
            try:
                print(f"########## ORCHESTRATOR: Processing with primary agent: {routing_decision.primary_agent}")
                response = await primary_agent.process(message, context)
                print(f"########## ORCHESTRATOR: Primary agent response: {response.content[:100]}...")
                responses.append(response)
            except Exception as e:
                print(f"########## ORCHESTRATOR: Error in primary agent {routing_decision.primary_agent}: {e}")
                import traceback
                traceback.print_exc()
        
        # Execute supporting agents
        for agent_name in routing_decision.supporting_agents:
            agent = self.registry.get_agent(agent_name)
            print(f"########## ORCHESTRATOR: Supporting agent {agent_name} found: {agent is not None}")
            if agent and agent.is_enabled:
                try:
                    print(f"########## ORCHESTRATOR: Processing with supporting agent: {agent_name}")
                    response = await agent.process(message, context)
                    print(f"########## ORCHESTRATOR: Supporting agent response: {response.content[:100]}...")
                    responses.append(response)
                except Exception as e:
                    print(f"########## ORCHESTRATOR: Error in supporting agent {agent_name}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"########## ORCHESTRATOR: Total responses collected: {len(responses)}")
        return responses
    
    def _combine_responses(
        self, 
        agent_responses: List[AgentResponse], 
        routing_decision: RoutingDecision,
        context: InterviewContext = None
    ) -> CombinedResponse:
        """Combine responses from multiple agents."""
        
        if not agent_responses:
            return CombinedResponse(
                content="I apologize, but I'm having trouble processing that. Could you please rephrase your response?",
                primary_agent="orchestrator",
                contributing_agents=[],
                total_confidence=0.1,
                metadata={"error": "No agent responses"},
                cost_breakdown={}
            )
        
        # Find the primary agent response
        primary_response = None
        search_response = None
        interview_response = None
        
        for response in agent_responses:
            if response.agent_name == routing_decision.primary_agent:
                primary_response = response
            if response.agent_name == "search":
                search_response = response
            if response.agent_name == "interview":
                interview_response = response
        
        # Store search results in context for the interview agent to use
        if search_response and search_response.content.strip() and len(search_response.content.strip()) > 50:
            # Add search results to context for future reference
            if "I couldn't find" not in search_response.content and "not available" not in search_response.content:
                # Store useful search results in context if context is available
                if context:
                    context.add_search_context(search_response.content)
        
        # Determine the main content - prioritize interview responses
        if primary_response and primary_response.content.strip():
            main_content = primary_response.content
        elif search_response and search_response.content.strip() and len(search_response.content.strip()) > 50:
            # Only use search as fallback if no interview response
            if "I couldn't find" not in search_response.content and "not available" not in search_response.content:
                main_content = search_response.content
            else:
                main_content = "I apologize, but I'm having trouble processing that. Could you please rephrase your response?"
        else:
            # Fallback
            main_content = "I apologize, but I'm having trouble processing that. Could you please rephrase your response?"
        
        # Add feedback data if available
        feedback_data = None
        
        # Calculate total confidence
        total_confidence = sum(response.confidence for response in agent_responses) / len(agent_responses)
        
        # Collect contributing agents
        contributing_agents = [response.agent_name for response in agent_responses if response.agent_name]
        
        # Collect cost breakdown
        cost_breakdown = {}
        for response in agent_responses:
            if response.metadata and "cost" in response.metadata:
                cost_breakdown[response.agent_name] = response.metadata["cost"]
        
        return CombinedResponse(
            content=main_content,
            primary_agent=routing_decision.primary_agent,
            contributing_agents=contributing_agents,
            total_confidence=total_confidence,
            feedback_data=feedback_data,
            metadata={
                "routing_decision": routing_decision,
                "response_count": len(agent_responses)
            },
            cost_breakdown=cost_breakdown
        )
    
    def _update_context(self, context: InterviewContext, message: AgentMessage, response: str):
        """Update the conversation context with the new message and response."""
        try:
            # Add user message to context
            user_turn = ConversationTurn(
                timestamp=time.time(),
                speaker="user",
                content=message.content,
                message_type=message.message_type.value,
                metadata=message.metadata
            )
            context.add_turn(user_turn)
            
            # Add interviewer response to context
            interviewer_turn = ConversationTurn(
                timestamp=time.time(),
                speaker="interviewer",
                content=response,
                message_type="message",
                metadata={"type": "interview_response"}
            )
            context.add_turn(interviewer_turn)
            
            print("########## ORCHESTRATOR: Context updated successfully")
            
        except Exception as e:
            print(f"########## ORCHESTRATOR: Error updating context: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_interview_phase(
        self, 
        context: InterviewContext, 
        message: AgentMessage, 
        response: CombinedResponse
    ):
        """Update the interview phase based on the interaction."""
        
        # Simple phase progression logic
        if message.message_type.value == "system_event" and "start" in message.content.lower():
            context.current_phase = InterviewPhase.INTRODUCTION
        elif message.message_type.value == "user_response":
            # Progress through phases based on conversation length
            message_count = len([m for m in context.conversation_history if m.speaker == "user"])
            if message_count <= 2:
                context.current_phase = InterviewPhase.INTRODUCTION
            elif message_count <= 5:
                context.current_phase = InterviewPhase.TECHNICAL_QUESTIONS
            else:
                context.current_phase = InterviewPhase.BEHAVIORAL_QUESTIONS
    
    def get_routing_history(self) -> List[RoutingDecision]:
        """Get the history of routing decisions."""
        return self.routing_history.copy()
    
    def get_orchestrator_metrics(self) -> Dict[str, Any]:
        """Get orchestrator performance metrics."""
        return {
            "total_requests": self.performance_metrics['total_requests'],
            "average_confidence": self.performance_metrics['average_confidence'],
            "average_response_time": self.performance_metrics['average_response_time'],
            "routing_history_length": len(self.routing_history),
            "agent_usage": self._calculate_agent_usage(),
            "average_agents_per_request": self._calculate_average_agents_per_request(),
            "confidence_distribution": self._calculate_confidence_distribution()
        }
    
    def _calculate_agent_usage(self) -> Dict[str, int]:
        """Calculate how often each agent was used."""
        usage = {}
        for decision in self.routing_history:
            if decision.primary_agent not in usage:
                usage[decision.primary_agent] = 0
            usage[decision.primary_agent] += 1
            
            for agent in decision.supporting_agents:
                if agent not in usage:
                    usage[agent] = 0
                usage[agent] += 1
        return usage
    
    def _calculate_average_agents_per_request(self) -> float:
        """Calculate average number of agents used per request."""
        if not self.routing_history:
            return 0.0
        
        total_agents = sum(
            1 + len(decision.supporting_agents) 
            for decision in self.routing_history
        )
        return total_agents / len(self.routing_history)
    
    def _calculate_confidence_distribution(self) -> Dict[str, int]:
        """Calculate distribution of confidence scores."""
        # This would need to be implemented based on actual confidence tracking
        return {"high": 0, "medium": 0, "low": 0}