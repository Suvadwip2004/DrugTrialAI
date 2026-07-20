# Multi-Agent Autonomous Clinical Trial & Drug Interaction Analyzer
## FINAL Backend Design — 100% Free-Stack Architecture

---

## 1. Project Overview

Backend-only (no UI) multi-agent system with RAG that:
- Detects drug-drug interactions with severity + mechanism
- Matches patients/conditions to relevant clinical trials
- Grounds every claim in retrieved sources (RAG), never raw LLM memory
- Produces a structured, cited, risk-scored report
- Runs entirely on free-tier services + open-source self-hosted components

---

## 2. Free-Stack Decisions (locked in)

| Layer | Free Choice | Why |
|---|---|---|
| LLM | **Gemini 2.5 Flash / Flash-Lite** (free tier, no card) | Best free RPM/RPD balance. Avoid Gemini 2.5 Pro free tier — too restrictive (low daily cap) for a multi-agent pipeline. |
| Embeddings | Gemini embedding endpoint (free quota) or self-hosted **PubMedBERT/BioBERT** (open weights, run locally — zero API cost) | Domain-specific embeddings improve retrieval accuracy on clinical text. |
| Vector DB | **Qdrant Cloud free tier** (0.5 vCPU / 1GB RAM / 4GB disk, no card) OR self-hosted Qdrant via Docker | Free forever; self-host if you want to avoid the 1-week auto-suspend on inactivity. |
| Drug interaction data | **RxNav Interaction API (NLM)** + **OpenFDA (FAERS)** + **DailyMed** | Free, public, no license needed — replaces DrugBank entirely. |
| Clinical trials data | **ClinicalTrials.gov API** | Free, public, official. |
| Literature (RAG fallback) | **PubMed / PMC E-utilities** | Free, public, no key required for light use. |
| Relational DB | **PostgreSQL** (self-hosted via Docker, or free tier of Supabase/Neon) | Free self-hosted. |
| Cache / Broker | **Redis** (self-hosted via Docker) | Free self-hosted. |
| Task Queue | **Celery** + Redis broker | Open source. |
| Orchestration | **LangGraph** (open source) | Free, fine-grained agent state control. |
| API Framework | **FastAPI** | Free, open source. |
| Containerization | **Docker + Docker Compose** | Free. |
| Hosting (optional deploy) | Free tiers: **Render**, **Railway**, **Fly.io**, or just run locally | Good enough for a portfolio/dev project. |

**Total cost: $0** for development and light usage. The only thing to watch is Gemini's daily request cap and Qdrant Cloud's inactivity auto-suspend — both are workflow issues, not cost issues.

---

## 3. High-Level Architecture

```
                         ┌───────────────────────────┐
                         │      Client / API Caller    │
                         │   (REST — Postman, script,  │
                         │    future frontend, etc.)    │
                         └─────────────┬─────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │       FastAPI Gateway        │
                         │  Auth (JWT) + Rate Limiting  │
                         └─────────────┬─────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │   Celery Task Queue (Redis)  │
                         │  (async job dispatch)         │
                         └─────────────┬─────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │         ORCHESTRATOR AGENT             │
                    │       (LangGraph StateGraph)           │
                    │  - Parses request → builds task DAG    │
                    │  - Rate-limits calls to Gemini free tier│
                    │  - Dispatches to sub-agents (sequential │
                    │    or small batches to respect RPM)     │
                    └───┬────────┬────────┬────────┬─────────┘
                       │        │        │        │
         ┌──────────────┘  ┌────┘  ┌────┘  ┌────┘──────────────┐
         ▼                 ▼       ▼       ▼                    ▼
┌────────────────┐ ┌──────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐
│ RAG Retrieval  │ │ Drug         │ │ Trial     │ │ Risk /    │ │ Report /    │
│ Agent          │ │ Interaction  │ │ Matching  │ │ Safety    │ │ Summarizer  │
│ (Gemini +      │ │ Agent        │ │ Agent     │ │ Agent     │ │ Agent       │
│  Qdrant)       │ │ (RxNav +     │ │ (Clinical │ │ (rule-    │ │ (Gemini,    │
│                │ │  OpenFDA +   │ │  Trials.  │ │  based +  │ │  strictly   │
│                │ │  DailyMed)   │ │  gov API) │ │  LLM      │ │  grounded)  │
│                │ │              │ │           │ │  review)  │ │             │
└───────┬────────┘ └──────┬───────┘ └─────┬─────┘ └─────┬─────┘ └──────┬──────┘
        │                 │               │             │              │
        ▼                 ▼               ▼             ▼              ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       SHARED DATA / TOOL LAYER                             │
│  Qdrant (vectors) | Postgres (structured) | Redis (cache) |                │
│  RxNav / OpenFDA / DailyMed / ClinicalTrials.gov / PubMed (external, free) │
└───────────────────────────────────────────────────────────────────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │  VALIDATOR / CRITIC AGENT    │
                         │  - Checks every claim has a   │
                         │    traceable source            │
                         │  - Rejects ungrounded output    │
                         └─────────────┬─────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │  Postgres Result Store +     │
                         │  Poll / Webhook Response       │
                         └───────────────────────────┘
```

---

## 4. Agents (final responsibilities)

