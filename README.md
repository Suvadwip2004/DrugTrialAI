# Multi-Agent Autonomous Clinical Trial & Drug Interaction Analyzer

A backend-only, multi-agent system that detects drug-drug interactions, matches patients to relevant clinical trials, and produces a structured, fully-cited, risk-scored report — grounded in retrieved evidence (RAG), never raw LLM memory.

Built entirely on a **$0 free-tier stack**: no paid APIs, no license fees.

---

## What It Does

- **Drug-drug interaction detection** — severity, mechanism, and evidence source for any drug pair.
- **Clinical trial matching** — semantically matches patient/condition context against live ClinicalTrials.gov listings.
- **Grounded reporting** — every claim in the final report is traceable to a real source (RxNav, OpenFDA, DailyMed, PubMed, or ClinicalTrials.gov). A dedicated validator agent rejects any ungrounded statement before it reaches the user.
- **Risk scoring** — a deterministic rule engine flags contraindicated combinations, with an LLM layer only used to explain the reasoning in plain language (never to make the safety decision itself).
- **Full audit trail** — every agent run, input, output, and confidence score is persisted for traceability.

This is a **decision-support tool**, not a diagnostic or prescribing system.

---

## Tech Stack (100% Free)

| Layer | Choice | Notes |
|---|---|---|
| LLM | Gemini 2.5 Flash / Flash-Lite | Free tier, no card required. Avoid Gemini 2.5 Pro's free tier — RPM/RPD caps are too tight for a multi-agent pipeline. |
| Embeddings | Gemini embeddings (free quota) or self-hosted PubMedBERT/BioBERT | Domain-specific embeddings improve retrieval on clinical text. |
| Vector DB | Qdrant Cloud (free tier) or self-hosted via Docker | Self-host to avoid the 1-week inactivity auto-suspend. |
| Drug interaction data | RxNav Interaction API (NLM), OpenFDA (FAERS), DailyMed | Free and public — no DrugBank license needed. |
| Clinical trials data | ClinicalTrials.gov API | Free, public, official. |
| Literature (RAG) | PubMed / PMC E-utilities | Free, no key required for light use. |
| Relational DB | PostgreSQL | Self-hosted via Docker, or free tier on Supabase/Neon. |
| Cache / Broker | Redis | Self-hosted via Docker. |
| Task Queue | Celery + Redis | Open source. |
| Orchestration | LangGraph | Open source, fine-grained multi-agent state control. |
| API Framework | FastAPI | Open source. |
| Containerization | Docker + Docker Compose | — |
| Hosting (optional) | Render / Railway / Fly.io | Free tiers are sufficient for a portfolio/dev deployment. |

The only real constraints are Gemini's daily request cap and Qdrant Cloud's inactivity auto-suspend — both are workflow considerations, not costs.

---

## Architecture

```
Client → FastAPI Gateway (JWT auth + rate limiting) → Celery Task Queue (Redis)
                                    │
                          ORCHESTRATOR AGENT (LangGraph)
       ┌───────────┬──────────────┬───────────────┬──────────────┐
       ▼           ▼              ▼               ▼              ▼
   RAG Agent   Drug            Trial          Risk /         Report /
  (Gemini +  Interaction     Matching       Safety Agent    Summarizer
   Qdrant)     Agent          Agent        (rule-based +      Agent
              (RxNav +     (ClinicalTrials    LLM review)   (Gemini,
             OpenFDA +        .gov API)                      strictly
             DailyMed)                                       grounded)
       └───────────┴──────────────┴───────────────┴──────────────┘
                                    │
                    Shared Data / Tool Layer
        (Qdrant · Postgres · Redis · external free APIs)
                                    │
                        VALIDATOR / CRITIC AGENT
              (rejects any claim without a traceable source)
                                    │
                   Postgres Result Store + API Response
```

---

## Agents

| Agent | Responsibility |
|---|---|
| **Orchestrator** | Builds the task DAG (LangGraph), throttles Gemini calls to respect free-tier RPM/RPD, merges outputs into a shared `CaseState`. |
| **RAG Retrieval** | Hybrid search (Qdrant vector + metadata filter) over PubMed abstracts and DailyMed labels; returns reranked, cited chunks. |
| **Drug Interaction** | Checks RxNav first (deterministic), cross-references OpenFDA FAERS, falls back to RAG over PubMed only if no structured entry exists. |
| **Clinical Trial Matching** | Queries ClinicalTrials.gov and scores patient/condition text against trial eligibility criteria via embeddings. |
| **Risk / Safety** | Deterministic rule engine for hard stops on contraindicated pairs; LLM only explains the reasoning, never decides. |
| **Report / Summarizer** | Gemini call that strictly formats the already-gathered `CaseState` into Markdown/JSON — cannot introduce new facts. |
| **Validator / Critic** | Final gate — checks every sentence in the draft report against attached sources; rejects or flags anything unsupported. |

---

## RAG Pipeline

**Ingestion** (scheduled weekly via Celery Beat): PubMed/PMC + DailyMed → document loader → metadata tagging (source, drug names, MeSH terms, date) → chunking (~300–500 tokens, ~50 overlap) → embedding (PubMedBERT locally, or Gemini free quota) → upsert into Qdrant, metadata mirrored to Postgres.

