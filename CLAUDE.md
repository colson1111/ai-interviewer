# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
poetry run python web_app.py
# Open http://localhost:3000 (use localhost, not 0.0.0.0, for microphone access)

# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_interview_agent.py

# Run with coverage
poetry run pytest --cov=interviewer

# Live LLM tests (make actual API calls, consume credits)
RUN_LIVE_LLM_TESTS=1 poetry run pytest -m live_llm

# Format code
poetry run black .
poetry run isort .

# Lint
poetry run flake8 interviewer/ tests/
```

## Environment Setup

Copy `.env_example` to `.env_local` and add API keys. The app loads `.env_local` with `override=True`, so it takes precedence over shell env vars.

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

## Architecture

### Request Flow

1. User submits the setup form (`POST /setup`) — creates a session, initializes `MultiAgentInterviewSystem`, stores everything in the in-memory `active_sessions` dict in `web_app.py`
2. Browser connects via WebSocket (`/ws/{session_id}`) — waits for `client_ready`, then triggers the initial interview message
3. Each user message is processed by `MultiAgentInterviewSystem.process_message()`, which routes through the `OrchestratorAgent` and delegates to `InterviewAgent`
4. When the interview ends, the frontend calls `POST /api/evaluate-session/{session_id}` — this creates an `EvaluationAgent` and generates a report card

### Multi-Agent System (`interviewer/multi_agent_system.py`)

`MultiAgentInterviewSystem` owns and coordinates three agents registered in `AgentRegistry`:
- **`InterviewAgent`** — primary conversation agent using pydantic-ai; manages `pydantic_message_history` for multi-turn context
- **`SearchAgent`** — real-time information lookup
- **`SummaryAgent`** — session summaries
- **`OrchestratorAgent`** — coordinates routing and combines responses
- **`EvaluationAgent`** — instantiated on demand at interview end; generates the structured `InterviewReport`

All agents extend `BaseInterviewAgent` (`interviewer/agents/base.py`), which requires implementing `can_handle()` and `process()`.

### Shared State: `InterviewContext`

`InterviewContext` (`interviewer/core/context.py`) is the central object passed to every agent. It holds:
- `llm_config`, `interview_config`, `candidate_info` — set once at session creation
- `conversation_history` — list of `ConversationTurn` objects appended each turn
- `agent_states` — per-agent persistent state dict
- `session_metadata` — used to pass flags like `wrap_up_triggered`

### pydantic-ai Integration

`InterviewAgent` and `EvaluationAgent` use pydantic-ai's `Agent` class. **Critical**: pydantic-ai reads API keys from environment variables (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`). The key must be explicitly set via `os.environ` before instantiating the agent — this is done in `web_app.py`'s `/setup` handler and again at WebSocket connection time.

The interview agent uses `deps_type=InterviewDeps` (a dataclass) to pass dynamic context, and a dynamic system prompt via `interview_system_prompt()`. Multi-turn history is maintained by storing `result.all_messages()` back into `self.pydantic_message_history` and passing it to the next `agent.run()` call.

### Initial Interview Trigger

The first LLM call is triggered by sending a system message with content `"start_interview"`. `InterviewAgent.process()` detects this, calls `_build_initial_context(deps)` to assemble a rich context string (JD, resume, interview type instructions), and sets `self.context_initialized = True` to prevent re-triggering.

### Prompts (`interviewer/prompts.py`)

All prompts are centralized here. `build_system_prompt(interview_type, tone, difficulty)` combines:
- `BASE_PROMPT` — core formatting rules (no markdown, spoken-language style)
- `TONE_MODIFIERS[tone]`
- `INTERVIEW_TYPE_GUIDANCE[interview_type]`
- `DIFFICULTY_MODIFIERS[difficulty]`

The `CUSTOM` interview type uses `CUSTOM_INTERVIEW_EXPANSION_PROMPT` plus `expand_custom_interview_plan()` (`interviewer/interview_plan_expander.py`) to expand user-provided interviewer descriptions into a detailed plan via an LLM call at setup time.

### Interview Types

| Type | Behavior |
|------|----------|
| `behavioral` | Past experience questions; JD is primary lens when provided; resume is secondary |
| `case_study` | Hypothetical problem; brief opening, details emerge through dialogue; no resume references |
| `custom` | LLM expands user instructions into a plan; that plan drives the entire interview |

### Recording Time Limit

`MAX_RECORDING_MINUTES = 20` (`interviewer/config.py`). When reached, `wrap_up_triggered=True` is set in `context.session_metadata`, which injects a wrap-up instruction into the interview agent's dynamic prompt. This is a soft signal — the agent transitions naturally rather than cutting off abruptly.

### Cost Tracking

`CostTracker` (`interviewer/cost_tracker.py`) tracks text tokens (LLM calls), Whisper audio minutes, and TTS characters. Cost summaries are sent to the frontend as `cost_update` WebSocket messages after each turn.
