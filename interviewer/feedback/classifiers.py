"""Response classification for determining the type of interview response."""

from typing import Dict, Any, List
import re


class ResponseClassifier:
    """Classifies interview responses by type and content."""
    
    def __init__(self):
        # Technical response indicators
        self.technical_indicators = [
            'python', 'sql', 'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
            'machine learning', 'deep learning', 'neural network', 'algorithm', 'data structure',
            'optimization', 'scaling', 'performance', 'efficiency', 'complexity', 'big o',
            'database', 'api', 'rest', 'graphql', 'docker', 'kubernetes', 'aws', 'azure',
            'git', 'version control', 'testing', 'unit test', 'integration test',
            'statistics', 'probability', 'regression', 'classification', 'clustering',
            'nlp', 'computer vision', 'time series', 'forecasting', 'etl', 'data pipeline',
            'code', 'programming', 'development', 'implementation', 'architecture'
        ]
        
        # Behavioral response indicators
        self.behavioral_indicators = [
            'experience', 'worked on', 'handled', 'managed', 'led', 'supervised',
            'team', 'collaboration', 'stakeholder', 'challenge', 'problem', 'situation',
            'action', 'result', 'outcome', 'impact', 'achievement', 'improvement',
            'project', 'role', 'responsibility', 'initiative', 'strategy', 'approach',
            'mentored', 'coached', 'guided', 'facilitated', 'coordinated', 'orchestrated'
        ]
        
        # Leadership response indicators
        self.leadership_indicators = [
            'led', 'managed', 'supervised', 'mentored', 'coached', 'guided', 'directed',
            'team', 'collaboration', 'stakeholder', 'presentation', 'strategy', 'vision',
            'decision', 'influence', 'motivate', 'inspire', 'delegate', 'empower',
            'leadership', 'management', 'supervision', 'coordination', 'facilitation',
            'strategic', 'organizational', 'transformational', 'change management'
        ]
        
        # Project response indicators
        self.project_indicators = [
            'project', 'initiative', 'campaign', 'program', 'system', 'platform',
            'application', 'tool', 'framework', 'solution', 'product', 'service',
            'implementation', 'deployment', 'launch', 'rollout', 'migration',
            'timeline', 'budget', 'scope', 'requirement', 'specification'
        ]
        
        # General response indicators
        self.general_indicators = [
            'think', 'believe', 'feel', 'would', 'could', 'should', 'might',
            'probably', 'possibly', 'maybe', 'perhaps', 'generally', 'typically',
            'usually', 'often', 'sometimes', 'rarely', 'never', 'always'
        ]
    
    def classify_response_type(self, response: str, context: Any = None) -> str:
        """Classify the type of response based on content and context."""
        if not response:
            return "general"
        
        response_lower = response.lower()
        
        # Count indicators for each type
        technical_score = sum(1 for indicator in self.technical_indicators 
                            if indicator.lower() in response_lower)
        behavioral_score = sum(1 for indicator in self.behavioral_indicators 
                             if indicator.lower() in response_lower)
        leadership_score = sum(1 for indicator in self.leadership_indicators 
                             if indicator.lower() in response_lower)
        project_score = sum(1 for indicator in self.project_indicators 
                          if indicator.lower() in response_lower)
        general_score = sum(1 for indicator in self.general_indicators 
                          if indicator.lower() in response_lower)
        
        # Normalize scores by response length
        word_count = len(response.split())
        if word_count > 0:
            technical_score /= word_count * 0.1
            behavioral_score /= word_count * 0.1
            leadership_score /= word_count * 0.1
            project_score /= word_count * 0.1
            general_score /= word_count * 0.1
        
        # Determine primary type
        scores = {
            "technical": technical_score,
            "behavioral": behavioral_score,
            "leadership": leadership_score,
            "project": project_score,
            "general": general_score
        }
        
        # Find the highest scoring type
        primary_type = max(scores, key=scores.get)
        
        # Apply context-based adjustments
        if context and hasattr(context, 'interview_config'):
            interview_type = context.interview_config.interview_type.value
            
            # Boost scores based on interview type
            if interview_type == "technical" and primary_type == "technical":
                scores["technical"] *= 1.5
            elif interview_type == "behavioral" and primary_type in ["behavioral", "leadership"]:
                scores["behavioral"] *= 1.3
                scores["leadership"] *= 1.2
            elif interview_type == "case_study" and primary_type in ["project", "technical"]:
                scores["project"] *= 1.3
                scores["technical"] *= 1.2
        
        # Re-determine primary type after adjustments
        primary_type = max(scores, key=scores.get)
        
        # Confidence threshold
        max_score = max(scores.values())
        if max_score < 0.1:  # Low confidence threshold
            return "general"
        
        return primary_type
    
    def get_response_subtype(self, response: str, response_type: str) -> str:
        """Get a more specific subtype within the main response type."""
        if not response:
            return "general"
        
        response_lower = response.lower()
        
        if response_type == "technical":
            # Technical subtypes
            if any(term in response_lower for term in ['sql', 'database', 'query']):
                return "sql"
            elif any(term in response_lower for term in ['pandas', 'numpy', 'dataframe']):
                return "data_analysis"
            elif any(term in response_lower for term in ['algorithm', 'complexity', 'big o']):
                return "algorithms"
            elif any(term in response_lower for term in ['machine learning', 'ml', 'model']):
                return "machine_learning"
            elif any(term in response_lower for term in ['api', 'rest', 'endpoint']):
                return "api_development"
            else:
                return "general_technical"
        
        elif response_type == "behavioral":
            # Behavioral subtypes
            if any(term in response_lower for term in ['situation', 'task', 'action', 'result']):
                return "star_method"
            elif any(term in response_lower for term in ['project', 'initiative', 'campaign']):
                return "project_experience"
            elif any(term in response_lower for term in ['challenge', 'problem', 'difficulty']):
                return "challenge_handling"
            elif any(term in response_lower for term in ['team', 'collaboration', 'stakeholder']):
                return "team_work"
            else:
                return "general_behavioral"
        
        elif response_type == "leadership":
            # Leadership subtypes
            if any(term in response_lower for term in ['led', 'managed', 'supervised']):
                return "people_management"
            elif any(term in response_lower for term in ['strategy', 'vision', 'planning']):
                return "strategic_thinking"
            elif any(term in response_lower for term in ['mentored', 'coached', 'guided']):
                return "mentoring"
            elif any(term in response_lower for term in ['influence', 'stakeholder', 'presentation']):
                return "influence_communication"
            else:
                return "general_leadership"
        
        elif response_type == "project":
            # Project subtypes
            if any(term in response_lower for term in ['implementation', 'deployment', 'launch']):
                return "project_execution"
            elif any(term in response_lower for term in ['timeline', 'budget', 'scope']):
                return "project_management"
            elif any(term in response_lower for term in ['requirement', 'specification', 'design']):
                return "project_planning"
            else:
                return "general_project"
        
        return "general"
    
    def should_evaluate_response(self, response: str, context: Any = None) -> bool:
        """Determine if a response should be evaluated for feedback."""
        if not response:
            return False
        
        # Skip very short responses
        word_count = len(response.split())
        if word_count < 10:
            return False
        
        # Skip responses that are just questions
        if response.strip().endswith('?'):
            return False
        
        # Skip responses that are just introductions
        intro_indicators = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'nice to meet you', 'pleasure to meet you', 'thank you for having me'
        ]
        
        if any(indicator in response.lower() for indicator in intro_indicators):
            return False
        
        # Skip responses that are just acknowledgments
        ack_indicators = [
            'yes', 'no', 'okay', 'sure', 'absolutely', 'definitely', 'of course',
            'i understand', 'got it', 'makes sense', 'thank you'
        ]
        
        if any(indicator in response.lower() for indicator in ack_indicators):
            return False
        
        return True
    
    def get_evaluation_priority(self, response_type: str) -> int:
        """Get the priority for evaluating different response types."""
        priorities = {
            "technical": 1,      # High priority - technical skills are key
            "behavioral": 2,     # Medium-high priority - important for fit
            "leadership": 2,     # Medium-high priority - important for senior roles
            "project": 3,        # Medium priority - good to evaluate
            "general": 4         # Low priority - less critical
        }
        
        return priorities.get(response_type, 4) 