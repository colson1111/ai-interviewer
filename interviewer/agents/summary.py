"""Summary agent for generating comprehensive interview analysis and reports."""

import time
from datetime import datetime
from typing import Any, Dict, List

from ..core import AgentCapability, AgentMessage, AgentResponse, InterviewContext
from .base import BaseInterviewAgent


class SummaryAgent(BaseInterviewAgent):
    """
    Agent that generates comprehensive interview summaries and analysis
    at the end of an interview session.
    """

    def __init__(self):
        super().__init__(
            name="summary",
            capabilities=[
                AgentCapability.SUMMARY_GENERATION,
                AgentCapability.PERFORMANCE_SCORING,
            ],
        )

    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Summary agent handles interview completion and summary requests."""
        content = message.content.lower()

        # High confidence for explicit summary requests
        if any(
            keyword in content
            for keyword in [
                "summary",
                "wrap up",
                "conclude",
                "end interview",
                "final thoughts",
            ]
        ):
            return 0.9

        # Medium confidence for interview completion indicators
        if context.current_phase.value in ["wrap_up", "completed"]:
            return 0.8

        # Low confidence for general messages
        return 0.1

    async def process(
        self, message: AgentMessage, context: InterviewContext
    ) -> AgentResponse:
        """Generate a comprehensive interview summary."""

        try:
            # Generate the summary
            summary_data = self._generate_comprehensive_summary(context)

            # Create human-readable summary text
            summary_text = self._format_summary_text(summary_data)

            return self._create_response(
                content=summary_text,
                confidence=0.9,
                metadata={
                    "summary_data": summary_data,
                    "summary_type": "comprehensive",
                    "generated_at": time.time(),
                },
            )

        except Exception as e:
            return self._create_response(
                content="Unable to generate interview summary at this time.",
                confidence=0.1,
                metadata={"error": str(e)},
            )

    def _generate_comprehensive_summary(
        self, context: InterviewContext
    ) -> Dict[str, Any]:
        """Generate comprehensive summary data."""

        # Basic interview metrics
        duration = context.get_interview_duration()
        total_turns = len(context.conversation_history)
        user_turns = [
            turn for turn in context.conversation_history if turn.speaker == "user"
        ]

        # Performance analysis
        feedback_data = context.get_agent_state("feedback")
        performance_scores = self._extract_performance_scores(feedback_data)

        # Conversation analysis
        conversation_analysis = self._analyze_conversation_flow(context)

        # Technical assessment
        technical_analysis = self._assess_technical_competency(context)

        # Communication assessment
        communication_analysis = self._assess_communication_skills(context)

        # Overall recommendations
        recommendations = self._generate_recommendations(
            performance_scores, technical_analysis, communication_analysis
        )

        summary_data = {
            "interview_metadata": {
                "session_id": context.session_id,
                "duration_minutes": round(duration / 60, 1),
                "total_exchanges": total_turns // 2,  # Approximate back-and-forth count
                "interview_type": context.interview_config.interview_type.value,
                "difficulty": context.interview_config.difficulty.value,
                "completed_at": datetime.now().isoformat(),
                "phases_covered": self._identify_phases_covered(context),
            },
            "performance_summary": {
                "overall_score": performance_scores.get("overall_average", 0.0),
                "technical_competency": technical_analysis["score"],
                "communication_effectiveness": communication_analysis["score"],
                "response_quality": performance_scores.get("quality_average", 0.0),
                "engagement_level": conversation_analysis["engagement_score"],
            },
            "detailed_analysis": {
                "strengths": self._identify_key_strengths(context, performance_scores),
                "areas_for_improvement": self._identify_improvement_areas(
                    context, performance_scores
                ),
                "technical_highlights": technical_analysis["highlights"],
                "communication_highlights": communication_analysis["highlights"],
                "question_handling": conversation_analysis["question_handling"],
            },
            "recommendations": recommendations,
            "conversation_insights": {
                "average_response_length": self._calculate_avg_response_length(
                    user_turns
                ),
                "technical_depth_trend": performance_scores.get("technical_trend", []),
                "confidence_trend": conversation_analysis["confidence_trend"],
                "topic_coverage": self._analyze_topic_coverage(context),
            },
        }

        return summary_data

    def _extract_performance_scores(
        self, feedback_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract performance scores from feedback agent data."""
        if not feedback_data:
            return {
                "overall_average": 0.6,
                "quality_average": 0.6,
                "technical_trend": [],
                "scores_available": False,
            }

        # If we have detailed feedback analysis data
        if "analysis_history" in feedback_data:
            return feedback_data

        # Default scores if no detailed data
        return {
            "overall_average": 0.65,
            "quality_average": 0.6,
            "technical_trend": [0.5, 0.6, 0.65],
            "scores_available": False,
        }

    def _analyze_conversation_flow(self, context: InterviewContext) -> Dict[str, Any]:
        """Analyze the flow and engagement of the conversation."""
        user_turns = [
            turn for turn in context.conversation_history if turn.speaker == "user"
        ]

        # Calculate engagement metrics
        total_words = sum(len(turn.content.split()) for turn in user_turns)
        avg_response_length = total_words / max(len(user_turns), 1)

        # Engagement score based on response length and consistency
        engagement_score = min(
            1.0, avg_response_length / 30.0
        )  # 30 words = good engagement

        # Analyze confidence trends (simplified)
        confidence_indicators = ["confident", "sure", "definitely", "clearly"]
        uncertainty_indicators = ["maybe", "not sure", "uncertain", "think"]

        confidence_trend = []
        for turn in user_turns[-5:]:  # Last 5 responses
            content_lower = turn.content.lower()
            confident_count = sum(
                1 for indicator in confidence_indicators if indicator in content_lower
            )
            uncertain_count = sum(
                1 for indicator in uncertainty_indicators if indicator in content_lower
            )

            if confident_count > uncertain_count:
                confidence_trend.append(0.8)
            elif uncertain_count > confident_count:
                confidence_trend.append(0.3)
            else:
                confidence_trend.append(0.6)

        # Question handling analysis
        questions_asked = sum(1 for turn in user_turns if "?" in turn.content)
        question_handling = "proactive" if questions_asked > 2 else "responsive"

        return {
            "engagement_score": round(engagement_score, 2),
            "confidence_trend": confidence_trend,
            "question_handling": question_handling,
            "questions_asked": questions_asked,
            "avg_response_length": round(avg_response_length, 1),
        }

    def _assess_technical_competency(self, context: InterviewContext) -> Dict[str, Any]:
        """Assess technical competency based on conversation content."""
        user_turns = [
            turn for turn in context.conversation_history if turn.speaker == "user"
        ]
        all_user_content = " ".join(turn.content for turn in user_turns).lower()

        # Technical terms assessment
        technical_terms = [
            "algorithm",
            "model",
            "data",
            "python",
            "sql",
            "machine learning",
            "statistics",
            "analysis",
            "database",
            "api",
            "framework",
            "library",
            "optimization",
            "performance",
            "scalability",
            "architecture",
        ]

        technical_mentions = sum(
            1 for term in technical_terms if term in all_user_content
        )
        technical_score = min(1.0, technical_mentions / 10.0)

        highlights = []
        if technical_mentions >= 8:
            highlights.append("Strong technical vocabulary")
        if "algorithm" in all_user_content and "optimization" in all_user_content:
            highlights.append("Understanding of algorithmic complexity")
        if any(term in all_user_content for term in ["python", "sql", "framework"]):
            highlights.append("Practical programming knowledge")

        return {
            "score": round(technical_score, 2),
            "technical_mentions": technical_mentions,
            "highlights": highlights or ["Basic technical understanding demonstrated"],
        }

    def _assess_communication_skills(self, context: InterviewContext) -> Dict[str, Any]:
        """Assess communication effectiveness."""
        user_turns = [
            turn for turn in context.conversation_history if turn.speaker == "user"
        ]

        # Calculate communication metrics
        total_words = sum(len(turn.content.split()) for turn in user_turns)
        avg_response_length = total_words / max(len(user_turns), 1)

        # Structure indicators
        structure_indicators = [
            "first",
            "second",
            "then",
            "because",
            "therefore",
            "for example",
        ]
        structure_count = 0

        for turn in user_turns:
            content_lower = turn.content.lower()
            structure_count += sum(
                1 for indicator in structure_indicators if indicator in content_lower
            )

        # Communication score
        length_score = min(1.0, avg_response_length / 25.0)  # 25 words = good length
        structure_score = min(
            1.0, structure_count / (len(user_turns) * 2)
        )  # 2 indicators per response ideal

        communication_score = (length_score + structure_score) / 2

        highlights = []
        if avg_response_length >= 30:
            highlights.append("Detailed responses")
        if structure_count >= len(user_turns):
            highlights.append("Well-structured explanations")
        if any("for example" in turn.content.lower() for turn in user_turns):
            highlights.append("Concrete examples provided")

        return {
            "score": round(communication_score, 2),
            "avg_response_length": round(avg_response_length, 1),
            "structure_score": round(structure_score, 2),
            "highlights": highlights or ["Clear communication demonstrated"],
        }

    def _identify_phases_covered(self, context: InterviewContext) -> List[str]:
        """Identify which interview phases were covered."""
        phases = []

        # Simple heuristic based on conversation content
        all_content = " ".join(
            turn.content for turn in context.conversation_history
        ).lower()

        if any(
            keyword in all_content
            for keyword in ["experience", "background", "previous"]
        ):
            phases.append("Background Discussion")

        if any(
            keyword in all_content for keyword in ["technical", "algorithm", "code"]
        ):
            phases.append("Technical Assessment")

        if any(keyword in all_content for keyword in ["project", "team", "challenge"]):
            phases.append("Behavioral Questions")

        if any(keyword in all_content for keyword in ["case", "business", "scenario"]):
            phases.append("Case Study")

        return phases or ["General Discussion"]

    def _identify_key_strengths(
        self, context: InterviewContext, performance_scores: Dict[str, Any]
    ) -> List[str]:
        """Identify the candidate's key strengths."""
        strengths = []

        # From performance scores
        if performance_scores.get("overall_average", 0) >= 0.7:
            strengths.append("Consistently strong responses")

        # From technical assessment
        technical_data = self._assess_technical_competency(context)
        if technical_data["score"] >= 0.6:
            strengths.append("Good technical foundation")

        # From communication assessment
        communication_data = self._assess_communication_skills(context)
        if communication_data["score"] >= 0.7:
            strengths.append("Effective communication skills")

        # From conversation analysis
        conversation_data = self._analyze_conversation_flow(context)
        if conversation_data["engagement_score"] >= 0.7:
            strengths.append("High engagement and participation")

        return strengths[:4]  # Limit to top 4 strengths

    def _identify_improvement_areas(
        self, context: InterviewContext, performance_scores: Dict[str, Any]
    ) -> List[str]:
        """Identify areas for improvement."""
        improvements = []

        # From technical assessment
        technical_data = self._assess_technical_competency(context)
        if technical_data["score"] < 0.5:
            improvements.append("Expand technical vocabulary and concepts")

        # From communication assessment
        communication_data = self._assess_communication_skills(context)
        if communication_data["score"] < 0.6:
            improvements.append("Provide more structured and detailed responses")

        # From conversation flow
        conversation_data = self._analyze_conversation_flow(context)
        if conversation_data["questions_asked"] < 2:
            improvements.append("Ask more clarifying questions")

        if conversation_data["avg_response_length"] < 15:
            improvements.append("Elaborate more on answers")

        return improvements[:3]  # Limit to top 3 improvements

    def _generate_recommendations(
        self,
        performance_scores: Dict[str, Any],
        technical_analysis: Dict[str, Any],
        communication_analysis: Dict[str, Any],
    ) -> List[str]:
        """Generate specific recommendations for the candidate."""
        recommendations = []

        overall_score = performance_scores.get("overall_average", 0.6)

        if overall_score >= 0.8:
            recommendations.append(
                "Excellent interview performance! Focus on maintaining this level."
            )
        elif overall_score >= 0.6:
            recommendations.append(
                "Good foundation demonstrated. Continue practicing interview skills."
            )
        else:
            recommendations.append(
                "Focus on providing more detailed and specific responses."
            )

        if technical_analysis["score"] < 0.6:
            recommendations.append(
                "Review core technical concepts and practice explaining them clearly."
            )

        if communication_analysis["score"] < 0.6:
            recommendations.append(
                "Practice structuring responses with clear examples and logical flow."
            )

        return recommendations

    def _calculate_avg_response_length(self, user_turns: List[Any]) -> float:
        """Calculate average response length in words."""
        if not user_turns:
            return 0.0

        total_words = sum(len(turn.content.split()) for turn in user_turns)
        return round(total_words / len(user_turns), 1)

    def _analyze_topic_coverage(self, context: InterviewContext) -> List[str]:
        """Analyze what topics were covered during the interview."""
        all_content = " ".join(
            turn.content for turn in context.conversation_history
        ).lower()

        topics = []
        topic_keywords = {
            "Machine Learning": [
                "machine learning",
                "ml",
                "model",
                "algorithm",
                "prediction",
            ],
            "Data Analysis": [
                "data analysis",
                "statistics",
                "visualization",
                "insights",
            ],
            "Programming": [
                "python",
                "code",
                "programming",
                "implementation",
                "development",
            ],
            "Databases": ["sql", "database", "query", "data storage"],
            "Business Understanding": [
                "business",
                "stakeholder",
                "requirement",
                "process",
            ],
            "Problem Solving": [
                "approach",
                "solution",
                "problem",
                "challenge",
                "methodology",
            ],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in all_content for keyword in keywords):
                topics.append(topic)

        return topics

    def _format_summary_text(self, summary_data: Dict[str, Any]) -> str:
        """Format the summary data into human-readable text."""
        metadata = summary_data["interview_metadata"]
        performance = summary_data["performance_summary"]
        analysis = summary_data["detailed_analysis"]

        summary_text = f"""
## Interview Summary

**Session Details:**
- Duration: {metadata['duration_minutes']} minutes
- Interview Type: {metadata['interview_type']}
- Total Exchanges: {metadata['total_exchanges']}

**Performance Overview:**
- Overall Score: {performance['overall_score']:.1f}/1.0
- Technical Competency: {performance['technical_competency']:.1f}/1.0
- Communication Effectiveness: {performance['communication_effectiveness']:.1f}/1.0

**Key Strengths:**
{chr(10).join(f'• {strength}' for strength in analysis['strengths'])}

**Areas for Improvement:**
{chr(10).join(f'• improvement' for improvement in analysis['areas_for_improvement'])}

**Recommendations:**
{chr(10).join(f'• {rec}' for rec in summary_data['recommendations'])}

This is a comprehensive AI-generated summary based on your interview performance.
"""

        return summary_text.strip()
