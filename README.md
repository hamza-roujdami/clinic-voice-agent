# Clinic Voice Agent

AI-powered voice scheduling assistant for hospital call centers, built on **Microsoft Azure and AI Foundry**.

## Overview

Voice scheduling system for telephony integration:

```
PSTN Caller → CCaaS Platform → Voice Gateway → Azure STT → Foundry Agent → Azure TTS → Audio Response
```

**Text interfaces** (Web UI / CLI) available for testing and development.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AZURE AI FOUNDRY                                │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    clinic-voice-agent                              │  │
│  │                   (Single Triage Agent)                            │  │
│  │                                                                    │  │
│  │  Model: gpt-4o-mini    │  15 Tools    │  Multi-turn Conversations │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│  ┌─────────────┐  ┌─────────────┐  │  ┌─────────────┐  ┌─────────────┐  │
│  │ Web Search  │  │ Memory      │  │  │ 13 Function │  │ Responses   │  │
│  │ Preview     │  │ Search      │  │  │ Tools       │  │ API         │  │
│  └─────────────┘  └─────────────┘  │  └─────────────┘  └─────────────┘  │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────┐
│                           FastAPI Server                                 │
│  ┌─────────────┐  ┌─────────────┐  │  ┌─────────────┐  ┌─────────────┐  │
│  │ POST /chat  │  │ Sessions    │◀─┘  │ Web UI      │  │ CLI         │  │
│  │ (text)      │  │ Manager     │     │ :8000/      │  │ cli.py      │  │
│  └─────────────┘  └──────┬──────┘     └─────────────┘  └─────────────┘  │
└──────────────────────────┼───────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Cosmos DB  │
                    │  Sessions   │
                    └─────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Agent SDK** | `azure-ai-projects` | Create and run Foundry agents |
| **LLM** | `gpt-4o-mini` | Conversation understanding and response generation |
| **Sessions** | Azure Cosmos DB | Persist conversation history and patient context (24h TTL) |
| **Web Search** | WebSearchPreviewTool | Answer general questions (visiting hours, directions) |
| **Memory** | Foundry Memory Store | Store long-term patient preferences |
| **RAG** | Azure AI Search | Policy and FAQ retrieval with citations |
| **API** | FastAPI + Uvicorn | HTTP endpoints for chat and voice |
| **Voice** | Azure Speech STT/TTS | Convert speech to text and text to speech |

## Prerequisites

- Python 3.11+
- Azure subscription.
- Azure CLI (`az login` authenticated)

## Quick Start

```bash
# 1. Setup
git clone https://github.com/hamza-roujdami/clinic-voice-agent
cd clinic-voice-agent

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Deploy infrastructure
cd infra/public
./deploy.sh rg-clinic-voice-agent swedencentral

# 4. Run
python main.py
```

## Testing Modes

### Web UI
Open http://localhost:8000 in your browser

### CLI Mode
```bash
# Interactive CLI (connect to running server)
python cli.py

```

### Test Scenarios (Demo Patient: MRN-5050)
```
1. "Hello, my MRN is MRN-5050"           → Patient lookup (Hamza El-Ghoujdami)
2. "The code is 123456"                   → OTP verification
3. "I need to see a cardiologist"         → Doctor search
4. "Book Tuesday at 10am"                 → Appointment booking
5. "What are the visiting hours?"         → Web search
6. "I need to speak to someone"           → Human transfer
```

## Project Structure

```
clinic-voice-agent/
├── agents/              # Foundry agent factory and prompts
│   ├── factory.py       # AgentFactory (creates/runs agent)
│   ├── prompts.py       # System prompt and examples
│   └── memory.py        # Foundry Memory helpers
├── api/                 # FastAPI routes
│   └── routes.py        # /chat, /session, /health endpoints
├── tools/               # Agent function tools
│   ├── otp.py           # Patient lookup, OTP verification
│   ├── scheduling.py    # Appointments, doctors, slots
│   ├── handoff.py       # Human transfer
│   ├── context.py       # Patient context injection
│   └── decorator.py     # Tool registration decorator
├── sessions/            # Session management
│   ├── manager.py       # SessionManager singleton
│   └── cosmos_store.py  # Cosmos DB persistence
├── tests/               # Integration tests
├── static/              # Web UI (index.html)
├── infra/               # Bicep IaC templates
├── config.py            # Environment configuration
├── main.py              # FastAPI server
├── cli.py               # CLI interface
└── requirements.txt
```

