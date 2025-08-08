"""
Interview context and conversation management system.

This module provides the core data structures and management for interview sessions:
- InterviewContext: Main container for interview state and data
- ConversationTurn: Individual conversation turns with metadata
- InterviewPhase: Enumeration of interview phases
- CandidateInfo: Candidate information and document context

The context system maintains conversation history, agent states, and session metadata
to provide a comprehensive view of the interview session for all agents.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..config import InterviewConfig, LLMConfig


class InterviewPhase(Enum):
    """
    Current phase of the interview.
    
    These phases help agents understand where they are in the interview process
    and adjust their behavior accordingly.
    """
    STARTING = "starting"                    # Initial setup and welcome
    INTRODUCTION = "introduction"            # Getting to know the candidate
    TECHNICAL_QUESTIONS = "technical_questions"  # Technical skills assessment
    BEHAVIORAL_QUESTIONS = "behavioral_questions"  # Behavioral and experience questions
    CASE_STUDY = "case_study"               # Hypothetical problem-solving scenarios
    CANDIDATE_QUESTIONS = "candidate_questions"  # Candidate asking questions
    WRAP_UP = "wrap_up"                     # Closing and next steps
    COMPLETED = "completed"                  # Interview finished


@dataclass
class CandidateInfo:
    """
    Information about the interview candidate.
    
    This class stores all candidate-related information including:
    - Resume text and parsed content
    - Job description and requirements
    - Custom instructions for the interview
    - Extracted skills, companies, and technologies
    
    This information helps agents provide more personalized and relevant questions.
    """
    resume_text: str = ""                    # Full text of uploaded resume
    job_description: str = ""                # Full text of job description
    custom_instructions: str = ""            # Custom instructions for the interview
    
    # Extracted information for quick access
    skills_mentioned: List[str] = field(default_factory=list)      # Skills from resume/job description
    companies_mentioned: List[str] = field(default_factory=list)   # Companies from experience
    technologies_mentioned: List[str] = field(default_factory=list) # Technologies and tools


@dataclass
class ConversationTurn:
    """
    Single turn in the conversation.
    
    This represents one exchange in the interview conversation with:
    - Timestamp for chronological ordering
    - Speaker identification (user, interviewer, agent)
    - Content of the message
    - Message type for categorization
    - Metadata for additional context
    
    This structure allows for detailed conversation analysis and context building.
    """
    timestamp: float                         # Unix timestamp of the turn
    speaker: str                            # "user", "interviewer", or agent name
    content: str                            # The actual message content
    message_type: str                       # Type of message (question, answer, feedback, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context and data


@dataclass
class InterviewContext:
    """
    Shared context for all agents in an interview session.
    
    This is the central data structure that maintains the complete state of an interview:
    - Session identification and configuration
    - Conversation history and flow
    - Agent states and metadata
    - Document context and candidate information
    
    All agents access and update this context to maintain consistency and provide
    personalized, contextual responses throughout the interview.
    """
    session_id: str                         # Unique session identifier
    llm_config: LLMConfig                   # LLM provider and model configuration
    interview_config: InterviewConfig       # Interview type, tone, difficulty settings
    candidate_info: CandidateInfo           # Candidate information and documents
    
    # Interview state and progression
    current_phase: InterviewPhase = InterviewPhase.STARTING
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    agent_states: Dict[str, Any] = field(default_factory=dict)  # Per-agent state storage
    session_metadata: Dict[str, Any] = field(default_factory=dict)  # Session-level metadata
    start_time: float = field(default_factory=time.time)  # Session start timestamp
    
    def add_turn(self, turn: ConversationTurn):
        """
        Add a conversation turn to the history.
        
        This method:
        - Adds the turn to the conversation history
        - Maintains chronological order
        - Updates session metadata if needed
        
        Args:
            turn: The conversation turn to add
        """
        self.conversation_history.append(turn)
    
    def add_search_context(self, search_content: str):
        """
        Add search results to context for future reference.
        
        This method stores search results so they can be referenced by other agents
        throughout the interview without needing to re-search.
        
        Args:
            search_content: Content from search results to store
        """
        if not hasattr(self, 'search_context'):
            self.search_context = []
        self.search_context.append(search_content)
    
    def get_search_context(self) -> List[str]:
        """
        Get recent search context.
        
        Returns the most recent search results for agents to reference.
        Limits to last 3 searches to avoid context overflow.
        
        Returns:
            List of recent search result content
        """
        if hasattr(self, 'search_context'):
            return self.search_context[-3:]  # Return last 3 search results
        return []
    
    def get_recent_turns(self, count: int = 5) -> List[ConversationTurn]:
        """
        Get the most recent conversation turns.
        
        This is useful for agents that need recent context without the full history.
        
        Args:
            count: Number of recent turns to return
            
        Returns:
            List of the most recent conversation turns
        """
        return self.conversation_history[-count:]
    
    def get_agent_state(self, agent_name: str) -> Dict[str, Any]:
        """
        Get state for a specific agent.
        
        Each agent can store its own state in the context for persistence
        across multiple interactions.
        
        Args:
            agent_name: Name of the agent whose state to retrieve
            
        Returns:
            Dictionary containing the agent's stored state
        """
        return self.agent_states.get(agent_name, {})
    
    def set_agent_state(self, agent_name: str, state: Dict[str, Any]):
        """
        Set state for a specific agent.
        
        This allows agents to store persistent state that survives across
        multiple message exchanges.
        
        Args:
            agent_name: Name of the agent
            state: State dictionary to store
        """
        self.agent_states[agent_name] = state
    
    def update_agent_state(self, agent_name: str, updates: Dict[str, Any]):
        """
        Update state for a specific agent.
        
        This method merges new state updates with existing state rather than
        replacing it entirely.
        
        Args:
            agent_name: Name of the agent
            updates: Dictionary of state updates to merge
        """
        if agent_name not in self.agent_states:
            self.agent_states[agent_name] = {}
        self.agent_states[agent_name].update(updates)
    
    def get_interview_duration(self) -> float:
        """
        Get interview duration in seconds.
        
        Returns:
            Duration of the interview session in seconds
        """
        return time.time() - self.start_time
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract potential keywords from text for agent routing.
        
        This method analyzes text to identify keywords that can help
        determine which agents should handle a particular message.
        
        Args:
            text: Text to analyze for keywords
            
        Returns:
            List of extracted keywords
        """
        # Simple keyword extraction - can be enhanced later
        keywords = []
        lower_text = text.lower()
        
        # Technical terms that might indicate technical questions
        tech_terms = ['python', 'sql', 'machine learning', 'data science', 'algorithm', 
                     'model', 'analysis', 'statistics', 'code', 'programming']
        keywords.extend([term for term in tech_terms if term in lower_text])
        
        # Company/business terms that might indicate behavioral questions
        business_terms = ['company', 'business', 'stakeholder', 'requirement', 'process']
        keywords.extend([term for term in business_terms if term in lower_text])
        
        return keywords