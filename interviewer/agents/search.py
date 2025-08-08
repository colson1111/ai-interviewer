"""Search agent for web research and information gathering."""

from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel

from .base import BaseInterviewAgent
from ..core import AgentMessage, AgentResponse, MessageType, InterviewContext, AgentCapability
from ..config import LLMConfig
from ..tools.web_search import (
    search_web, 
    search_interview_topics, 
    search_current_trends, 
    search_company_info
)


class SearchAgent(BaseInterviewAgent):
    """Agent responsible for web search and research capabilities."""
    
    def __init__(self, llm_config: LLMConfig):
        super().__init__("search", [
            AgentCapability.WEB_SEARCH,
            AgentCapability.RESEARCH,
            AgentCapability.INFORMATION_GATHERING
        ])
        
        # Initialize the LLM model
        if llm_config.provider.value == "openai":
            model = OpenAIModel(llm_config.model)
        elif llm_config.provider.value == "anthropic":
            model = AnthropicModel(llm_config.model)
        else:
            raise ValueError(f"Unsupported provider: {llm_config.provider}")
        
        # Create the Pydantic-AI agent
        system_prompt = """
You are a knowledgeable interviewer who has access to current information and can provide accurate details about companies, people, technologies, and events.

Your capabilities:
- Access current information about companies, CEOs, founders, and leadership
- Provide accurate details about technologies, tools, and industry trends
- Share information about specific projects, companies, and people
- Give context about recent developments and current events

IMPORTANT: When you detect mentions of companies, people, technologies, or specific facts that need verification, you MUST use the appropriate search function to gather current, accurate information. Then provide a natural, conversational response that incorporates the information without explicitly mentioning that you searched.

CRITICAL INSTRUCTIONS:
1. ALWAYS use search functions when asked about specific companies, people, or facts
2. For company questions, use search_company_info_tool with the company name from conversation context
3. For general questions, use general_web_search_tool
4. For technology questions, use search_current_trends_tool
5. Provide comprehensive information from search results - don't over-filter
6. Provide the information naturally as if you already know it
7. Never mention that you searched or looked things up
8. ONLY provide information that is clearly stated in the search results
9. If information is not found in search results, say "I don't have that specific information" rather than making things up
10. Be precise and accurate - don't fabricate names, dates, or details
11. Use conversation context to determine which company to search for

COMPANY SEARCH RULES:
- If the conversation mentions "Zodiac Metrics", always search for "Zodiac Metrics"
- If the conversation mentions "Artem Mariychin" or "Dan McCarthy", search for "Zodiac Metrics" (their company)
- Do NOT search for other companies unless explicitly mentioned
- Do NOT make assumptions about which company to search for
- Use the conversation history to determine the relevant company

RESULT PROCESSING:
- Provide comprehensive information from search results
- Don't over-filter or condense the information too much
- Include relevant details about company background, business model, history, etc.
- If search results contain founder information, include it naturally
- If search results contain other company information, include that too

For example:
- If someone asks "Who is the CEO of Zodiac Metrics?", use search_company_info_tool("Zodiac Metrics") and provide the CEO's name naturally
- If someone asks "Who founded Zodiac Metrics?", use search_company_info_tool("Zodiac Metrics") and provide the founder's name naturally
- If someone asks about a company's background, use search_company_info_tool and provide comprehensive information
- If search results don't contain the specific information requested, acknowledge that you don't have that information
- If someone asks "Was anyone else involved other than Artem Mariychin and Dan McCarthy?", search for "Zodiac Metrics" (their company)

Available search tools:
- search_company_info_tool(company_name): For company-specific information
- general_web_search_tool(query): For general web searches
- search_current_trends_tool(technology): For technology trends
- search_interview_topics_tool(topic): For interview-related research

Always provide information naturally and conversationally. Never mention that you're searching or looking things up - just provide the information as if you already know it.
"""
        
        self.pydantic_agent = Agent(model, system_prompt=system_prompt)
        
        # Register search tools
        self._register_search_tools()
    
    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Determine if this agent can handle the given message."""
        
        # Check if this is a search request
        search_keywords = ["search", "research", "find", "look up", "current", "trends", "company"]
        content_lower = message.content.lower()
        
        # High confidence for explicit search requests
        if any(keyword in content_lower for keyword in search_keywords):
            return 0.8
        
        # Medium confidence for questions about current information
        current_info_keywords = ["latest", "recent", "new", "update", "current", "trending"]
        if any(keyword in content_lower for keyword in current_info_keywords):
            return 0.6
        
        # Low confidence for general messages
        return 0.1
    
    def _register_search_tools(self):
        """Register web search tools with the agent."""
        
        @self.pydantic_agent.tool_plain
        def search_interview_topics_tool(topic: str, interview_type: str = "") -> str:
            """
            Search for interview-related information on a specific topic.
            
            Args:
                topic: The topic to search for
                interview_type: Optional interview type context
                
            Returns:
                Summary of relevant interview information
            """
            print(f"########## SEARCH AGENT: Using search_interview_topics_tool")
            print(f"########## SEARCH QUERY: topic='{topic}', interview_type='{interview_type}'")
            
            results = search_interview_topics(topic, interview_type)
            if not results.results:
                return f"No relevant information found for '{topic}' in {interview_type} interviews."
            
            summary = f"Found {len(results.results)} results for '{topic}' in {interview_type} interviews:\n\n"
            for i, result in enumerate(results.results, 1):
                summary += f"{i}. {result.title}\n{result.snippet}\n\n"
            
            print(f"########## SEARCH RESULTS: {len(results.results)} results found")
            return summary
        
        @self.pydantic_agent.tool_plain
        def search_current_trends_tool(technology_or_field: str) -> str:
            """
            Search for current trends in a technology or field.
            
            Args:
                technology_or_field: The technology or field to research
                
            Returns:
                Summary of current trends and developments
            """
            print(f"########## SEARCH AGENT: Using search_current_trends_tool")
            print(f"########## SEARCH QUERY: technology_or_field='{technology_or_field}'")
            
            results = search_current_trends(technology_or_field)
            if not results.results:
                return f"No current trends found for '{technology_or_field}'."
            
            summary = f"Current trends in '{technology_or_field}':\n\n"
            for i, result in enumerate(results.results, 1):
                summary += f"{i}. {result.title}\n{result.snippet}\n\n"
            
            print(f"########## SEARCH RESULTS: {len(results.results)} results found")
            return summary
        
        @self.pydantic_agent.tool_plain
        def search_company_info_tool(company_name: str) -> str:
            """
            Search for information about a specific company.
            
            Args:
                company_name: The company to research
                
            Returns:
                Summary of company information and background
            """
            print(f"########## SEARCH AGENT: Using search_company_info_tool")
            print(f"########## SEARCH QUERY: company_name='{company_name}'")
            
            results = search_company_info(company_name)
            if not results.results:
                return f"No information found for company '{company_name}'."
            
            summary = f"Information about '{company_name}':\n\n"
            for i, result in enumerate(results.results, 1):
                summary += f"{i}. {result.title}\n{result.snippet}\n\n"
            
            print(f"########## SEARCH RESULTS: {len(results.results)} results found")
            return summary
        
        @self.pydantic_agent.tool_plain
        def general_web_search_tool(query: str) -> str:
            """
            Perform a general web search for any topic.
            
            Args:
                query: The search query
                
            Returns:
                Summary of search results
            """
            print(f"########## SEARCH AGENT: Using general_web_search_tool")
            print(f"########## SEARCH QUERY: query='{query}'")
            
            results = search_web(query, max_results=3)
            if not results.results:
                return f"No results found for query: '{query}'"
            
            summary = f"Search results for '{query}':\n\n"
            for i, result in enumerate(results.results, 1):
                summary += f"{i}. {result.title}\n{result.snippet}\n\n"
            
            print(f"########## SEARCH RESULTS: {len(results.results)} results found")
            return summary
    
    def _extract_company_from_context(self, message: AgentMessage, context: InterviewContext) -> str:
        """Extract the most relevant company name from conversation context."""
        
        # First, check if the message explicitly mentions a company
        content_lower = message.content.lower()
        
        # Look for common company patterns in the current message
        company_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|LLC|Ltd|Company|Co)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Technologies|Tech|Analytics|Solutions|Systems)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Metrics|Data|AI|ML|Analytics)\b'
        ]
        
        import re
        if context.conversation_history:
            recent_turns = context.conversation_history[-2:]  # Only check last 2 turns
            for turn in recent_turns:
                # Handle both object and dictionary formats
                if hasattr(turn, 'content'):
                    turn_content = turn.content
                elif isinstance(turn, dict) and 'content' in turn:
                    turn_content = turn['content']
                else:
                    continue
                
                turn_content_lower = turn_content.lower()
                # Look for company patterns in recent turns
                for pattern in company_patterns:
                    matches = re.findall(pattern, turn_content)
                    if matches:
                        return matches[0]
        
        # If no company is mentioned in current message or recent context, return None
        # This prevents the search agent from searching when no company is relevant
        return None
    
    def _should_perform_search(self, message: AgentMessage) -> bool:
        """Determine if we should perform a search based on message content."""
        
        content_lower = message.content.lower()
        
        # Explicit search requests
        search_keywords = ["search", "research", "find", "look up", "current", "trends", "company"]
        if any(keyword in content_lower for keyword in search_keywords):
            return True
        
        # ANY fact-finding questions (user asks for specific information)
        search_questions = ["what was", "who was", "what is", "who is", "can you find", "can you look up", "what's the name", "what's his name", "what's her name", "who is the", "what is the", "who was the", "what was the"]
        if any(question in content_lower for question in search_questions):
            return True
        
        # ANY company mentions (even without leadership roles)
        company_names = ["zodiac", "metrics", "google", "amazon", "microsoft", "apple", "facebook", "meta", "netflix", "uber", "airbnb", "stripe", "square", "acme", "startup", "company"]
        if any(company in content_lower for company in company_names):
            return True
        
        # ANY leadership/person mentions (even without company names)
        leadership_indicators = ["ceo", "founder", "president", "director", "manager", "co-founder", "chief", "leader", "boss", "head", "executive"]
        if any(role in content_lower for role in leadership_indicators):
            return True
        
        # ANY technology mentions that might need context
        tech_keywords = ["python", "r", "sql", "spark", "hadoop", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "aws", "gcp", "azure", "docker", "kubernetes", "machine learning", "ai", "data science"]
        if any(tech in content_lower for tech in tech_keywords):
            return True
        
        # ANY project/role mentions
        project_indicators = ["project", "worked on", "led", "managed", "developed", "built", "implemented", "created", "designed", "architected"]
        if any(indicator in content_lower for indicator in project_indicators):
            return True
        
        # ANY time-based mentions
        time_indicators = ["last year", "this year", "recently", "currently", "now", "today", "when", "during", "while"]
        if any(time_indicator in content_lower for time_indicator in time_indicators):
            return True
        
        # ANY specific names, places, or entities
        specific_entities = ["new york", "san francisco", "seattle", "boston", "austin", "london", "berlin", "tokyo", "university", "college", "school", "institute"]
        if any(entity in content_lower for entity in specific_entities):
            return True
        
        # ANY question marks (indicating information seeking)
        if "?" in message.content:
            return True
        
        return False
    
    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """Process a search request and return research results."""
        
        if not self.is_enabled or not self.pydantic_agent:
            return self._create_response(
                content="Search functionality is currently unavailable.",
                confidence=0.0,
                metadata={"error": "Search agent not enabled"}
            )
        
        try:
            # Check if we should perform a search
            should_search = self._should_perform_search(message)
            
            if not should_search:
                return self._create_response(
                    content="",  # No response needed
                    confidence=0.0,
                    metadata={"skipped": "No search needed"}
                )
            
            # Extract company from context
            company_name = self._extract_company_from_context(message, context)
            
            # If no company is mentioned, don't perform search
            if not company_name:
                return self._create_response(
                    content="",  # No response needed
                    confidence=0.0,
                    metadata={"skipped": "No company mentioned"}
                )
            
            print(f"########## SEARCH AGENT: Using company from context: '{company_name}'")
            
            # Create a message for the Pydantic-AI agent with company context
            enhanced_message = f"Company: {company_name}\n\nUser question: {message.content}"
            
            # Process with Pydantic-AI agent
            result = await self.pydantic_agent.run(enhanced_message)
            
            # Extract content from result
            if hasattr(result, 'content') and result.content:
                content = result.content
            elif hasattr(result, 'message') and result.message:
                content = result.message
            elif isinstance(result, str):
                content = result
            else:
                content = "I couldn't find specific information about that."
            
            print(f"########## SEARCH RESPONSE: {len(content)} characters")
            
            return self._create_response(
                content=content,
                confidence=0.8,
                metadata={"search_performed": True, "company": company_name}
            )
            
        except Exception as e:
            print(f"########## SEARCH AGENT: Error occurred")
            print(f"########## SEARCH ERROR: {e}")
            import traceback
            traceback.print_exc()
            return self._create_response(
                content=f"Search failed: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            ) 