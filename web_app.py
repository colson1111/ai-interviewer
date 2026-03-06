"""
AI-powered mock interview application with multi-agent system.

This application provides:
- Real-time interview conversations with AI agents
- Multi-agent coordination (interview, search, summary, evaluation)
- WebSocket-based communication
- Cost tracking and monitoring
- File upload and processing
- TTS and STT capabilities
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# Load environment variables from .env_local
# override=True ensures .env_local values take precedence over shell environment
load_dotenv(".env_local", override=True)

from interviewer.config import (
    Difficulty,
    InterviewConfig,
    InterviewType,
    LLMConfig,
    LLMProvider,
    MAX_RECORDING_MINUTES,
    Tone,
)
from interviewer.core import CandidateInfo, InterviewContext
from interviewer.cost_tracker import CostTracker, estimate_tokens_detailed
from interviewer.document_parser import create_document_context
from interviewer.interview_plan_expander import expand_custom_interview_plan
from interviewer.multi_agent_system import create_multi_agent_interview_system


async def detect_user_intent(user_message: str, session) -> str:
    """
    Use LLM to detect user intent from natural language.
    Returns: 'other' (as simplified for behavioral/case study only)
    """
    # Intent detection logic can be simplified or enhanced for behavioral interviews later
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
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "llm_providers": [provider.value for provider in LLMProvider],
            "interview_types": [itype.value for itype in InterviewType],
            "tones": [tone.value for tone in Tone],
            "difficulties": [diff.value for diff in Difficulty],
        },
    )


@app.post("/setup")
async def setup_interview(
    llm_provider: str = Form(...),
    llm_model: str = Form(...),
    api_key: Optional[str] = Form(""),  # Make optional
    interview_type: str = Form(...),
    tone: str = Form(...),
    difficulty: str = Form(...),
    tts_voice: str = Form("yYcS13q9YIRwVXmvXnBq"),  # ElevenLabs voice_id (default: Craig)
    tts_enabled: Optional[str] = Form(None),  # Checkbox (None if unchecked)
    company_name: Optional[str] = Form(None),
    role_title: Optional[str] = Form(None),
    custom_instructions: Optional[str] = Form(""),  # Custom user instructions
    resume: Optional[UploadFile] = File(None),
    job_description: Optional[UploadFile] = File(None),
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

        # Initialize cost tracker early (used for expansion when custom type)
        cost_tracker = CostTracker(session_id)

        # Process API key (use environment variable if not provided)
        if not api_key:
            api_key_env_var = f"{llm_provider.upper()}_API_KEY"
            api_key = os.getenv(api_key_env_var)
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail=f"No API key provided for {llm_provider}. Checked env var: {api_key_env_var}",
                )

        # Create LLM configuration
        llm_config = LLMConfig(
            provider=LLMProvider(llm_provider), api_key=api_key, model=llm_model
        )

        # CRITICAL: Set the environment variable BEFORE creating the agent system
        # pydantic-ai's AnthropicModel reads ANTHROPIC_API_KEY from the environment
        os.environ["ANTHROPIC_API_KEY"] = api_key

        # Create interview configuration
        interview_config = InterviewConfig(
            interview_type=InterviewType(interview_type),
            tone=Tone(tone),
            difficulty=Difficulty(difficulty),
        )

        # Validate custom instructions when interview type is custom
        if interview_type == "custom":
            instructions = (custom_instructions or "").strip()
            if not instructions:
                raise HTTPException(
                    status_code=400,
                    detail="Custom instructions are required for Custom interviews.",
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
            custom_instructions=custom_instructions or "",
            company_name=company_name,
            role_title=role_title,
        )

        # Expand custom instructions into fuller plan when interview type is custom
        if interview_type == "custom" and (custom_instructions or "").strip():
            expanded_plan = await expand_custom_interview_plan(
                custom_instructions=(custom_instructions or "").strip(),
                resume_text=resume_text,
                job_description=job_description_text,
                company_name=company_name,
                role_title=role_title,
                llm_config=llm_config,
                cost_tracker=cost_tracker,
            )
            candidate_info.custom_interview_plan = expanded_plan

        # Create document context for the interview
        document_context = create_document_context(resume_text, job_description_text)

        # Create the multi-agent interview system
        interview_system = create_multi_agent_interview_system(
            llm_config=llm_config, interview_config=interview_config
        )

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
            "created_at": datetime.now(),
        }

        # Redirect to interview page
        return RedirectResponse(url=f"/interview/{session_id}", status_code=303)

    except Exception as e:
        print(f"Error in setup_interview: {e}")
        import traceback

        traceback.print_exc()
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

        if file.filename.endswith(".pdf"):
            # Process PDF file
            import io

            from PyPDF2 import PdfReader

            pdf_reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text

        elif file.filename.endswith(".docx"):
            # Process DOCX file
            import io

            from docx import Document

            doc = Document(io.BytesIO(content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text

        elif file.filename.endswith(".txt"):
            # Process text file
            return content.decode("utf-8")

        else:
            # Unsupported file type
            raise ValueError(f"Unsupported file type: {file.filename}")

    except Exception as e:
        print(f"Error processing uploaded file: {e}")
        return ""


@app.get("/api/elevenlabs-available")
async def elevenlabs_available():
    """Check if ElevenLabs API is available (used for both STT and TTS)."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    return {"available": bool(api_key)}


