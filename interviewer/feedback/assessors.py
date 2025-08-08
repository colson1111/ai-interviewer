"""Response assessment methods for evaluating interview responses."""

from typing import Dict, Any, List
import re
from dataclasses import dataclass


@dataclass
class AssessmentMetrics:
    """Container for assessment metrics."""
    technical_depth: float = 0.0
    technical_accuracy: float = 0.0
    communication_clarity: float = 0.0
    specificity: float = 0.0
    structure: float = 0.0
    problem_solving: float = 0.0
    communication_style: float = 0.0
    star_method_usage: float = 0.0
    impact_quantification: float = 0.0
    leadership_demonstration: float = 0.0
    word_count: int = 0
    keywords: List[str] = None
    sentiment: str = "neutral"
    completeness: float = 0.0


class ResponseAssessor:
    """Assesses various aspects of interview responses."""
    
    def __init__(self):
        self.technical_keywords = [
            'python', 'sql', 'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
            'machine learning', 'deep learning', 'neural network', 'algorithm', 'data structure',
            'optimization', 'scaling', 'performance', 'efficiency', 'complexity', 'big o',
            'database', 'api', 'rest', 'graphql', 'docker', 'kubernetes', 'aws', 'azure',
            'git', 'version control', 'testing', 'unit test', 'integration test',
            'statistics', 'probability', 'regression', 'classification', 'clustering',
            'nlp', 'computer vision', 'time series', 'forecasting', 'etl', 'data pipeline'
        ]
        
        self.star_keywords = [
            'situation', 'task', 'action', 'result', 'challenge', 'problem', 'solution',
            'implemented', 'developed', 'created', 'built', 'designed', 'managed', 'led',
            'improved', 'increased', 'decreased', 'reduced', 'optimized', 'solved'
        ]
        
        self.leadership_keywords = [
            'led', 'managed', 'supervised', 'mentored', 'coached', 'guided', 'directed',
            'team', 'collaboration', 'stakeholder', 'presentation', 'strategy', 'vision',
            'decision', 'influence', 'motivate', 'inspire', 'delegate', 'empower'
        ]
    
    def assess_technical_depth(self, response: str) -> float:
        """Assess the technical depth of the response."""
        if not response:
            return 0.0
        
        # Count technical keywords
        tech_count = sum(1 for keyword in self.technical_keywords 
                        if keyword.lower() in response.lower())
        
        # Check for technical explanations
        technical_indicators = [
            'because', 'due to', 'as a result', 'therefore', 'consequently',
            'algorithm', 'approach', 'methodology', 'technique', 'process',
            'implementation', 'architecture', 'design pattern', 'framework'
        ]
        
        explanation_count = sum(1 for indicator in technical_indicators 
                              if indicator.lower() in response.lower())
        
        # Normalize by response length
        word_count = len(response.split())
        if word_count == 0:
            return 0.0
        
        # Calculate depth score
        keyword_score = min(1.0, tech_count / 5.0)  # Cap at 5 keywords
        explanation_score = min(1.0, explanation_count / 3.0)  # Cap at 3 explanations
        
        return round((keyword_score * 0.6 + explanation_score * 0.4), 2)
    
    def assess_communication_clarity(self, response: str) -> float:
        """Assess the clarity of communication."""
        if not response:
            return 0.0
        
        # Check for clear structure indicators
        structure_indicators = [
            'first', 'second', 'third', 'initially', 'then', 'finally',
            'step 1', 'step 2', 'step 3', 'phase 1', 'phase 2',
            'beginning', 'middle', 'end', 'start', 'conclude'
        ]
        
        structure_count = sum(1 for indicator in structure_indicators 
                            if indicator.lower() in response.lower())
        
        # Check for clear explanations
        clarity_indicators = [
            'specifically', 'in detail', 'to clarify', 'in other words',
            'for example', 'such as', 'including', 'namely', 'that is'
        ]
        
        clarity_count = sum(1 for indicator in clarity_indicators 
                           if indicator.lower() in response.lower())
        
        # Check sentence complexity (simpler is often clearer)
        sentences = re.split(r'[.!?]+', response)
        avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(len(sentences), 1)
        
        # Calculate clarity score
        structure_score = min(1.0, structure_count / 2.0)
        clarity_score = min(1.0, clarity_count / 2.0)
        complexity_score = max(0.0, 1.0 - (avg_sentence_length - 15) / 10.0)  # Prefer 15 words per sentence
        
        return round((structure_score * 0.4 + clarity_score * 0.4 + complexity_score * 0.2), 2)
    
    def assess_specificity(self, response: str) -> float:
        """Assess the specificity of examples and details."""
        if not response:
            return 0.0
        
        # Count specific numbers and metrics
        numbers = re.findall(r'\d+', response)
        number_score = min(1.0, len(numbers) / 3.0)
        
        # Count specific examples
        example_indicators = [
            'for example', 'such as', 'specifically', 'in particular',
            'including', 'namely', 'that is', 'i.e.', 'e.g.'
        ]
        
        example_count = sum(1 for indicator in example_indicators 
                           if indicator.lower() in response.lower())
        example_score = min(1.0, example_count / 2.0)
        
        # Check for concrete details
        detail_indicators = [
            'company', 'project', 'team', 'role', 'technology', 'tool',
            'timeline', 'budget', 'scope', 'stakeholder', 'requirement'
        ]
        
        detail_count = sum(1 for indicator in detail_indicators 
                          if indicator.lower() in response.lower())
        detail_score = min(1.0, detail_count / 3.0)
        
        return round((number_score * 0.4 + example_score * 0.3 + detail_score * 0.3), 2)
    
    def assess_structure(self, response: str) -> float:
        """Assess the logical structure and organization."""
        if not response:
            return 0.0
        
        # Check for logical flow indicators
        flow_indicators = [
            'first', 'second', 'third', 'next', 'then', 'finally',
            'initially', 'subsequently', 'consequently', 'therefore',
            'as a result', 'because of this', 'leading to'
        ]
        
        flow_count = sum(1 for indicator in flow_indicators 
                        if indicator.lower() in response.lower())
        
        # Check for clear topic sentences
        sentences = re.split(r'[.!?]+', response)
        topic_sentences = sum(1 for sentence in sentences 
                            if len(sentence.split()) > 5 and 
                            any(word in sentence.lower() for word in ['was', 'is', 'had', 'did', 'created', 'developed']))
        
        # Check paragraph structure
        paragraphs = response.split('\n\n')
        paragraph_score = min(1.0, len(paragraphs) / 2.0)
        
        flow_score = min(1.0, flow_count / 3.0)
        topic_score = min(1.0, topic_sentences / 2.0)
        
        return round((flow_score * 0.4 + topic_score * 0.3 + paragraph_score * 0.3), 2)
    
    def assess_technical_accuracy(self, response: str) -> float:
        """Assess technical accuracy and precision."""
        if not response:
            return 0.0
        
        # Check for precise technical language
        precise_terms = [
            'algorithm', 'complexity', 'optimization', 'scaling', 'performance',
            'efficiency', 'throughput', 'latency', 'bandwidth', 'memory',
            'cpu', 'gpu', 'parallel', 'distributed', 'microservices',
            'api', 'endpoint', 'request', 'response', 'authentication'
        ]
        
        precise_count = sum(1 for term in precise_terms 
                           if term.lower() in response.lower())
        
        # Check for correct technical explanations
        correct_patterns = [
            r'big o\([^)]*\)', r'complexity of [^.]*', r'algorithm [^.]*',
            r'data structure[^.]*', r'optimization[^.]*', r'scaling[^.]*'
        ]
        
        pattern_matches = sum(1 for pattern in correct_patterns 
                             if re.search(pattern, response, re.IGNORECASE))
        
        precise_score = min(1.0, precise_count / 4.0)
        pattern_score = min(1.0, pattern_matches / 2.0)
        
        return round((precise_score * 0.6 + pattern_score * 0.4), 2)
    
    def assess_problem_solving(self, response: str) -> float:
        """Assess problem-solving approach and methodology."""
        if not response:
            return 0.0
        
        # Check for systematic approach
        systematic_indicators = [
            'step by step', 'systematic', 'methodical', 'approach',
            'process', 'methodology', 'framework', 'strategy'
        ]
        
        systematic_count = sum(1 for indicator in systematic_indicators 
                             if indicator.lower() in response.lower())
        
        # Check for problem analysis
        analysis_indicators = [
            'analyzed', 'identified', 'understood', 'assessed', 'evaluated',
            'considered', 'examined', 'investigated', 'researched'
        ]
        
        analysis_count = sum(1 for indicator in analysis_indicators 
                           if indicator.lower() in response.lower())
        
        # Check for solution generation
        solution_indicators = [
            'solution', 'approach', 'method', 'technique', 'strategy',
            'implemented', 'developed', 'created', 'designed', 'built'
        ]
        
        solution_count = sum(1 for indicator in solution_indicators 
                           if indicator.lower() in response.lower())
        
        systematic_score = min(1.0, systematic_count / 2.0)
        analysis_score = min(1.0, analysis_count / 3.0)
        solution_score = min(1.0, solution_count / 3.0)
        
        return round((systematic_score * 0.4 + analysis_score * 0.3 + solution_score * 0.3), 2)
    
    def assess_communication_style(self, response: str) -> float:
        """Assess professional communication style."""
        if not response:
            return 0.0
        
        # Check for professional tone
        professional_indicators = [
            'professional', 'collaborative', 'respectful', 'constructive',
            'positive', 'confident', 'humble', 'open-minded'
        ]
        
        professional_count = sum(1 for indicator in professional_indicators 
                               if indicator.lower() in response.lower())
        
        # Check for appropriate language
        inappropriate_words = ['bad', 'terrible', 'awful', 'hate', 'stupid', 'dumb']
        inappropriate_count = sum(1 for word in inappropriate_words 
                                if word.lower() in response.lower())
        
        # Check for balanced perspective
        balanced_indicators = [
            'however', 'on the other hand', 'alternatively', 'meanwhile',
            'although', 'despite', 'nevertheless', 'conversely'
        ]
        
        balanced_count = sum(1 for indicator in balanced_indicators 
                           if indicator.lower() in response.lower())
        
        professional_score = min(1.0, professional_count / 2.0)
        inappropriate_penalty = min(1.0, inappropriate_count * 0.2)
        balanced_score = min(1.0, balanced_count / 2.0)
        
        return round(max(0.0, (professional_score * 0.5 + balanced_score * 0.5) - inappropriate_penalty), 2)
    
    def assess_star_method(self, response: str) -> float:
        """Assess STAR method usage in behavioral responses."""
        if not response:
            return 0.0
        
        # Check for STAR components
        star_components = {
            'situation': ['situation', 'context', 'background', 'environment'],
            'task': ['task', 'challenge', 'problem', 'goal', 'objective'],
            'action': ['action', 'approach', 'method', 'strategy', 'implemented'],
            'result': ['result', 'outcome', 'impact', 'achievement', 'improvement']
        }
        
        component_scores = {}
        for component, keywords in star_components.items():
            count = sum(1 for keyword in keywords 
                       if keyword.lower() in response.lower())
            component_scores[component] = min(1.0, count / 2.0)
        
        # Calculate overall STAR score
        total_score = sum(component_scores.values()) / len(component_scores)
        return round(total_score, 2)
    
    def assess_impact_quantification(self, response: str) -> float:
        """Assess quantification of impact and results."""
        if not response:
            return 0.0
        
        # Count specific metrics
        metrics = re.findall(r'\d+%|\d+ percent|\d+ times|\d+x|\$\d+|\d+ dollars', response, re.IGNORECASE)
        metric_score = min(1.0, len(metrics) / 2.0)
        
        # Check for impact indicators
        impact_indicators = [
            'increased', 'decreased', 'improved', 'reduced', 'enhanced',
            'boosted', 'accelerated', 'optimized', 'streamlined', 'efficient'
        ]
        
        impact_count = sum(1 for indicator in impact_indicators 
                          if indicator.lower() in response.lower())
        impact_score = min(1.0, impact_count / 3.0)
        
        # Check for before/after comparisons
        comparison_indicators = [
            'before', 'after', 'previously', 'now', 'from', 'to',
            'changed', 'transformed', 'evolved', 'progressed'
        ]
        
        comparison_count = sum(1 for indicator in comparison_indicators 
                             if indicator.lower() in response.lower())
        comparison_score = min(1.0, comparison_count / 2.0)
        
        return round((metric_score * 0.5 + impact_score * 0.3 + comparison_score * 0.2), 2)
    
    def assess_leadership_demonstration(self, response: str) -> float:
        """Assess leadership and influence demonstration."""
        if not response:
            return 0.0
        
        # Check for leadership actions
        leadership_actions = [
            'led', 'managed', 'supervised', 'mentored', 'coached',
            'guided', 'directed', 'orchestrated', 'coordinated', 'facilitated'
        ]
        
        action_count = sum(1 for action in leadership_actions 
                          if action.lower() in response.lower())
        
        # Check for team collaboration
        team_indicators = [
            'team', 'collaboration', 'partnership', 'stakeholder',
            'cross-functional', 'interdisciplinary', 'coordination'
        ]
        
        team_count = sum(1 for indicator in team_indicators 
                        if indicator.lower() in response.lower())
        
        # Check for strategic thinking
        strategic_indicators = [
            'strategy', 'vision', 'planning', 'roadmap', 'initiative',
            'transformation', 'change management', 'organizational'
        ]
        
        strategic_count = sum(1 for indicator in strategic_indicators 
                            if indicator.lower() in response.lower())
        
        action_score = min(1.0, action_count / 3.0)
        team_score = min(1.0, team_count / 2.0)
        strategic_score = min(1.0, strategic_count / 2.0)
        
        return round((action_score * 0.5 + team_score * 0.3 + strategic_score * 0.2), 2)
    
    def extract_keywords(self, response: str) -> List[str]:
        """Extract relevant keywords from the response."""
        if not response:
            return []
        
        # Combine all keyword lists
        all_keywords = (self.technical_keywords + self.star_keywords + 
                       self.leadership_keywords)
        
        # Find keywords in response
        found_keywords = []
        for keyword in all_keywords:
            if keyword.lower() in response.lower():
                found_keywords.append(keyword)
        
        return found_keywords[:10]  # Limit to top 10 keywords
    
    def assess_sentiment(self, response: str) -> str:
        """Assess the overall sentiment of the response."""
        if not response:
            return "neutral"
        
        positive_words = ['success', 'achievement', 'improved', 'positive', 'excellent', 'great']
        negative_words = ['failure', 'problem', 'issue', 'difficult', 'challenge', 'struggle']
        
        positive_count = sum(1 for word in positive_words 
                           if word.lower() in response.lower())
        negative_count = sum(1 for word in negative_words 
                           if word.lower() in response.lower())
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def assess_completeness(self, response: str, context: Any = None) -> float:
        """Assess the completeness of the response relative to the question."""
        if not response:
            return 0.0
        
        # Basic completeness based on length
        word_count = len(response.split())
        
        # Expected length varies by response type
        # This is a simplified approach - could be enhanced with question analysis
        expected_length = 50  # Default expectation
        
        completeness = min(1.0, word_count / expected_length)
        return round(completeness, 2)
    
    def assess_response(self, response: str, context: Any = None) -> AssessmentMetrics:
        """Perform comprehensive assessment of a response."""
        metrics = AssessmentMetrics()
        
        metrics.technical_depth = self.assess_technical_depth(response)
        metrics.technical_accuracy = self.assess_technical_accuracy(response)
        metrics.communication_clarity = self.assess_communication_clarity(response)
        metrics.specificity = self.assess_specificity(response)
        metrics.structure = self.assess_structure(response)
        metrics.problem_solving = self.assess_problem_solving(response)
        metrics.communication_style = self.assess_communication_style(response)
        metrics.star_method_usage = self.assess_star_method(response)
        metrics.impact_quantification = self.assess_impact_quantification(response)
        metrics.leadership_demonstration = self.assess_leadership_demonstration(response)
        metrics.word_count = len(response.split())
        metrics.keywords = self.extract_keywords(response)
        metrics.sentiment = self.assess_sentiment(response)
        metrics.completeness = self.assess_completeness(response, context)
        
        return metrics 