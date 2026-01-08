# 🎤 AI Mock Interview Coach

Practice behavioral and case study interviews with an AI interviewer that adapts to your resume, job description, and target company. Get a comprehensive Report Card when you're done.

## ✨ Features

- **Realistic Interview Simulation** - Natural, human-like conversation that reacts to your responses
- **Context-Aware Questions** - Tailored to your resume, job description, and target company/role
- **Voice Interaction** - Speak your answers with speech-to-text, hear questions with text-to-speech
- **Post-Interview Report Card** - Comprehensive evaluation with scores, strengths, and improvement areas
- **Multiple LLM Support** - Choose between OpenAI (GPT-4o) or Anthropic (Claude Sonnet 4)
- **Configurable Difficulty & Tone** - From friendly practice to rigorous preparation

## 🎯 Interview Types

| Type | Description |
|------|-------------|
| **Behavioral** | Past experiences, leadership, teamwork, STAR method responses |
| **Case Study** | Hypothetical business problems, strategic thinking, problem-solving |

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- OpenAI API key and/or Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/colson1111/ai-interviewer.git
cd ai-interviewer

# Install dependencies
poetry install

# Configure API keys
cp .env_example .env_local
# Edit .env_local with your API keys
```

### Run the Application

```bash
poetry run python web_app.py
```

Open **http://localhost:3000** in your browser.

> 💡 **Tip**: Use localhost (not 0.0.0.0) for microphone access in browsers.

## 🎙️ Usage

1. **Configure Your Interview**
   - Select LLM provider and model
   - Choose interview type (Behavioral or Case Study)
   - Set tone (Friendly → Challenging) and difficulty
   - Optionally add company name, role title, and custom instructions

2. **Upload Context (Optional)**
   - Resume (PDF, DOCX, TXT)
   - Job Description

3. **Start Interviewing**
   - Click the microphone to speak, or type your responses
   - The interviewer will ask follow-up questions naturally
   - End the interview when ready to receive your Report Card

4. **Review Your Report Card**
   - Overall score (1-10)
   - Strengths and areas for improvement
   - Communication and cultural fit assessments

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │◄──►│   FastAPI App   │◄──►│  Multi-Agent    │
│   (HTML/JS)     │    │   (WebSocket)   │    │    System       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LLM Provider  │
                       │ (OpenAI/Claude) │
                       └─────────────────┘
```

### Multi-Agent System

| Agent | Role |
|-------|------|
| **Interview** | Primary conversation, question generation (pydantic-ai) |
| **Search** | Real-time information lookup |
| **Feedback** | Response analysis |
| **Evaluation** | Post-interview Report Card generation |
| **Summary** | Session summaries |
| **Orchestrator** | Agent coordination and routing |

## 📁 Project Structure

```
ai-interviewer/
├── web_app.py                 # FastAPI application
├── interviewer/
│   ├── agents/                # Agent implementations
│   │   ├── base.py           # Base agent class
│   │   ├── interview.py      # Main interview agent (pydantic-ai)
│   │   ├── evaluation.py     # Report Card generation
│   │   ├── feedback.py       # Response analysis
│   │   ├── search.py         # Information lookup
│   │   ├── summary.py        # Session summaries
│   │   └── orchestrator.py   # Agent coordination
│   ├── core/                  # Data structures
│   │   ├── context.py        # Interview context management
│   │   ├── messaging.py      # Message/response models
│   │   └── routing.py        # Agent routing
│   ├── prompts.py            # 📝 All prompts (easy to customize!)
│   ├── config.py             # LLM and interview configuration
│   └── multi_agent_system.py # System orchestration
├── templates/                 # Jinja2 HTML templates
├── static/                    # CSS and JavaScript
├── tests/                     # Test suite
└── .github/workflows/         # CI/CD
```

## ⚙️ Configuration

### Supported Models

**OpenAI:**
- `gpt-4o` (default)
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`

**Anthropic:**
- `claude-sonnet-4-20250514` (default)
- `claude-opus-4-20250514`
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`

### Customizing Prompts

All prompts are centralized in `interviewer/prompts.py` for easy customization:

```python
# interviewer/prompts.py

BASE_PROMPT = """You are a professional interviewer..."""

TONE_MODIFIERS = {
    "friendly": "Be warm and encouraging...",
    "professional": "Maintain a balanced tone...",
    # ...
}

DIFFICULTY_MODIFIERS = {
    "easy": "Ask straightforward questions...",
    "medium": "Include some challenging follow-ups...",
    # ...
}
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=interviewer

# Run specific test file
poetry run pytest tests/test_interview_agent.py
```

### Code Formatting

```bash
# Format code
poetry run black .
poetry run isort .

# Check linting
poetry run flake8 interviewer/ tests/
```

### CI/CD

GitHub Actions automatically runs on push/PR to `main`:
- ✅ Tests (Python 3.10, 3.11, 3.12)
- ✅ Linting (flake8)
- ✅ Formatting check (black)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com) - GPT models, Whisper, TTS
- [Anthropic](https://anthropic.com) - Claude models
- [pydantic-ai](https://github.com/pydantic/pydantic-ai) - AI agent framework
- [FastAPI](https://fastapi.tiangolo.com) - Web framework

---

**Happy practicing! 🎉**
