"""Routing logic for the multi-agent system."""

from enum import Enum
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from .context import InterviewContext
    from .messaging import AgentMessage


class AgentCapability(Enum):
    """Capabilities that agents can have."""

    INTERVIEW_QUESTIONS = "interview_questions"
    CONVERSATION_FLOW = "conversation_flow"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    BEHAVIORAL_ASSESSMENT = "behavioral_assessment"
    CASE_STUDY_FACILITATION = "case_study_facilitation"
    FEEDBACK_ANALYSIS = "feedback_analysis"
    PERFORMANCE_SCORING = "performance_scoring"
    SUMMARY_GENERATION = "summary_generation"
    WEB_SEARCH = "web_search"
    RESEARCH = "research"
    INFORMATION_GATHERING = "information_gathering"


class RoutingDecision:
    """Decision about which agents should handle a message."""

    def __init__(self, primary_agent: str, supporting_agents: List[str] = None):
        self.primary_agent = primary_agent
        self.supporting_agents = supporting_agents or []

    def __repr__(self):
        return f"RoutingDecision(primary={self.primary_agent}, supporting={self.supporting_agents})"


class AgentSelector:
    """Selects the best agents for handling a message."""

    def __init__(self):
        self.agent_capabilities = {
            "interview": [
                AgentCapability.INTERVIEW_QUESTIONS,
                AgentCapability.CONVERSATION_FLOW,
                AgentCapability.TECHNICAL_ASSESSMENT,
                AgentCapability.BEHAVIORAL_ASSESSMENT,
                AgentCapability.CASE_STUDY_FACILITATION,
            ],
            "feedback": [
                AgentCapability.FEEDBACK_ANALYSIS,
                AgentCapability.PERFORMANCE_SCORING,
            ],
            "summary": [
                AgentCapability.SUMMARY_GENERATION,
                AgentCapability.PERFORMANCE_SCORING,
            ],
            "search": [
                AgentCapability.WEB_SEARCH,
                AgentCapability.RESEARCH,
                AgentCapability.INFORMATION_GATHERING,
            ],
        }

    def select_agents(
        self, message: "AgentMessage", context: "InterviewContext"
    ) -> RoutingDecision:
        """Select the best agents to handle a message."""

        # Calculate agent scores based on message content and context
        scores = self._calculate_agent_scores(message, context)

        # Select primary agent (highest score)
        primary_agent = max(scores.keys(), key=lambda k: scores[k])

        # Select supporting agents (scores above threshold)
        supporting_agents = [
            agent
            for agent, score in scores.items()
            if score > 0.3 and agent != primary_agent
        ]

        return RoutingDecision(primary_agent, supporting_agents)

    def _calculate_agent_scores(
        self, message: "AgentMessage", context: "InterviewContext"
    ) -> Dict[str, float]:
        """Calculate how well each agent can handle the message."""

        scores = {"interview": 0.0, "feedback": 0.0, "summary": 0.0, "search": 0.0}

        content_lower = message.content.lower()

        # Interview agent - handles most user responses
        if message.message_type.value == "user_response":
            scores["interview"] = 0.9

        # Summary agent - for summary requests
        if message.message_type.value == "summary_request":
            scores["summary"] = 0.9
            scores["interview"] = 0.0

        # AGGRESSIVE SEARCH LOGIC - The interviewer should proactively search for ANY factual information:

        # 1. Explicit search requests (user asks for research)
        search_keywords = [
            "search",
            "research",
            "find",
            "look up",
            "current",
            "trends",
            "company",
        ]
        if any(keyword in content_lower for keyword in search_keywords):
            scores["search"] = 0.9
            scores["interview"] = 0.3
            print(f"########## ROUTING: Explicit search request detected")

        # 2. ANY fact-finding questions (user asks for specific information)
        search_questions = [
            "what was",
            "who was",
            "what is",
            "who is",
            "can you find",
            "can you look up",
            "what's the name",
            "what's his name",
            "what's her name",
            "who is the",
            "what is the",
            "who was the",
            "what was the",
        ]
        if any(question in content_lower for question in search_questions):
            scores["search"] = 0.8
            scores["interview"] = 0.4
            print(f"########## ROUTING: Fact-finding question detected")

        # 3. ANY company mentions (even without leadership roles)
        company_names = [
            "zodiac",
            "metrics",
            "google",
            "amazon",
            "microsoft",
            "apple",
            "facebook",
            "meta",
            "netflix",
            "uber",
            "airbnb",
            "stripe",
            "square",
            "acme",
            "startup",
            "company",
        ]
        has_company_mention = any(company in content_lower for company in company_names)

        if has_company_mention:
            # If it's a detailed response (longer than 100 words), prioritize interview over search
            if len(message.content.split()) > 100:
                scores["search"] = 0.2  # Much lower search score for detailed responses
                scores[
                    "interview"
                ] = 0.9  # Much higher interview score for detailed responses
                print(
                    f"########## ROUTING: Company mention in detailed response - prioritizing interview"
                )
            else:
                scores["search"] = 0.4  # Lower search score generally
                scores["interview"] = 0.7  # Higher interview score
                print(
                    f"########## ROUTING: Company mention detected - minimal search trigger"
                )

        # 4. ANY leadership/person mentions (even without company names)
        leadership_indicators = [
            "ceo",
            "founder",
            "president",
            "director",
            "manager",
            "co-founder",
            "chief",
            "leader",
            "boss",
            "head",
            "executive",
        ]
        has_leadership_mention = any(
            role in content_lower for role in leadership_indicators
        )

        if has_leadership_mention:
            scores["search"] = 0.3  # Lower search score
            scores["interview"] = 0.8  # Higher interview score
            print(
                f"########## ROUTING: Leadership mention detected - minimal search trigger"
            )

        # 5. ANY technology/tool mentions that might need context
        tech_keywords = [
            "python",
            "r",
            "sql",
            "spark",
            "hadoop",
            "tensorflow",
            "pytorch",
            "scikit-learn",
            "pandas",
            "numpy",
            "aws",
            "gcp",
            "azure",
            "docker",
            "kubernetes",
            "machine learning",
            "ai",
            "data science",
        ]
        if any(tech in content_lower for tech in tech_keywords):
            scores["search"] = 0.2  # Very low search score for tech mentions
            scores["interview"] = 0.8  # High interview score
            print(
                f"########## ROUTING: Technology mention detected - minimal search trigger"
            )

        # 6. ANY project/role mentions that might need context
        project_indicators = [
            "project",
            "worked on",
            "led",
            "managed",
            "developed",
            "built",
            "implemented",
            "created",
            "designed",
            "architected",
        ]
        if any(indicator in content_lower for indicator in project_indicators):
            scores["search"] = 0.2  # Very low search score
            scores["interview"] = 0.8  # High interview score
            print(
                f"########## ROUTING: Project/role mention detected - minimal search trigger"
            )

        # 7. ANY time-based mentions that might need current context
        time_indicators = [
            "last year",
            "this year",
            "recently",
            "currently",
            "now",
            "today",
            "when",
            "during",
            "while",
        ]
        if any(time_indicator in content_lower for time_indicator in time_indicators):
            scores["search"] = 0.2  # Very low search score
            scores["interview"] = 0.8  # High interview score
            print(
                f"########## ROUTING: Time-based mention detected - minimal search trigger"
            )

        # 8. ANY specific names, places, or entities that might need verification
        specific_entities = [
            "new york",
            "san francisco",
            "seattle",
            "boston",
            "austin",
            "london",
            "berlin",
            "tokyo",
            "university",
            "college",
            "school",
            "institute",
        ]
        if any(entity in content_lower for entity in specific_entities):
            scores["search"] = 0.2  # Very low search score
            scores["interview"] = 0.8  # High interview score
            print(
                f"########## ROUTING: Specific entity mention detected - minimal search trigger"
            )

        # 9. ANY question marks (indicating information seeking)
        if "?" in message.content:
            # Boost search score for any question
            scores["search"] = max(scores["search"], 0.4)  # Lower boost
            print(f"########## ROUTING: Question detected - minimal search boost")

        # System events - handled by interview agent
        if message.message_type.value == "system_event":
            scores["interview"] = 0.9

        # Ensure at least one agent has a score
        if all(score == 0.0 for score in scores.values()):
            scores["interview"] = 0.5

        # Log the final scores for debugging
        if scores["search"] > 0.0:
            print(
                f"########## ROUTING: Final scores - search: {scores['search']}, interview: {scores['interview']}"
            )

        return scores
