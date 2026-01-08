"""Base class for all interview agents."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time

from ..core import InterviewContext, AgentMessage, AgentResponse, AgentCapability


class BaseInterviewAgent(ABC):
    """Abstract base class for all interview agents."""
    
    def __init__(self, name: str, capabilities: List[AgentCapability], pydantic_agent: Optional[Any] = None):
        self.name = name
        self.capabilities = capabilities
        self.pydantic_agent = pydantic_agent
        self.is_enabled = True
        self.last_used = 0.0
        self.usage_count = 0
        self.performance_metrics = {
            'total_requests': 0,
            'successful_responses': 0,
            'average_confidence': 0.0,
            'average_response_time': 0.0
        }
    
    @abstractmethod
    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """
        Determine if this agent can handle the given message.
        
        Args:
            message: The message to evaluate
            context: Current interview context
            
        Returns:
            float: Confidence score (0.0 to 1.0) indicating ability to handle the message
        """
        pass
    
    @abstractmethod
    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """
        Process a message and generate a response.
        
        Args:
            message: The message to process
            context: Current interview context
            
        Returns:
            AgentResponse: The agent's response
        """
        pass
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Return the capabilities this agent provides."""
        return self.capabilities.copy()
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if this agent has a specific capability."""
        return capability in self.capabilities
    
    def update_performance_metrics(self, response: AgentResponse, response_time: float):
        """Update performance tracking metrics."""
        self.performance_metrics['total_requests'] += 1
        
        if response.confidence > 0.5:  # Consider responses with >50% confidence as successful
            self.performance_metrics['successful_responses'] += 1
        
        # Update average confidence (rolling average)
        total_requests = self.performance_metrics['total_requests']
        current_avg_confidence = self.performance_metrics['average_confidence']
        self.performance_metrics['average_confidence'] = (
            (current_avg_confidence * (total_requests - 1) + response.confidence) / total_requests
        )
        
        # Update average response time (rolling average)
        current_avg_time = self.performance_metrics['average_response_time']
        self.performance_metrics['average_response_time'] = (
            (current_avg_time * (total_requests - 1) + response_time) / total_requests
        )
        
        self.last_used = time.time()
        self.usage_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status and performance metrics."""
        return {
            'name': self.name,
            'capabilities': [cap.value for cap in self.capabilities],
            'is_enabled': self.is_enabled,
            'usage_count': self.usage_count,
            'last_used': self.last_used,
            'performance_metrics': self.performance_metrics.copy(),
            'pydantic_agent_status': str(self.pydantic_agent) if self.pydantic_agent else None
        }
    
    def enable(self):
        """Enable this agent."""
        self.is_enabled = True
    
    def disable(self):
        """Disable this agent."""
        self.is_enabled = False
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.performance_metrics = {
            'total_requests': 0,
            'successful_responses': 0,
            'average_confidence': 0.0,
            'average_response_time': 0.0
        }
        self.usage_count = 0
    
    def _create_response(
        self,
        content: str,
        confidence: float,
        requires_followup: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        next_suggested_agents: Optional[List[str]] = None,
        cost_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Helper method to create standardized responses."""
        return AgentResponse(
            content=content,
            confidence=confidence,
            agent_name=self.name,
            requires_followup=requires_followup,
            metadata=metadata or {},
            next_suggested_agents=next_suggested_agents or [],
            cost_info=cost_info
        )
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', capabilities={len(self.capabilities)})"
    
    def __repr__(self) -> str:
        return self.__str__()