**Retrieval** (query time): query → RxNorm synonym expansion → Qdrant vector search + Postgres metadata filter (hybrid) → lightweight rerank (cosine similarity + source-trust weighting, e.g. PubMed > general web) → top-k cited chunks passed to the requesting agent.

A dedicated cross-encoder reranker is intentionally skipped to keep the stack free/lightweight; a simple weighted score is used instead.

---

## Database Schema (Postgres)

```sql
users(id, email, role, created_at)

analysis_requests(id, user_id, query_text, patient_context JSONB,
                   status, created_at, completed_at)

agent_runs(id, request_id, agent_name, input JSONB, output JSONB,
           confidence FLOAT, sources JSONB, started_at, finished_at, status)

drugs(id, rxcui, name, synonyms JSONB)

interactions(id, drug_a_id, drug_b_id, severity, mechanism,
             source TEXT,          -- 'rxnav' | 'openfda' | 'rag_pubmed'
             evidence_url TEXT)

clinical_trials(id, nct_id, title, condition, phase,
                 eligibility_text, status, locations JSONB)

documents(id, source, title, url, published_date, ingested_at)

document_chunks(id, document_id, chunk_text, embedding_id, metadata JSONB)

reports(id, request_id, content_md, citations JSONB,
        risk_score, validated BOOLEAN, created_at)
```

---

## API

```
POST   /api/v1/analyze
       body: { drugs: [...], condition, patient_context }
       → { request_id, status: "queued" }

GET    /api/v1/analyze/{request_id}          → status / progress
GET    /api/v1/analyze/{request_id}/report   → report_md, citations, risk_score

GET    /api/v1/drugs/{name}/interactions
GET    /api/v1/trials/search?condition=&drug=&phase=

GET    /api/v1/health
GET    /api/v1/docs                          → auto Swagger (FastAPI)
```

All analysis runs are async (job + polling/webhook pattern) since Gemini's free-tier RPM limits mean agents often run sequentially rather than in parallel.

---

## Orchestration Flow (LangGraph)

```
parse_query → plan
   → retrieve_context ┐
   → check_interactions├─ sequential / small batches (respect Gemini free RPM)
   → match_trials      ┘
   → assess_risk
   → draft_report
   → validate_report
        ├─ fail → re-run flagged node → validate_report (max 2 retries)
        └─ pass → finalize → persist to Postgres
```

Unlike a paid-LLM design where sub-agents fire in parallel, this orchestrator serializes or lightly batches Gemini calls with exponential backoff on HTTP 429, since Flash's free tier is limited to roughly 10–15 requests/minute.

---

## Project Structure

```
clinical-trial-analyzer/
├── app/
│   ├── main.py
│   ├── api/routes/{analyze.py, drugs.py, trials.py}
│   ├── agents/{orchestrator.py, rag_agent.py, interaction_agent.py,
│   │            trial_matching_agent.py, risk_agent.py,
│   │            report_agent.py, validator_agent.py}
│   ├── rag/{ingestion/, chunking.py, embeddings.py, vector_store.py, retriever.py}
│   ├── integrations/{pubmed_client.py, clinicaltrials_client.py,
│   │                  openfda_client.py, rxnav_client.py, dailymed_client.py,
│   │                  gemini_client.py}
│   ├── models/            # Pydantic + SQLAlchemy
│   ├── db/{session.py, migrations/}
│   ├── tasks/              # Celery tasks
│   ├── core/{config.py, logging.py, security.py, rate_limiter.py}
│   └── tests/
├── docker-compose.yml       # api, worker, redis, postgres, qdrant
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Running Locally

```bash
git clone <repo-url>
cd clinical-trial-analyzer
cp .env.example .env       # add your Gemini API key, DB creds, etc.
docker compose up --build
```

Services started: `api` (FastAPI), `worker` (Celery), `redis`, `postgres`, `qdrant`.

Once running:
- API docs: `http://localhost:8000/api/v1/docs`
- Health check: `http://localhost:8000/api/v1/health`

For a hosted demo, still free: **Render** or **Railway** for `api`/`worker`, **Neon** or **Supabase** for Postgres, **Qdrant Cloud** free tier, and Render's free Redis or **Upstash** for the broker/cache.

---

## Build Roadmap

1. FastAPI skeleton + Postgres schema + Docker Compose, stub `/analyze`.
2. Wire RxNav + OpenFDA + DailyMed clients → Drug Interaction Agent (fully deterministic, no LLM yet).
3. Ingest PubMed abstracts + DailyMed labels → Qdrant → RAG Retrieval Agent.
4. Add Gemini-powered Report Agent + Validator Agent (grounding check).
5. Add Trial Matching Agent (ClinicalTrials.gov) + Risk Agent (rule engine).
6. Wrap everything in the LangGraph Orchestrator with rate-limit-aware sequencing.
7. Add audit logging (`agent_runs`), tests, and optional deployment to free hosting.

---

## Safety Notes

- This is a **decision-support tool**, not a diagnostic or prescribing system.
- Structured, deterministic sources (RxNav/OpenFDA) always outrank LLM-generated interaction claims.
- A full audit trail is kept via `agent_runs` for traceability.
- No real patient identifiers are stored — `patient_context` must contain de-identified attributes only.

---

## License

Add your license of choice here (MIT recommended for a portfolio project).