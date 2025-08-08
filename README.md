# 🤖 AI-Powered Mock Interview Practice

A comprehensive web application for conducting AI-powered mock interviews with real-time feedback, voice interaction, and multi-agent coordination.

## 🚀 Features

### **Multi-Agent Interview System**
- **Interview Agent**: Primary conversation and question generation
- **Search Agent**: Real-time information lookup and fact-checking
- **Feedback Agent**: Live response analysis and performance scoring
- **Summary Agent**: Session summaries and final assessments
- **Orchestrator Agent**: Intelligent agent coordination and routing

### **Interview Types**
- **Technical Interviews**: Coding, SQL, algorithms, data science concepts
- **Behavioral Interviews**: Past experiences, project walkthroughs, STAR method
- **Case Study Interviews**: Hypothetical problem-solving scenarios

### **Real-Time Features**
- **Live Feedback**: Instant response analysis with strengths and improvements
- **Voice Interaction**: Speech-to-text and text-to-speech capabilities
- **Cost Tracking**: Real-time API usage monitoring and cost estimation
- **Document Integration**: Resume and job description upload and analysis

### **Advanced Capabilities**
- **Contextual Responses**: Agents adapt based on conversation history
- **Personalized Questions**: Dynamic question generation based on candidate responses
- **Performance Analytics**: Detailed scoring across multiple dimensions
- **Session Management**: Persistent interview sessions with full history

## 🏗️ Architecture

### **System Overview**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   FastAPI App   │    │  Multi-Agent    │
│   (HTML/CSS/JS) │◄──►│   (WebSocket)   │◄──►│    System       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LLM Services  │
                       │ (OpenAI/Anthropic) │
                       └─────────────────┘
```

### **Agent Architecture**
```
MultiAgentInterviewSystem
├── InterviewAgent (Primary conversation)
├── SearchAgent (Information lookup)
├── FeedbackAgent (Response analysis)
├── SummaryAgent (Session summaries)
└── OrchestratorAgent (Coordination)
```

### **Core Components**
- **`web_app.py`**: FastAPI application with WebSocket support
- **`interviewer/multi_agent_system.py`**: Agent coordination and routing
- **`interviewer/agents/`**: Individual agent implementations
- **`interviewer/core/`**: Data structures and context management
- **`interviewer/feedback/`**: Modular feedback analysis system

## 📦 Installation

### **Prerequisites**
- Python 3.9+
- Poetry (for dependency management)
- OpenAI API key (for LLM and voice features)
- Optional: Anthropic API key (alternative LLM provider)

### **Setup Instructions**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd interviewer
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Configure environment variables**
   ```bash
   cp .env_example .env_local
   ```
   
   Edit `.env_local` and add your API keys:
   ```env
   # Required: Choose one or both
   OPENAI_API_KEY=sk-your-openai-api-key-here
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
   ```

4. **Start the application**
   ```bash
   poetry run python web_app.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn web_app:app --host 0.0.0.0 --port 3000
   ```

5. **Access the application**
   Open your browser and navigate to `http://localhost:3000`

## 🎯 Usage Guide

### **Starting an Interview**

1. **Configure Interview Settings**
   - Choose LLM provider (OpenAI or Anthropic)
   - Select interview type (Technical, Behavioral, Case Study)
   - Set interviewer tone and difficulty level
   - Configure voice settings (optional)

2. **Upload Documents (Optional)**
   - Resume: Provides context for personalized questions
   - Job Description: Helps tailor questions to specific role
   - Supported formats: PDF, DOCX, TXT

3. **Begin Interview**
   - Click "Start Interview" to begin
   - The AI interviewer will welcome you and ask the first question

### **During the Interview**

- **Real-time Feedback**: Receive instant analysis of your responses
- **Voice Interaction**: Use microphone for speech-to-text (if enabled)
- **Cost Tracking**: Monitor API usage in real-time
- **Natural Conversation**: The interviewer adapts to your responses

### **Interview Types**

#### **Technical Interviews**
- Coding questions and algorithm problems
- SQL and data analysis scenarios
- System design and architecture discussions
- Technology-specific deep dives

#### **Behavioral Interviews**
- Past experience and project discussions
- Leadership and teamwork scenarios
- Problem-solving and conflict resolution
- STAR method responses

#### **Case Study Interviews**
- Hypothetical business problems
- Data analysis and interpretation
- Strategic thinking and decision-making
- Cross-functional collaboration scenarios

## 🔧 Development

### **Project Structure**
```
interviewer/
├── agents/                 # Agent implementations
│   ├── base.py            # Base agent class
│   ├── interview.py       # Primary interview agent
│   ├── feedback.py        # Response analysis agent
│   ├── search.py          # Information lookup agent
│   ├── summary.py         # Session summary agent
│   └── orchestrator.py    # Agent coordination
├── core/                  # Core data structures
│   ├── context.py         # Interview context management
│   ├── messaging.py       # Message/response models
│   └── routing.py         # Agent routing logic
├── feedback/              # Modular feedback system
│   ├── assessors.py       # Response assessment methods
│   ├── classifiers.py     # Response type classification
│   ├── generators.py      # Feedback generation
│   └── contextual.py      # Contextual feedback logic
├── config.py              # Configuration management
├── cost_tracker.py        # API cost tracking
├── document_parser.py     # Document processing
└── multi_agent_system.py # System orchestration
```

### **Adding New Agents**

1. **Create agent class**
   ```python
   from .base import BaseInterviewAgent
   
   class MyAgent(BaseInterviewAgent):
       def __init__(self):
           super().__init__(
               name="my_agent",
               capabilities=[AgentCapability.MY_CAPABILITY]
           )
       
       def can_handle(self, message, context):
           # Return confidence score (0.0 to 1.0)
           return 0.8
       
       async def process(self, message, context):
           # Process message and return response
           return self._create_response(content="...", confidence=0.9)
   ```

2. **Register agent in multi-agent system**
   ```python
   # In multi_agent_system.py
   self.my_agent = MyAgent()
   self.agent_registry.register_agent(self.my_agent)
   ```

### **Extending Feedback System**

The feedback system is modular and extensible:

- **Add new assessment methods** in `feedback/assessors.py`
- **Create new response classifiers** in `feedback/classifiers.py`
- **Implement custom feedback generators** in `feedback/generators.py`
- **Add contextual logic** in `feedback/contextual.py`

### **Configuration**

The system supports multiple LLM providers and models:

```python
# OpenAI Configuration
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000
)

# Interview Configuration
interview_config = InterviewConfig(
    interview_type=InterviewType.TECHNICAL,
    tone=Tone.PROFESSIONAL,
    difficulty=Difficulty.MEDIUM
)
```

## 📊 Performance & Monitoring

### **Cost Tracking**
The system tracks API usage and costs in real-time:
- Token usage for each LLM call
- Audio transcription costs (Whisper)
- Text-to-speech synthesis costs
- Per-session and cumulative cost tracking

### **Session Analytics**
- Response quality scoring
- Interview progression tracking
- Agent usage statistics
- Performance trends and insights

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### **Code Style**
- Follow PEP 8 guidelines
- Add comprehensive docstrings
- Include type hints
- Write clear commit messages

### **Testing**
```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=interviewer
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT models and Whisper API
- **Anthropic** for Claude models
- **FastAPI** for the web framework
- **Pydantic** for data validation
- **WebSocket** for real-time communication

## 📞 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check the documentation in the code
- Review the architecture diagrams

---

**Happy interviewing! 🎉**