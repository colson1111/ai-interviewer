"""
AI-powered mock interview application with multi-agent system.

This application provides:
- Real-time interview conversations with AI agents
- Multi-agent coordination (interview, search, feedback, summary)
- WebSocket-based communication
- Cost tracking and monitoring
- File upload and processing
- TTS and STT capabilities
"""

import os
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from openai import OpenAI
        
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from interviewer.config import LLMConfig, InterviewConfig, LLMProvider, InterviewType, Tone, Difficulty, TechnicalTrack
from interviewer.core import InterviewContext, CandidateInfo
from interviewer.document_parser import create_document_context
from interviewer.multi_agent_system import create_multi_agent_interview_system
from interviewer.cost_tracker import CostTracker


# Load environment variables from .env_local
load_dotenv('.env_local')

# Import our existing interviewer components
from interviewer.config import LLMConfig, InterviewConfig, LLMProvider, InterviewType, Tone, Difficulty
from interviewer.multi_agent_system import create_multi_agent_interview_system
from interviewer.document_parser import create_document_context
from interviewer.cost_tracker import CostTracker, estimate_tokens_detailed
from interviewer.core import InterviewContext, CandidateInfo, InterviewPhase
import subprocess
import sys
import tempfile


# Technical problem skill categories for diverse coverage
TECHNICAL_SKILL_CATEGORIES = [
    {
        "name": "basic_aggregation",
        "description": "simple groupby operations, basic statistics (sum, mean, count)",
        "keywords": ["groupby", "aggregation", "sum", "mean", "count", "total"],
        "focus": "Group data by categories and calculate totals, averages, or counts"
    },
    {
        "name": "filtering_ranking", 
        "description": "filtering data with conditions, sorting and ranking results",
        "keywords": ["filter", "sort", "top", "bottom", "rank", "condition"],
        "focus": "Find records that meet criteria, rank items, identify outliers"
    },
    {
        "name": "date_extraction",
        "description": "extracting date components, basic date filtering", 
        "keywords": ["date", "year", "month", "day", "weekday", "extract"],
        "focus": "Extract date parts, filter by date ranges, format dates"
    },
    {
        "name": "time_series_analysis",
        "description": "rolling calculations, lag operations, growth rates",
        "keywords": ["rolling", "cumulative", "window", "lag", "lead", "growth"],
        "focus": "Calculate moving averages, compare periods, trend analysis"
    },
    {
        "name": "data_relationships",
        "description": "merging datasets, joining tables, combining data sources",
        "keywords": ["join", "merge", "combine", "relationship", "foreign key"],
        "focus": "Combine multiple datasets, match records across tables"
    },
    {
        "name": "text_operations",
        "description": "string manipulation, pattern matching, text cleaning",
        "keywords": ["string", "text", "contains", "regex", "pattern", "split"],
        "focus": "Clean text data, extract patterns, categorize text content"
    },
    {
        "name": "conditional_logic",
        "description": "complex filtering, multi-step transformations, business logic",
        "keywords": ["if", "where", "case", "condition", "logic", "transform"],
        "focus": "Apply business rules, multi-step data transformations, conditional operations"
    }
]

async def handle_next_technical_problem(session, interview_system, context, websocket):
    """
    Generate the next technical problem in a 3-problem sequence with diverse skill coverage.
    """
    try:
        # Initialize or get problem tracking
        if "technical_problems" not in session:
            session["technical_problems"] = {
                "completed": 0,
                "used_categories": [],
                "total_target": 3
            }
        
        problem_tracker = session["technical_problems"]
        problem_tracker["completed"] += 1
        
        print(f"DEBUG: Technical problem {problem_tracker['completed']}/{problem_tracker['total_target']} completed")
        
        # Check if we should generate another problem
        if problem_tracker["completed"] < problem_tracker["total_target"]:
            # Choose next skill category (avoid previously used ones)
            available_categories = [cat for cat in TECHNICAL_SKILL_CATEGORIES 
                                  if cat["name"] not in problem_tracker["used_categories"]]
            
            if available_categories:
                import random
                next_category = random.choice(available_categories)
                problem_tracker["used_categories"].append(next_category["name"])
                
                print(f"DEBUG: Generating next problem with category: {next_category['name']}")
                
                # Generate next problem with specific skill focus
                await generate_next_technical_problem(session, interview_system, context, websocket, next_category)
            else:
                # Fallback if we've used all categories
                await generate_next_technical_problem(session, interview_system, context, websocket, None)
        else:
            # All problems completed
            await websocket.send_text(json.dumps({
                "type": "interviewer",
                "content": "Excellent work! You've completed all three technical challenges. That concludes the technical portion of our interview. Do you have any questions about the problems or would you like to discuss your approach to any of them?",
                "timestamp": datetime.now().isoformat()
            }))
            
    except Exception as e:
        print(f"DEBUG: Error in handle_next_technical_problem: {e}")
        import traceback
        traceback.print_exc()

