# 🏢 EKIP: Enterprise Knowledge Intelligence Platform
> **Production-Grade, Multi-Tenant Retrieval-Augmented Generation (RAG) System**  
> *Engineered with Zero-Hallucination Guardrails, Hybrid Search (pgvector HNSW + Full-Text Search), Two-Tier Semantic Caching, Real-Time SSE Streaming, and Asynchronous Background Processing.*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![FastEmbed](https://img.shields.io/badge/FastEmbed-BAAI%201024--d-orange)](https://github.com/qdrant/fastembed)
[![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini%20API-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-56%2F56%20Passing-brightgreen)](tests/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🌟 Executive Summary

**EKIP** is an enterprise-ready, multi-tenant RAG platform designed to eliminate hallucinations, enforce rigorous citation verification, and operate at ultra-low latency and zero cloud infrastructure cost. 

Unlike basic chatbot wrappers or demo scripts, EKIP is built according to production distributed systems and AI engineering standards:
* **Strict Grounding Guarantee:** Every factual claim must be backed by a verified source citation `[n]`. Queries unsupported by the knowledge base trigger an **Abstention Gate** refusal instead of hallucinating.
* **Hybrid Two-Stage Retrieval:** Combines 1024-dimensional dense vectors (pgvector HNSW index) with sparse lexical Full-Text Search fused via **Reciprocal Rank Fusion (RRF)**, followed by a **Cross-Encoder Reranker** and **Extractive Sentence Compression**.
* **Enterprise Multi-Tenancy:** Hard tenant data perimeter enforced at the database, vector index, and cache layers.
* **Two-Tier Semantic Caching:** L1 exact SHA-256 hash match (`<1ms`) + L2 Cosine vector similarity match (`<5ms`) to bypass redundant LLM executions.
* **Real-Time Streaming & Observability:** Token-by-token Server-Sent Events (SSE) delivery and real-time **RAG Triad** evaluation (Faithfulness, Context Relevance, Answer Relevance).
* **100% Free & Local-First:** Embeddings, reranking, vectors, and relational data run locally on CPU for **$0.00**, powered by free-tier Google Gemini synthesis.

---

## 📐 System Architecture

```mermaid
flowchart TD
    User([User / Web Client]) -->|1. Submit Query| API[FastAPI Gateway]
    
    subgraph CachingLayer [Phase 11: Two-Tier Semantic Cache]
        API -->|Check Cache| Redis[(Redis L1 Exact Hash & L2 Vector Cosine)]
        Redis -.->|Cache Hit < 3ms| User
    end
    
    subgraph QueryPipeline [Phases 6, 9 & 10: Retrieval & Reranking]
        API -->|Cache Miss| Transform[Query Transformation: HyDE / Multi-Query Expansion]
        Transform --> Hybrid[Hybrid Search: Dense Vector + Lexical FTS]
        Hybrid -->|pgvector HNSW + tsvector| PG[(PostgreSQL 16 + pgvector)]
        Hybrid --> RRF[Reciprocal Rank Fusion k=60]
        RRF --> Reranker[Stage 2 Cross-Encoder Reranker]
        Reranker --> Compressor[Extractive Sentence Compression]
        Compressor --> LostMiddle[Context Builder: Lost-in-the-Middle Permutation]
    end

    subgraph LLMAndEvaluation [Phases 7, 8, 12 & 13: Generation & Guardrails]
        LostMiddle --> Router{Resilient LLM Router}
        Router -->|Primary| Gemini[Google Gemini API]
        Router -.->|Circuit Breaker Fallback| MockLLM[Offline Deterministic Engine]
        Gemini --> Verifier[Citation Verifier]
        Verifier --> Triad[RAG Triad Evaluator: Groundedness & Relevance]
        Triad --> Streamer[SSE Token Streamer]
    end

    Streamer -->|Real-Time Token Flow| User
    Streamer -->|Async Persist Telemetry| PG
    Streamer -->|Populate Cache| Redis
```

---

## 🚀 Key Features by Engineering Phase

| Phase | Module | Capabilities & Production Standards |
| :--- | :--- | :--- |
| **Phase 1** | Clean Architecture | Modular domain-driven design, Pydantic v2 settings, structured JSON logging (`structlog`). |
| **Phase 2** | Database & Vector Schema | PostgreSQL 16 + `pgvector` HNSW cosine indexing, tenant isolation, Alembic migrations. |
| **Phase 3** | Security & Multi-Tenancy | Multi-tenant RBAC (admin, editor, viewer), password hashing (`bcrypt`), JWT tokens. |
| **Phase 4** | Ingestion & Chunking | Hierarchical markdown & PDF parsing, recursive structural chunking, SHA-256 deduplication. |
| **Phase 5** | Vector Embeddings | Local ONNX `BAAI/bge-large-en-v1.5` embeddings (1024-d) via FastEmbed (zero GPU cost). |
| **Phase 6** | Hybrid Retrieval | Parallel Dense Vector + Lexical FTS, fused via Reciprocal Rank Fusion ($k=60$). |
| **Phase 7** | LLM Resilience | Circuit breakers, exponential jitter retries, and automated fallback routing. |
| **Phase 8** | Context Assembly | Token budget management, structured `<context>` injection, Lost-in-the-Middle permutation. |
| **Phase 9** | Reranking & Compression | Cross-Encoder scoring (`BAAI/bge-reranker-base`) + extractive sentence noise filtering. |
| **Phase 10** | Query Transformation | HyDE (Hypothetical Document Embeddings), Multi-Query Expansion, and Query Rewriting. |
| **Phase 11** | Two-Tier Semantic Cache | Redis L1 exact SHA-256 match + L2 vector cosine similarity ($O(1)$ sub-millisecond responses). |
| **Phase 12** | Real-Time SSE Streaming | RFC 8895 Server-Sent Events with structured event types (`ping`, `sources`, `token`, `done`, `abstention`). |
| **Phase 13** | RAG Triad Guardrails | Real-time automated evaluation: Groundedness (Faithfulness), Context Relevance, Answer Relevance. |
| **Phase 14** | Telemetry & Observability | Model cost accounting, latency p50/p95 tracking, user feedback engine (👍/👎), audit logging. |
| **Phase 15** | Background Task Queue | Asynchronous Redis ingestion queue (`BRPOP`), worker daemon with 4-stage live stepper. |
| **Phase 16** | Web UI Dashboard | Modern bright enterprise dashboard, live markdown rendering, interactive telemetry meters. |

---

## 🛠️ Tech Stack & Prerequisites

* **Operating System:** Windows, macOS, or Linux
* **Python:** 3.12+
* **Vector Database:** PostgreSQL 16 with `pgvector` extension
* **Cache & Message Broker:** Redis 7
* **Local Embedding Engine:** FastEmbed (ONNX Runtime, CPU-optimized)
* **LLM Engine:** Google Gemini (`gemini-flash-lite-latest`) or offline mock double

---

## ⚡ Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/echoistprashant/EKIP.git
cd EKIP
```

### 2. Start PostgreSQL & Redis via Docker
```bash
docker compose up -d
```
Verify healthy status:
```bash
docker ps
# ekip-postgres on port 5432
# ekip-redis on port 6379
```

### 3. Setup Python Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update `.env` with your settings:
```dotenv
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://ekip_user:ekip_password@localhost:5432/ekip_db
REDIS_URL=redis://localhost:6379/0

# Optional: Add your free Google Gemini API key from https://aistudio.google.com/
LLM_PROVIDER=gemini
LLM_MODEL=gemini-flash-lite-latest
GEMINI_API_KEY=your_free_gemini_api_key_here
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Launch the Application Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 💻 Interactive Dashboard

Open your browser and navigate to:
👉 **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

### Dashboard Capabilities:
1. **RAG Chat Assistant:** Real-time token streaming, query transformation toggle (HyDE, Expansion), and verified citation cards.
2. **Knowledge Ingestion & Queue:** Upload PDF or Markdown files with a live 4-stage background processing stepper.
3. **System Telemetry & Observability:** Live monitoring of cache hit rate, token counts, cost distribution, and RAG Triad scores.

---

## 🧪 Automated Testing

The platform includes a comprehensive test suite covering unit, integration, multi-tenant isolation, and end-to-end streaming behaviors.

```bash
# Run the complete test suite (56 tests)
pytest

# Run with verbose output
pytest -v

# Run specific integration tests
pytest tests/integration/test_streaming_e2e.py
pytest tests/integration/test_analytics_and_feedback.py
pytest tests/integration/test_tenant_isolation.py
```

---

## 📚 API Endpoints Summary

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/health` | System health check (DB + Redis status) | No |
| `POST` | `/api/v1/auth/register` | Register new organization tenant & admin user | No |
| `POST` | `/api/v1/auth/login` | Authenticate user & issue JWT bearer token | No |
| `GET` | `/api/v1/collections` | List collections in current tenant | Yes |
| `POST` | `/api/v1/collections` | Create isolated knowledge collection (Admin only) | Yes |
| `POST` | `/api/v1/documents/upload` | Upload & ingest document (sync or async Redis queue) | Yes |
| `GET` | `/api/v1/documents/jobs/{id}` | Poll background ingestion job status | Yes |
| `POST` | `/api/v1/query` | Synchronous RAG query execution | Yes |
| `POST` | `/api/v1/query/stream` | Server-Sent Events (SSE) real-time token stream | Yes |
| `POST` | `/api/v1/feedback` | Submit user helpfulness feedback (👍 / 👎) | Yes |
| `GET` | `/api/v1/analytics/overview` | Fetch tenant telemetry, cost, and RAG Triad metrics | Yes |

---

## 🛡️ License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
