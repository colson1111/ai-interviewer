"""Technical interviewer agent specialized for coding interviews.

This agent focuses on:
- Pivoting quickly to a coding challenge after the intro
- Short, targeted technical guidance (correctness, complexity, tests, edge cases)
- Avoiding behavioral/STAR questions entirely
"""

from typing import Dict, Any, Optional, Tuple
import time
import re
import subprocess
import sys
import tempfile
from textwrap import dedent
import json

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
        # Prompt with strict constraints and JSON contract output
        role = (getattr(context.candidate_info, 'role_title', None) or '').lower().strip()
        default_role = 'data scientist'
        target_role = role if role else default_role
        difficulty = context.interview_config.difficulty.value
        track = context.interview_config.technical_track.value if getattr(context.interview_config, 'technical_track', None) else None
        
        # Check for skill category hints in the context metadata (passed from our multi-problem system)
        skill_hint = context.session_metadata.get('skill_category_hint', "")
        
        # Build category guidance if we have a skill hint
        category_guidance = ""
        if skill_hint:
            category_guidance = f"\nSKILL FOCUS: {skill_hint} Make sure to design a problem that specifically tests these skills."
        
        # Extract company context
        company_name = getattr(context.candidate_info, 'company_name', None) or ''
        company_context = ""
        if company_name and len(company_name.strip()) > 2:
            company_context = f"\nCOMPANY CONTEXT: This is for {company_name}. Generate data and scenarios relevant to {company_name}'s business domain and operations. Use realistic column names, values, and business questions that would be meaningful for {company_name}."

        # Track-specific prompts
        if track == TechnicalTrack.PANDAS.value:
            prompt = (
                "You are conducting a technical interview. Generate a specific, solvable pandas data analysis problem with a clear expected output.\n"
                "Requirements:\n"
                f"- Difficulty: {difficulty}\n" + self._get_pandas_difficulty_guidance(difficulty) + "\n"
                "- Include a specific question with measurable output (e.g., 'Find the top 3 categories by average sales', 'Count employees hired after 2020 by department')\n"
                "- Provide realistic business data that supports the question\n"
                "- The dataset should make the answer non-trivial but achievable\n"
                "\n" + self._get_pandas_examples_by_difficulty(difficulty) + "\n"
                "\nBad questions (too vague): 'Analyze the data', 'Filter and aggregate', 'Find patterns'\n"
                + company_context + category_guidance
            )
        elif track == TechnicalTrack.SQL.value:
            prompt = (
                "You are conducting a technical interview. Generate a specific, solvable SQL problem with a clear expected output.\n"
                "Requirements:\n"
                f"- Difficulty: {difficulty}\n" + self._get_sql_difficulty_guidance(difficulty) + "\n"
                "- Include a specific question with measurable output (e.g., 'Find the top 5 customers by total order value', 'Calculate monthly revenue growth rate')\n"
                "- Provide realistic business data that supports the question\n"
                "- The dataset should make the answer non-trivial but achievable\n"
                "\n" + self._get_sql_examples_by_difficulty(difficulty) + "\n"
                "\nBad questions (too vague): 'Query the data', 'Find insights', 'Analyze trends'\n"
                + company_context
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
                    "You are conducting a technical interview for a data analyst/scientist. Generate a specific, solvable data analysis problem with a clear expected output.\n"
                    "Requirements:\n"
                    f"- Difficulty: {difficulty} (easy = 1-2 operations, medium = multi-step analysis, hard = complex business logic)\n"
                    "- Include a specific question with measurable output (e.g., 'Calculate customer churn rate by segment', 'Find the most profitable product categories')\n"
                    "- Provide realistic business data that supports the question\n"
                    "- The dataset should make the answer non-trivial but achievable with pandas or SQL\n"
                    "\nExample good questions:\n"
                    "- 'Calculate the conversion rate for each marketing channel and identify the most effective channel'\n"
                    "- 'Find customers who made purchases in both Q1 and Q2 2023, and calculate their average order value'\n"
                    "- 'Analyze sales trends by region and identify which regions had declining sales in the last quarter'\n"
                    "\nBad questions (too vague): 'Explore the data', 'Find patterns', 'Generate insights'\n"
                    + company_context
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
        # Strict JSON contract: model must return a single JSON object
        contract = (
            "You must respond ONLY with a JSON object matching this schema: \n"
            "{\n"
            "  \"description\": \"SPECIFIC actionable task with measurable output\",\n"
            "  \"dataset\": {\n"
            "    \"columns\": {\n"
            "      \"col1\": [val1, val2, val3, ... AT LEAST 80 values],\n"
            "      \"col2\": [val1, val2, val3, ... AT LEAST 80 values],\n"
            "      \"col3\": [val1, val2, val3, ... AT LEAST 80 values]\n"
            "    }\n"
            "  }\n"
            "}\n"
            "DESCRIPTION RULES: Must be a specific task, NOT vague like 'Analyze data' or 'Find insights'. Examples:\n"
            "✅ GOOD: 'Calculate the average rating for each movie genre and identify the top 3 highest-rated genres'\n"
            "✅ GOOD: 'Find all customers who made purchases over $500 and group by region showing total revenue per region'\n"
            "❌ BAD: 'Analyzing movie ratings', 'Explore the data', 'Find patterns'\n"
            "\n"
            "🎯 DATASET REQUIREMENTS 🎯\n"
            "- CRITICAL: Generate EXACTLY 80 values per column (minimum 80, maximum 100)\n"
            "- Use 3 columns only to stay under token limits\n"
            "- Count carefully: you need 80+ values in each array\n"
            "- Example with SHORT values:\n"
            '  "columns": {\n'
            '    "item": ["A1","A2","A3","A4","A5",...continue to 80+ items],\n'
            '    "price": [10,20,30,40,50,...continue to 80+ numbers],\n'
            '    "type": ["X","Y","Z","X","Y",...continue to 80+ values]\n'
            "  }\n"
            "- Use SHORT values: single letters/words (A,B,C not ProductA,ProductB,ProductC)\n"
            "- Repeat patterns if needed: [A,B,C,A,B,C,A,B,C...] to reach 80+\n"
            "- System will trim to equal lengths, so generate 80-90 values per column\n"
            "Focus area: " + ("pandas" if track == TechnicalTrack.PANDAS.value else ("sql" if track == TechnicalTrack.SQL.value else "analytics"))
        )

        max_attempts = 5
        attempt = 1
        parsed: Dict[str, Any] = {}
        last_error = ""
        while attempt <= max_attempts:
            print(f"DEBUG: JSON generation attempt {attempt}/{max_attempts}")
            text = await self._call_llm(prompt + "\n\n" + contract, max_tokens=2500, force_json=True)
            print(f"DEBUG: LLM raw response length: {len(text)} chars")
            print(f"DEBUG: LLM raw response (first 800 chars): {text[:800]}")
            if len(text) > 800:
                print(f"DEBUG: LLM raw response (last 200 chars): ...{text[-200:]}")
            obj, err = self._extract_json_object(text)
            print(f"DEBUG: JSON extraction result: obj={bool(obj)}, err={err}")
            if err and "json" in text.lower():
                # Check if JSON looks truncated
                if text.count("{") > text.count("}"):
                    print(f"DEBUG: JSON appears truncated - missing closing braces")
            if err:
                last_error = f"extract: {err}"
            else:
                # validate fields
                if not isinstance(obj, dict) or "description" not in obj or "dataset" not in obj:
                    last_error = "missing required keys description/dataset"
                    print(f"DEBUG: Missing keys. obj type: {type(obj)}, keys: {list(obj.keys()) if isinstance(obj, dict) else 'N/A'}")
                else:
                    description = str(obj.get("description", "")).strip()
                    print(f"DEBUG: Object has required keys. Dataset: {str(obj.get('dataset'))[:200]}")
                    print(f"DEBUG: Description: {description}")
                    
                    # Validate description specificity
                    vague_patterns = ["analyz", "explor", "find pattern", "find insight", "investigat", "examin"]
                    if len(description) < 20 or any(pattern in description.lower() for pattern in vague_patterns):
                        last_error = f"Description too vague: '{description}'. Need specific task with measurable output."
                        print(f"DEBUG: Description validation failed: {last_error}")
                    else:
                        # Use new validation and trimming function
                        ok, verr, trimmed_dataset = self._validate_and_trim_json_dataset(json.dumps(obj.get("dataset")))
                        print(f"DEBUG: Dataset validation: ok={ok}, error={verr}")
                        if ok and trimmed_dataset:
                            # Check if description is consistent with dataset column names
                            column_names = list(trimmed_dataset.get("columns", {}).keys())
                            desc_ok, desc_err = self._validate_description_column_consistency(description, column_names)
                            print(f"DEBUG: Description-column consistency: ok={desc_ok}, error={desc_err}")
                            if desc_ok:
                                # Additional validation: Check if Easy difficulty is actually easy
                                diff_ok, diff_err = self._validate_difficulty_appropriateness(description, difficulty)
                                print(f"DEBUG: Difficulty appropriateness: ok={diff_ok}, error={diff_err}")
                                if diff_ok:
                                    # Replace the original dataset with the trimmed one
                                    obj["dataset"] = trimmed_dataset
                                    parsed = obj
                                    break
                                else:
                                    last_error = diff_err
                            else:
                                last_error = desc_err
                        else:
                            last_error = verr
            # refine and try again
            print(f"DEBUG: Attempt {attempt} failed: {last_error}")
            
            # More specific refinement based on error type
            if "Insufficient data" in last_error:
                refinement = (
                    f"❌ FAILED: {last_error}\n\n"
                    "🔧 FIX: You're generating too FEW values! COUNT CAREFULLY:\n"
                    "- Each column needs MINIMUM 80 values\n"
                    "- Count as you go: 10, 20, 30, 40, 50, 60, 70, 80!\n"
                    "- Use patterns: A,B,C,A,B,C,A,B,C... (repeat to reach 80)\n"
                    "- Example: [1,2,3,4,5,6,7,8,9,10,11,12,...80] (count to 80!)\n"
                    "- Use only 3 columns with SHORT values\n"
                    "CRITICAL: Actually count to 80+ values per column!"
                )
            elif "must be lists" in last_error:
                refinement = (
                    f"❌ FAILED: {last_error}\n\n"
                    "🔧 FIX: All column values must be arrays/lists. Use [ ] brackets for each column.\n"
                    'Correct format: "column_name": [val1, val2, val3, ...]'
                )
            elif "no json found" in last_error or "truncated" in last_error:
                refinement = (
                    f"❌ FAILED: {last_error}\n\n"
                    "🔧 FIX: Your response is too LONG! Make it SHORTER:\n"
                    "- Use ONLY 3 columns (not 4!)\n"
                    "- Use SINGLE characters: A,B,C,1,2,3,X,Y,Z\n"
                    "- Generate exactly 80 values (not 100+)\n"
                    "- NO long names like 'Product1', use 'A' instead\n"
                    "- Keep JSON compact: remove spaces, short keys\n"
                    "Reply with COMPLETE, valid JSON that fits in response limit."
                )
            elif "Description refers to columns that don't exist" in last_error:
                refinement = (
                    f"❌ FAILED: {last_error}\n\n"
                    "🔧 FIX: Your task description mentions column names that don't exist in your dataset!\n"
                    "Either:\n"
                    "1. Change the column names in your dataset to match the task, OR\n"
                    "2. Rewrite the task description to use the column names you actually provided\n"
                    "Make sure the task description only refers to columns that exist in your dataset."
                )
            elif "EASY problem contains forbidden complexity" in last_error:
                refinement = (
                    f"❌ FAILED: {last_error}\n\n"
                    "🔧 FIX: Your EASY problem is too complex! EASY problems must be single-step only.\n"
                    "Examples of EASY tasks:\n"
                    "- 'Display the first 10 rows'\n"
                    "- 'Show all records where price > 100'\n"
                    "- 'Calculate the total revenue'\n"
                    "- 'Find the average price'\n"
                    "NO grouping, sorting, or multi-step operations for EASY!"
                )
            elif "EASY problem must use simple" in last_error:
                refinement = (
                    f"❌ FAILED: {last_error}\n\n"
                    "🔧 FIX: Make your EASY problem simpler and more direct.\n"
                    "Use words like: show, display, find, total, average, count, where, first, last\n"
                    "Single-step operations only!"
                )
            else:
                refinement = (
                    f"Previous output invalid: {last_error}. Reply ONLY with valid JSON. Keep it simple: 3-4 columns, 80-100 SHORT values each."
                )
            
            prompt = prompt + "\n\n" + refinement
            attempt += 1

        if not parsed:
            # Final fallback: still return something informative rather than empty
            return (
                "### Challenge Description\n"
                "An issue occurred generating the dataset. Please request another problem."
            )

        # Construct the final editor prompt ourselves: description + fenced JSON dataset
        description = str(parsed.get("description", ""))
        dataset_json = json.dumps(parsed.get("dataset", {}), indent=2)
        editor_text = (
            "### Challenge Description\n" + description + "\n\n" +
            "```json\n" + dataset_json + "\n```"
        )
        print(f"DEBUG: Final editor_text being returned: {editor_text[:300]}")
        return editor_text

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
        text = await self._call_llm(prompt, max_tokens=800)
        return self._sanitize_keep_fences(text)

    async def _call_llm(self, user_prompt: str, max_tokens: int = 220, force_json: bool = False) -> str:
        if self.llm_config.provider.value == "openai":
            import openai
            client = openai.OpenAI(api_key=self.llm_config.api_key)
            
            # Determine system message based on whether we need JSON or natural text
            # Only use JSON if explicitly forced or if user wants JSON generation (not just mentions JSON)
            wants_json_generation = "respond with JSON" in user_prompt.lower() or "return JSON" in user_prompt.lower() or "generate JSON" in user_prompt.lower()
            if force_json or wants_json_generation:
                system_content = (
                    "You are a strict technical interviewer. Keep guidance concise and technical. "
                    "Never include placeholders in square brackets. Respond with JSON when asked."
                )
                use_json_format = True
            else:
                system_content = (
                    "You are a friendly but professional technical interviewer. "
                    "Provide helpful, constructive feedback in natural conversational language. "
                    "Write in plain text paragraphs like normal human conversation. "
                    "NEVER use JSON, dictionaries, structured data, or any curly braces {}. "
                    "Write as if you're speaking directly to the candidate."
                )
                use_json_format = False
            
            resp = client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.5,
                response_format={"type": "json_object"} if (use_json_format and "gpt" in self.llm_config.model) else None,
            )
            return resp.choices[0].message.content.strip()
        elif self.llm_config.provider.value == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=self.llm_config.api_key)
            resp = client.messages.create(
                model=self.llm_config.model,
                max_tokens=max_tokens,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "System: You are a strict technical interviewer. Keep guidance concise and technical. "
                            "Never include placeholders in square brackets. Respond with JSON when asked.\n\nUser: "
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

    def _extract_json_block(self, text: str) -> str:
        if not text:
            return ""
        m = re.search(r"```json\n([\s\S]*?)```", text)
        if m:
            return m.group(1).strip()
        m_incomplete = re.search(r"```json\n([\s\S]*?)$", text)
        if m_incomplete:
            return m_incomplete.group(1).strip()
        return ""

    def _extract_python_block(self, text: str) -> str:
        if not text:
            return ""
        m = re.search(r"```python\n([\s\S]*?)```", text)
        if m:
            return dedent(m.group(1)).strip()
        m_incomplete = re.search(r"```python\n([\s\S]*?)$", text)
        if m_incomplete:
            return dedent(m_incomplete.group(1)).strip()
        return ""

    def _validate_python_setup(self, python_code: str) -> Tuple[bool, str]:
        """Execute python_code in isolated subprocess; verify it defines a pandas DataFrame 'df'.
        Returns (ok, error_message).
        """
        try:
            code_literal = repr(dedent(python_code or ""))
            script = (
                "import sys\n"
                "try:\n"
                "    import pandas as pd\n"
                "except Exception:\n"
                "    pass\n"
                "try:\n"
                "    _code = " + code_literal + "\n"
                "    exec(_code, globals())\n"
                "    import pandas as pd\n"
                "    assert 'df' in globals(), 'name \'df\' is not defined'\n"
                "    assert isinstance(df, pd.DataFrame), 'df is not a pandas DataFrame'\n"
                "    n = len(df)\n"
                "    assert 30 <= n <= 200, f'row count {n} out of expected bounds (30-200)'\n"
                "    print('OK', n)\n"
                "except Exception as e:\n"
                "    print('ERR', str(e))\n"
                "    sys.exit(1)\n"
            )
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
                tmp.write(script)
                path = tmp.name
            try:
                completed = subprocess.run([sys.executable, "-I", "-B", path], capture_output=True, text=True, timeout=10)
                if completed.returncode == 0 and "OK" in (completed.stdout or ""):
                    return True, ""
                err_msg = (completed.stdout + "\n" + completed.stderr).strip()
                return False, err_msg
            finally:
                try:
                    import os
                    os.unlink(path)
                except Exception:
                    pass
        except Exception as e:
            return False, str(e)

    def _validate_and_trim_json_dataset(self, json_text: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate and trim dataset to ensure equal column lengths.
        Returns (ok, error_message, trimmed_dataset)
        """
        try:
            obj = json.loads(json_text)
        except Exception as e:
            return False, f"Invalid JSON: {e}", None
            
        # columns schema
        if isinstance(obj, dict) and "columns" in obj and isinstance(obj["columns"], dict):
            columns = obj["columns"]
            if not columns:
                return False, "columns dict is empty", None
            
            # Check that all values are lists
            non_list_columns = [k for k, v in columns.items() if not isinstance(v, list)]
            if non_list_columns:
                return False, f"columns {non_list_columns} must be lists", None
            
            # Get lengths 
            column_lengths = {k: len(v) for k, v in columns.items()}
            lengths = list(column_lengths.values())
            
            if not lengths:
                return False, "no column data found", None
            
            # Check minimum length requirement (at least 40 values to work with)
            min_length = min(lengths)
            if min_length < 40:
                length_summary = ", ".join([f"{k}({length})" for k, length in column_lengths.items()])
                return False, f"Insufficient data: minimum column has {min_length} values, need at least 40. Got: {length_summary}", None
            
            # Trim all columns to equal length (random between 40-70, but not exceeding min_length)
            import random
            max_possible = min(min_length, 70)
            target_length = random.randint(40, max_possible)
            
            # Trim each column to target_length
            trimmed_columns = {}
            for col_name, col_data in columns.items():
                trimmed_columns[col_name] = col_data[:target_length]
            
            trimmed_dataset = {"columns": trimmed_columns}
            print(f"DEBUG: Successfully trimmed dataset to {target_length} rows per column")
            
            return True, "", trimmed_dataset
            
        # rows schema (legacy support)
        if isinstance(obj, dict) and "rows" in obj and isinstance(obj["rows"], list):
            n = len(obj["rows"])
            if n < 30:
                return False, f"Insufficient rows: {n} (need at least 30)", None
            # Trim rows if too many
            if n > 70:
                import random
                target_rows = random.randint(40, 70)
                obj["rows"] = obj["rows"][:target_rows]
                print(f"DEBUG: Trimmed rows from {n} to {target_rows}")
            return True, "", obj
            
        return False, "expected 'columns' or 'rows' schema", None

    def _validate_json_dataset(self, json_text: str) -> Tuple[bool, str]:
        """Legacy wrapper for compatibility"""
        ok, error, _ = self._validate_and_trim_json_dataset(json_text)
        return ok, error
    
    def _validate_description_column_consistency(self, description: str, column_names: list) -> Tuple[bool, str]:
        """Check if the challenge description refers to column names that actually exist in the dataset.
        Returns (ok, error_message)
        """
        import re
        
        # Convert description to lowercase for comparison
        desc_lower = description.lower()
        
        # Common column reference patterns to check
        # Look for phrases like "by category", "group by category", "product_category", etc.
        potential_column_refs = []
        
        # Extract quoted column names
        quoted_matches = re.findall(r'["`]([^"`]+)["`]', description)
        potential_column_refs.extend(quoted_matches)
        
        # Extract words that might be column names (common patterns)
        # Look for patterns like "by X", "group by X", "aggregate by X", "X column"
        by_pattern_matches = re.findall(r'\bby\s+([a-zA-Z_][a-zA-Z0-9_]*)', desc_lower)
        potential_column_refs.extend(by_pattern_matches)
        
        # Look for underscore patterns that are common in column names
        underscore_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*_[a-zA-Z0-9_]+)\b', desc_lower)
        potential_column_refs.extend(underscore_matches)
        
        # Normalize column names for comparison
        column_names_lower = [col.lower() for col in column_names]
        
        # Check if any potential column references don't exist in actual columns
        missing_columns = []
        for ref in potential_column_refs:
            ref_lower = ref.lower().strip()
            if ref_lower and ref_lower not in column_names_lower:
                # Only flag if it's likely a column name (not generic words)
                if ('_' in ref_lower or 
                    any(keyword in ref_lower for keyword in ['category', 'type', 'group', 'segment', 'region', 'department', 'status'])):
                    missing_columns.append(ref)
        
        if missing_columns:
            available_cols = ', '.join(column_names)
            missing_cols = ', '.join(missing_columns)
            return False, f"Description refers to columns that don't exist: {missing_cols}. Available columns: {available_cols}"
        
        return True, ""
    
    def _validate_difficulty_appropriateness(self, description: str, difficulty: str) -> Tuple[bool, str]:
        """Validate that the challenge description matches the specified difficulty level."""
        desc_lower = description.lower()
        
        if difficulty.lower() == "easy":
            # Check for forbidden complexity indicators in Easy problems
            forbidden_easy_patterns = [
                'group by', 'groupby', 'sort', 'sorting', 'rank', 'top ', 'highest', 'lowest',
                'merge', 'join', 'pivot', 'rolling', 'window', 'aggregate', 'agg',
                'each category', 'per category', 'by category', 'category breakdown',
                'descending', 'ascending', 'order by', 'sorted by'
            ]
            
            found_forbidden = [pattern for pattern in forbidden_easy_patterns if pattern in desc_lower]
            if found_forbidden:
                return False, f"EASY problem contains forbidden complexity: {', '.join(found_forbidden)}. Easy problems must be single-step operations only."
                
            # Check for required simplicity indicators
            simple_patterns = [
                'first', 'last', 'show', 'display', 'find all', 'total', 'sum', 'average', 'mean',
                'count', 'where', 'greater than', 'less than', 'equals'
            ]
            
            has_simple = any(pattern in desc_lower for pattern in simple_patterns)
            if not has_simple:
                return False, "EASY problem must use simple, single-step language like 'show first 10', 'find total', 'filter where X > Y'"
        
        elif difficulty.lower() == "medium":
            # Medium should have some complexity but not too much
            complex_patterns = ['group', 'sort', 'top', 'aggregate', 'merge', 'join']
            has_complexity = any(pattern in desc_lower for pattern in complex_patterns)
            
            # But shouldn't have advanced features (use same patterns as hard validation)
            advanced_patterns = [
                'rolling', 'window', 'pivot', 'shift', 'lag', 'cumulative',
                'moving average', 'growth rate', 'percentage change', 'month over month',
                'rate of change', '7-day', '30-day', 'running total', 'running average'
            ]
            has_advanced = any(pattern in desc_lower for pattern in advanced_patterns)
            
            if has_advanced:
                return False, f"MEDIUM problem contains HARD-level features: {[p for p in advanced_patterns if p in desc_lower]}. Use simpler operations for medium."
        
        elif difficulty.lower() == "hard":
            # Hard should have advanced complexity - check for various forms of advanced concepts
            advanced_patterns = [
                # Explicit pandas terms
                'rolling', 'window', 'pivot', 'shift', 'lag', 'cumulative', 'complex', 'multi-step',
                # Time series and growth analysis
                'moving average', 'growth rate', 'percentage change', 'month over month', 'monthly change',
                'rate of change', 'change over time', 'time series', 'trend analysis',
                # Window function concepts
                'running total', 'running average', 'running sum', 'previous period', 'prior period',
                '7-day', '30-day', 'daily average', 'weekly average', 'monthly average',
                # Advanced aggregations and transformations
                'rank by', 'percentile', 'quartile', 'correlation', 'variance',
                'standard deviation', 'normalize', 'scaling'
            ]
            
            # Multi-step complexity patterns (hard via sequential operations)
            multi_step_patterns = [
                # Sequential operation indicators
                'then', 'after that', 'next', 'followed by', 'finally', 'step by step',
                # Multiple requirements
                'and then', 'also', 'additionally', 'furthermore', 'as well as',
                # Conditional logic
                'if', 'where', 'when', 'for each', 'depending on', 'based on',
                # Multiple transformations
                'first.*then', 'calculate.*and.*identify', 'find.*and.*rank', 'group.*sort.*filter',
                # Complex filtering/conditions
                'exclude', 'remove', 'only include', 'that meet', 'satisfying', 'criteria'
            ]
            
            has_advanced = any(pattern in desc_lower for pattern in advanced_patterns)
            has_multi_step = any(pattern in desc_lower for pattern in multi_step_patterns)
            
            # Count operation words to detect multi-step complexity
            operation_words = ['calculate', 'find', 'identify', 'filter', 'sort', 'group', 'rank', 'select', 'transform', 'merge', 'join', 'aggregate', 'sum', 'count', 'average']
            operation_count = sum(1 for word in operation_words if word in desc_lower)
            
            if not (has_advanced or has_multi_step or operation_count >= 3):
                # Check if it at least has moderate complexity
                moderate_patterns = ['group', 'aggregate', 'multiple', 'combine', 'merge', 'join', 'transformation']
                has_moderate = any(pattern in desc_lower for pattern in moderate_patterns)
                
                if not has_moderate:
                    return False, "HARD problem is too simple. Must include either: (1) Advanced pandas features like rolling/pivot functions, (2) Multi-step sequential operations, or (3) Complex conditional logic requiring 3+ operations."
        
        return True, ""
    
    def _get_pandas_difficulty_guidance(self, difficulty: str) -> str:
        """Get specific, actionable difficulty guidance for pandas problems."""
        if difficulty.lower() == "easy":
            return (
                "🟢 EASY DIFFICULTY - STRICT REQUIREMENTS:\n"
                "  • MAXIMUM 1-2 operations - NO METHOD CHAINING\n"
                "  • ALLOWED ONLY: .head(), .tail(), .info(), .describe(), basic filtering df[condition], df.sum(), df.mean(), df.count()\n"
                "  • SIMPLE single-step tasks: 'Show first 10 rows', 'Find total of column X', 'Filter where column > value'\n"
                "  • STRICTLY FORBIDDEN: .groupby(), .sort_values(), .merge(), chaining operations, multiple steps\n"
                "  • If you need groupby or sorting, this is MEDIUM difficulty, not EASY\n"
                "  • Dataset: 3 columns max, simple data types (int, string)\n"
                "  • Expected solution: EXACTLY 1 line of pandas code\n"
                "  • Examples: df.head(10), df[df['price'] > 100], df['sales'].sum(), df['category'].value_counts()"
            )
        elif difficulty.lower() == "medium":
            return (
                "🟡 MEDIUM DIFFICULTY REQUIREMENTS:\n"
                "  • Use 2-4 pandas operations, some chaining allowed\n"
                "  • Focus on: .groupby() with multiple aggs, .merge(), .sort_values(), .nlargest(), filtering with conditions\n"
                "  • Examples: 'Find top 3 customers by total spend', 'Calculate average rating per category, show only >4.0'\n"
                "  • Allow: Method chaining, multiple conditions, basic date operations, .reset_index()\n"
                "  • Dataset: 3-4 columns, mixed data types (int, float, string, simple dates)\n"
                "  • Expected solution: 2-4 lines of pandas code with some intermediate steps"
            )
        elif difficulty.lower() == "hard":
            return (
                "🔴 HARD DIFFICULTY REQUIREMENTS (Multiple paths to complexity):\n"
                "  PATH 1 - Advanced Functions: Window functions (.rolling(), .shift()), .pivot_table(), multi-level indexing\n"
                "  PATH 2 - Multi-Step Logic: Sequential operations requiring 3+ distinct steps with intermediate results\n"
                "  PATH 3 - Complex Conditions: Multiple filters, conditional transformations, data cleaning + analysis\n"
                "  \n"
                "  • Examples - Advanced: 'Calculate 3-month rolling average by category'\n"
                "  • Examples - Multi-step: 'First filter outliers, then group by region, finally rank top 3 performers'\n"
                "  • Examples - Conditional: 'Identify products where sales increased AND margin decreased, exclude seasonal items'\n"
                "  \n"
                "  • Require: Either advanced pandas features OR multi-step workflow OR complex business logic\n"
                "  • Dataset: 4+ columns, mixed data types enabling complex analysis\n"
                "  • Expected solution: 5+ lines requiring careful planning and execution"
            )
        else:
            return "• Follow the specified difficulty level requirements"
    
    def _get_sql_difficulty_guidance(self, difficulty: str) -> str:
        """Get specific, actionable difficulty guidance for SQL problems."""
        if difficulty.lower() == "easy":
            return (
                "🟢 EASY SQL REQUIREMENTS:\n"
                "  • Use basic SELECT, WHERE, ORDER BY only\n"
                "  • Focus on: Simple filtering, sorting, basic aggregation (COUNT, SUM, AVG)\n"
                "  • Examples: 'SELECT * WHERE price > 100', 'COUNT customers by region'\n"
                "  • Avoid: JOINs, subqueries, window functions, complex conditions\n"
                "  • Expected solution: 1-3 lines of SQL"
            )
        elif difficulty.lower() == "medium":
            return (
                "🟡 MEDIUM SQL REQUIREMENTS:\n"
                "  • Use GROUP BY, HAVING, simple JOINs, CASE statements\n"
                "  • Focus on: Aggregation with grouping, inner joins, conditional logic\n"
                "  • Examples: 'JOIN tables to find customer orders', 'GROUP BY with HAVING clauses'\n"
                "  • Allow: Multiple table operations, subqueries in WHERE\n"
                "  • Expected solution: 4-8 lines of SQL with moderate complexity"
            )
        elif difficulty.lower() == "hard":
            return (
                "🔴 HARD SQL REQUIREMENTS:\n"
                "  • Use window functions, CTEs, complex subqueries, multiple JOINs\n"
                "  • Focus on: ROW_NUMBER(), RANK(), LAG(), LEAD(), recursive CTEs\n"
                "  • Examples: 'Calculate running totals', 'Find nth highest value per group'\n"
                "  • Require: Advanced SQL concepts, nested queries, complex business logic\n"
                "  • Expected solution: 10+ lines of SQL with high complexity"
            )
        else:
            return "• Follow the specified difficulty level requirements"
    
    def _get_pandas_examples_by_difficulty(self, difficulty: str) -> str:
        """Get difficulty-appropriate example questions for pandas."""
        if difficulty.lower() == "easy":
            return (
                "Example EASY questions (single-step only):\n"
                "- 'Display the first 10 rows of the dataset'\n"
                "- 'Show all products where price is greater than $100'\n"
                "- 'Calculate the total revenue across all records'\n"
                "- 'Find the average price of all products'\n"
                "- 'Count the total number of customers in the dataset'\n"
                "- 'Show basic statistics for the price column'"
            )
        elif difficulty.lower() == "medium":
            return (
                "Example MEDIUM questions:\n"
                "- 'Find the top 5 customers by total purchase amount and display their names and total spent'\n"
                "- 'Calculate the average rating for each product category and show only categories with rating > 4.0'\n"
                "- 'Group orders by month and calculate total revenue per month, sorted by revenue descending'\n"
                "- 'Find products that have both high sales (>$1000) and high ratings (>4.5)'"
            )
        elif difficulty.lower() == "hard":
            return (
                "Example HARD questions:\n"
                "- 'Calculate the 3-month rolling average of sales for each product category'\n"
                "- 'Find customers whose purchase amounts increased each quarter compared to the previous quarter'\n"
                "- 'Create a pivot table showing average order value by customer segment and payment method'\n"
                "- 'Identify customers who made purchases in consecutive months and calculate their monthly growth rate'"
            )
        else:
            return (
                "Example questions:\n"
                "- Generate appropriate examples based on the difficulty level"
            )
    
    def _get_sql_examples_by_difficulty(self, difficulty: str) -> str:
        """Get difficulty-appropriate example questions for SQL."""
        if difficulty.lower() == "easy":
            return (
                "Example EASY questions:\n"
                "- 'SELECT all customers from California'\n"
                "- 'COUNT the total number of orders'\n"
                "- 'Find the highest priced product'\n"
                "- 'Show all orders placed after 2023-01-01 ordered by date'"
            )
        elif difficulty.lower() == "medium":
            return (
                "Example MEDIUM questions:\n"
                "- 'JOIN customers and orders to find total spent per customer'\n"
                "- 'GROUP BY category and calculate average price, show only categories with avg > $50'\n"
                "- 'Find the top 5 customers by order count using subqueries'\n"
                "- 'Use CASE statements to categorize orders as small/medium/large based on value'"
            )
        elif difficulty.lower() == "hard":
            return (
                "Example HARD questions:\n"
                "- 'Use ROW_NUMBER() to find the 2nd highest order value for each customer'\n"
                "- 'Calculate running totals of revenue by month using window functions'\n"
                "- 'Use CTEs to find customers who had increasing order values in consecutive months'\n"
                "- 'Complex multi-table JOIN with subqueries to find top performing product categories by region'"
            )
        else:
            return (
                "Example questions:\n"
                "- Generate appropriate examples based on the difficulty level"
            )

    def _extract_json_object(self, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        # Try direct JSON
        try:
            return json.loads(text), ""
        except Exception:
            pass
        # Try fenced block
        block = self._extract_json_block(text)
        if block:
            try:
                return json.loads(block), ""
            except Exception as e:
                return None, f"fenced json invalid: {e}"
        # Try loose extraction between first and last brace
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start:end+1]), ""
        except Exception as e:
            return None, f"loose parse failed: {e}"
        return None, "no json found"