1. **Orchestrator Agent** — builds the task DAG via LangGraph, throttles Gemini calls to stay under free RPM/RPD, merges agent outputs into shared `CaseState`.
2. **RAG Retrieval Agent** — hybrid search (Qdrant vector + keyword/metadata filter) over PubMed abstracts and DailyMed label text; reranks and returns cited chunks.
3. **Drug Interaction Agent** — checks **RxNav Interaction API first** (deterministic, structured); cross-references **OpenFDA FAERS** for real-world adverse-event signals; falls back to RAG over PubMed only if structured sources have no entry. Outputs severity, mechanism, source.
4. **Clinical Trial Matching Agent** — queries **ClinicalTrials.gov API**; uses embeddings to semantically score patient/condition text against trial eligibility criteria.
5. **Risk / Safety Agent** — deterministic rule engine (hard stop on contraindicated pairs) combined with an LLM pass that explains reasoning in plain language — the *decision* is rule-based, the *explanation* is LLM-assisted.
6. **Report / Summarizer Agent** — Gemini call that strictly summarizes the already-gathered CaseState into Markdown/JSON. Not allowed to introduce new facts.
7. **Validator / Critic Agent** — final gate; checks each sentence in the draft report against the sources attached in CaseState; rejects/flags anything unsupported.

---

## 5. RAG Pipeline (free-stack version)

```
Ingestion (scheduled, e.g. weekly via Celery Beat):
  PubMed/PMC E-utilities  ──┐
  DailyMed label exports  ──┤──▶ Document Loader → Clean/Tag Metadata
                            │      (source, drug names, MeSH terms, date)
                            ▼
                     Chunking (~300–500 tokens, ~50 overlap)
                            ▼
              Embedding (PubMedBERT locally, or Gemini embedding free quota)
                            ▼
                  Upsert into Qdrant (free tier / self-hosted)
                            ▼
              Metadata mirrored into Postgres for hybrid filtering

Retrieval (at query time):
  Query → expand with RxNorm synonyms
        → Qdrant vector search + Postgres metadata filter (hybrid)
        → light rerank (cosine score + recency/source-trust weighting —
          skip a separate cross-encoder reranker to save compute if self-hosting)
        → top-k chunks + citations passed to the requesting agent
```

**Note on rerankers:** a dedicated cross-encoder reranker adds accuracy but also cost/complexity. On a free-tier setup, a simpler weighted score (vector similarity + source authority, e.g. PubMed > general web) is a reasonable free substitute.

---

## 6. Database Schema (Postgres)

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

## 7. API Design

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

Async job pattern throughout — required anyway since Gemini free-tier RPM limits mean multi-agent runs take real wall-clock time (agents often run sequentially, not in parallel, to stay under quota).

---

## 8. Orchestration Flow (LangGraph)

```
parse_query → plan
   → retrieve_context ┐
   → check_interactions├─ (run sequentially or in small batches,
   → match_trials      ┘   NOT all-parallel, to respect Gemini free RPM)
   → assess_risk
   → draft_report
   → validate_report
        ├─ fail → re-run flagged node → validate_report (loop, max 2 retries)
        └─ pass → finalize → persist to Postgres
```

**Free-tier-specific design point:** unlike a paid-LLM design where all sub-agents fire in parallel, this orchestrator should **serialize or lightly batch** Gemini calls with exponential backoff on HTTP 429, since free tier RPM is only 10–15 requests/minute on Flash.

---

## 9. Folder Structure

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

## 10. Deployment (all free)

```yaml
# docker-compose.yml (conceptual)
services:
  api:        # FastAPI
  worker:     # Celery worker
  redis:      # broker + cache
  postgres:   # relational store
  qdrant:     # local free vector DB (or point to Qdrant Cloud free tier instead)
```

For a hosted demo (still free): **Render** or **Railway** free tier for `api`/`worker`, **Neon**/**Supabase** free Postgres, **Qdrant Cloud** free tier, Redis via Render's free Redis or Upstash free tier.

---

## 11. Build Roadmap

1. **Phase 1:** FastAPI skeleton + Postgres schema + Docker Compose, stub `/analyze`.
2. **Phase 2:** Wire RxNav + OpenFDA + DailyMed clients → Drug Interaction Agent (fully deterministic, no LLM needed yet — get this right first).
3. **Phase 3:** Ingest PubMed abstracts + DailyMed labels → Qdrant → RAG Retrieval Agent.
4. **Phase 4:** Add Gemini-powered Report Agent + Validator Agent (grounding check).
5. **Phase 5:** Add Trial Matching Agent (ClinicalTrials.gov) + Risk Agent (rule engine).
6. **Phase 6:** Wrap it all in the LangGraph Orchestrator with rate-limit-aware sequencing.
7. **Phase 7:** Add audit logging (`agent_runs`), tests, and (optionally) deploy to free hosting.

---

## 12. Safety Notes (unchanged, still critical)

- This is a decision-support tool, not a diagnostic/prescribing system.
- Structured deterministic sources (RxNav/OpenFDA) always outrank LLM-generated interaction claims.
- Full audit trail via `agent_runs` for traceability.
- Don't store real patient identifiers — `patient_context` should be de-identified attributes only.

---

**Ready to build.** Say the word and I'll scaffold the actual repo — FastAPI + Docker Compose + Postgres schema + the Drug Interaction Agent fully wired to RxNav/OpenFDA (no LLM needed for this first working slice) as a real, runnable starting codebase.
