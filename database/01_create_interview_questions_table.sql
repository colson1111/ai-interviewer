-- ============================================================================
-- Interview Questions Table
-- ============================================================================
-- This table stores curated interview questions for the AI interviewer agent
-- 
-- Usage:
--   1. Copy this entire SQL content
--   2. Go to your Supabase dashboard → SQL Editor
--   3. Paste and run this SQL
-- ============================================================================

CREATE TABLE IF NOT EXISTS interview_questions (
    -- Primary key and metadata
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Question content
    question_text TEXT NOT NULL,
    -- The actual interview question text
    -- Example: "Explain the bias-variance tradeoff in machine learning"
    
    -- Question classification
    topic VARCHAR(100) NOT NULL,
    -- Main topic/subject area (e.g., 'machine_learning', 'python', 'statistics')
    -- Used for filtering questions by subject
    
    interview_type VARCHAR(50) NOT NULL CHECK (interview_type IN ('technical', 'behavioral', 'case_study')),
    -- Type of interview this question is suited for
    -- - technical: Tests technical knowledge and skills
    -- - behavioral: Tests soft skills and past experiences  
    -- - case_study: Tests problem-solving with scenarios
    
    difficulty VARCHAR(20) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    -- Difficulty level to help match questions to candidate experience
    -- - easy: Entry level, basic concepts
    -- - medium: Mid-level, practical application
    -- - hard: Senior level, complex scenarios
    
    category VARCHAR(100),
    -- Optional sub-category for more granular filtering
    -- Examples: 'algorithms', 'data_structures', 'system_design', 'communication'
    
    tags TEXT[],
    -- Array of tags for flexible searching and categorization
    -- Examples: ['python', 'pandas', 'data_cleaning'], ['leadership', 'conflict_resolution']
    
    -- Question metadata
    expected_duration_minutes INTEGER DEFAULT 5,
    -- Expected time for candidate to answer (helps with interview pacing)
    
    follow_up_suggestions TEXT[],
    -- Optional array of follow-up questions or talking points
    -- Helps the AI interviewer create natural conversation flow
    
    skill_level VARCHAR(50) DEFAULT 'general',
    -- Target skill level: 'entry', 'mid', 'senior', 'principal', 'general'
    -- Helps match questions to job level
    
    company_type VARCHAR(50) DEFAULT 'general',
    -- Company context: 'startup', 'big_tech', 'consulting', 'healthcare', 'general'
    -- Allows customization for different company environments
    
    is_active BOOLEAN DEFAULT TRUE
    -- Allows soft deletion - questions can be deactivated without removal
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
-- These indexes will make querying faster as the question database grows

-- Index for common filtering combinations
CREATE INDEX IF NOT EXISTS idx_questions_filter 
ON interview_questions (interview_type, difficulty, topic, is_active);

-- Index for tag-based searches
CREATE INDEX IF NOT EXISTS idx_questions_tags 
ON interview_questions USING GIN (tags);

-- Index for text search on question content
CREATE INDEX IF NOT EXISTS idx_questions_text_search 
ON interview_questions USING GIN (to_tsvector('english', question_text));

-- ============================================================================
-- Trigger for Updated Timestamp
-- ============================================================================
-- Automatically update the updated_at column when a row is modified

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_interview_questions_updated_at 
    BEFORE UPDATE ON interview_questions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
-- Add descriptive comments to the table and columns

COMMENT ON TABLE interview_questions IS 'Curated interview questions for the AI interviewer agent, organized by topic, difficulty, and interview type';

COMMENT ON COLUMN interview_questions.id IS 'Unique identifier for each question';
COMMENT ON COLUMN interview_questions.question_text IS 'The actual interview question text that will be asked';
COMMENT ON COLUMN interview_questions.topic IS 'Main subject area (e.g., machine_learning, python, statistics)';
COMMENT ON COLUMN interview_questions.interview_type IS 'Type of interview: technical, behavioral, or case_study';
COMMENT ON COLUMN interview_questions.difficulty IS 'Question difficulty: easy, medium, or hard';
COMMENT ON COLUMN interview_questions.category IS 'Optional sub-category for granular filtering';
COMMENT ON COLUMN interview_questions.tags IS 'Array of tags for flexible searching and categorization';
COMMENT ON COLUMN interview_questions.expected_duration_minutes IS 'Expected time for candidate to answer (for pacing)';
COMMENT ON COLUMN interview_questions.follow_up_suggestions IS 'Array of suggested follow-up questions';
COMMENT ON COLUMN interview_questions.skill_level IS 'Target skill level: entry, mid, senior, principal, general';
COMMENT ON COLUMN interview_questions.company_type IS 'Company context: startup, big_tech, consulting, etc.';
COMMENT ON COLUMN interview_questions.is_active IS 'Whether this question is currently active (soft delete flag)';

-- ============================================================================
-- Success Message
-- ============================================================================
-- This will show in the SQL Editor after successful execution

SELECT 'interview_questions table created successfully!' as status;