async def generate_next_technical_problem(session, interview_system, context, websocket, skill_category):
    """
    Generate a new technical problem with optional skill category focus.
    """
    try:
        # Build a prompt that focuses on the specific skill category
        if skill_category:
            category_prompt = (f"Generate a {skill_category['description']} problem. "
                             f"Focus on skills like: {', '.join(skill_category['keywords'])}. "
                             "Make sure this is different from previous problems.")
        else:
            category_prompt = "Generate a different type of problem from previous ones."
        
        # Create a more detailed prompt for the next problem
        next_problem_prompt = (
            f"Please provide the next coding challenge. {category_prompt} "
            "Create a new dataset and problem that tests different pandas/SQL skills. "
            "This should be a standalone challenge with its own dataset."
        )
        
        # Add skill category hint to context if available
        if skill_category:
            # Store skill hint in session for the technical agent to use  
            session["skill_category_hint"] = f"{skill_category['description']} - {skill_category['focus']}"
            print(f"DEBUG: Set skill hint: {session['skill_category_hint']}")
            
            # Also add to context metadata for immediate use
            context.session_metadata = context.session_metadata or {}
            context.session_metadata['skill_category_hint'] = session["skill_category_hint"]
        
        print(f"DEBUG: Generating next problem with prompt: {next_problem_prompt}")
        
        # Generate coding challenge directly instead of going through normal message processing
        from interviewer.agents.technical import TechnicalInterviewerAgent
        tech_agent = TechnicalInterviewerAgent(llm_config=session["llm_config"])
        
        # Call the coding challenge generation directly
        challenge = await tech_agent._generate_coding_challenge(context)
        
        # Create a proper response with coding challenge metadata
        class MockResponse:
            def __init__(self):
                self.content = "I'll place the next coding problem in the editor now. This one focuses on different skills from the previous challenge."
                self.metadata = {
                    'question_type': 'coding_challenge',
                    'question_number': session["technical_problems"]["completed"] + 1,
                    'interview_phase': 'coding',
                    'editor_prompt': challenge,
                    'primary_agent_metadata': {
                        'question_type': 'coding_challenge',
                        'question_number': session["technical_problems"]["completed"] + 1,
                        'interview_phase': 'coding',
                        'editor_prompt': challenge,
                    }
                }
        
        primary = MockResponse()
        combined_response = {
            'primary_response': primary,
            'metadata': {'agents_used': ['technical_interviewer']}
        }
        meta_raw = getattr(primary, "metadata", {}) or {}
        agent_meta = meta_raw.get("primary_agent_metadata", {}) if isinstance(meta_raw, dict) else {}
        
        question_type = agent_meta.get("question_type") or meta_raw.get("question_type")
        
        if question_type == "coding_challenge":
            # Send coding prompt to editor
            editor_prompt = agent_meta.get("editor_prompt", "")
            if editor_prompt:
                question_num = agent_meta.get("question_number", 1)
                print(f"DEBUG: Sending coding_prompt with question_number: {question_num}")
                await websocket.send_text(json.dumps({
                    "type": "coding_prompt",
                    "content": editor_prompt,
                    "question_number": question_num,
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Store current problem
                session["current_problem"] = editor_prompt
                print(f"DEBUG: Next problem sent to editor")
                
                # Increment completed count after successfully sending subsequent challenge
                session["technical_problems"]["completed"] += 1
                print(f"DEBUG: Incremented completed count after sending challenge: {session['technical_problems']['completed']}")
            
            # Send concise chat response
            await websocket.send_text(json.dumps({
                "type": "interviewer",
                "content": primary.content,
                "timestamp": datetime.now().isoformat()
            }))
        else:
            # Regular response
            await websocket.send_text(json.dumps({
                "type": "interviewer", 
                "content": primary.content,
                "timestamp": datetime.now().isoformat()
            }))
            
    except Exception as e:
        print(f"DEBUG: Error generating next technical problem: {e}")
        import traceback
        traceback.print_exc()

async def send_feedback_followup_prompt(session, websocket):
    """
    Send a follow-up prompt after feedback asking if user wants to discuss or proceed.
    """
    try:
        # Initialize or get problem tracking
        if "technical_problems" not in session:
            session["technical_problems"] = {
                "completed": 0,
                "used_categories": [],
                "total_target": 3
            }
        
        problem_tracker = session["technical_problems"]
        
        if problem_tracker["completed"] < problem_tracker["total_target"]:
            problems_remaining = problem_tracker["total_target"] - problem_tracker["completed"]
            
            followup_message = (
                f"\n\nWould you like to discuss this solution further, or shall we move on to the next challenge? "
                f"({problems_remaining} more challenge{'s' if problems_remaining > 1 else ''} remaining)"
            )
        else:
            followup_message = (
                "\n\nWould you like to discuss this solution further, or are you ready to wrap up the technical portion?"
            )
        
        await websocket.send_text(json.dumps({
            "type": "interviewer",
            "content": followup_message,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Mark that we're waiting for user decision
        session["awaiting_next_action"] = True
        
    except Exception as e:
        print(f"DEBUG: Error in send_feedback_followup_prompt: {e}")

async def generate_next_technical_problem_on_demand(session, interview_system, context, websocket):
    """
    Generate the next technical problem when user explicitly requests it (don't auto-increment counter).
    """
    try:
        # Initialize or get problem tracking
        if "technical_problems" not in session:
            session["technical_problems"] = {
                "completed": 0,
                "used_categories": [],
                "total_target": 3
            }
        
        problem_tracker = session["technical_problems"]
        
        print(f"DEBUG: Generating next technical problem on demand: {problem_tracker['completed']}/{problem_tracker['total_target']} completed")
        
        # Check if we should generate another problem
        if problem_tracker["completed"] < problem_tracker["total_target"]:
            # Choose next skill category (avoid previously used ones)
            available_categories = [cat for cat in TECHNICAL_SKILL_CATEGORIES 
                                  if cat["name"] not in problem_tracker["used_categories"]]
            
            if available_categories:
                import random
                next_category = random.choice(available_categories)
                problem_tracker["used_categories"].append(next_category["name"])
                
                print(f"DEBUG: Generating next problem with category: {next_category['name']}")
                
                # Clear the editor first
                await websocket.send_text(json.dumps({
                    "type": "clear_editor",
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Send "generating" message to user
                await websocket.send_text(json.dumps({
                    "type": "interviewer",
                    "content": f"Great! Let me prepare your next challenge focusing on {next_category['description']}. This will take a moment...",
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Generate next problem with specific skill focus
                await generate_next_technical_problem(session, interview_system, context, websocket, next_category)
            else:
                # Fallback if we've used all categories
                await websocket.send_text(json.dumps({
                    "type": "interviewer",
                    "content": "Great! Let me prepare your final challenge. This will take a moment...",
                    "timestamp": datetime.now().isoformat()
                }))
                await generate_next_technical_problem(session, interview_system, context, websocket, None)
        else:
            # All problems completed
            await websocket.send_text(json.dumps({
                "type": "interviewer",
                "content": "Excellent work! You've completed all three technical challenges. That concludes the technical portion of our interview. Do you have any questions about the problems or would you like to discuss your approach to any of them?",
                "timestamp": datetime.now().isoformat()
            }))
            
    except Exception as e:
        print(f"DEBUG: Error in generate_next_technical_problem_on_demand: {e}")
        import traceback
        traceback.print_exc()

async def detect_user_intent(user_message: str, session) -> str:
    """
    Use LLM to detect user intent from natural language.
    Returns: 'proceed_to_next_challenge', 'discuss_current_solution', or 'other'
    """
    try:
        # Get LLM config from session
        llm_config = session.get("llm_config")
        if not llm_config:
            return "other"
        
        intent_prompt = f"""Analyze this user message and determine their intent in a technical interview context.

User message: "{user_message}"

Context: This is during a technical interview. The user might want to:
1. Move on to the next challenge/question/problem
2. Discuss their current solution further  
3. Something else entirely

Respond with EXACTLY one of these three options:
- "proceed_to_next_challenge" - if they want to move to the next problem/challenge
- "discuss_current_solution" - if they want to talk more about their current answer
- "other" - for anything else

Examples:
- "Let's move on" → proceed_to_next_challenge
- "Next question please" → proceed_to_next_challenge  
- "g'head wid #2" → proceed_to_next_challenge
- "Can we discuss this more?" → discuss_current_solution
- "I'd like to explain my approach" → discuss_current_solution
- "How's the weather?" → other

Intent:"""

        if llm_config.provider.value == "openai":
            import openai
            client = openai.OpenAI(api_key=llm_config.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use fast model for intent detection
                messages=[
                    {"role": "user", "content": intent_prompt}
                ],
                max_tokens=50,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            intent = response.choices[0].message.content.strip().lower()
            
            # Validate response
            valid_intents = ["proceed_to_next_challenge", "discuss_current_solution", "other"]
            if intent in valid_intents:
                return intent
            else:
                print(f"DEBUG: Invalid intent response: {intent}, defaulting to 'other'")
                return "other"
                
        else:
            # Fallback for other providers or if OpenAI fails
            print(f"DEBUG: Intent detection not implemented for provider {llm_config.provider.value}")
            return "other"
            
    except Exception as e:
        print(f"DEBUG: Error in intent detection: {e}")
        return "other"


# Initialize FastAPI application
app = FastAPI(title="Mock Interview Practice", version="1.0.0")
@app.get("/api/data-setup")
async def get_data_setup(session_id: str):
    sess = active_sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    setups = sess.get("data_setups", {})
    return {
        "python_setup": setups.get("python_setup", ""),
        "sql_setup": setups.get("sql_setup", ""),
        "json_setup": setups.get("json_setup", ""),
    }

# Static files and templates configuration
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# In-memory storage for demo (would use database in production)
# This stores active interview sessions with their configuration and state
active_sessions: Dict[str, Dict] = {}


@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon to prevent 404s in browser requests."""
    return Response(status_code=204)  # No Content


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page with interview setup form.
    
    This endpoint:
    - Renders the interview setup page
    - Provides configuration options for LLM, interview type, tone, etc.
    - Handles initial interview configuration
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response with the setup page
    """
    return templates.TemplateResponse("index.html", {
        "request": request,
        "llm_providers": [provider.value for provider in LLMProvider],
        "interview_types": [itype.value for itype in InterviewType],
        "tones": [tone.value for tone in Tone],
        "difficulties": [diff.value for diff in Difficulty]
    })


@app.post("/setup")
async def setup_interview(
    llm_provider: str = Form(...),
    llm_model: str = Form(...),
    api_key: Optional[str] = Form(""),  # Make optional
    interview_type: str = Form(...),
    tone: str = Form(...),
    difficulty: str = Form(...),
    technical_track: Optional[str] = Form(None),
    tts_voice: str = Form("alloy"),  # Voice selection
    tts_enabled: Optional[str] = Form(None),  # Checkbox (None if unchecked)
    company_name: Optional[str] = Form(None),
    role_title: Optional[str] = Form(None),
    custom_instructions: Optional[str] = Form(""),  # Custom user instructions
    resume: Optional[UploadFile] = File(None),
    job_description: Optional[UploadFile] = File(None)
):
    """
    Setup and initialize a new interview session.
    
    This endpoint:
    1. Processes interview configuration from the setup form
    2. Handles document uploads (resume, job description)
    3. Creates the multi-agent interview system
    4. Initializes cost tracking and session management
    5. Redirects to the interview page
    
    Args:
        llm_provider: Selected LLM provider (openai, anthropic)
        llm_model: Selected model for the provider
        api_key: Optional API key (uses .env_local if not provided)
        interview_type: Type of interview (technical, behavioral, case_study)
        tone: Interviewer tone (professional, friendly, challenging, supportive)
        difficulty: Interview difficulty (easy, medium, hard)
        tts_voice: Text-to-speech voice selection
        tts_enabled: Whether TTS is enabled (checkbox state)
        company_name: Optional company name for context
        role_title: Optional role title for context
        custom_instructions: Custom instructions for the interviewer
        resume: Uploaded resume file
        job_description: Uploaded job description file
        
    Returns:
        Redirect response to the interview page
    """
    try:
        # Generate unique session ID
        session_id = f"session_{int(datetime.now().timestamp())}"
        
        # Process API key (use environment variable if not provided)
        if not api_key:
            api_key = os.getenv(f"{llm_provider.upper()}_API_KEY")
            if not api_key:
                raise HTTPException(status_code=400, detail=f"No API key provided for {llm_provider}")
        
        # Create LLM configuration
        llm_config = LLMConfig(
            provider=LLMProvider(llm_provider),
            api_key=api_key,
            model=llm_model
        )
        
        # Create interview configuration
        interview_config = InterviewConfig(
            interview_type=InterviewType(interview_type),
            tone=Tone(tone),
            difficulty=Difficulty(difficulty),
            technical_track=TechnicalTrack(technical_track) if (technical_track and interview_type == 'technical') else None,
        )
        
        # Process uploaded documents
        resume_text = ""
        job_description_text = ""
        
        if resume:
            resume_text = await _process_uploaded_file(resume)
        
        if job_description:
            job_description_text = await _process_uploaded_file(job_description)
        
        # Create candidate info with document context
        candidate_info = CandidateInfo(
            resume_text=resume_text,
            job_description=job_description_text,
            custom_instructions=custom_instructions,
            company_name=company_name,
            role_title=role_title,
        )
        
        # Create document context for the interview
        document_context = create_document_context(resume_text, job_description_text)
        
        # Create the multi-agent interview system
        interview_system = create_multi_agent_interview_system(
            llm_config=llm_config,
            interview_config=interview_config
        )
        
        # Initialize cost tracker
        cost_tracker = CostTracker(session_id)
        
        # Store session data
        active_sessions[session_id] = {
            "llm_config": llm_config,
            "interview_config": interview_config,
            "candidate_info": candidate_info,
            "document_context": document_context,
            "interview_system": interview_system,
            "cost_tracker": cost_tracker,
            "tts_voice": tts_voice,
            "tts_enabled": tts_enabled is not None,  # Convert checkbox to boolean
            "messages": [],
            "created_at": datetime.now()
        }
        
        # Redirect to interview page
        return RedirectResponse(url=f"/interview/{session_id}", status_code=303)
        
    except Exception as e:
        print(f"Error in setup_interview: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup interview")


async def _process_uploaded_file(file: UploadFile) -> str:
    """
    Process an uploaded file and extract its text content.
    
    This function:
    - Reads the uploaded file
    - Determines file type (PDF, DOCX, TXT)
    - Extracts text content using appropriate parser
    - Handles errors gracefully
    
    Args:
        file: Uploaded file from the form
        
    Returns:
        Extracted text content from the file
    """
    # Check if file is None or has no filename
    if not file or not file.filename:
        return ""
    
    try:
        content = await file.read()
        
        if file.filename.endswith('.pdf'):
            # Process PDF file
            from PyPDF2 import PdfReader
            import io
            pdf_reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        
        elif file.filename.endswith('.docx'):
            # Process DOCX file
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        elif file.filename.endswith('.txt'):
            # Process text file
            return content.decode('utf-8')
        
        else:
            # Unsupported file type
            raise ValueError(f"Unsupported file type: {file.filename}")
            
    except Exception as e:
        print(f"Error processing uploaded file: {e}")
        return ""


@app.get("/api/whisper-available")
async def whisper_available():
    """
    Check if OpenAI Whisper API is available.
    
    This endpoint:
    - Verifies OpenAI API key is configured
    - Returns availability status for frontend
    
    Returns:
        JSON response with availability status
    """
    api_key = os.getenv("OPENAI_API_KEY")
    return {"available": bool(api_key)}


@app.post("/api/execute")
async def execute_code(request: Request):
    """
    Execute code for technical interviews (Phase 1 sandbox):
    - Python: run in isolated subprocess with timeout
    - SQL: run in DuckDB in-memory database

    Request JSON: { language: "python"|"sql", code: str, session_id?: str }
    Response JSON: { success, stdout, stderr, duration_ms, error_type?, table? }
    """
    try:
        body = await request.json()
        language = (body.get("language") or "").lower().strip()
        code = body.get("code") or ""
        session_id = body.get("session_id")

        if not code or language not in {"python", "sql"}:
            raise HTTPException(status_code=400, detail="Provide language in {python, sql} and non-empty code")

        start_time = time.time()

        # Enforce track-language alignment (server-side guard)
        sess = active_sessions.get(session_id) if session_id else None
        track = None
        try:
            cfg = (sess or {}).get("interview_config")
            track = getattr(cfg, "technical_track", None)
            track = track.value if track else None
        except Exception:
            track = None
        if track:
            if track == "sql" and language != "sql":
                raise HTTPException(status_code=400, detail="This interview is SQL-only. Switch language to SQL.")
            if track in {"pandas", "basic_python", "algorithms"} and language != "python":
                raise HTTPException(status_code=400, detail="This interview is Python-only. Switch language to Python.")

        if language == "python":
            # For pandas/sql tracks, treat Run as JSON dataset validation only
            from textwrap import dedent
            # If the track expects data work, inject DataFrame and run code
            if track in {"pandas", "sql", None}:
                import re, json as _json
                problem = (sess or {}).get("current_problem", "")
                print(f"DEBUG: Looking for JSON in problem text: {problem[:500] if problem else 'EMPTY'}")
                mj = re.search(r"```json\n([\s\S]*?)```", problem)
                print(f"DEBUG: JSON regex match result: {bool(mj)}")
                if mj:
                    print(f"DEBUG: Found JSON block: {mj.group(1)[:200]}")
                if not mj:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return JSONResponse({
                        "success": False,
                        "stdout": "",
                        "stderr": "Data setup required but not found (no JSON dataset block).",
                        "duration_ms": duration_ms,
                        "error_type": "SetupError",
                    })
                json_text = mj.group(1)
                try:
                    obj = _json.loads(json_text)
                    # Validate and parse schema
                    df_setup_code = ""
                    if isinstance(obj, dict) and "columns" in obj:
                        columns = obj["columns"]
                        if not isinstance(columns, dict) or not columns:
                            raise ValueError("columns must be a non-empty object")
                        lengths = [len(v) for v in columns.values() if isinstance(v, list)]
                        if len(lengths) != len(columns):
                            raise ValueError("all columns must be lists")
                        if any(l != lengths[0] for l in lengths):
                            raise ValueError("column lists have unequal lengths")
                        rows = lengths[0]
                        # Create pandas DataFrame setup code
                        df_setup_code = f"import pandas as pd\ndf = pd.DataFrame({repr(columns)})"
                    elif isinstance(obj, dict) and "rows" in obj:
                        if not isinstance(obj["rows"], list):
                            raise ValueError("rows must be a list of objects")
                        rows = len(obj["rows"])
                        df_setup_code = f"import pandas as pd\ndf = pd.DataFrame({repr(obj['rows'])})"
                    else:
                        raise ValueError("expected 'columns' or 'rows' schema")
                    if rows < 30 or rows > 100:
                        raise ValueError(f"row count {rows} out of bounds (30-100)")

                    # Save for 'View data setup'
                    try:
                        if session_id and session_id in active_sessions:
                            s2 = active_sessions[session_id]
                            if not s2.get("data_setups"):
                                s2["data_setups"] = {}
                            s2["data_setups"]["json_setup"] = json_text
                    except Exception:
                        pass

                    # Now execute the user's code with DataFrame injected
                    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
                        final_code = df_setup_code + "\n\n" + code
                        print(f"DEBUG: Final code with DataFrame injection:\n{final_code}")
                        tmp.write(final_code)
                        tmp_path = tmp.name

                    try:
                        completed = subprocess.run(
                            [sys.executable, "-I", "-B", tmp_path],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        stdout = completed.stdout
                        stderr = completed.stderr
                        rc = completed.returncode
                        success = rc == 0
                        error_type = None if success else "RuntimeError"
                    except subprocess.TimeoutExpired as e:
                        stdout = e.stdout or ""
                        stderr = (e.stderr or "") + "\n[Timed out after 10s]"
                        success = False
                        error_type = "Timeout"
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass

                    duration_ms = int((time.time() - start_time) * 1000)
                    return JSONResponse({
                        "success": success,
                        "stdout": (stdout or "")[:10000],
                        "stderr": (stderr or "")[:10000],
                        "duration_ms": duration_ms,
                        "error_type": error_type,
                    })
                    
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return JSONResponse({
                        "success": False,
                        "stdout": "",
                        "stderr": f"Invalid JSON dataset: {e}",
                        "duration_ms": duration_ms,
                        "error_type": "SetupError",
                    })

            # For non-data tracks (algorithms/basic_python), execute raw python as before
            prelude = ""
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
                final_code = prelude + "\n\n" + code
                tmp.write(final_code)
                tmp_path = tmp.name

            try:
                completed = subprocess.run(
                    [sys.executable, "-I", "-B", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                stdout = completed.stdout
                stderr = completed.stderr
                rc = completed.returncode
                success = rc == 0
                error_type = None if success else "RuntimeError"
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout or ""
                stderr = (e.stderr or "") + "\n[Timed out after 10s]"
                success = False
                error_type = "Timeout"
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

            duration_ms = int((time.time() - start_time) * 1000)
            result = {
                "success": success,
                "stdout": (stdout or "")[:10000],
                "stderr": (stderr or "")[:10000],
                "duration_ms": duration_ms,
                "error_type": error_type,
            }

        else:  # SQL via DuckDB
            try:
                import duckdb  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="SQL engine not available on server")

            con = duckdb.connect(database=":memory:")
            # Seed DuckDB table 'tbl' from LLM-provided JSON dataset (preferred) or SQL setup; do NOT fallback
            seeded = False
            try:
                sess = active_sessions.get(session_id) if session_id else None
                problem = (sess or {}).get("current_problem", "")
                import re
                # Prefer JSON dataset
                mj = re.search(r"```json\n([\s\S]*?)```", problem)
                if mj:
                    import json as _json
                    import pandas as pd  # type: ignore
                    json_text = mj.group(1)
                    try:
                        obj = _json.loads(json_text)
                        if isinstance(obj, dict) and 'columns' in obj:
                            df_seed = pd.DataFrame(obj['columns'])
                        elif isinstance(obj, dict) and 'rows' in obj:
                            df_seed = pd.DataFrame(obj['rows'])
                        else:
                            raise ValueError("Invalid JSON dataset structure")
                        con.register('df_seed', df_seed)
                        con.execute("CREATE TABLE tbl AS SELECT * FROM df_seed;")
                        seeded = True
                    except Exception:
                        seeded = False
                if not seeded:
                    m = re.search(r"```sql\n([\s\S]*?)```", problem)
                    if m:
                        sql_setup = m.group(1)
                        con.execute(sql_setup)
                        seeded = True
            except Exception:
                seeded = False
            if not seeded:
                # No LLM-provided SQL setup → hard error per requirements
                try:
                    con.close()
                except Exception:
                    pass
                duration_ms = int((time.time() - start_time) * 1000)
                return JSONResponse({
                    "success": False,
                    "stdout": "",
                    "stderr": "Data setup required but not found (no JSON or SQL setup block).",
                    "duration_ms": duration_ms,
                    "error_type": "SetupError",
                    "table": None,
                })

            # Save setups to session for 'View data setup'
            try:
                sess = active_sessions.get(session_id)
                if sess is not None:
                    if not sess.get("data_setups"):
                        sess["data_setups"] = {}
                    # Store raw blocks if present
                    import re
                    py_block = ""
                    sql_block = ""
                    json_block = ""
                    mpy = re.search(r"```python\n([\s\S]*?)```", (sess.get("current_problem", "")))
                    if mpy:
                        py_block = mpy.group(1)
                    msql = re.search(r"```sql\n([\s\S]*?)```", (sess.get("current_problem", "")))
                    if msql:
                        sql_block = msql.group(1)
                    mjson = re.search(r"```json\n([\s\S]*?)```", (sess.get("current_problem", "")))
                    if mjson:
                        json_block = mjson.group(1)
                    sess["data_setups"]["python_setup"] = py_block
                    sess["data_setups"]["sql_setup"] = sql_block
                    sess["data_setups"]["json_setup"] = json_block
            except Exception:
                pass

            stdout = ""
            stderr = ""
            table = None
            success = True
            error_type = None
            try:
                # DuckDB can run multiple statements separated by ; but we will execute as a single script.
                res = con.execute(code)
                try:
                    df = res.df()
                    # Truncate rows to 200
                    if len(df) > 200:
                        df = df.head(200)
                    table = {
                        "columns": list(df.columns),
                        "rows": df.values.tolist(),
                    }
                except Exception:
                    # Non-select statements
                    stdout = "OK"
            except Exception as e:
                success = False
                error_type = "SQLError"
                stderr = str(e)
            finally:
                try:
                    con.close()
                except Exception:
                    pass

            duration_ms = int((time.time() - start_time) * 1000)
            result = {
                "success": success,
                "stdout": (stdout or "")[:10000],
                "stderr": (stderr or "")[:10000],
                "duration_ms": duration_ms,
                "error_type": error_type,
                "table": table,
            }

        # Optionally store last run in session
        if session_id and session_id in active_sessions:
            active_sessions[session_id]["last_run"] = {
                "language": language,
                "result": result,
                "at": datetime.now().isoformat(),
            }

        return JSONResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in execute_code: {e}")
        raise HTTPException(status_code=500, detail="Execution failed")

@app.post("/api/whisper-transcribe")
async def whisper_transcribe(audio_file: UploadFile = File(...), session_id: str = Form(None)):
    """
    Transcribe audio using OpenAI Whisper API.
    
    This endpoint:
    1. Receives audio file from frontend
    2. Sends to OpenAI Whisper API for transcription
    3. Returns transcribed text
    4. Tracks cost for transcription
    
    Args:
        audio_file: Audio file to transcribe
        session_id: Optional session ID for cost tracking
        
    Returns:
        JSON response with transcribed text
    """
    try:
        # Read audio file
        audio_content = await audio_file.read()
        
        # Get OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured")
        
        # Initialize OpenAI client
        
        client = OpenAI(api_key=api_key)
        
        # Transcribe audio using Whisper
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio_content, "audio/webm")
        )
        
        transcribed_text = response.text
        
        # Track cost if session exists
        if session_id and session_id in active_sessions:
            session = active_sessions[session_id]
            cost_tracker = session["cost_tracker"]
            
            # Estimate cost for Whisper transcription
            # Whisper pricing: $0.006 per minute
            duration_seconds = len(audio_content) / 16000  # Rough estimate
            cost_tracker.add_whisper_call(audio_seconds=duration_seconds)

        return {"success": True, "transcript": transcribed_text}
        
    except Exception as e:
        print(f"Error in whisper_transcribe: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")


@app.post("/api/tts-synthesize")
async def tts_synthesize(request: Request):
    """
    Synthesize speech using OpenAI TTS API.
    
    This endpoint:
    1. Receives text to synthesize
    2. Sends to OpenAI TTS API
    3. Returns audio data
    4. Tracks cost for synthesis
    
    Args:
        request: FastAPI request with JSON body containing text and session_id
        
    Returns:
        Audio response with synthesized speech
    """
    try:
        # Parse request body
        body = await request.json()
        text = body.get("text", "")
        session_id = body.get("session_id")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Get session data
        if not session_id or session_id not in active_sessions:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        session = active_sessions[session_id]
        tts_voice = session.get("tts_voice", "alloy")
        tts_enabled = session.get("tts_enabled", False)
        
        if not tts_enabled:
            return JSONResponse({"disabled": True}, status_code=200)
        
        # Get OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Synthesize speech
        response = client.audio.speech.create(
            model="tts-1",
            voice=tts_voice,
            input=text
        )
        
        # Get audio data
        audio_data = response.content
        
        # Track cost
        cost_tracker = session["cost_tracker"]
        cost_tracker.add_tts_call(characters=len(text), model="tts-1")
        
        # Return audio response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
        
    except Exception as e:
        print(f"Error in tts_synthesize: {e}")
        raise HTTPException(status_code=500, detail="TTS synthesis failed")


@app.post("/api/update-tts-setting")
async def update_tts_setting(request: Request):
    """
    Update TTS settings for a session.
    
    This endpoint allows dynamic updates to TTS settings during an interview.
    
    Args:
        request: FastAPI request with JSON body containing session_id and tts_enabled
        
    Returns:
        JSON response with updated settings
    """
    try:
        body = await request.json()
        session_id = body.get("session_id")
        tts_enabled = body.get("tts_enabled", False)
        
        if not session_id or session_id not in active_sessions:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # Update session TTS settings
        active_sessions[session_id]["tts_enabled"] = tts_enabled
        
        return {"success": True, "tts_enabled": tts_enabled}
        
    except Exception as e:
        print(f"Error in update_tts_setting: {e}")
        raise HTTPException(status_code=500, detail="Failed to update TTS settings")


@app.get("/interview/{session_id}", response_class=HTMLResponse)
async def interview_page(request: Request, session_id: str):
    """
    Interview page with real-time chat interface.
    
    This endpoint:
    - Renders the interview interface
    - Provides session data to the frontend
    - Handles WebSocket connection setup
    
    Args:
        request: FastAPI request object
        session_id: Session ID for the interview
        
    Returns:
        HTML response with the interview page
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    return templates.TemplateResponse("interview.html", {
        "request": request,
        "session_id": session_id,
        "interview_type": session["interview_config"].interview_type.value,
        "technical_track": (session["interview_config"].technical_track.value if session["interview_config"].technical_track else None),
        "tts_enabled": session.get("tts_enabled", False)
    })


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time interview communication.
    
    This endpoint:
    1. Establishes WebSocket connection
    2. Handles real-time message exchange
    3. Processes interview messages through multi-agent system
    4. Sends responses and feedback to frontend
    5. Tracks costs and session data
    
    Args:
        websocket: WebSocket connection
        session_id: Session ID for the interview
    """
    await websocket.accept()
    
    if session_id not in active_sessions:
        try:
            await websocket.close(code=4004, reason="Session not found")
        except Exception:
            # Connection might already be closed
            pass
        return
    
    session = active_sessions[session_id]
    
    try:
        # Set API key for the session
        os.environ[f"{session['llm_config'].provider.value.upper()}_API_KEY"] = session["llm_config"].api_key
        
        # Get interview system and context
        interview_system = session["interview_system"]
        context = InterviewContext(
            session_id=session_id,
            llm_config=session["llm_config"],
            interview_config=session["interview_config"],
            candidate_info=session["candidate_info"]
        )
        
        # Get cost tracker
        cost_tracker = session["cost_tracker"]
        
        # Store initial message but don't send it yet - wait for client ready signal
        session["initial_message_pending"] = True
        
        # Main message processing loop
        while True:
            try:
                # Receive message from frontend
                data = await websocket.receive_text()
                print(f"DEBUG: Received WebSocket data: {data}")
                message_data = json.loads(data)
                print(f"DEBUG: Parsed message data: {message_data}")
                
                if message_data["type"] == "client_ready":
                    # Client is ready - send initial message if pending
                    if session.get("initial_message_pending"):
                        print("DEBUG: Client ready - sending initial message")
                        initial_message = await interview_system.get_initial_message(context)
                        await websocket.send_text(json.dumps({
                            "type": "interviewer",
                            "content": initial_message.content,
                            "timestamp": datetime.now().isoformat()
                        }))
                        session["initial_message_pending"] = False
                        
                        # Technical interviews will generate problems fresh when requested

                elif message_data["type"] == "user_message":
                    print(f"DEBUG: Received user message: {message_data['content']}")
                    print(f"DEBUG: About to process message through interview system")
                    
                    # Use LLM to detect user intent instead of primitive keyword matching
                    user_intent = await detect_user_intent(message_data["content"], session)
                    print(f"DEBUG: Detected user intent: {user_intent}")
                    
                    if user_intent == "proceed_to_next_challenge":
                        interview_type = session.get("interview_config", {})
                        if hasattr(interview_type, 'interview_type'):
                            interview_type_value = interview_type.interview_type.value
                        else:
                            interview_type_value = "unknown"
                        
                        if interview_type_value == "technical":
                            print(f"DEBUG: User wants to proceed to next challenge (LLM detected)")
                            session["awaiting_next_action"] = False
                            await generate_next_technical_problem_on_demand(session, interview_system, context, websocket)
                            continue  # Skip normal message processing
                    elif user_intent == "discuss_current_solution":
                        print(f"DEBUG: User wants to discuss current solution (LLM detected)")
                        session["awaiting_next_action"] = False
                        # Continue with normal message processing for discussion
                    else:
                        # For other intents, clear awaiting flag if set and continue normally
                        if session.get("awaiting_next_action"):
                            session["awaiting_next_action"] = False
                    
                    # For technical interviews, assign a skill category for the first challenge
                    interview_type = session.get("interview_config", {})
                    if hasattr(interview_type, 'interview_type') and interview_type.interview_type.value == "technical":
                        # Initialize technical problems tracking if first time
                        if "technical_problems" not in session:
                            session["technical_problems"] = {
                                "completed": 0,
                                "used_categories": [],
                                "total_target": 3
                            }
                        
                        # If this is the first challenge and no categories used yet, assign one
                        if (session["technical_problems"]["completed"] == 0 and 
                            len(session["technical_problems"]["used_categories"]) == 0):
                            import random
                            first_category = random.choice(TECHNICAL_SKILL_CATEGORIES)
                            session["technical_problems"]["used_categories"].append(first_category["name"])
                            print(f"DEBUG: Assigned first challenge category: {first_category['name']}")
                            
                            # Add skill hint to context for the LLM
                            context.session_metadata = context.session_metadata or {}
                            context.session_metadata['skill_category_hint'] = f"{first_category['description']} - {first_category['focus']}"
                    
                    # Process user message through multi-agent system - always fresh generation
                    print(f"DEBUG: Calling interview_system.process_message with fresh LLM generation")
                    combined_response = await interview_system.process_message(
                        message_data["content"],
                        context
                    )
                    print(f"DEBUG: Combined response: {combined_response}")
                    
                    # Process the response
                    try:
                        # Send interviewer response, but if this is a coding challenge, place the
                        # full prompt into the code editor and keep chat concise
                        primary = combined_response["primary_response"]
                        # Pull agent metadata (may be nested under primary_agent_metadata)
                        meta_raw = getattr(primary, "metadata", {}) or {}
                        agent_meta = meta_raw.get("primary_agent_metadata", {}) if isinstance(meta_raw, dict) else {}
                        # If not present, also check the top level returned dict's metadata
                        if not agent_meta:
                            agent_meta = (combined_response.get("primary_response").metadata or {}).get("primary_agent_metadata", {}) if hasattr(combined_response.get("primary_response"), "metadata") else {}

                        question_type = agent_meta.get("question_type") or meta_raw.get("question_type")

                        if question_type == "coding_challenge":
                            # Send coding prompt to editor
                            print(f"DEBUG: agent_meta keys: {list(agent_meta.keys()) if agent_meta else 'None'}")
                            print(f"DEBUG: meta_raw keys: {list(meta_raw.keys()) if meta_raw else 'None'}")
                            print(f"DEBUG: editor_prompt in agent_meta: {agent_meta.get('editor_prompt', 'NOT_FOUND')[:200] if agent_meta else 'NO_AGENT_META'}")
                            editor_text = agent_meta.get("editor_prompt") or meta_raw.get("editor_prompt") or primary.content
                            # Try to extract and cache current problem in session
                            session["current_problem"] = editor_text
                            print(f"DEBUG: Setting current_problem in session: {editor_text[:300]}")
                            
                            # Increment completed count for first challenge when it's sent to editor
                            if session["technical_problems"]["completed"] == 0:
                                session["technical_problems"]["completed"] += 1
                                print(f"DEBUG: Incremented completed count for first challenge: {session['technical_problems']['completed']}")
                            
                            await websocket.send_text(json.dumps({
                                "type": "coding_prompt",
                                "content": editor_text,
                                "question_number": agent_meta.get("question_number", 1) if agent_meta else 1,
                                "timestamp": datetime.now().isoformat()
                            }))

                            # Brief chat message
                            await websocket.send_text(json.dumps({
                                "type": "interviewer",
                                "content": "Problem added to the editor. Use Run Code and the hint buttons whenever you like.",
                                "timestamp": datetime.now().isoformat()
                            }))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "interviewer",
                                "content": primary.content,
                                "timestamp": datetime.now().isoformat()
                            }))
                        print(f"DEBUG: Sent interviewer response: {combined_response['primary_response'].content}")
                        
                        # Send cost update
                        cost_summary = session["cost_tracker"].get_summary()
                        await websocket.send_text(json.dumps({
                            "type": "cost_update",
                            "content": cost_summary,
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    except Exception as e:
                        print(f"DEBUG: Error processing message: {e}")
                        import traceback
                        traceback.print_exc()
                        # Send error response
                        await websocket.send_text(json.dumps({
                            "type": "interviewer",
                            "content": "I apologize, but I encountered an issue processing your message. Let's continue with the interview.",
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    # Track LLM text cost
                    try:
                        provider = session["llm_config"].provider.value
                        model = session["llm_config"].model
                        user_tokens = estimate_tokens_detailed(message_data["content"])
                        assistant_tokens = estimate_tokens_detailed(combined_response["primary_response"].content)
                        cost_tracker.add_text_call(provider, model, user_tokens, assistant_tokens)
                    except Exception as e:
                        print(f"Token cost tracking failed: {e}")
                    
                    # Store message in session
                    session["messages"].append({
                        "type": "user",
                        "content": message_data["content"],
                        "timestamp": datetime.now().isoformat()
                    })
                    
                elif message_data["type"] == "code_run":
                    # Store last code run (silent by default; no auto-interviewer reply)
                    code = message_data.get("code", "")
                    language = message_data.get("language", "")
                    result = message_data.get("result", {})

                    session["last_code"] = {"language": language, "code": code}
                    session["last_result"] = result
                    # Optionally, we could emit a lightweight ack for UI debugging
                    # await websocket.send_text(json.dumps({"type": "code_ack", "timestamp": datetime.now().isoformat()}))

                elif message_data["type"] == "evaluate_solution":
                    # Evaluate the solution and provide detailed feedback
                    language = message_data.get("language", "python")
                    code = message_data.get("code", "")
                    try:
                        print(f"DEBUG: Evaluating solution: {code[:100]}...")
                        
                        # Create evaluation prompt with explicit format examples
                        evaluation_prompt = (
                            f"Review this {language} code and provide feedback as a conversational interviewer:\n\n"
                            f"```{language}\n{code}\n```\n\n"
                            "⚠️ CRITICAL FORMAT REQUIREMENTS:\n"
                            "- Write ONLY in natural paragraphs like normal conversation\n"
                            "- NEVER use JSON, dictionaries, or structured data formats\n"
                            "- NO curly braces {}, square brackets [], or key:value pairs\n"
                            "- Write like you're speaking to a candidate face-to-face\n\n"
                            "Example GOOD response format:\n"
                            "Your code looks solid and correctly solves the problem! Here are a few suggestions to make it even better:\n\n"
                            "The logic is sound, but you could improve readability by adding comments explaining the grouping step. Also, consider adding error handling for edge cases where the category might not exist.\n\n"
                            "For performance, the current approach is efficient for this dataset size. If working with larger datasets, you might consider using vectorized operations.\n\n"
                            "Example BAD response (DO NOT DO THIS):\n"
                            '{{ "response": "feedback here", "areas": ["item1", "item2"] }}\n\n'
                            "Focus only on areas for improvement. If the code is good, say so and suggest minor enhancements.\n\n"
                            "Write your feedback as natural conversation:"
                        )
                        
                        # Call technical interviewer directly to avoid JSON formatting from routing system
                        from interviewer.agents.technical import TechnicalInterviewerAgent
                        tech_agent = TechnicalInterviewerAgent(
                            llm_config=session["llm_config"]
                        )
                        
                        # Call the agent directly with our evaluation prompt
                        evaluation_response = await tech_agent._call_llm(
                            evaluation_prompt, 
                            max_tokens=800, 
                            force_json=False
                        )
                        
                        # Send evaluation as interviewer response (direct string from agent)
                        await websocket.send_text(json.dumps({
                            "type": "interviewer",
                            "content": evaluation_response,
                            "timestamp": datetime.now().isoformat()
                        }))
                        print(f"DEBUG: Sent evaluation response")
                        
                        # Send follow-up prompt for user to choose next action
                        await send_feedback_followup_prompt(session, websocket)
                        
                    except Exception as e:
                        print(f"DEBUG: Error in solution evaluation: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "interviewer", 
                            "content": "I apologize, but I had trouble evaluating your solution. Could you try submitting again?",
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                elif message_data["type"] == "hint_request":
                    focus = message_data.get("focus", "problem")
                    language = message_data.get("language", "")
                    code = message_data.get("code", "")
                    try:
                        # Build a hint prompt
                        prompt = [
                            f"The candidate requested a hint focused on: {focus}.",
                            "Provide a brief, progressive hint (do not reveal full solution).",
                        ]
                        if code:
                            prompt.append(f"Their current {language} code (truncated):\n{code.splitlines()[:30]}")
                        guidance_input = "\n\n".join(str(p) for p in prompt)
                        combined_response = await interview_system.process_message(guidance_input, context)
                        await websocket.send_text(json.dumps({
                            "type": "interviewer",
                            "content": combined_response["primary_response"].content,
                            "timestamp": datetime.now().isoformat()
                        }))
                    except Exception as e:
                        print(f"hint_request failed: {e}")

                elif message_data["type"] == "tts_request":
                    # Handle TTS synthesis request
                    if session.get("tts_enabled", False):
                        # This would trigger TTS synthesis
                        # For now, just acknowledge the request
                        await websocket.send_text(json.dumps({
                            "type": "tts_ready",
                            "content": "TTS synthesis ready",
                            "timestamp": datetime.now().isoformat()
                        }))
                else:
                    print(f"DEBUG: Message type '{message_data['type']}' not handled")
                    
            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"DEBUG: Unexpected WebSocket error: {e}")
                import traceback
                traceback.print_exc()
                break
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"Error in websocket_endpoint: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "An error occurred during the interview",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception:
            # Connection might already be closed
            pass


@app.get("/api/sessions")
async def list_sessions():
    """
    List all active interview sessions.
    
    This endpoint provides session information for debugging and monitoring.
    
    Returns:
        JSON response with session list
    """
    sessions = []
    for session_id, session_data in active_sessions.items():
        sessions.append({
            "session_id": session_id,
            "interview_type": session_data["interview_config"].interview_type.value,
            "created_at": session_data["created_at"].isoformat(),
            "message_count": len(session_data["messages"])
        })
    
    return {"sessions": sessions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, reload=True)