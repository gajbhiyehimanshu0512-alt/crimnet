# 🕵️ CrimNet — AI-Powered Criminal Network Analyzer

> An AI-powered intelligence platform that ingests heterogeneous criminal data, extracts entities via NLP, maps relationships into a knowledge graph, detects suspicious patterns with ML, and surfaces actionable insights through an interactive investigator dashboard.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   React Dashboard (Port 3000)               │
│  Graph Viz │ Timelines │ Alert Feed │ AI Q&A │ Reports      │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│  /ingest  /graph  /analytics  /ai                           │
└──┬──────────────┬──────────────────────────────────────────┘
   │              │
   ▼              ▼
Neo4j           ChromaDB          PostgreSQL · Redis
(Graph DB)    (Vector Store)     (Structured  · Cache)
   ▲
   │
┌──┴──────────────────────────────────────────────────────────┐
│              AI Processing Pipeline                         │
│  NLP (spaCy) → Graph Builder → Analytics → LLM (Ollama)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Graph Database | Neo4j 5.x Community |
| Vector Store | ChromaDB |
| Cache | Redis |
| NLP | spaCy `en_core_web_sm` + HuggingFace |
| Graph Analytics | NetworkX + CDLib + python-louvain |
| ML Anomaly | scikit-learn Isolation Forest |
| LLM | Ollama (local) — llama3 / mistral |
| Frontend | React + Cytoscape.js + Recharts + Tailwind |
| Infrastructure | Docker Compose |

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac/Linux)
- 8 GB RAM minimum (16 GB recommended for GPU LLM)
- 20 GB free disk space

### 1 — Clone & Configure

```bash
git clone <repo-url>
cd criminal-network-analyzer
cp .env.example .env
# Edit .env if needed (defaults work for local Docker setup)
```

### 2 — Start All Services

```bash
docker compose up -d
```

This starts: Neo4j · PostgreSQL · Redis · ChromaDB · Ollama · Backend · Frontend

Wait ~60 seconds for all services to be healthy.

### 3 — Download the LLM Model

```bash
docker exec cna_ollama ollama pull llama3
```

> This downloads ~4 GB. Alternatively use `mistral` (smaller) or `phi3` (fastest).

### 4 — Load Demo Data

```bash
# Option A: via Docker
docker exec cna_backend python /app/../scripts/seed_demo_data.py

# Option B: locally (requires Python 3.11 + backend deps installed)
cd backend
pip install -r requirements.txt
python ../scripts/seed_demo_data.py
```

### 5 — Open the Dashboard

| Service | URL |
|---|---|
| **Dashboard** | http://localhost:3000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Neo4j Browser** | http://localhost:7474 (neo4j / cna_password123) |

### 6 — Run Analytics

Click **"Run Analytics"** on the Dashboard to compute centrality, detect communities, and score risks.

---

## 📂 Project Structure

```
criminal-network-analyzer/
├── backend/
│   ├── ingestion/           # FIR, CDR, financial, surveillance, social parsers
│   ├── nlp/                 # Entity extraction + relation extraction (spaCy)
│   ├── graph/               # Neo4j client, graph builder, Pydantic schemas
│   ├── analytics/           # Centrality, community detection, anomaly detection, timeline
│   ├── ai/                  # RAG engine, report generator, risk scorer
│   ├── api/routes/          # FastAPI route handlers (ingest, graph, analytics, ai)
│   ├── tests/               # Unit tests (pytest)
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (pydantic-settings)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard, GraphView, InvestigatorSearch, Timeline, Reports, DataIngestion
│       ├── components/      # Sidebar
│       └── api/client.js    # Axios API client
├── scripts/
│   └── seed_demo_data.py    # Synthetic demo data generator
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 📊 Features

### 🔍 Data Ingestion
- **FIR Parser** — PDF/TXT First Information Reports → entities + relationships
- **CDR Parser** — CSV/Excel call records → CALLED graph edges
- **Financial Parser** — Bank transactions → TRANSFERRED_TO edges + suspicious flagging
- **Surveillance Parser** — Watch reports → PRESENT_AT edges
- **Social Media Parser** — SOCMINT → handles, hashtags, location mentions
- **Free-text** — Any intelligence text via NLP pipeline

### 🧠 AI / NLP Pipeline
- **Named Entity Recognition** — spaCy `en_core_web_sm` + custom Indian-context patterns
- **Custom patterns** — Vehicle plates (MH-01-AB-1234), FIR numbers, Aadhaar, PAN, Indian phones
- **Relation Extraction** — Dependency parsing + co-occurrence + LLM zero-shot
- **Graph RAG** — ChromaDB vector search + Neo4j graph context → Ollama LLM answer

### 📈 Analytics Engine
| Algorithm | Purpose |
|---|---|
| Degree Centrality | Most connected individuals |
| Betweenness Centrality | Brokers / middlemen |
| PageRank | Influence weighted by neighbor quality |
| Eigenvector Centrality | Connected to important nodes |
| **Louvain Community Detection** | Identify criminal cells / syndicates |
| Label Propagation | Fast alternative community detection |
| **Isolation Forest (ML)** | CDR burst / night activity anomalies |
| Rule-based detectors | Hawala (round amounts), large transactions, critical brokers |

### 🗺️ Interactive Graph
- Force-directed layout (Cytoscape.js COSE)
- Nodes sized by PageRank, colored by entity type
- Risk-level border highlighting (red=CRITICAL)
- Click-to-expand neighbor subgraph
- Community coloring
- Filter by entity type

### 🤖 Investigator AI
Ask natural language questions:
- *"Who are the top suspects connected to the Mumbai case?"*
- *"Which phone numbers have the most suspicious calling patterns?"*
- *"Who is the critical broker between the Delhi and Punjab networks?"*

### 📄 Intelligence Reports
- Risk score (0–100) with breakdown
- Executive summary (LLM-generated)
- Known associates grid
- Centrality scores
- Investigative recommendations
- Downloadable text report

---

## 🧪 Running Tests

```bash
cd backend
pip install pytest
pytest tests/ -v
```

---

## ⚙️ Configuration

Key settings in `.env`:

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URL` | `bolt://localhost:7687` | Neo4j connection |
| `NEO4J_PASSWORD` | `cna_password123` | Change in production |
| `OLLAMA_MODEL` | `llama3` | LLM model name |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `OPENAI_API_KEY` | *(blank)* | Optional: use GPT-4 instead of Ollama |

