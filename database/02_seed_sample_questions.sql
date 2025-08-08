-- ============================================================================
-- Sample Interview Questions - Seed Data
-- ============================================================================
-- This file contains high-quality sample questions to get started
-- Run this AFTER creating the interview_questions table
-- 
-- Usage:
--   1. Make sure you've run 01_create_interview_questions_table.sql first
--   2. Copy this entire SQL content
--   3. Go to your Supabase dashboard → SQL Editor  
--   4. Paste and run this SQL
-- ============================================================================

-- Clear any existing data (optional - remove if you want to keep existing questions)
-- DELETE FROM interview_questions;

-- ============================================================================
-- Technical Questions - Machine Learning
-- ============================================================================

INSERT INTO interview_questions (
    question_text, topic, interview_type, difficulty, category, tags, 
    expected_duration_minutes, follow_up_suggestions, skill_level
) VALUES 

-- Easy ML Questions
(
    'What is the difference between supervised and unsupervised learning?',
    'machine_learning', 'technical', 'easy', 'fundamentals',
    ARRAY['ml_basics', 'theory'],
    3,
    ARRAY['Can you give examples of each?', 'When would you use each approach?'],
    'entry'
),

(
    'Explain what overfitting means in machine learning.',
    'machine_learning', 'technical', 'easy', 'fundamentals', 
    ARRAY['overfitting', 'model_validation'],
    4,
    ARRAY['How can you detect overfitting?', 'What techniques prevent overfitting?'],
    'entry'
),

-- Medium ML Questions  
(
    'Explain the bias-variance tradeoff and how it affects model performance.',
    'machine_learning', 'technical', 'medium', 'theory',
    ARRAY['bias_variance', 'model_selection'],
    6,
    ARRAY['How does model complexity relate to this tradeoff?', 'Give an example of high bias vs high variance'],
    'mid'
),

(
    'How would you approach a machine learning project if you had very limited labeled data?',
    'machine_learning', 'technical', 'medium', 'practical',
    ARRAY['limited_data', 'transfer_learning', 'semi_supervised'],
    8,
    ARRAY['What about active learning?', 'How would you validate your approach?'],
    'mid'
),

-- Hard ML Questions
(
    'Design a recommendation system for a streaming platform. Walk me through your approach from data collection to deployment.',
    'machine_learning', 'technical', 'hard', 'system_design',
    ARRAY['recommendation_systems', 'system_design', 'scalability'],
    15,
    ARRAY['How would you handle the cold start problem?', 'How would you measure success?', 'What about real-time updates?'],
    'senior'
);

-- ============================================================================
-- Technical Questions - Python/Programming
-- ============================================================================

INSERT INTO interview_questions (
    question_text, topic, interview_type, difficulty, category, tags, 
    expected_duration_minutes, follow_up_suggestions, skill_level
) VALUES

-- Easy Python Questions
(
    'What is the difference between a list and a tuple in Python?',
    'python', 'technical', 'easy', 'data_structures',
    ARRAY['python_basics', 'data_structures'],
    3,
    ARRAY['When would you use each?', 'What about performance differences?'],
    'entry'
),

(
    'Explain how Python handles memory management.',
    'python', 'technical', 'medium', 'internals',
    ARRAY['memory_management', 'garbage_collection'],
    5,
    ARRAY['What is reference counting?', 'How does garbage collection work?'],
    'mid'
),

-- Programming Problem
(
    'How would you optimize a slow-running data processing script that handles millions of records?',
    'python', 'technical', 'medium', 'optimization',
    ARRAY['performance', 'optimization', 'data_processing'],
    10,
    ARRAY['What profiling tools would you use?', 'Consider both memory and CPU optimization'],
    'mid'
);

-- ============================================================================
-- Technical Questions - Statistics & Data Analysis
-- ============================================================================

INSERT INTO interview_questions (
    question_text, topic, interview_type, difficulty, category, tags, 
    expected_duration_minutes, follow_up_suggestions, skill_level
) VALUES

