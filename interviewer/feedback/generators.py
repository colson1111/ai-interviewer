"""Feedback generation and display for interview responses."""

from typing import Dict, Any, List
from .assessors import AssessmentMetrics


class FeedbackGenerator:
    """Generates feedback content based on assessment metrics."""
    
    def __init__(self):
        self.strength_templates = {
            "technical": [
                "Strong technical knowledge demonstrated",
                "Excellent technical depth and precision",
                "Good understanding of technical concepts",
                "Solid technical foundation shown"
            ],
            "behavioral": [
                "Great use of specific examples",
                "Strong behavioral response with clear structure",
                "Excellent demonstration of relevant experience",
                "Good use of STAR method"
            ],
            "leadership": [
                "Strong leadership qualities demonstrated",
                "Excellent strategic thinking shown",
                "Good demonstration of influence and collaboration",
                "Solid leadership approach"
            ],
            "project": [
                "Comprehensive project understanding",
                "Strong project management skills",
                "Excellent attention to project details",
                "Good project execution approach"
            ],
            "general": [
                "Clear and well-structured response",
                "Good communication skills demonstrated",
                "Comprehensive answer provided",
                "Strong response overall"
            ]
        }
        
        self.improvement_templates = {
            "technical": [
                "Consider adding more technical details",
                "Could benefit from more specific technical examples",
                "Try to include more technical depth",
                "Consider elaborating on technical approach"
            ],
            "behavioral": [
                "Consider using more specific examples",
                "Could benefit from more detailed STAR structure",
                "Try to include more quantifiable results",
                "Consider adding more context to your examples"
            ],
            "leadership": [
                "Consider demonstrating more leadership impact",
                "Could benefit from more strategic thinking examples",
                "Try to include more influence and collaboration details",
                "Consider adding more leadership context"
            ],
            "project": [
                "Consider adding more project management details",
                "Could benefit from more specific project metrics",
                "Try to include more project execution details",
                "Consider elaborating on project challenges and solutions"
            ],
            "general": [
                "Consider adding more specific details",
                "Could benefit from more concrete examples",
                "Try to include more quantifiable results",
                "Consider adding more context to your response"
            ]
        }
    
    def generate_strengths(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate strengths based on assessment metrics and response type."""
        strengths = []
        
        # Type-specific strengths
        if response_type in self.strength_templates:
            strengths.extend(self.strength_templates[response_type][:2])
        
        # Metric-based strengths
        if metrics.technical_depth > 0.7:
            strengths.append("Strong technical depth demonstrated")
        elif metrics.technical_depth > 0.5:
            strengths.append("Good technical understanding")
        
        if metrics.communication_clarity > 0.8:
            strengths.append("Excellent communication clarity")
        elif metrics.communication_clarity > 0.6:
            strengths.append("Clear and well-structured communication")
        
        if metrics.specificity > 0.7:
            strengths.append("Specific examples and details provided")
        elif metrics.specificity > 0.5:
            strengths.append("Good level of detail")
        
        if metrics.structure > 0.7:
            strengths.append("Well-organized response structure")
        elif metrics.structure > 0.5:
            strengths.append("Good logical flow")
        
        # Response type specific strengths
        if response_type == "technical":
            if metrics.technical_accuracy > 0.8:
                strengths.append("High technical accuracy")
            if metrics.problem_solving > 0.7:
                strengths.append("Strong problem-solving approach")
        
        elif response_type == "behavioral":
            if metrics.star_method_usage > 0.7:
                strengths.append("Excellent STAR method usage")
            if metrics.impact_quantification > 0.6:
                strengths.append("Good quantification of impact")
        
        elif response_type == "leadership":
            if metrics.leadership_demonstration > 0.7:
                strengths.append("Strong leadership demonstration")
            if metrics.impact_quantification > 0.6:
                strengths.append("Good leadership impact shown")
        
        return strengths[:3]  # Limit to top 3 strengths
    
    def generate_improvements(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate improvement suggestions based on assessment metrics and response type."""
        improvements = []
        
        # Type-specific improvements
        if response_type in self.improvement_templates:
            improvements.extend(self.improvement_templates[response_type][:2])
        
        # Metric-based improvements
        if metrics.technical_depth < 0.5:
            improvements.append("Add more technical depth and detail")
        elif metrics.technical_depth < 0.7:
            improvements.append("Consider deepening technical explanation")
        
        if metrics.communication_clarity < 0.6:
            improvements.append("Improve clarity and structure")
        elif metrics.communication_clarity < 0.8:
            improvements.append("Enhance communication flow")
        
        if metrics.specificity < 0.5:
            improvements.append("Provide more specific examples")
        elif metrics.specificity < 0.7:
            improvements.append("Add more concrete details")
        
        if metrics.structure < 0.6:
            improvements.append("Improve response organization")
        elif metrics.structure < 0.8:
            improvements.append("Enhance logical flow")
        
        # Response type specific improvements
        if response_type == "technical":
            if metrics.technical_accuracy < 0.6:
                improvements.append("Verify technical accuracy")
            if metrics.problem_solving < 0.5:
                improvements.append("Show more systematic problem-solving approach")
        
        elif response_type == "behavioral":
            if metrics.star_method_usage < 0.5:
                improvements.append("Use STAR method more effectively")
            if metrics.impact_quantification < 0.5:
                improvements.append("Quantify impact and results more")
        
        elif response_type == "leadership":
            if metrics.leadership_demonstration < 0.5:
                improvements.append("Demonstrate more leadership impact")
            if metrics.impact_quantification < 0.5:
                improvements.append("Show more leadership outcomes")
        
        return improvements[:3]  # Limit to top 3 improvements
    
    def generate_suggestions(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate specific actionable suggestions."""
        suggestions = []
        
        # General suggestions
        if metrics.word_count < 50:
            suggestions.append("Expand your response with more detail")
        
        if len(metrics.keywords) < 3:
            suggestions.append("Use more relevant technical terminology")
        
        # Type-specific suggestions
        if response_type == "technical":
            if metrics.technical_accuracy < 0.7:
                suggestions.append("Double-check technical concepts for accuracy")
            if metrics.problem_solving < 0.6:
                suggestions.append("Show your step-by-step problem-solving process")
        
        elif response_type == "behavioral":
            if metrics.star_method_usage < 0.6:
                suggestions.append("Structure your response using STAR method")
            if metrics.impact_quantification < 0.5:
                suggestions.append("Include specific metrics and outcomes")
        
        elif response_type == "leadership":
            if metrics.leadership_demonstration < 0.6:
                suggestions.append("Focus on your leadership actions and decisions")
            if metrics.impact_quantification < 0.5:
                suggestions.append("Quantify your leadership impact")
        
        return suggestions[:2]  # Limit to top 2 suggestions
    
    def generate_technical_insights(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate technical insights for technical responses."""
        insights = []
        
        if response_type != "technical":
            return insights
        
        if metrics.technical_depth > 0.7:
            insights.append("Strong technical foundation demonstrated")
        
        if metrics.technical_accuracy > 0.8:
            insights.append("High technical precision shown")
        
        if metrics.problem_solving > 0.7:
            insights.append("Excellent systematic approach to technical problems")
        
        if metrics.structure > 0.7:
            insights.append("Well-organized technical explanation")
        
        return insights[:2]  # Limit to top 2 insights
    
    def generate_communication_tips(self, metrics: AssessmentMetrics, response_type: str) -> List[str]:
        """Generate communication tips for all response types."""
        tips = []
        
        if metrics.communication_clarity < 0.7:
            tips.append("Use clearer, more concise language")
        
        if metrics.structure < 0.6:
            tips.append("Organize your thoughts before speaking")
        
        if metrics.communication_style < 0.7:
            tips.append("Maintain professional tone throughout")
        
        if metrics.specificity < 0.6:
            tips.append("Include more specific examples and details")
        
        return tips[:2]  # Limit to top 2 tips
    
    def generate_feedback_display(self, metrics: AssessmentMetrics, response_type: str) -> str:
        """Generate the feedback display string for the UI."""
        if not metrics:
            return "Feedback analysis available"
        
        # Overall score
        score_display = f"{metrics.technical_depth:.1f}/1.0"  # Using technical_depth as overall score
        
        # Response type indicator
        type_indicator = f" | Type: {response_type.title()}" if response_type != "general" else ""
        
        # Strengths
        strengths = self.generate_strengths(metrics, response_type)
        strengths_text = ", ".join(strengths[:2]) if strengths else "Good response structure"
        
        # Improvements
        improvements = self.generate_improvements(metrics, response_type)
        improvements_text = ", ".join(improvements[:2]) if improvements else "Continue building on this"
        
        # Contextual metrics based on response type
        contextual_metrics = ""
        if response_type == "technical":
            tech_score = f" | Tech: {metrics.technical_accuracy:.1f}"
            problem_score = f" | Problem: {metrics.problem_solving:.1f}"
            contextual_metrics = f"{tech_score}{problem_score}"
        elif response_type == "behavioral":
            star_score = f" | STAR: {metrics.star_method_usage:.1f}"
            impact_score = f" | Impact: {metrics.impact_quantification:.1f}"
            contextual_metrics = f"{star_score}{impact_score}"
        elif response_type == "leadership":
            leadership_score = f" | Leadership: {metrics.leadership_demonstration:.1f}"
            impact_score = f" | Impact: {metrics.impact_quantification:.1f}"
            contextual_metrics = f"{leadership_score}{impact_score}"
        
        # Suggestions
        suggestions = self.generate_suggestions(metrics, response_type)
        suggestions_text = f" | 💡 Next: {suggestions[0]}" if suggestions else ""
        
        # Technical insights
        insights = self.generate_technical_insights(metrics, response_type)
        insights_text = f" | 🔬 Insight: {insights[0]}" if insights and response_type == "technical" else ""
        
        # Communication tips
        tips = self.generate_communication_tips(metrics, response_type)
        tips_text = f" | 🎯 Tip: {tips[0]}" if tips else ""
        
        return f"Score: {score_display}{contextual_metrics}{type_indicator} | Strengths: {strengths_text} | Focus: {improvements_text}{suggestions_text}{insights_text}{tips_text}"
    
    def generate_summary_feedback(self, all_metrics: List[AssessmentMetrics], response_types: List[str]) -> Dict[str, Any]:
        """Generate summary feedback for the entire interview session."""
        if not all_metrics:
            return {"error": "No assessment data available"}
        
        # Calculate aggregated metrics
        total_responses = len(all_metrics)
        avg_technical_depth = sum(m.technical_depth for m in all_metrics) / total_responses
        avg_communication_clarity = sum(m.communication_clarity for m in all_metrics) / total_responses
        avg_specificity = sum(m.specificity for m in all_metrics) / total_responses
        avg_structure = sum(m.structure for m in all_metrics) / total_responses
        
        # Response type distribution
        type_counts = {}
        for response_type in response_types:
            type_counts[response_type] = type_counts.get(response_type, 0) + 1
        
        # Overall assessment
        overall_score = (avg_technical_depth + avg_communication_clarity + avg_specificity + avg_structure) / 4
        
        # Generate strengths and improvements for the session
        session_strengths = []
        session_improvements = []
        
        if avg_technical_depth > 0.7:
            session_strengths.append("Strong technical skills demonstrated")
        elif avg_technical_depth < 0.5:
            session_improvements.append("Work on technical depth and detail")
        
        if avg_communication_clarity > 0.7:
            session_strengths.append("Excellent communication skills")
        elif avg_communication_clarity < 0.6:
            session_improvements.append("Improve communication clarity")
        
        if avg_specificity > 0.6:
            session_strengths.append("Good use of specific examples")
        elif avg_specificity < 0.5:
            session_improvements.append("Include more specific details")
        
        if avg_structure > 0.6:
            session_strengths.append("Well-structured responses")
        elif avg_structure < 0.5:
            session_improvements.append("Improve response organization")
        
        return {
            "overall_score": round(overall_score, 2),
            "total_responses": total_responses,
            "response_type_distribution": type_counts,
            "average_metrics": {
                "technical_depth": round(avg_technical_depth, 2),
                "communication_clarity": round(avg_communication_clarity, 2),
                "specificity": round(avg_specificity, 2),
                "structure": round(avg_structure, 2)
            },
            "strengths": session_strengths,
            "improvements": session_improvements
        } 