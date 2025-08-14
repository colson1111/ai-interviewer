"""Technical interviewer agent specialized for coding interviews.

This agent focuses on:
- Pivoting quickly to a coding challenge after the intro
- Short, targeted technical guidance (correctness, complexity, tests, edge cases)
- Avoiding behavioral/STAR questions entirely
"""

from typing import Dict, Any, Optional
import time
import re

from .base import BaseInterviewAgent
from ..config import LLMConfig, TechnicalTrack
from ..core import InterviewContext, AgentMessage, AgentResponse, AgentCapability


class TechnicalInterviewerAgent(BaseInterviewAgent):
    def __init__(self, llm_config: LLMConfig):
        super().__init__(
            name="technical_interviewer",
            capabilities=[
                AgentCapability.INTERVIEW_QUESTIONS,
                AgentCapability.CONVERSATION_FLOW,
            ],
        )
        self.llm_config = llm_config
        self.current_phase = "introduction"
        self.question_count = 0
        self.last_question_time = None

    def can_handle(self, message: AgentMessage, context: InterviewContext) -> float:
        return 0.9 if message.sender in {"user", "system"} else 0.3

    async def process(self, message: AgentMessage, context: InterviewContext) -> AgentResponse:
        if message.sender == "system":
            return self._create_response(
                content=self._welcome_message(context),
                confidence=0.9,
                metadata={"phase": "introduction"},
            )

        # First user reply → pivot to coding
        if self.current_phase == "introduction":
            challenge = await self._generate_coding_challenge(context)
            self.current_phase = "coding"
            self.question_count += 1
            self.last_question_time = time.time()
            return self._create_response(
                content="I'll place the coding problem in the editor now. Use the Run button and hint controls as needed.",
                confidence=0.95,
                metadata={
                    "question_type": "coding_challenge",
                    "question_number": self.question_count,
                    "interview_phase": self.current_phase,
                    "editor_prompt": challenge,
                },
            )

        # During coding phase, keep follow-ups short and technical
        followup = await self._generate_technical_followup(message.content, context)
        self.question_count += 1
        self.last_question_time = time.time()
        return self._create_response(
            content=followup,
            confidence=0.85,
            metadata={
                "question_type": "technical_followup",
                "question_number": self.question_count,
                "interview_phase": self.current_phase,
            },
        )

    def _welcome_message(self, context: InterviewContext) -> str:
        interviewer_names = ["Jordan", "Alex", "Casey", "Taylor"]
        name = interviewer_names[hash(context.session_id) % len(interviewer_names)]
        tone = context.interview_config.tone.value
        return (
            f"Hi, I'm {name}. I'll be conducting your technical interview today. "
            f"We'll use the code editor on the right for the challenge. Give me a one‑line intro, and then I'll place the problem in the editor."
        )

    async def _generate_coding_challenge(self, context: InterviewContext) -> str:
        # Prompt with strict constraints (no placeholders, Python signature without extra imports)
        role = (getattr(context.candidate_info, 'role_title', None) or '').lower().strip()
        default_role = 'data scientist'
        target_role = role if role else default_role
        difficulty = context.interview_config.difficulty.value
        track = context.interview_config.technical_track.value if getattr(context.interview_config, 'technical_track', None) else None

        # Track-specific prompts
        if track == TechnicalTrack.PANDAS.value:
            prompt = (
                "You are running a technical interview focused strictly on Pandas for a data scientist/analyst. Provide ONE concise DATA MANIPULATION problem.\n"
                "We will create a realistic dataset and make it available BOTH in DuckDB as table 'tbl' and in pandas as DataFrame 'df'.\n"
                "Style: Pandas operations (filtering, grouping, aggregation, joins). Avoid algorithmic problems.\n"
                "Include in the prompt:\n"
                "- A realistic table schema (columns with types) and 5 concrete example rows.\n"
                "- SQL to CREATE TABLE tbl(...) and INSERT sample rows; ensure it runs in DuckDB.\n"
                "- Python code to build the same DataFrame df (using a list/dict, not reading external files).\n"
                "- A clear analytical task referencing tbl/df that matches the sample data.\n"
                "- Expected output description with a tiny example.\n"
                f"- Match difficulty: '{difficulty}' (easy → 1-2 operations).\n"
                "- No placeholders like [something].\n"
                "Important formatting and size requirements:\n"
                "- Provide the SQL block fenced as ```sql ... ``` and the Python block fenced as ```python ... ``` so they can be parsed.\n"
                "- The inserted dataset should contain between 30 and 100 rows (not just 5), realistic values, and use the exact names 'tbl' (SQL) and 'df' (pandas).\n"
            )
        elif track == TechnicalTrack.SQL.value:
            prompt = (
                "You are running a technical interview focused strictly on SQL (DuckDB). Provide ONE concise SQL problem.\n"
                "We will create a realistic dataset and make it available as DuckDB table 'tbl' and as a pandas DataFrame 'df' for reference.\n"
                "Style: SQL querying (filtering, grouping, aggregation, joins, window functions as appropriate).\n"
                "Include in the prompt:\n"
                "- A realistic table schema (columns with types) and 5 concrete example rows.\n"
                "- SQL to CREATE TABLE tbl(...) and INSERT sample rows; ensure it runs in DuckDB.\n"
                "- Python code to build the same DataFrame df for parity (using list/dict).\n"
                "- A clear SQL task referencing tbl that matches the sample data.\n"
                "- Expected output description with a tiny example.\n"
                f"- Match difficulty: '{difficulty}'.\n"
                "- No placeholders like [something].\n"
                "Important: Fence the SQL as ```sql ... ``` and Python as ```python ... ```. Ensure dataset 30-100 rows, realistic values, names 'tbl' and 'df'.\n"
            )
        elif track == TechnicalTrack.ALGORITHMS.value:
            prompt = (
                "You are running a technical coding interview for a machine learning engineer / software engineer. Provide ONE concise ALGORITHM problem.\n"
                "Style: array/string/hashmap/graph, etc. (LeetCode-like).\n"
                "Include in the prompt:\n"
                "- A precise problem statement.\n"
                "- A Python function signature (no extra imports) and constraints.\n"
                "- 2-3 example inputs and outputs.\n"
                f"- Match difficulty: '{difficulty}'.\n"
                "- No placeholders like [something].\n"
                "- End with a directive to implement and run tests."
            )
        elif track == TechnicalTrack.BASIC_PYTHON.value:
            prompt = (
                "You are running a technical interview focused on basic Python (no heavy algorithms). Provide ONE concise problem.\n"
                "Style: core Python (lists/dicts/sets/comprehensions, simple file/string processing).\n"
                "Include in the prompt:\n"
                "- A precise problem statement.\n"
                "- A Python function signature (no extra imports).\n"
                "- 2-3 example inputs and outputs.\n"
                f"- Match difficulty: '{difficulty}'.\n"
                "- No placeholders like [something].\n"
                "- End with a directive to implement and run quick tests."
            )
        else:
            # Fallback on role inference (legacy behavior)
            is_analytics = any(k in target_role for k in ["data scientist", "data analyst", "analyst", "analytics"]) or target_role == ""
            if is_analytics:
                prompt = (
                    "You are running a technical coding interview for a data scientist/analyst. Provide ONE concise ANALYTICAL problem.\n"
                    "We will create a tiny realistic dataset and make it available BOTH in DuckDB as table 'tbl' and in pandas as DataFrame 'df'.\n"
                    "Style: Pandas/SQL data manipulation (filtering, grouping, aggregation, joins). Avoid algorithmic problems.\n"
                    "Include in the prompt:\n"
                    "- A realistic table schema (columns with types) and 5 concrete example rows.\n"
                    "- SQL to CREATE TABLE tbl(...) and INSERT sample rows; ensure it runs in DuckDB.\n"
                    "- Python code to build the same DataFrame df (using a list/dict, not reading external files).\n"
                    "- A clear analytical task referencing tbl/df that matches the sample data.\n"
                    "- Expected output description with a tiny example.\n"
                    f"- Match difficulty: '{difficulty}' (easy → 1-2 operations).\n"
                    "- No placeholders like [something].\n"
                    "Important formatting and size requirements:\n"
                    "- Provide the SQL block fenced as ```sql ... ``` and the Python block fenced as ```python ... ``` so they can be parsed.\n"
                    "- The inserted dataset should contain between 30 and 100 rows (not just 5), realistic values, and use the exact names 'tbl' (SQL) and 'df' (pandas).\n"
                )
            else:
                prompt = (
                    "You are running a technical coding interview for a machine learning engineer / software engineer. Provide ONE concise ALGORITHM problem.\n"
                    "Style: array/string/hashmap/graph, etc. (LeetCode-like).\n"
                    "Include in the prompt:\n"
                    "- A precise problem statement.\n"
                    "- A Python function signature (no extra imports) and constraints.\n"
                    "- 2-3 example inputs and outputs.\n"
                    f"- Match difficulty: '{difficulty}'.\n"
                    "- No placeholders like [something].\n"
                    "- End with a directive to implement and run tests."
                )
        text = await self._call_llm(prompt)
        cleaned = self._sanitize_keep_fences(text)
        return cleaned

    async def _generate_technical_followup(self, previous_response: str, context: InterviewContext) -> str:
        # Keep strictly technical; avoid behavioral/STAR
        prompt = (
            "You are in the middle of a coding interview. The candidate responded: \n"
            f"{previous_response}\n"
            "Provide ONE short follow-up (1-2 sentences) focusing on correctness, complexity, edge cases, or tests.\n"
            "Examples of allowed styles: 'What's the time complexity?', 'How would you handle empty input?', "
            "'Can you add a quick test?', 'How could you optimize memory usage?'.\n"
            "Forbidden: any behavioral/STAR 'tell me about a time...' questions."
        )
        text = await self._call_llm(prompt)
        return self._sanitize(text)

    async def _call_llm(self, user_prompt: str) -> str:
        if self.llm_config.provider.value == "openai":
            import openai
            client = openai.OpenAI(api_key=self.llm_config.api_key)
            resp = client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict technical interviewer. Keep guidance concise and technical. "
                            "Never include placeholders in square brackets."
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=220,
                temperature=0.5,
            )
            return resp.choices[0].message.content.strip()
        elif self.llm_config.provider.value == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=self.llm_config.api_key)
            resp = client.messages.create(
                model=self.llm_config.model,
                max_tokens=220,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "System: You are a strict technical interviewer. Keep guidance concise and technical. "
                            "Never include placeholders in square brackets.\n\nUser: "
                            + user_prompt
                        ),
                    }
                ],
            )
            return resp.content[0].text.strip()
        else:
            raise ValueError(f"Unknown provider {self.llm_config.provider.value}")

    def _sanitize_keep_fences(self, text: str) -> str:
        # Remove [placeholders], but KEEP fenced code blocks so backend can parse setup
        if not text:
            return text
        text = re.sub(r"\[[^\]]+\]", "", text)
        return text.strip()

