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
from typing import Dict, Any, Optional
from pathlib import Path
from openai import OpenAI
        
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from interviewer.config import LLMConfig, InterviewConfig, LLMProvider, InterviewType, Tone, Difficulty
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


# Initialize FastAPI application
app = FastAPI(title="Mock Interview Practice", version="1.0.0")

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
            difficulty=Difficulty(difficulty)
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
            custom_instructions=custom_instructions
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
        
        # Send initial message
        initial_message = await interview_system.get_initial_message(context)
        await websocket.send_text(json.dumps({
            "type": "interviewer",
            "content": initial_message.content,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Main message processing loop
        while True:
            try:
                # Receive message from frontend
                data = await websocket.receive_text()
                print(f"DEBUG: Received WebSocket data: {data}")
                message_data = json.loads(data)
                print(f"DEBUG: Parsed message data: {message_data}")
                
                if message_data["type"] == "user_message":
                    print(f"DEBUG: Received user message: {message_data['content']}")
                    print(f"DEBUG: About to process message through interview system")
                    
                    # Process user message through multi-agent system
                    try:
                        print(f"DEBUG: Calling interview_system.process_message")
                        combined_response = await interview_system.process_message(
                            message_data["content"],
                            context
                        )
                        print(f"DEBUG: Combined response: {combined_response}")
                        
                        # Send interviewer response
                        await websocket.send_text(json.dumps({
                            "type": "interviewer",
                            "content": combined_response["primary_response"].content,
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