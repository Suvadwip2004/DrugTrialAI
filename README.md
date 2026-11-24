# DrugTrialAI: Multi-Agent Autonomous Clinical Trial & Drug Interaction Analyzer

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/uv-fast-blueviolet.svg)](https://docs.astral.sh/uv/)
[![Orchestration](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Vector DB](https://img.shields.io/badge/Qdrant-Vector%20Search-red.svg)](https://qdrant.tech/)
[![Inference](https://img.shields.io/badge/Ollama-llama3.2%3A3b-black.svg)](https://ollama.ai/)
[![Tests](https://img.shields.io/badge/pytest-51%20passed-brightgreen.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An autonomous, multi-agent clinical decision-support system that detects drug-drug interactions, evaluates clinical trial eligibility, and generates structured, audit-ready reports. Built on a **100% free, local-first stack** utilizing LangGraph, Ollama (`llama3.2:3b`), Qdrant, and authoritative public federal APIs (RxNav, OpenFDA, ClinicalTrials.gov, PubMed, and DailyMed).

> **Medical & Decision-Support Disclaimer:**  
> DrugTrialAI is a decision-support and research reference tool, not a diagnostic, prescribing, or clinical treatment system. Safety-critical decisions are guarded by deterministic rule engines and source-grounded verification.

---

## Key Features

- **Grounded Drug-Drug Interaction (DDI) Detection:** Identifies mechanism, clinical significance, and severity between co-prescribed drugs using RxNav ontologies and official OpenFDA package inserts.
- **Exact FDA Label Quote Verification:** Refuses to trust raw LLM memory. The model must provide verbatim quotes from retrieved FDA labels, which are verified in Python before being accepted as evidence.
- **Clinical Trial Semantic Matching:** Queries live human studies on ClinicalTrials.gov v2 and evaluates patient profiles (age, organ function, comorbidities) against protocol eligibility criteria.
- **Deterministic Risk Scoring:** A mathematical rules engine computes composite risk scores ($0.0 - 10.0$) and enforces hard stops for contraindicated combinations. The LLM explains the reasoning in plain English but is mathematically prevented from deciding the score.
- **Hybrid RAG Literature Retrieval:** Uses spaCy sentence boundary chunking with sliding-window overlap and 768-dimensional local embeddings (`nomic-embed-text`) stored in Qdrant to retrieve PubMed abstracts.
- **10-Point Deterministic Validator Gate:** Audits generated reports against raw source data, verifying trial NCT IDs, numbers, risk tiers, and citation integrity. If validation fails, an automatic retry and deterministic fallback loop ensures the report is never released corrupted.
- **Full Audit Trail:** Emits a clinician-friendly Markdown report (`report.md`) alongside a complete JSON audit payload (`report.json`) logging intermediate agent outputs and confidence scores.

---

## System Architecture

DrugTrialAI coordinates 6 specialized agents via a compiled **LangGraph** `StateGraph`:

```
                       ┌─────────────────────────┐
                       │   CLI Entry (run.py)    │
                       └────────────┬────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH ORCHESTRATOR PIPELINE                        │
│                                                                           │
│  Stage 1: check_interactions ──▶ OpenFDA Label Scraping + RxNav RxCUIs   │
│                 │                                                         │
│                 ▼                                                         │
│  Stage 2: assess_risk        ──▶ Deterministic Scoring Engine (0-10)      │
│                 │                                                         │
│                 ▼                                                         │
│  Stage 3: find_trials        ──▶ ClinicalTrials.gov v2 + Matching LLM     │
│                 │                                                         │
│                 ▼                                                         │
│  Stage 4: search_literature  ──▶ Qdrant Hybrid RAG + PubMed Ingestion     │
│                 │                                                         │
│                 ▼                                                         │
│  Stage 5: write_report       ──▶ Structured Builder + LLM Summary ◀──┐    │
│                 │                                                    │    │
│                 ▼                                                    │    │
│  Stage 6: validate           ──▶ 10-Check Audit Gate                 │    │
│                 │                     │                              │    │
│                 │                     └── [Fail: Retries < 2] ───────┘    │
│                 ▼                                                         │
│          [Pass / Fallback] ──▶ report.md & report.json                    │
└───────────────────────────────────────────────────────────────────────────┘
```

Detailed visual architecture and sequence diagrams are available in [diagram.md](diagram.md).

---

## Multi-Agent Cluster

| Agent | Responsibility | Knowledge & Tool Sources |
|---|---|---|
| **Orchestrator** | Manages `PipelineState`, stage error isolation, and validation retry loops. | `core_engine/agents/orchestrator.py` |
| **Interaction Agent** | Resolves RxCUIs, parses FDA label sections, and validates quoted evidence. | NLM RxNav, OpenFDA Drug Labels, Ollama |
| **Risk Assessment Agent** | Deterministic arithmetic scoring (age, renal/hepatic impairment, comorbidities, hard stops). | Deterministic Engine + Ollama explanation |
| **Trial Matching Agent** | Queries active clinical trials, extracts protocol modules, and scores eligibility. | ClinicalTrials.gov REST API v2, Ollama |
| **Literature RAG Agent** | Embeds queries, queries Qdrant vector store, and enforces in-context citation verification. | PubMed E-Utilities, Qdrant, nomic-embed-text |
| **Report Agent** | Assembles code-generated factual sections and prompts LLM for executive summaries. | Internal State, Deterministic Fallbacks |
| **Validator Agent** | Final compliance gate: checks numbers, NCT IDs, risk alignment, and drug names. | Deterministic Python Verification Suite |

---

## Tech Stack ($0 Free-Tier)

- **Language & Runtime:** Python `>=3.13` managed with [`uv`](https://docs.astral.sh/uv/)
- **Agent Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph)
- **Local LLM Inference:** [Ollama](https://ollama.ai/) (`llama3.2:3b` default)
- **Vector Database:** [Qdrant](https://qdrant.tech/) (`clinical_documents` collection, 768d cosine)
- **Embeddings:** `nomic-embed-text` via Ollama
- **Text Processing & Chunking:** [spaCy](https://spacy.io/) (`en_core_web_sm`)
- **Data Integrations:**
  - [NLM RxNav REST API](https://rxnav.nlm.nih.gov/) (RxCUI resolution)
  - [OpenFDA Drug Label API](https://open.fda.gov/) (Official FDA package inserts)
  - [ClinicalTrials.gov API v2](https://clinicaltrials.gov/) (Human study protocols)
  - [NCBI Entrez E-Utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) (PubMed abstracts)
  - [NLM DailyMed REST API v2](https://dailymed.nlm.nih.gov/) (SPL metadata)
- **Validation & Schemas:** Pydantic v2
- **Testing:** `pytest` & `pytest-asyncio`

---

## Project Structure

```
DrugTrialAI/
├── core_engine/
│   ├── agents/
│   │   ├── orchestrator.py           # LangGraph DAG & pipeline loop
│   │   ├── interaction_agent.py      # DDI detection & quote verification
│   │   ├── risk_agent.py             # Deterministic scoring (0-10) & explanation
│   │   ├── trial_matching_agent.py   # ClinicalTrials.gov eligibility scoring
│   │   ├── rag_agent.py              # Grounded PubMed literature Q&A
│   │   ├── report_agent.py           # Report builder & fallback summary
│   │   └── validator_agent.py        # 10-point anti-hallucination gate
│   ├── integrations/
│   │   ├── rxnav_client.py           # RxNav RxCUI resolution
│   │   ├── openfda_client.py         # FDA package insert scraping
│   │   ├── clinicaltrials_client.py  # ClinicalTrials.gov v2 search
│   │   ├── pubmed_client.py          # NCBI PubMed ESearch & EFetch
│   │   ├── pubmed_ingest.py          # Batch literature ingestion pipeline
│   │   ├── dailymed_client.py        # DailyMed SPL client
│   │   └── llm_client.py             # Ollama chat & structured JSON client
│   ├── rag/
│   │   ├── chunking.py               # spaCy sentence chunker with overlap
│   │   ├── embeddings.py             # nomic-embed-text embedding client
│   │   ├── vector_store.py           # Qdrant client & collection lifecycle
│   │   └── retriever.py              # Cosine similarity retrieval
│   ├── models/
│   │   └── schemas.py                # Pydantic v2 request/response models
│   └── config.py                     # Centralized settings & environment variables
├── tests/
│   ├── test_interaction_agent.py     # 37 unit tests for quote verification & extraction
│   ├── test_risk_agent.py            # 9 unit tests for risk math & organ weighting
│   └── test_validator_agent.py       # 5 unit tests for validation & hallucination checks
├── diagram.md                        # Complete Mermaid architectural diagrams
├── project_report.md                 # Detailed project audit & status report
├── run.py                            # CLI analysis runner
├── main.py                           # Programmatic demo runner
├── pyproject.toml                    # Dependencies & pytest configuration
└── README.md
```

---

## Getting Started

### 1. Prerequisites

1. **Install [`uv`](https://docs.astral.sh/uv/):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Start Ollama and Pull Required Models:**
   ```bash
   ollama serve
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```

3. **Start Qdrant (Docker or Local):**
   ```bash
   docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
   ```

### 2. Installation

Clone the repository and install dependencies using `uv`:

```bash
git clone https://github.com/Suvadwip2004/DrugTrialAI.git
cd DrugTrialAI
uv sync
```

Download the lightweight spaCy English model:
```bash
uv run python -m spacy download en_core_web_sm
```

### 3. Environment Configuration

Create or update your `.env` file in the project root:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
QDRANT_URL=http://localhost:6333
# Optional: NCBI Entrez API Key for higher rate limits
NCBI_API_KEY=
NCBI_EMAIL=your_email@example.com
```

---

## Running the System

### A. CLI Analysis Runner (`run.py`)

Execute an analysis with customizable drugs, clinical conditions, and patient parameters:

```bash
uv run python run.py \
    --drugs Warfarin Amoxicillin \
    --condition "Atrial Fibrillation" \
    --age 68 \
    --renal-function moderate_impairment \
    --comorbidities "Hypertension" "Chronic Kidney Disease"
```

**Options:**
- `--drugs`: List of drug names (e.g. `Warfarin Amoxicillin Aspirin`)
- `--condition`: Condition for clinical trial search (e.g. `"Atrial Fibrillation"`)
- `--age`: Patient age in years
- `--renal-function`: `normal`, `mild_impairment`, `moderate_impairment`, `severe_impairment`
- `--hepatic-function`: `normal`, `mild_impairment`, `moderate_impairment`, `severe_impairment`
- `--comorbidities`: Additional diagnosed conditions
- `--phases`: Filter trial phases (e.g. `PHASE2 PHASE3`)

Upon completion, the pipeline outputs:
- **`report.md`**: Clinician-facing Markdown decision-support report.
- **`report.json`**: Structured audit trail containing agent payloads, citations, and validation checks.

### B. Programmatic Demo Runner (`main.py`)

Run the preconfigured demonstration:

```bash
uv run python main.py
```

### C. Ingest Literature into Qdrant

Ingest PubMed abstracts for specific clinical domains or drug combinations:

```bash
uv run python -m core_engine.integrations.pubmed_ingest \
    --query "warfarin amoxicillin interaction" \
    --drugs Warfarin Amoxicillin \
    --max-results 10
```

---

## Running Tests

DrugTrialAI includes a comprehensive unit test suite covering DDI quote validation, deterministic risk arithmetic, and anti-hallucination validation rules:

```bash
uv run pytest tests/
```

**Test Output:**
```text
tests/test_interaction_agent.py .....................................    [ 72%]
tests/test_risk_agent.py .........                                       [ 90%]
tests/test_validator_agent.py .....                                      [100%]

============================== 51 passed in 0.32s ==============================
```

---

## Sample Generated Report (`report.md`)

```markdown
# Drug Interaction & Clinical Trial Report

**Drugs:** Warfarin, Amoxicillin
**Condition:** Atrial Fibrillation
**Patient context:** age: 68, renal function: moderate_impairment

> **Decision-support only.** This report summarizes retrieved FDA label text, published literature and registered trials. It is not medical advice and does not replace clinical judgment.

## Summary
For patients with atrial fibrillation, the use of Warfarin and Amoxicillin is associated with a moderate risk level of 3.5/10. The interaction between Warfarin and Amoxicillin is considered minor. Age 68 is an independent risk factor for increased risk, and moderate renal impairment also carries an increased risk.

## Drug Interaction Findings
- **Warfarin + Amoxicillin** — severity: **minor** (confidence 0.80)
  - Mechanism: Amoxicillin and oral anticoagulants may increase the prolongation of prothrombin time.
  - Clinical note: Taking amoxicillin with oral anticoagulants may prolong prothrombin time, which can increase the risk of bleeding.
  - Label evidence: "Abnormal prolongation of prothrombin time (increased international normalized ratio [INR]) has been reported in patients receiving amoxicillin and oral anticoagulants."
  - Source: openfda+llm

## Risk Assessment
- **Risk level:** moderate
- **Composite score:** 3.5 / 10
- **Contributing factors:**
  - Age 68 is an independent risk factor (≥65)
  - Renal function: moderate_impairment

## Matching Clinical Trials
- **[NCT05353140](https://clinicaltrials.gov/study/NCT05353140)** — LAAO Versus NOAC in Patients with AF and PCI
  - Phase: NA | Status: RECRUITING | Eligibility match: 0.50
  - Why: The patient's renal function is a concern for exclusion criterion 14 (Severe renal insufficiency), but the patient's age and other conditions do not clearly indicate eligibility.
  - Possible exclusions: Severe renal insufficiency (CrCl≤30ml/min)

## Literature Evidence
No relevant literature was found in the knowledge base.
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
