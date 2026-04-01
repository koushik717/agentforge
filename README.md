# 🤖 AgentForge

**Production-grade distributed AI agent runtime** — create, manage, and execute AI agents with multi-provider LLM support, tool integration, and real-time observability.

```
┌──────────────────────────────────────────────────────────────────┐
│                        AgentForge                                │
│                                                                  │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │ Frontend │───▶│ FastAPI  │───▶│  Engine  │───▶│ LLM APIs  │  │
│  │ (React)  │    │   API    │    │          │    │ Groq/     │  │
│  └─────────┘    └────┬─────┘    └────┬─────┘    │ Gemini/   │  │
│                      │               │           │ OpenAI/   │  │
│                 ┌────▼─────┐    ┌────▼─────┐    │ Ollama    │  │
│                 │PostgreSQL│    │  Tools   │    └───────────┘  │
│                 │          │    │ Search/  │                    │
│                 └──────────┘    │ Calc     │    ┌───────────┐  │
│                                 └──────────┘    │  Worker   │  │
│                 ┌──────────┐                    │ (Async)   │  │
│                 │  Redis   │◀───────────────────│           │  │
│                 │ Pub/Sub  │                    └───────────┘  │
│                 └──────────┘                                   │
│                                                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │Prometheus│───▶│ Grafana  │    │   K8s    │                 │
│  │ Metrics  │    │Dashboard │    │  Ready   │                 │
│  └──────────┘    └──────────┘    └──────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

## ✨ Features

- **Multi-Provider LLM Support** — Groq (blazing fast), Google Gemini, OpenAI, Ollama (local)
- **Tool System** — Extensible tool framework with built-in web search and calculator
- **Agent Execution Engine** — Iterative tool-calling loop with automatic retry
- **Async Worker** — Background processing via Redis pub/sub
- **Full REST API** — CRUD for agents and runs, sync + async execution
- **Real-time Dashboard** — React frontend with live agent monitoring
- **Observability** — Structured JSON logging, Prometheus metrics, Grafana dashboards
- **Production Ready** — Docker Compose, Kubernetes manifests, GitHub Actions CI

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local dev)

### Run with Docker Compose

```bash
# Clone and configure
git clone https://github.com/yourusername/agentforge.git
cd agentforge
cp .env.example .env
# Edit .env with your API keys

# Start everything
docker-compose up -d

# Verify
curl http://localhost:8000/api/v1/health
```

### Run Locally

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the API server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start the background worker (separate terminal)
python -m runtime.worker

# Start the frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check (DB + Redis status) |
| `GET` | `/api/v1/tools` | List available tools |
| `GET` | `/api/v1/providers` | List LLM providers |
| `POST` | `/api/v1/agents` | Create an agent |
| `GET` | `/api/v1/agents` | List agents |
| `GET` | `/api/v1/agents/{id}` | Get agent details |
| `DELETE` | `/api/v1/agents/{id}` | Delete agent |
| `POST` | `/api/v1/runs` | Create async run |
| `POST` | `/api/v1/runs/sync` | Create sync run |
| `GET` | `/api/v1/runs` | List runs |
| `GET` | `/api/v1/runs/{id}` | Get run details |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Swagger UI |

## 🏗️ Architecture

```
agentforge/
├── api/                    # FastAPI application
│   ├── config.py          # Pydantic settings
│   ├── db/                # Database + Redis clients
│   ├── models/            # Pydantic schemas
│   └── routes/            # API endpoints
├── runtime/               # Agent execution
│   ├── engine.py          # Execution engine with tool loop
│   ├── worker.py          # Background worker (Redis consumer)
│   └── llm/               # LLM provider abstraction
│       └── providers.py   # Groq, Gemini, OpenAI, Ollama
├── tools/                 # Tool system
│   ├── web_search.py      # DuckDuckGo search
│   └── calculator.py      # Safe math evaluator
├── observability/         # Logging + metrics
│   ├── metrics.py         # Prometheus counters/histograms
│   └── prometheus.yml     # Scrape config
├── frontend/              # React dashboard
├── grafana/               # Grafana dashboards + provisioning
├── k8s/                   # Kubernetes manifests
├── docker-compose.yml     # Full stack orchestration
├── Dockerfile             # Multi-stage Python build
└── main.py                # FastAPI entrypoint
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic, Uvicorn |
| Database | PostgreSQL 16, asyncpg |
| Cache / Pub-Sub | Redis 7 |
| LLM | Groq, Gemini, OpenAI, Ollama |
| Frontend | React, Vite |
| Observability | structlog, Prometheus, Grafana |
| Containerization | Docker, Kubernetes |
| CI/CD | GitHub Actions |

## 📊 Monitoring

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3001` (admin / agentforge)
- **Swagger Docs**: `http://localhost:8000/docs`

## 📜 License

MIT
