"""Core interview agent for general interview questions and conversation flow.

This agent handles the primary interview conversation, including:
- Generating contextual questions based on interview type
- Maintaining conversation flow and natural dialogue
- Adapting to candidate responses and interview context
- Providing realistic interviewer behavior and tone
"""

from typing import List, Dict, Any, Optional
import time
import re

from .base import BaseInterviewAgent
from ..config import LLMConfig
from ..core import InterviewContext, AgentMessage, AgentResponse, AgentCapability


class InterviewAgent(BaseInterviewAgent):
    """
    Primary interview agent responsible for conducting the actual interview.
    
    This agent:
    - Generates contextual questions based on interview type (technical, behavioral, case study)
    - Maintains natural conversation flow
    - Adapts questions based on candidate responses
    - Provides realistic interviewer behavior and tone
    - Handles conversation context and history
    """
    
    def __init__(self, llm_config: LLMConfig):
        """Initialize the interview agent with LLM configuration."""
        super().__init__(
            name="interview",
            capabilities=[
                AgentCapability.INTERVIEW_QUESTIONS,
                AgentCapability.CONVERSATION_FLOW
            ]
        )
        self.llm_config = llm_config
        self.conversation_history = []
        self.question_count = 0
        self.current_phase = "introduction"
        
        # Track interview progress and candidate information
        self.candidate_name = None
        self.interview_start_time = time.time()
        self.last_question_time = None
    
    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """
        Determine if this agent can handle the message.
        
        The interview agent handles:
        - User responses (to generate follow-up questions)
        - System messages (to start the interview)
        - Context updates (to adapt the interview flow)
        
        Returns confidence score (0.0 to 1.0)
        """
        # High confidence for user messages (candidate responses)
        if message.sender == "user":
            return 0.9
        
        # Medium confidence for system messages (interview setup)
        if message.sender == "system":
            return 0.7
        
        # Lower confidence for other agent messages
        return 0.3
    
    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """
        Process the message and generate an appropriate interview response.
        
        This method:
        1. Analyzes the incoming message and context
        2. Determines the appropriate interview phase
        3. Generates contextual questions or responses
        4. Updates conversation history and context
        5. Returns a natural, conversational response
        
        Args:
            message: The incoming message to process
            context: The current interview context
            
        Returns:
            AgentResponse with the generated interview response
        """
        # Update conversation history
        self.conversation_history.append({
            "timestamp": time.time(),
            "sender": message.sender,
            "content": message.content
        })
        
        # Extract candidate name if not already known
        if not self.candidate_name and message.sender == "user":
            self.candidate_name = self._extract_candidate_name(message.content)
        
        # Generate appropriate response based on context
        if message.sender == "user":
            # Handle candidate response - generate follow-up question
            response = await self._generate_follow_up_question(message, context)
        elif message.sender == "system":
            # Handle system message - start interview or handle setup
            response = await self._handle_system_message(message, context)
        else:
            # Handle other agent messages
            response = await self._handle_agent_message(message, context)
        
        # Update interview context
        self._update_interview_context(context, response)
        
        return response
    
    async def _generate_follow_up_question(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """
        Generate a follow-up question based on the candidate's response.
        
        This method:
        - Analyzes the candidate's response for key information
        - Determines the next appropriate question type
        - Generates a natural, contextual follow-up
        - Maintains conversation flow and interview progression
        
        Args:
            message: The candidate's response message
            context: Current interview context
            
        Returns:
            AgentResponse with the follow-up question
        """
        # Analyze the candidate's response
        response_analysis = self._analyze_candidate_response(message.content)
        
        # Determine next question type based on interview phase and response
        next_question_type = self._determine_next_question_type(context, response_analysis)
        
        # Generate the follow-up question
        question_content = await self._generate_contextual_question(
            question_type=next_question_type,
            context=context,
            previous_response=message.content,
            response_analysis=response_analysis
        )
        
        # Update question count and timing
        self.question_count += 1
        self.last_question_time = time.time()
        
        return self._create_response(
            content=question_content,
            confidence=0.8,
            metadata={
                "question_type": next_question_type,
                "question_number": self.question_count,
                "interview_phase": self.current_phase
            }
        )
    
    async def _handle_system_message(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """
        Handle system messages for interview setup and control.
        
        This method:
        - Processes interview initialization messages
        - Handles interview phase transitions
        - Manages interview configuration updates
        
        Args:
            message: The system message to process
            context: Current interview context
            
        Returns:
            AgentResponse with appropriate system response
        """
        if "start_interview" in message.content.lower():
            # Generate initial welcome message with simple first question
            welcome_message = await self._generate_welcome_message(context)
            
            return self._create_response(
                content=welcome_message,
                confidence=0.9,
                metadata={"interview_started": True, "phase": "introduction"}
            )
        
        # Handle other system messages
        return self._create_response(
            content="Interview system ready.",
            confidence=0.5,
            metadata={"system_message": True}
        )
    
    async def _handle_agent_message(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """
        Handle messages from other agents in the system.
        
        This method:
        - Processes messages from search, feedback, or summary agents
        - Integrates external information into the interview flow
        - Maintains conversation coherence when multiple agents are involved
        
        Args:
            message: The agent message to process
            context: Current interview context
            
        Returns:
            AgentResponse with appropriate response
        """
        # For now, acknowledge other agent messages
        return self._create_response(
            content="",  # Empty content to avoid interference
            confidence=0.1,
            metadata={"agent_message_processed": True}
        )
    
    def _extract_candidate_name(self, response: str) -> Optional[str]:
        """
        Extract the candidate's name from their response.
        
        Looks for common name introduction patterns like:
        - "My name is [Name]"
        - "I'm [Name]"
        - "I am [Name]"
        - "Hi, I'm [Name]"
        
        Args:
            response: The candidate's response text
            
        Returns:
            Extracted name or None if not found
        """
        # Common name introduction patterns
        patterns = [
            r"my name is (\w+)",
            r"i'm (\w+)",
            r"i am (\w+)",
            r"hi, i'm (\w+)",
            r"hello, i'm (\w+)",
            r"hey, i'm (\w+)"
        ]
        
        response_lower = response.lower()
        for pattern in patterns:
            match = re.search(pattern, response_lower)
            if match:
                return match.group(1).title()
        
        return None
    
    def _analyze_candidate_response(self, response: str) -> Dict[str, Any]:
        """
        Analyze the candidate's response for key information.
        
        This method extracts:
        - Response length and complexity
        - Technical terms and concepts mentioned
        - Experience indicators
        - Confidence level indicators
        - Specific examples or metrics mentioned
        
        Args:
            response: The candidate's response text
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "length": len(response.split()),
            "technical_terms": self._extract_technical_terms(response),
            "experience_indicators": self._extract_experience_indicators(response),
            "confidence_level": self._assess_confidence_level(response),
            "specific_examples": self._extract_specific_examples(response),
            "metrics_mentioned": self._extract_metrics(response)
        }
        
        return analysis
    
    def _extract_technical_terms(self, response: str) -> List[str]:
        """Extract technical terms and concepts from the response."""
        technical_terms = [
            "python", "sql", "machine learning", "data science", "algorithm",
            "model", "analysis", "statistics", "database", "api", "framework",
            "regression", "classification", "clustering", "neural network",
            "deep learning", "optimization", "scaling", "performance"
        ]
        
        found_terms = []
        response_lower = response.lower()
        for term in technical_terms:
            if term in response_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _extract_experience_indicators(self, response: str) -> List[str]:
        """Extract experience and project indicators from the response."""
        experience_indicators = [
            "worked on", "implemented", "developed", "created", "built",
            "managed", "led", "supervised", "project", "experience",
            "previously", "at [company]", "in my role", "responsibility"
        ]
        
        found_indicators = []
        response_lower = response.lower()
        for indicator in experience_indicators:
            if indicator in response_lower:
                found_indicators.append(indicator)
        
        return found_indicators
    
    def _assess_confidence_level(self, response: str) -> str:
        """Assess the confidence level expressed in the response."""
        confident_indicators = ["confident", "sure", "definitely", "clearly", "obviously"]
        uncertain_indicators = ["maybe", "perhaps", "might", "could", "not sure", "uncertain"]
        
        response_lower = response.lower()
        confident_count = sum(1 for indicator in confident_indicators if indicator in response_lower)
        uncertain_count = sum(1 for indicator in uncertain_indicators if indicator in response_lower)
        
        if confident_count > uncertain_count:
            return "confident"
        elif uncertain_count > confident_count:
            return "uncertain"
        else:
            return "neutral"
    
    def _extract_specific_examples(self, response: str) -> List[str]:
        """Extract specific examples and concrete details from the response."""
        example_indicators = [
            "for example", "specifically", "in particular", "such as",
            "including", "namely", "that is", "i.e.", "e.g."
        ]
        
        examples = []
        response_lower = response.lower()
        for indicator in example_indicators:
            if indicator in response_lower:
                # Extract the example following the indicator
                start_idx = response_lower.find(indicator)
                if start_idx != -1:
                    # Simple extraction - could be enhanced
                    example_text = response[start_idx:start_idx + 100]  # Get next 100 chars
                    examples.append(example_text.strip())
        
        return examples
    
    def _extract_metrics(self, response: str) -> List[str]:
        """Extract metrics, numbers, and quantifiable results from the response."""
        # Look for percentage, numbers, time periods, etc.
        metrics = re.findall(r'\d+%|\d+ percent|\d+ times|\d+x|\$\d+|\d+ dollars|\d+ weeks|\d+ months', response, re.IGNORECASE)
        return metrics
    
    def _determine_next_question_type(self, context: InterviewContext, response_analysis: Dict[str, Any]) -> str:
        """
        Determine the next question type based on interview context and response analysis.
        
        This method considers:
        - Current interview phase
        - Interview type (technical, behavioral, case study)
        - Previous question types asked
        - Candidate's response depth and content
        - Interview progression and timing
        
        Args:
            context: Current interview context
            response_analysis: Analysis of the candidate's response
            
        Returns:
            String indicating the next question type
        """
        interview_type = context.interview_config.interview_type.value
        
        # Determine question type based on interview type and phase
        if interview_type == "technical":
            return self._determine_technical_question_type(response_analysis)
        elif interview_type == "behavioral":
            return self._determine_behavioral_question_type(response_analysis)
        elif interview_type == "case_study":
            return self._determine_case_study_question_type(response_analysis)
        else:
            return "general"
    
    def _determine_technical_question_type(self, response_analysis: Dict[str, Any]) -> str:
        """Determine the next technical question type based on response analysis."""
        # If candidate showed strong technical depth, ask for more detail
        if len(response_analysis["technical_terms"]) > 3:
            return "technical_depth"
        
        # If candidate mentioned specific technologies, ask about implementation
        if response_analysis["technical_terms"]:
            return "technical_implementation"
        
        # If candidate showed good problem-solving, ask about optimization
        if response_analysis["confidence_level"] == "confident":
            return "technical_optimization"
        
        # Default to basic technical question
        return "technical_basic"
    
    def _determine_behavioral_question_type(self, response_analysis: Dict[str, Any]) -> str:
        """Determine the next behavioral question type based on response analysis."""
        # If candidate provided specific examples, ask for more detail
        if response_analysis["specific_examples"]:
            return "behavioral_depth"
        
        # If candidate showed leadership, ask about team management
        if "led" in response_analysis["experience_indicators"] or "managed" in response_analysis["experience_indicators"]:
            return "behavioral_leadership"
        
        # If candidate mentioned challenges, ask about problem-solving
        if "challenge" in response_analysis["experience_indicators"]:
            return "behavioral_challenge"
        
        # Default to general behavioral question
        return "behavioral_general"
    
    def _determine_case_study_question_type(self, response_analysis: Dict[str, Any]) -> str:
        """Determine the next case study question type based on response analysis."""
        # If candidate showed analytical thinking, ask for more detail
        if response_analysis["length"] > 100:
            return "case_study_depth"
        
        # If candidate mentioned specific approaches, ask about alternatives
        if response_analysis["technical_terms"]:
            return "case_study_alternatives"
        
        # If candidate showed confidence, ask about challenges
        if response_analysis["confidence_level"] == "confident":
            return "case_study_challenges"
        
        # Default to general case study question
        return "case_study_general"
    
    async def _generate_contextual_question(self, question_type: str, context: InterviewContext, 
                                          previous_response: str, response_analysis: Dict[str, Any]) -> str:
        """
        Generate a contextual question based on the question type and analysis.
        
        This method:
        - Uses the LLM to generate natural, contextual questions
        - Incorporates information from the candidate's previous response
        - Maintains appropriate interview tone and style
        - Ensures questions are relevant to the interview type and phase
        
        Args:
            question_type: Type of question to generate
            context: Current interview context
            previous_response: The candidate's previous response
            response_analysis: Analysis of the candidate's response
            
        Returns:
            Generated question text
        """
        # Build context prompt for the LLM
        prompt = self._build_question_generation_prompt(
            question_type=question_type,
            context=context,
            previous_response=previous_response,
            response_analysis=response_analysis
        )
        
        # Generate question using LLM (simplified for now)
        # In a real implementation, this would call the configured LLM
        question = await self._generate_question_from_prompt(prompt, question_type)
        
        return question
    
    def _build_question_generation_prompt(self, question_type: str, context: InterviewContext,
                                        previous_response: str, response_analysis: Dict[str, Any]) -> str:
        """
        Build a prompt for generating contextual questions.
        
        This method constructs a comprehensive prompt that includes:
        - Interview type and context
        - Previous candidate response
        - Response analysis results
        - Desired question type and style
        - Interview tone and difficulty level
        
        Args:
            question_type: Type of question to generate
            context: Current interview context
            previous_response: The candidate's previous response
            response_analysis: Analysis of the candidate's response
            
        Returns:
            Formatted prompt string
        """
        interview_type = context.interview_config.interview_type.value
        tone = context.interview_config.tone.value
        difficulty = context.interview_config.difficulty.value
        
        prompt = f"""
        You are conducting a {interview_type} interview with a {tone} tone at {difficulty} difficulty level.
        
        The candidate just responded: "{previous_response}"
        
        Response analysis:
        - Length: {response_analysis['length']} words
        - Technical terms: {', '.join(response_analysis['technical_terms'])}
        - Confidence: {response_analysis['confidence_level']}
        - Specific examples: {len(response_analysis['specific_examples'])} provided
        
        Based on their response, generate a specific, contextual {question_type} question that:
        1. References specific details they mentioned (technologies, projects, experiences)
        2. Asks for concrete examples or deeper explanations
        3. Maintains a {tone} tone
        4. Is appropriate for {difficulty} difficulty
        5. Encourages detailed, specific responses
        
        IMPORTANT: Do NOT use placeholder text like [specific technology] or [programming language]. Instead, reference actual technologies, tools, or concepts they mentioned, or ask about specific aspects of their experience.

        If they didn't give enough information for you to ask an intelligent question, ask for more details.
        
        Question:"""
        
        return prompt
    
    async def _generate_question_from_prompt(self, prompt: str, question_type: str) -> str:
        """
        Generate a question from the prompt using the configured LLM.
        
        This method:
        - Calls the configured LLM (OpenAI, Anthropic, etc.)
        - Handles API responses and errors
        - Applies response formatting and validation
        
        Args:
            prompt: The prompt to send to the LLM
            question_type: Type of question being generated
            
        Returns:
            Generated question text
        """
        if self.llm_config.provider.value == "openai":
            import openai
            print(f"DEBUG: Using OpenAI with model {self.llm_config.model}")
            client = openai.OpenAI(api_key=self.llm_config.api_key)
            
            response = client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {"role": "system", "content": "You are an expert interviewer. Generate natural, conversational questions based on the given prompt. Keep responses concise and professional. NEVER use placeholder text like [specific technology] or [programming language]. Always reference actual details mentioned by the candidate or ask specific, concrete questions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            print(f"DEBUG: OpenAI response: {result}")
            return result
            
        elif self.llm_config.provider.value == "anthropic":
            import anthropic
            print(f"DEBUG: Using Anthropic with model {self.llm_config.model}")
            client = anthropic.Anthropic(api_key=self.llm_config.api_key)
            
            response = client.messages.create(
                model=self.llm_config.model,
                max_tokens=150,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": f"System: You are an expert interviewer. Generate natural, conversational questions based on the given prompt. Keep responses concise and professional. NEVER use placeholder text like [specific technology] or [programming language]. Always reference actual details mentioned by the candidate or ask specific, concrete questions.\n\nUser: {prompt}"}
                ]
            )
            
            result = response.content[0].text.strip()
            print(f"DEBUG: Anthropic response: {result}")
            return result
            
        else:
            raise ValueError(f"Unknown provider {self.llm_config.provider.value}")
    
    async def _generate_welcome_message(self, context: InterviewContext) -> str:
        """
        Generate a welcome message for the interview using the LLM.
        
        This method creates a personalized welcome message that:
        - Introduces the interviewer with a neutral name
        - Sets the interview context and expectations
        - Creates a professional but approachable tone
        - Includes a simple "Tell me about yourself" question
        - Mentions the interview type and company/role if available
        
        Args:
            context: Current interview context
            
        Returns:
            Welcome message text with first question
        """
        interview_type = context.interview_config.interview_type.value
        tone = context.interview_config.tone.value
        
        # Get company and role information if available
        company_name = getattr(context.candidate_info, 'company_name', None)
        role_title = getattr(context.candidate_info, 'role_title', None)
        
        # Choose a neutral interviewer name
        interviewer_names = ["Jordan", "Alex", "Casey", "Taylor"]
        interviewer_name = interviewer_names[hash(context.session_id) % len(interviewer_names)]
        
        # Build the prompt for the LLM
        prompt_parts = [
            f"You are {interviewer_name}, an expert interviewer conducting a {interview_type} interview.",
            f"Interview tone: {tone}",
            f"Interview type: {interview_type}"
        ]
        
        if company_name and role_title:
            prompt_parts.append(f"Company: {company_name}")
            prompt_parts.append(f"Position: {role_title}")
        elif role_title:
            prompt_parts.append(f"Position: {role_title}")
        
        prompt_parts.extend([
            "Generate a natural, conversational welcome message that:",
            "1. Introduces yourself by name",
            "2. If company and role information is provided, include it in your introduction (e.g., 'I'm Jordan, a Data Science Manager here at Netflix')",
            "3. Mentions the interview type",
            "4. Sets a professional but approachable tone",
            "5. Expresses enthusiasm for the conversation",
            "6. Ends with a simple question: 'Tell me about yourself'",
            "7. Keeps it concise (2-3 sentences max)",
            "",
            "IMPORTANT: Do NOT use placeholder text like [Company Name/Role] or [Position]. If company/role information is available, use the actual names. If not available, simply mention the interview type without placeholders.",
            "",
            "CRITICAL: If no specific company or role information is provided, do NOT use placeholders. Simply say something like 'I'll be conducting your technical interview today' without any brackets or placeholders.",
            "",
            "Write only the welcome message with the question, no additional text:"
        ])
        
        prompt = "\n".join(prompt_parts)
        print(f"DEBUG: Welcome message prompt: {prompt}")
        
        return await self._generate_question_from_prompt(prompt, "welcome")
    
    def _update_interview_context(self, context: InterviewContext, response: AgentResponse):
        """
        Update the interview context with the generated response.
        
        This method:
        - Updates conversation history
        - Tracks interview progression
        - Updates phase information
        - Maintains timing and question counts
        
        Args:
            context: Current interview context
            response: The generated response to record
        """
        # Update conversation history in context
        context.add_turn({
            "timestamp": time.time(),
            "speaker": "interviewer",
            "content": response.content,
            "message_type": "question",
            "metadata": response.metadata
        })
        
        # Update interview phase if needed
        if "phase" in response.metadata:
            self.current_phase = response.metadata["phase"]
    
    def update_configuration(self, llm_config: LLMConfig):
        """
        Update the agent's LLM configuration.
        
        This method allows dynamic configuration updates during the interview,
        such as switching models or adjusting parameters.
        
        Args:
            llm_config: New LLM configuration
        """
        self.llm_config = llm_config