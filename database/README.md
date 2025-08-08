# Database Schema

This directory contains the SQL files for setting up the interview questions database in Supabase.

## Setup Instructions

### 1. Create the Table
1. Go to your Supabase dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the contents of `01_create_interview_questions_table.sql`
4. Click **Run** to create the table

### 2. Add Sample Data
1. In the same SQL Editor
2. Copy and paste the contents of `02_seed_sample_questions.sql`  
3. Click **Run** to add sample questions

## Table Structure

### `interview_questions` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `question_text` | TEXT | The actual interview question |
| `topic` | VARCHAR(100) | Main subject (e.g., 'machine_learning', 'python') |
| `interview_type` | VARCHAR(50) | 'technical', 'behavioral', or 'case_study' |
| `difficulty` | VARCHAR(20) | 'easy', 'medium', or 'hard' |
| `category` | VARCHAR(100) | Optional sub-category |
| `tags` | TEXT[] | Array of tags for searching |
| `expected_duration_minutes` | INTEGER | Time estimate for answering |
| `follow_up_suggestions` | TEXT[] | Suggested follow-up questions |
| `skill_level` | VARCHAR(50) | Target skill level |
| `company_type` | VARCHAR(50) | Company context |
| `is_active` | BOOLEAN | Soft delete flag |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

## Indexes

- **Performance index**: `(interview_type, difficulty, topic, is_active)`
- **Tag search**: GIN index on `tags` array
- **Text search**: Full-text search on `question_text`

## Sample Data

The seed file includes:
- **Technical questions**: Machine learning, Python, Statistics
- **Behavioral questions**: Communication, teamwork, problem-solving  
- **Case studies**: Business problems, system design
- **Multiple difficulty levels**: Entry to senior level questions
- **Rich metadata**: Tags, follow-ups, duration estimates

## Usage in Code

```python
from interviewer.database.supabase_client import supabase_client

# Get Python questions for technical interviews
questions = supabase_client.get_questions(
    topic="python",
    interview_type="technical", 
    difficulty="medium",
    limit=3
)
```

## Adding New Questions

Use the Supabase dashboard Table Editor or add via SQL:

```sql
INSERT INTO interview_questions (
    question_text, topic, interview_type, difficulty, 
    category, tags, expected_duration_minutes
) VALUES (
    'Your question here',
    'topic_name', 
    'technical',
    'medium',
    'sub_category',
    ARRAY['tag1', 'tag2'],
    5
);
```