---

## 🔒 Security Notes

> ⚠️ This system is designed for **law enforcement use only**.
> - Never expose ports publicly without authentication
> - All data remains on-premises when using Ollama (local LLM)
> - Add API key authentication before deploying in a multi-user environment
> - Audit logs are stored in PostgreSQL

---

## 📋 API Reference

Full Swagger docs at http://localhost:8000/docs

> **Note:** All `/api/*` routes (except `/api/auth/login`) require a JWT Bearer token in the `Authorization` header.

### Key Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | ✗ | Authenticate and obtain JWT |
| `GET`  | `/api/auth/me` | ✓ | Get current user profile |
| `POST` | `/api/ingest/fir` | ✓ | Upload FIR document |
| `POST` | `/api/ingest/cdr` | ✓ | Upload CDR file |
| `POST` | `/api/ingest/financial` | ✓ | Upload transaction file |
| `POST` | `/api/ingest/text` | ✓ | Ingest free text |
| `GET`  | `/api/graph/network` | ✓ | Full graph for visualization |
| `GET`  | `/api/graph/entity/{id}` | ✓ | Entity + neighbors |
| `GET`  | `/api/graph/path?from=X&to=Y` | ✓ | Shortest path |
| `GET`  | `/api/graph/search?q=name` | ✓ | Entity search |
| `POST` | `/api/analytics/run` | ✓ | Run full analytics pipeline |
| `GET`  | `/api/analytics/influencers` | ✓ | Top influencers |
| `GET`  | `/api/analytics/anomalies` | ✓ | Anomaly alerts |
| `GET`  | `/api/analytics/timeline/{id}` | ✓ | Entity timeline |
| `POST` | `/api/ai/query` | ✓ | Natural language Q&A |
| `GET`  | `/api/ai/report/{id}` | ✓ | Intelligence report (JSON) |
| `GET`  | `/api/ai/report/{id}/pdf` | ✓ | Intelligence report (PDF download) |
| `GET`  | `/api/cases` | ✓ | List all cases |
| `POST` | `/api/cases` | ✓ | Create a new case |
| `GET`  | `/api/cases/{id}` | ✓ | Get case details |
| `PUT`  | `/api/cases/{id}` | ✓ | Update case |
| `DELETE`| `/api/cases/{id}` | ✓ | Delete case |
| `POST` | `/api/cases/{id}/entities` | ✓ | Link entity to case |
| `DELETE`| `/api/cases/{id}/entities/{eid}` | ✓ | Unlink entity from case |

### Default Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `analyst` | `analyst123` | analyst |

---

## 🗺️ Roadmap

- [ ] Real-time CDR streaming (Apache Kafka)
- [ ] Hindi/regional language NER support
- [ ] Geospatial map view (Leaflet.js)
- [x] PDF report export
- [x] Multi-user authentication (JWT)
- [x] Case management module
- [ ] Automated daily digest alerts

---

*Built with ❤️ for law enforcement intelligence analysis.*
