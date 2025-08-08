"""Feedback agent for real-time response analysis and performance scoring."""

from typing import List, Dict, Any, Optional
import time

from .base import BaseInterviewAgent
from ..core import InterviewContext, AgentMessage, AgentResponse, AgentCapability
from ..feedback import ResponseAssessor, ResponseClassifier, FeedbackGenerator, ContextualFeedback


class FeedbackAgent(BaseInterviewAgent):
    """
    Agent that analyzes candidate responses in real-time and provides
    feedback data for the live feedback widget.
    """
    
    def __init__(self):
        super().__init__(
            name="feedback",
            capabilities=[
                AgentCapability.FEEDBACK_ANALYSIS,
                AgentCapability.PERFORMANCE_SCORING
            ]
        )
        self.analysis_history = []
        
        # Initialize modular feedback components
        self.assessor = ResponseAssessor()
        self.classifier = ResponseClassifier()
        self.generator = FeedbackGenerator()
        self.contextual = ContextualFeedback()
    
    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        """Feedback agent can analyze any user response."""
        if message.sender == "user":
            return 0.9  # High confidence for user messages
        return 0.1  # Low confidence for interviewer messages
    
    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        """Analyze the candidate's response and provide feedback data."""
        
        try:
            # Check if this response should be evaluated
            if not self.classifier.should_evaluate_response(message.content, context):
                return self._create_response(
                    content="",  # Empty content means no feedback
                    confidence=0.0,
                    metadata={"skipped": "Response not suitable for evaluation"}
                )
            
            # Analyze the response using modular system
            analysis = self._analyze_response(message.content, context)
            
            # Store analysis in history
            self.analysis_history.append({
                "timestamp": time.time(),
                "message": message.content,
                "analysis": analysis
            })
            
            # Generate feedback content for the widget
            feedback_content = self._generate_feedback_display(analysis)
            
            return self._create_response(
                content=feedback_content,
                confidence=0.8,
                metadata={
                    "analysis": analysis,
                    "feedback_type": "real_time",
                    "session_id": context.session_id
                }
            )
            
        except Exception as e:
            return self._create_response(
                content="Feedback analysis unavailable",
                confidence=0.1,
                metadata={"error": str(e)}
            )
    
    def _analyze_response(self, response: str, context: InterviewContext) -> Dict[str, Any]:
        """Analyze the response using the modular feedback system."""
        
        # Classify response type
        response_type = self.classifier.classify_response_type(response, context)
        
        # Assess response using modular assessor
        metrics = self.assessor.assess_response(response, context)
        
        # Calculate contextual score
        overall_score = self.contextual.calculate_contextual_score(metrics, response_type)
        
        # Generate contextual feedback
        strengths = self.contextual.generate_contextual_strengths(metrics, response_type)
        improvements = self.contextual.generate_contextual_improvements(metrics, response_type)
        suggestions = self.contextual.generate_contextual_suggestions(metrics, response_type)
        technical_insights = self.contextual.generate_contextual_technical_insights(metrics, response_type)
        communication_tips = self.contextual.generate_contextual_communication_tips(metrics, response_type)
        
        # Get contextual display metrics
        display_metrics = self.contextual.get_contextual_display_metrics(metrics, response_type)
        
        return {
            "response_type": response_type,
            "overall_score": overall_score,
            "strengths": strengths,
            "improvements": improvements,
            "specific_suggestions": suggestions,
            "technical_insights": technical_insights,
            "communication_tips": communication_tips,
            "display_metrics": display_metrics,
            # Include all metrics for detailed analysis
            "technical_depth": metrics.technical_depth,
            "technical_accuracy": metrics.technical_accuracy,
            "communication_clarity": metrics.communication_clarity,
            "specificity": metrics.specificity,
            "structure": metrics.structure,
            "problem_solving": metrics.problem_solving,
            "communication_style": metrics.communication_style,
            "star_method_usage": metrics.star_method_usage,
            "impact_quantification": metrics.impact_quantification,
            "leadership_demonstration": metrics.leadership_demonstration,
            "word_count": metrics.word_count,
            "keywords": metrics.keywords,
            "sentiment": metrics.sentiment,
            "completeness": metrics.completeness
        }
    
    def _generate_feedback_display(self, analysis: Dict[str, Any]) -> str:
        """Generate feedback display using the modular generator."""
        # Convert analysis dict to AssessmentMetrics for the generator
        from ..feedback.assessors import AssessmentMetrics
        
        metrics = AssessmentMetrics(
            technical_depth=analysis.get("technical_depth", 0.0),
            technical_accuracy=analysis.get("technical_accuracy", 0.0),
            communication_clarity=analysis.get("communication_clarity", 0.0),
            specificity=analysis.get("specificity", 0.0),
            structure=analysis.get("structure", 0.0),
            problem_solving=analysis.get("problem_solving", 0.0),
            communication_style=analysis.get("communication_style", 0.0),
            star_method_usage=analysis.get("star_method_usage", 0.0),
            impact_quantification=analysis.get("impact_quantification", 0.0),
            leadership_demonstration=analysis.get("leadership_demonstration", 0.0),
            word_count=analysis.get("word_count", 0),
            keywords=analysis.get("keywords", []),
            sentiment=analysis.get("sentiment", "neutral"),
            completeness=analysis.get("completeness", 0.0)
        )
        
        response_type = analysis.get("response_type", "general")
        return self.generator.generate_feedback_display(metrics, response_type)
    
    def get_session_summary(self, context: InterviewContext) -> Dict[str, Any]:
        """Generate a summary of feedback for the entire session."""
        if not self.analysis_history:
            return {"error": "No analysis data available"}
        
        # Extract metrics and response types for summary
        all_metrics = []
        response_types = []
        
        for analysis_item in self.analysis_history:
            analysis = analysis_item["analysis"]
            response_types.append(analysis.get("response_type", "general"))
            
            # Convert to AssessmentMetrics for summary generation
            from ..feedback.assessors import AssessmentMetrics
            metrics = AssessmentMetrics(
                technical_depth=analysis.get("technical_depth", 0.0),
                technical_accuracy=analysis.get("technical_accuracy", 0.0),
                communication_clarity=analysis.get("communication_clarity", 0.0),
                specificity=analysis.get("specificity", 0.0),
                structure=analysis.get("structure", 0.0),
                problem_solving=analysis.get("problem_solving", 0.0),
                communication_style=analysis.get("communication_style", 0.0),
                star_method_usage=analysis.get("star_method_usage", 0.0),
                impact_quantification=analysis.get("impact_quantification", 0.0),
                leadership_demonstration=analysis.get("leadership_demonstration", 0.0),
                word_count=analysis.get("word_count", 0),
                keywords=analysis.get("keywords", []),
                sentiment=analysis.get("sentiment", "neutral"),
                completeness=analysis.get("completeness", 0.0)
            )
            all_metrics.append(metrics)
        
        return self.generator.generate_summary_feedback(all_metrics, response_types)