(
    'When would you use a t-test versus a chi-square test?',
    'statistics', 'technical', 'easy', 'hypothesis_testing',
    ARRAY['hypothesis_testing', 'statistical_tests'],
    4,
    ARRAY['What are the assumptions of each test?', 'What if assumptions are violated?'],
    'entry'
),

(
    'Explain the concept of p-hacking and how to avoid it in data analysis.',
    'statistics', 'technical', 'medium', 'best_practices',
    ARRAY['p_hacking', 'statistical_ethics', 'multiple_testing'],
    6,
    ARRAY['What is the multiple testing problem?', 'How do you adjust for multiple comparisons?'],
    'mid'
),

(
    'You notice that your A/B test results are statistically significant, but the effect size is very small. How do you interpret and communicate this to stakeholders?',
    'statistics', 'technical', 'medium', 'business_application',
    ARRAY['ab_testing', 'effect_size', 'business_communication'],
    8,
    ARRAY['What is practical significance vs statistical significance?', 'How would you design a better test?'],
    'mid'
);

-- ============================================================================
-- Behavioral Questions
-- ============================================================================

INSERT INTO interview_questions (
    question_text, topic, interview_type, difficulty, category, tags, 
    expected_duration_minutes, follow_up_suggestions, skill_level
) VALUES

(
    'Tell me about a time when you had to explain a complex technical concept to a non-technical stakeholder.',
    'communication', 'behavioral', 'medium', 'communication',
    ARRAY['communication', 'stakeholder_management', 'technical_explanation'],
    7,
    ARRAY['How did you adapt your explanation?', 'What was the outcome?', 'What would you do differently?'],
    'general'
),

(
    'Describe a situation where you disagreed with a team decision about a data science approach. How did you handle it?',
    'teamwork', 'behavioral', 'medium', 'conflict_resolution', 
    ARRAY['teamwork', 'conflict_resolution', 'technical_decisions'],
    8,
    ARRAY['How did you present your alternative?', 'What was the final decision?', 'How did this affect team dynamics?'],
    'general'
),

(
    'Tell me about a time when your initial data analysis or model was completely wrong. What happened and how did you handle it?',
    'problem_solving', 'behavioral', 'medium', 'failure_recovery',
    ARRAY['failure_recovery', 'learning', 'problem_solving'],
    8,
    ARRAY['What did you learn from this experience?', 'How do you prevent similar issues now?'],
    'general'
);

-- ============================================================================
-- Case Study Questions  
-- ============================================================================

INSERT INTO interview_questions (
    question_text, topic, interview_type, difficulty, category, tags, 
    expected_duration_minutes, follow_up_suggestions, skill_level
) VALUES

(
    'A retail company notices their sales have dropped 15% this quarter. They want to use data science to understand why. Walk me through your approach.',
    'business_analysis', 'case_study', 'medium', 'business_problem',
    ARRAY['business_analysis', 'root_cause', 'data_investigation'],
    12,
    ARRAY['What data would you need?', 'How would you prioritize your investigation?', 'What external factors would you consider?'],
    'mid'
),

(
    'Design a fraud detection system for a credit card company. Consider both the technical implementation and business constraints.',
    'fraud_detection', 'case_study', 'hard', 'system_design',
    ARRAY['fraud_detection', 'real_time', 'false_positives', 'business_impact'],
    20,
    ARRAY['How would you handle false positives?', 'What about real-time constraints?', 'How would you measure success?'],
    'senior'
);

-- ============================================================================
-- Verification Query
-- ============================================================================
-- Check that our data was inserted correctly

SELECT 
    interview_type,
    difficulty, 
    COUNT(*) as question_count,
    ARRAY_AGG(DISTINCT topic) as topics
FROM interview_questions 
GROUP BY interview_type, difficulty 
ORDER BY interview_type, 
    CASE difficulty 
        WHEN 'easy' THEN 1 
        WHEN 'medium' THEN 2 
        WHEN 'hard' THEN 3 
    END;

-- Show total count
SELECT 'Successfully added ' || COUNT(*) || ' sample questions!' as status
FROM interview_questions;