"""
Tests for interviewer/prompts.py

Tests prompt building and component assembly.
"""

import pytest

from interviewer.prompts import (
    BASE_PROMPT, TONE_MODIFIERS, DIFFICULTY_MODIFIERS, INTERVIEW_TYPE_GUIDANCE,
    EVALUATION_PROMPT, build_system_prompt
)


class TestPromptConstants:
    """Tests for prompt constant definitions."""
    
    def test_base_prompt_exists(self):
        """Test that base prompt is defined and non-empty."""
        assert BASE_PROMPT is not None
        assert len(BASE_PROMPT) > 0
    
    def test_base_prompt_contains_key_instructions(self):
        """Test that base prompt contains critical instructions."""
        assert "CRITICAL CONTEXT RULES" in BASE_PROMPT
        assert "company name" in BASE_PROMPT.lower()
        assert "role" in BASE_PROMPT.lower()
    
    def test_tone_modifiers_all_defined(self):
        """Test that all tone modifiers are defined."""
        expected_tones = ["professional", "friendly", "challenging", "supportive"]
        for tone in expected_tones:
            assert tone in TONE_MODIFIERS
            assert len(TONE_MODIFIERS[tone]) > 0
    
    def test_difficulty_modifiers_all_defined(self):
        """Test that all difficulty modifiers are defined."""
        expected_difficulties = ["easy", "medium", "hard"]
        for difficulty in expected_difficulties:
            assert difficulty in DIFFICULTY_MODIFIERS
            assert len(DIFFICULTY_MODIFIERS[difficulty]) > 0
    
    def test_difficulty_modifiers_contain_level(self):
        """Test that difficulty modifiers mention their level."""
        assert "Easy" in DIFFICULTY_MODIFIERS["easy"]
        assert "Medium" in DIFFICULTY_MODIFIERS["medium"]
        assert "Hard" in DIFFICULTY_MODIFIERS["hard"]
    
    def test_interview_type_guidance_all_defined(self):
        """Test that all interview type guidance is defined."""
        expected_types = ["behavioral", "case_study"]
        for interview_type in expected_types:
            assert interview_type in INTERVIEW_TYPE_GUIDANCE
            assert len(INTERVIEW_TYPE_GUIDANCE[interview_type]) > 0
    
    def test_behavioral_guidance_contains_star(self):
        """Test that behavioral guidance mentions STAR method."""
        assert "STAR" in INTERVIEW_TYPE_GUIDANCE["behavioral"]
    
    def test_case_study_guidance_contains_scenarios(self):
        """Test that case study guidance mentions scenarios."""
        assert "scenario" in INTERVIEW_TYPE_GUIDANCE["case_study"].lower()
    
    def test_evaluation_prompt_exists(self):
        """Test that evaluation prompt is defined."""
        assert EVALUATION_PROMPT is not None
        assert len(EVALUATION_PROMPT) > 0
    
    def test_evaluation_prompt_contains_scoring(self):
        """Test that evaluation prompt contains scoring criteria."""
        assert "Score" in EVALUATION_PROMPT or "score" in EVALUATION_PROMPT
        assert "0-10" in EVALUATION_PROMPT or "0 to 10" in EVALUATION_PROMPT


class TestBuildSystemPrompt:
    """Tests for the build_system_prompt function."""
    
    def test_build_basic_prompt(self):
        """Test building a basic system prompt."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="medium"
        )
        
        assert prompt is not None
        assert len(prompt) > 0
    
    def test_build_prompt_includes_base(self):
        """Test that built prompt includes base prompt content."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="medium"
        )
        
        # Should contain key parts of base prompt
        assert "CRITICAL CONTEXT RULES" in prompt
    
    def test_build_prompt_includes_tone(self):
        """Test that built prompt includes tone modifier."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="challenging",
            difficulty="medium"
        )
        
        # Should contain the challenging tone content
        assert "direct" in prompt.lower() or "probe" in prompt.lower()
    
    def test_build_prompt_includes_difficulty(self):
        """Test that built prompt includes difficulty modifier."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="hard"
        )
        
        # Should contain hard difficulty markers
        assert "Hard" in prompt or "HARD" in prompt
    
    def test_build_prompt_includes_interview_type(self):
        """Test that built prompt includes interview type guidance."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="medium"
        )
        
        # Should contain behavioral interview markers
        assert "STAR" in prompt or "Behavioral" in prompt
    
    def test_build_prompt_all_combinations(self):
        """Test that all valid combinations produce valid prompts."""
        tones = ["professional", "friendly", "challenging", "supportive"]
        difficulties = ["easy", "medium", "hard"]
        interview_types = ["behavioral", "case_study"]
        
        for tone in tones:
            for difficulty in difficulties:
                for interview_type in interview_types:
                    prompt = build_system_prompt(
                        interview_type=interview_type,
                        tone=tone,
                        difficulty=difficulty
                    )
                    
                    # All prompts should be non-empty strings
                    assert isinstance(prompt, str)
                    assert len(prompt) > 100  # Should be substantial
    
    def test_build_prompt_fallback_unknown_tone(self):
        """Test that unknown tone falls back to professional."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="unknown_tone",
            difficulty="medium"
        )
        
        # Should not crash and should include professional tone
        assert prompt is not None
        assert TONE_MODIFIERS["professional"] in prompt
    
    def test_build_prompt_fallback_unknown_difficulty(self):
        """Test that unknown difficulty falls back to medium."""
        prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="unknown_difficulty"
        )
        
        # Should not crash and should include medium difficulty
        assert prompt is not None
        assert DIFFICULTY_MODIFIERS["medium"] in prompt
    
    def test_build_prompt_fallback_unknown_type(self):
        """Test that unknown interview type falls back to behavioral."""
        prompt = build_system_prompt(
            interview_type="unknown_type",
            tone="professional",
            difficulty="medium"
        )
        
        # Should not crash and should include behavioral guidance
        assert prompt is not None
        assert INTERVIEW_TYPE_GUIDANCE["behavioral"] in prompt
    
    def test_case_study_prompt_different_from_behavioral(self):
        """Test that case study prompt differs from behavioral."""
        behavioral_prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="medium"
        )
        
        case_study_prompt = build_system_prompt(
            interview_type="case_study",
            tone="professional",
            difficulty="medium"
        )
        
        # They should be different
        assert behavioral_prompt != case_study_prompt
        
        # Behavioral should have STAR, case study should have scenario
        assert "STAR" in behavioral_prompt
        assert "scenario" in case_study_prompt.lower()
    
    def test_difficulty_affects_prompt_length(self):
        """Test that harder difficulties have more detailed instructions."""
        easy_prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="easy"
        )
        
        hard_prompt = build_system_prompt(
            interview_type="behavioral",
            tone="professional",
            difficulty="hard"
        )
        
        # Hard difficulty should have more detailed instructions
        # (This is a reasonable assumption based on the prompt structure)
        assert len(hard_prompt) >= len(easy_prompt)