## Environment Variables

```bash
# Required - Azure AI Foundry
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
FOUNDRY_MODEL_PRIMARY=gpt-4o-mini

# Required - Azure AI Search (for RAG)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net

# Optional - Session storage
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_DATABASE=enterprise_memory
COSMOS_CONTAINER=sessions

# Optional - Foundry Memory (for patient preferences)
FOUNDRY_MEMORY_STORE_NAME=clinic-patient-memory
```

## System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Azure AI Foundry                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   clinic-voice-agent                           │  │
│  │                                                                │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐    │  │
│  │   │ gpt-4o-mini │  │ WebSearch   │  │ MemorySearchTool   │    │  │
│  │   │   (LLM)     │  │ PreviewTool │  │ (patient context)  │    │  │
│  │   └─────────────┘  └─────────────┘  └────────────────────┘    │  │
│  │                                                                │  │
│  │   ┌──────────────────────────────────────────────────────┐    │  │
│  │   │              13 Function Tools                        │    │  │
│  │   │  Identity: lookup_patient, send_otp, verify_otp       │    │  │
│  │   │  Scheduling: search_doctors, check_availability,      │    │  │
│  │   │              book/reschedule/cancel_appointment, ...   │    │  │
│  │   │  Policy: search_policies    Handoff: human_transfer   │    │  │
│  │   └──────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │  Foundry Memory     │  │  Responses API      │                   │
│  │  (patient prefs)    │  │  (conversation)     │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  POST /chat     │  │ Session Manager │  │ Web UI / CLI        │  │
│  │  GET /health    │  │ (Cosmos DB)     │  │ localhost:8000      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Azure Services                               │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │  Cosmos DB          │  │  AI Search          │                   │
│  │  (sessions, 24h TTL)│  │  (policy RAG)       │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Message → POST /chat → Session Lookup (Cosmos DB)
                               ↓
                    AgentFactory.run() → Foundry Responses API
                               ↓
                    Tool Execution (if needed) → tools/*.py
                               ↓
                    Session Update → Response to User
```

### Voice Integration

```
PSTN → CCaaS → Voice Gateway → Azure STT → Agent → Azure TTS → Audio Response
                    ↑
         (Audio stays in telephony platform - no raw audio in Azure)
```

### Security & Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Data Sovereignty** | UAE North for production (voice data) |
| **No Audio Storage** | Audio stays in telephony platform |
| **PHI Gating** | Identity verification before scheduling access |
| **RBAC** | AAD-only auth for Cosmos DB (no connection strings) |
| **Audit Logs** | Azure Monitor + App Insights tracing |
| **Session TTL** | 24-hour auto-expiry in Cosmos DB |

---

## Sources & References

### Azure AI Foundry Documentation
- [Azure AI Foundry SDK (azure-ai-projects)](https://learn.microsoft.com/en-us/azure/ai-services/agents/quickstart) - Agent creation and Responses API
- [Foundry Agents How-To](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/) - Tool binding, memory, web search

### SDK Samples (azure-sdk-for-python)
- [agents_basics.py](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/agents_basics.py) - Basic agent creation
- [agents_with_resources_in_thread.py](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/agents_with_resources_in_thread.py) - File and search resources
- [sample_agent_web_search.py](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/tools/sample_agent_web_search.py) - Web search tool

### Responses API (v2 Pattern)
- [sample_agents_responses_stream.py](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/sample_agents_responses_stream.py) - Streaming responses
- [sample_agents_responses.py](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/sample_agents_responses.py) - Responses API
- [sample_agents_responses_local_function_tools.py](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/sample_agents_responses_local_function_tools.py) - Function tool execution

### Azure Services
- [Azure Cosmos DB Python SDK](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/sdk-python) - Session storage
- [Azure Speech SDK](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-speech-to-text) - STT/TTS (Phase 2)
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/) - RAG retrieval (Planned)

### Python Libraries
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Rich](https://rich.readthedocs.io/) - CLI formatting


---

## License

Demo/PoC purposes only. Not for production healthcare use without proper compliance review.