@app.post("/api/elevenlabs-transcribe")
async def elevenlabs_transcribe(
    audio_file: UploadFile = File(...), session_id: str = Form(None)
):
    """Transcribe audio using ElevenLabs Scribe."""
    try:
        audio_content = await audio_file.read()

        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")

        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)
        result = client.speech_to_text.convert(
            file=("recording.webm", audio_content, "audio/webm"),
            model_id="scribe_v1",
            language_code="en",
            tag_audio_events=False,
        )
        transcript = result.text

        if session_id and session_id in active_sessions:
            duration_seconds = len(audio_content) / 16000  # rough estimate
            active_sessions[session_id]["cost_tracker"].add_elevenlabs_stt_call(
                audio_seconds=duration_seconds
            )

        return {"success": True, "transcript": transcript}

    except Exception as e:
        print(f"Error in elevenlabs_transcribe: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")


@app.post("/api/tts-synthesize")
async def tts_synthesize(request: Request):
    """Synthesize speech using ElevenLabs TTS."""
    try:
        body = await request.json()
        text = body.get("text", "")
        session_id = body.get("session_id")

        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        if not session_id or session_id not in active_sessions:
            raise HTTPException(status_code=400, detail="Invalid session ID")

        session = active_sessions[session_id]
        # tts_voice stores an ElevenLabs voice_id
        tts_voice = session.get("tts_voice", "yYcS13q9YIRwVXmvXnBq")  # Craig
        tts_enabled = session.get("tts_enabled", False)

        if not tts_enabled:
            return JSONResponse({"disabled": True}, status_code=200)

        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")

        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)
        audio_generator = client.text_to_speech.convert(
            voice_id=tts_voice,
            text=text,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128",
        )
        audio_data = b"".join(audio_generator)

        session["cost_tracker"].add_elevenlabs_call(characters=len(text))

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"},
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
            # Session expired or invalid - this is expected after server reload
            return {"success": False, "error": "Session expired", "tts_enabled": False}

        # Update session TTS settings
        active_sessions[session_id]["tts_enabled"] = tts_enabled

        return {"success": True, "tts_enabled": tts_enabled}

    except HTTPException:
        raise  # Let HTTPExceptions propagate
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

    # Check if we have technical track info (removed but check safely)
    technical_track = None

    return templates.TemplateResponse(
        "interview.html",
        {
            "request": request,
            "session_id": session_id,
            "interview_type": session["interview_config"].interview_type.value,
            "technical_track": technical_track,
            "tts_enabled": session.get("tts_enabled", False),
        },
    )


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
        os.environ["ANTHROPIC_API_KEY"] = session["llm_config"].api_key

        # Get interview system and context
        interview_system = session["interview_system"]
        context = InterviewContext(
            session_id=session_id,
            llm_config=session["llm_config"],
            interview_config=session["interview_config"],
            candidate_info=session["candidate_info"],
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
                message_data = json.loads(data)

                if message_data["type"] == "client_ready":
                    # Client is ready - send initial message if pending
                    if session.get("initial_message_pending"):
                        initial_message = await interview_system.get_initial_message(
                            context
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "interviewer",
                                    "content": initial_message.content,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )
                        session["initial_message_pending"] = False

                elif message_data["type"] == "user_message":
                    # Soft trigger: when 20 min reached, signal AI to wrap up (no hard stop)
                    # Use frontend recording time (mic-on time); fallback to Whisper minutes if no frontend data
                    frontend_seconds = message_data.get("recording_seconds", 0) or 0
                    session["recording_seconds"] = max(
                        session.get("recording_seconds", 0), frontend_seconds
                    )
                    whisper_minutes = cost_tracker.get_token_stats().get(
                        "audio_minutes", 0
                    )
                    # Prefer frontend (tracks all mic time); Whisper covers refine-only usage
                    audio_minutes = max(
                        session["recording_seconds"] / 60,
                        whisper_minutes,
                    )
                    first_trigger = False
                    if audio_minutes >= MAX_RECORDING_MINUTES:
                        if not session.get("wrap_up_triggered"):
                            session["wrap_up_triggered"] = True
                            first_trigger = True

                    # Pass wrap-up hint to agents so they transition naturally
                    context.session_metadata["wrap_up_triggered"] = session.get(
                        "wrap_up_triggered", False
                    )

                    # Process user message through multi-agent system
                    combined_response = await interview_system.process_message(
                        message_data["content"], context
                    )

                    # On first wrap-up trigger, notify frontend (informational only)
                    if first_trigger:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "wrap_up_triggered",
                                    "content": {"audio_minutes": audio_minutes},
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

                    # Process the response
                    try:
                        primary = combined_response["primary_response"]

                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "interviewer",
                                    "content": primary.content,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

                        # Send cost update
                        cost_summary = session["cost_tracker"].get_summary()
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "cost_update",
                                    "content": cost_summary,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

                        # Store interviewer response in session history
                        session["messages"].append(
                            {
                                "type": "interviewer",
                                "content": primary.content,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                    except Exception as e:
                        print(f"Error processing message: {e}")
                        import traceback

                        traceback.print_exc()
                        # Send error response
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "interviewer",
                                    "content": "I apologize, but I encountered an issue processing your message. Let's continue with the interview.",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

                    # Track LLM text cost
                    try:
                        provider = session["llm_config"].provider.value
                        model = session["llm_config"].model
                        user_tokens = estimate_tokens_detailed(message_data["content"])
                        assistant_tokens = estimate_tokens_detailed(
                            combined_response["primary_response"].content
                        )
                        cost_tracker.add_text_call(
                            provider, model, user_tokens, assistant_tokens
                        )
                    except Exception as e:
                        print(f"Token cost tracking failed: {e}")

                    # Store message in session
                    session["messages"].append(
                        {
                            "type": "user",
                            "content": message_data["content"],
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                elif message_data["type"] == "tts_request":
                    # Handle TTS synthesis request
                    if session.get("tts_enabled", False):
                        # This would trigger TTS synthesis
                        # For now, just acknowledge the request
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "tts_ready",
                                    "content": "TTS synthesis ready",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )
                else:
                    # Unknown message type
                    pass

            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"Unexpected WebSocket error: {e}")
                import traceback

                traceback.print_exc()
                break

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"Error in websocket_endpoint: {e}")
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "content": "An error occurred during the interview",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
        except Exception:
            # Connection might already be closed
            pass


@app.post("/api/evaluate-session/{session_id}")
async def evaluate_session(session_id: str):
    """
    Generate a post-interview evaluation report.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    # Initialize evaluation agent
    from interviewer.agents.evaluation import EvaluationAgent

    agent = EvaluationAgent(session["llm_config"])

    # Reconstruct context
    context = InterviewContext(
        session_id=session_id,
        llm_config=session["llm_config"],
        interview_config=session["interview_config"],
        candidate_info=session["candidate_info"],
    )

    # Populate history from session storage
    # We need to ensure we have a good history. If the session was just created, it might be empty.
    # We rely on session["messages"] being populated during the WS chat.
    for msg in session.get("messages", []):
        context.add_turn(
            {
                "speaker": msg["type"],  # 'user' or 'interviewer'
                "content": msg["content"],
                "timestamp": time.time(),  # simplified
                "message_type": "message",
            }
        )

    try:
        report = await agent.generate_report(context)
        return report.model_dump()
    except Exception as e:
        print(f"Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        sessions.append(
            {
                "session_id": session_id,
                "interview_type": session_data["interview_config"].interview_type.value,
                "created_at": session_data["created_at"].isoformat(),
                "message_count": len(session_data["messages"]),
            }
        )

    return {"sessions": sessions}


@app.on_event("startup")
async def startup_event():
    """Print helpful startup message with clickable localhost URL."""
    print("\n" + "=" * 50)
    print("🎤 AI Interviewer is running!")
    print("=" * 50)
    print(f"\n👉 Open in browser: http://localhost:3000\n")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="0.0.0.0", port=3000, reload=True)
