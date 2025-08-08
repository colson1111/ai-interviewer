"""Contextual feedback system for interview responses."""

from typing import Dict, Any, List
from .assessors import AssessmentMetrics


class ContextualFeedback:
    """Handles contextual feedback based on response type and interview context."""
    
    def __init__(self):
        # Contextual scoring weights for different response types
        self.scoring_weights = {
            "technical": {
                "technical_depth": 0.25,
                "technical_accuracy": 0.20,
                "problem_solving": 0.20,
                "communication_clarity": 0.15,
                "specificity": 0.10,
                "structure": 0.10
            },
            "behavioral": {
                "star_method_usage": 0.25,
                "impact_quantification": 0.20,
                "specificity": 0.20,
                "communication_clarity": 0.15,
                "structure": 0.10,
                "communication_style": 0.10
            },
            "leadership": {
                "leadership_demonstration": 0.30,
                "impact_quantification": 0.20,
                "communication_clarity": 0.15,
                "specificity": 0.15,
                "structure": 0.10,
                "communication_style": 0.10
            },
            "project": {
                "specificity": 0.25,
                "structure": 0.20,
                "communication_clarity": 0.15,
                "technical_depth": 0.15,
                "problem_solving": 0.15,
                "communication_style": 0.10
            },
            "general": {
                "communication_clarity": 0.25,
                "structure": 0.20,
                "specificity": 0.20,
                "communication_style": 0.15,
                "technical_depth": 0.10,
                "problem_solving": 0.10
            }
        }
    
    def calculate_contextual_score(self, metrics: AssessmentMetrics, response_type: str) -> float:
        """Calculate a contextual score based on response type and metrics."""
        if not metrics or response_type not in self.scoring_weights:
            return 0.0
        
        weights = self.scoring_weights[response_type]
        total_score = 0.0
        
        for metric_name, weight in weights.items():
            if hasattr(metrics, metric_name):
                metric_value = getattr(metrics, metric_name)
                total_score += metric_value * weight
        
        return round(total_score, 2)
    
    def get_contextual_metrics(self, metrics: AssessmentMetrics, response_type: str) -> Dict[str, float]:
        """Get the most relevant metrics for a given response type."""
        if not metrics:
            return {}
        
        if response_type == "technical":
            return {
                "technical_accuracy": metrics.technical_accuracy,
                "problem_solving": metrics.problem_solving,
                "technical_depth": metrics.technical_depth
            }
        elif response_type == "behavioral":
            return {
                "star_method_usage": metrics.star_method_usage,
                "impact_quantification": metrics.impact_quantification,
                "specificity": metrics.specificity
            }
        elif response_type == "leadership":
            return {
                "leadership_demonstration": metrics.leadership_demonstration,
                "impact_quantification": metrics.impact_quantification,
                "communication_clarity": metrics.communication_clarity
            }
        elif response_type == "project":
            return {
                "specificity": metrics.specificity,
                "structure": metrics.structure,
                "technical_depth": metrics.technical_depth
            }
        else:  # general
            return {
                "communication_clarity": metrics.communication_clarity,
                "structure": metrics.structure,
                "specificity": metrics.specificity
            }
    
    def generate_contextual_strengths(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate contextually relevant strengths."""
        strengths = []
        
        if response_type == "technical":
            if metrics.technical_accuracy > 0.8:
                strengths.append("High technical accuracy demonstrated")
            if metrics.problem_solving > 0.7:
                strengths.append("Strong systematic problem-solving approach")
            if metrics.technical_depth > 0.7:
                strengths.append("Excellent technical depth and knowledge")
        
        elif response_type == "behavioral":
            if metrics.star_method_usage > 0.7:
                strengths.append("Excellent STAR method implementation")
            if metrics.impact_quantification > 0.6:
                strengths.append("Strong quantification of results and impact")
            if metrics.specificity > 0.7:
                strengths.append("Specific and detailed examples provided")
        
        elif response_type == "leadership":
            if metrics.leadership_demonstration > 0.7:
                strengths.append("Strong leadership qualities demonstrated")
            if metrics.impact_quantification > 0.6:
                strengths.append("Clear leadership impact and outcomes")
            if metrics.communication_clarity > 0.7:
                strengths.append("Excellent leadership communication")
        
        elif response_type == "project":
            if metrics.specificity > 0.7:
                strengths.append("Comprehensive project details provided")
            if metrics.structure > 0.7:
                strengths.append("Well-organized project explanation")
            if metrics.technical_depth > 0.6:
                strengths.append("Good technical understanding of project")
        
        else:  # general
            if metrics.communication_clarity > 0.7:
                strengths.append("Clear and effective communication")
            if metrics.structure > 0.7:
                strengths.append("Well-structured response")
            if metrics.specificity > 0.6:
                strengths.append("Good use of specific details")
        
        return strengths[:3]  # Limit to top 3 strengths
    
    def generate_contextual_improvements(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate contextually relevant improvement suggestions."""
        improvements = []
        
        if response_type == "technical":
            if metrics.technical_accuracy < 0.6:
                improvements.append("Verify technical concepts for accuracy")
            if metrics.problem_solving < 0.5:
                improvements.append("Show more systematic problem-solving steps")
            if metrics.technical_depth < 0.5:
                improvements.append("Add more technical depth and detail")
        
        elif response_type == "behavioral":
            if metrics.star_method_usage < 0.5:
                improvements.append("Use STAR method more effectively")
            if metrics.impact_quantification < 0.5:
                improvements.append("Quantify your impact and results more")
            if metrics.specificity < 0.5:
                improvements.append("Provide more specific examples")
        
        elif response_type == "leadership":
            if metrics.leadership_demonstration < 0.5:
                improvements.append("Demonstrate more leadership actions")
            if metrics.impact_quantification < 0.5:
                improvements.append("Show more leadership outcomes")
            if metrics.communication_clarity < 0.6:
                improvements.append("Improve leadership communication clarity")
        
        elif response_type == "project":
            if metrics.specificity < 0.5:
                improvements.append("Include more project-specific details")
            if metrics.structure < 0.6:
                improvements.append("Organize project explanation better")
            if metrics.technical_depth < 0.5:
                improvements.append("Add more technical project details")
        
        else:  # general
            if metrics.communication_clarity < 0.6:
                improvements.append("Improve communication clarity")
            if metrics.structure < 0.6:
                improvements.append("Better organize your response")
            if metrics.specificity < 0.5:
                improvements.append("Include more specific details")
        
        return improvements[:3]  # Limit to top 3 improvements
    
    def generate_contextual_suggestions(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate contextually relevant actionable suggestions."""
        suggestions = []
        
        if response_type == "technical":
            if metrics.technical_accuracy < 0.7:
                suggestions.append("Double-check technical terminology and concepts")
            if metrics.problem_solving < 0.6:
                suggestions.append("Walk through your problem-solving process step-by-step")
            if metrics.technical_depth < 0.6:
                suggestions.append("Explain the technical reasoning behind your approach")
        
        elif response_type == "behavioral":
            if metrics.star_method_usage < 0.6:
                suggestions.append("Structure your response: Situation, Task, Action, Result")
            if metrics.impact_quantification < 0.5:
                suggestions.append("Include specific metrics and measurable outcomes")
            if metrics.specificity < 0.6:
                suggestions.append("Provide concrete examples with specific details")
        
        elif response_type == "leadership":
            if metrics.leadership_demonstration < 0.6:
                suggestions.append("Focus on your leadership decisions and actions")
            if metrics.impact_quantification < 0.5:
                suggestions.append("Quantify your leadership impact and results")
            if metrics.communication_clarity < 0.7:
                suggestions.append("Clearly articulate your leadership approach")
        
        elif response_type == "project":
            if metrics.specificity < 0.6:
                suggestions.append("Include specific project details and metrics")
            if metrics.structure < 0.6:
                suggestions.append("Organize your project explanation chronologically")
            if metrics.technical_depth < 0.5:
                suggestions.append("Add more technical details about the project")
        
        else:  # general
            if metrics.communication_clarity < 0.7:
                suggestions.append("Use clearer, more concise language")
            if metrics.structure < 0.6:
                suggestions.append("Organize your thoughts before responding")
            if metrics.specificity < 0.6:
                suggestions.append("Include more specific examples and details")
        
        return suggestions[:2]  # Limit to top 2 suggestions
    
    def generate_contextual_technical_insights(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate technical insights for technical responses."""
        insights = []
        
        if response_type != "technical":
            return insights
        
        if metrics.technical_accuracy > 0.8:
            insights.append("High technical precision and accuracy demonstrated")
        
        if metrics.problem_solving > 0.7:
            insights.append("Excellent systematic approach to technical problems")
        
        if metrics.technical_depth > 0.7:
            insights.append("Strong technical foundation and knowledge base")
        
        if metrics.structure > 0.7:
            insights.append("Well-organized technical explanation")
        
        return insights[:2]  # Limit to top 2 insights
    
    def generate_contextual_communication_tips(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate communication tips based on response type."""
        tips = []
        
        if response_type == "technical":
            if metrics.communication_clarity < 0.7:
                tips.append("Simplify technical explanations for non-technical audiences")
            if metrics.structure < 0.6:
                tips.append("Organize technical concepts in logical order")
        
        elif response_type == "behavioral":
            if metrics.communication_clarity < 0.7:
                tips.append("Use clear, concise language when describing experiences")
            if metrics.structure < 0.6:
                tips.append("Structure behavioral responses with clear beginning, middle, and end")
        
        elif response_type == "leadership":
            if metrics.communication_clarity < 0.7:
                tips.append("Communicate leadership vision and strategy clearly")
            if metrics.communication_style < 0.7:
                tips.append("Maintain confident, authoritative tone when discussing leadership")
        
        elif response_type == "project":
            if metrics.communication_clarity < 0.7:
                tips.append("Explain project details in accessible language")
            if metrics.structure < 0.6:
                tips.append("Present project information in logical sequence")
        
        else:  # general
            if metrics.communication_clarity < 0.7:
                tips.append("Use clear, concise language")
            if metrics.communication_style < 0.7:
                tips.append("Maintain professional tone throughout")
        
        return tips[:2]  # Limit to top 2 tips
    
    def get_contextual_display_metrics(self, metrics: AssessmentMetrics, response_type: str) -> Dict[str, float]:
        """Get metrics to display based on response type."""
        if response_type == "technical":
            return {
                "Tech": metrics.technical_accuracy,
                "Problem": metrics.problem_solving,
                "Depth": metrics.technical_depth
            }
        elif response_type == "behavioral":
            return {
                "STAR": metrics.star_method_usage,
                "Impact": metrics.impact_quantification,
                "Detail": metrics.specificity
            }
        elif response_type == "leadership":
            return {
                "Leadership": metrics.leadership_demonstration,
                "Impact": metrics.impact_quantification,
                "Communication": metrics.communication_clarity
            }
        elif response_type == "project":
            return {
                "Detail": metrics.specificity,
                "Structure": metrics.structure,
                "Technical": metrics.technical_depth
            }
        else:  # general
            return {
                "Clarity": metrics.communication_clarity,
                "Structure": metrics.structure,
                "Detail": metrics.specificity
            } 