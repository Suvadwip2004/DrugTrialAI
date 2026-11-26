# DrugTrialAI Frontend

React + JavaScript + Vite + Tailwind CSS v4 frontend for the **DrugTrialAI** FastAPI backend (`backend/`).

## Features

- **Multi-Agent Case Analysis (`POST /api/v1/analyze`):**
  - Horizontal clinical regimen & patient profile input bar (drugs, primary condition, age, sex, renal/hepatic impairment, comorbidities, trial phases) with quick presets and local analysis history.
  - 6-stage LangGraph pipeline progress indicator with live elapsed timer.
  - 8-point anti-hallucination audit panel (`validated`, checks grid, errors, warnings, stage isolation notes).
  - Deterministic composite risk gauge (`0.0 - 10.0`), hard-stop alert banner, and contributing factors.
  - Pairwise drug interaction cards with RxCUIs, confidence score, mechanism, and verbatim OpenFDA label evidence quotes.
  - Clinical trial match cards sorted by eligibility score with direct ClinicalTrials.gov links and exclusion concerns.
  - PubMed Hybrid RAG literature evidence and citation audit list.
  - Rendered Markdown report, raw `report.md`, and audit `report.json` viewer/downloader.
- **DDI & FDA Label Explorer:**
  - Direct pairwise DDI check (`POST /api/v1/drugs/interactions`).
  - NLM RxNav RxCUI lookup (`GET /api/v1/drugs/{drug_name}/rxcui`) and OpenFDA package insert viewer (`GET /api/v1/drugs/{drug_name}/label`).
- **Clinical Trials Search (`GET /api/v1/trials/search`):**
  - Search ClinicalTrials.gov v2 directly by condition, intervention, phase, and recruitment status.
- **Live Service Health Bar (`GET /api/v1/health`):**
  - Displays Backend API, Ollama LLM, and Qdrant Vector DB connectivity and allows overriding the API base URL.

## Running Locally

1. Start the FastAPI backend from the project root:
   ```bash
   uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Install dependencies and start the frontend dev server from `frontend/`:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173).

   Vite proxies `/api/*` requests to `http://localhost:8000` by default. You can also set `VITE_API_BASE_URL` or configure the API URL directly in the header settings button.
