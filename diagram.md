# DrugTrialAI - System Architecture & Component Diagrams

This document contains comprehensive visual diagrams representing the architecture, agent pipelines, data flows, validation loops, and scoring engines of the **Multi-Agent Autonomous Clinical Trial & Drug Interaction Analyzer (DrugTrialAI)**.

All diagrams are authored in standard Mermaid syntax for direct rendering in GitHub, Antigravity, and compatible Markdown viewers.

---

## 1. High-Level System Architecture

The following diagram illustrates the layered architecture of DrugTrialAI, spanning from client entrypoints, the multi-agent orchestrator, specialized agent workers, local inference/embedding services, external clinical knowledge sources, and the final validation gateway.

```mermaid
graph TB
    subgraph ClientLayer ["1. Client & Invocation Layer"]
        CLI["CLI Entrypoint (run.py)"]
        API["FastAPI Gateway (Target / Future)"]
    end

    subgraph OrchestrationLayer ["2. Multi-Agent Orchestrator (LangGraph)"]
        Orchestrator["Orchestrator Engine (core_engine/agents/orchestrator.py)"]
        State["Shared State: PipelineState (TypedDict)"]
    end

    subgraph AgentLayer ["3. Specialized Agent Cluster"]
        InteractionAgent["Drug Interaction Agent\n(OpenFDA + RxNav + LLM)"]
        RiskAgent["Risk Assessment Agent\n(Deterministic Rules + LLM)"]
        TrialAgent["Trial Matching Agent\n(ClinicalTrials.gov API v2)"]
        RAGAgent["Literature RAG Agent\n(PubMed + Vector Retrieval)"]
        ReportAgent["Report Assembler Agent\n(Structured Generator + LLM Summary)"]
        ValidatorAgent["Validator & Critic Agent\n(Anti-Hallucination Gate)"]
    end

    subgraph LocalInference ["4. Free Local Inference & Vector Layer"]
        OllamaLLM["Local LLM: Ollama (phi3:mini / llama3.1)"]
        OllamaEmbed["Local Embeddings: nomic-embed-text (768d)"]
        QdrantDB[("Qdrant Vector DB\n(Collection: clinical_documents)")]
    end

    subgraph ExternalSources ["5. External Public APIs ($0 Free Tier)"]
        RxNavAPI["NLM RxNav REST API\n(RxCUI resolution)"]
        OpenFDAAPI["OpenFDA Drug Label API\n(Official Package Inserts)"]
        ClinTrialsAPI["ClinicalTrials.gov REST API v2\n(Active Studies & Protocols)"]
        PubMedAPI["NCBI Entrez E-Utilities\n(ESearch + EFetch XML)"]
    end

    subgraph OutputLayer ["6. Verified Deliverables & Audit Trail"]
        ReportMD["report.md (Clinician Markdown Report)"]
        ReportJSON["report.json (Audit Trail & Structured Payload)"]
    end

    %% Invocations
    CLI --> Orchestrator
    API -.-> Orchestrator
    Orchestrator <--> State

    %% Orchestrator to Agents
    Orchestrator --> InteractionAgent
    Orchestrator --> RiskAgent
    Orchestrator --> TrialAgent
    Orchestrator --> RAGAgent
    Orchestrator --> ReportAgent
    Orchestrator --> ValidatorAgent

    %% Agent External & Local Connections
    InteractionAgent --> RxNavAPI
    InteractionAgent --> OpenFDAAPI
    InteractionAgent --> OllamaLLM

    RiskAgent --> OllamaLLM

    TrialAgent --> ClinTrialsAPI

    RAGAgent --> QdrantDB
    RAGAgent --> OllamaEmbed
    RAGAgent --> OllamaLLM

    ReportAgent --> OllamaLLM

    %% Validation to outputs
    ValidatorAgent --> Orchestrator
    Orchestrator --> ReportMD
    Orchestrator --> ReportJSON
```

---

## 2. LangGraph Execution DAG & Validation Retry Loop

The orchestrator executes agents in a deterministic sequence to respect local compute constraints (one Ollama instance). If the output fails semantic and factual validation, it loops back to regenerate the report (up to 2 LLM attempts) before falling back to a deterministic summary.

```mermaid
stateDiagram-v2
    [*] --> check_interactions: Start pipeline with drugs, condition, patient_context

    state "Stage 1: check_interactions" as check_interactions
    note right of check_interactions
        Resolves RxCUIs via RxNav.
        Fetches FDA label interaction text.
        Extracts interactions via LLM & verifies quotes.
    end note

    state "Stage 2: assess_risk" as assess_risk
    note right of assess_risk
        Calculates deterministic composite risk score (0-10).
        Applies age, renal, hepatic & comorbidity weights.
        Checks for hard stop (contraindications).
        Generates LLM clinician explanation.
    end note

    state "Stage 3: find_trials" as find_trials
    note right of find_trials
        Searches ClinicalTrials.gov for condition/interventions.
        Filters by recruitment status & phase.
        Extracts eligibility & arm protocols.
    end note

    state "Stage 4: search_literature" as search_literature
    note right of search_literature
        Embeds clinical query with nomic-embed-text.
        Retrieves top PubMed chunks from Qdrant.
        Answers question with strict in-context citations.
        Sanitizes invalid citations.
    end note

    state "Stage 5: write_report" as write_report
    note right of write_report
        Constructs factual sections directly from agent data.
        Generates executive summary (LLM or deterministic fallback).
        Appends mandatory decision-support disclaimer.
    end note

    state "Stage 6: validate" as validate
    note right of validate
        Runs 8-step deterministic audit suite.
        Checks trial NCT IDs, numbers, risk level,
        drug names, and citation validity.
    end note

    check_interactions --> assess_risk
    assess_risk --> find_trials
    find_trials --> search_literature
    search_literature --> write_report
    write_report --> validate

    state ValidationDecision <<choice>>
    validate --> ValidationDecision

    ValidationDecision --> [*]: Passed == True (Emit report.md & report.json)
    ValidationDecision --> write_report: Passed == False & attempts < 2 (Retry LLM summary)
    ValidationDecision --> write_report: Passed == False & attempts >= 2 (Fallback deterministic summary)
    ValidationDecision --> [*]: Validation failed after fallback (Emit report with loud Warning Banner)
```

---

## 3. Data Flow & Shared State Lifecycle (`PipelineState`)

This sequence diagram details how the shared `PipelineState` TypedDict evolves across all execution stages.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / CLI (run.py)
    participant Orch as Orchestrator (LangGraph)
    participant InterAgent as Interaction Agent
    participant RiskAg as Risk Agent
    participant TrialAg as Trial Matching Agent
    participant RAGAg as RAG Agent
    participant RepAg as Report Agent
    participant ValAg as Validator Agent

    User->>Orch: run_pipeline(drugs, condition, patient_context, phases)
    Note over Orch: Initialise PipelineState<br/>{drugs, condition, patient_context, phases, report_attempts: 0}

    %% Stage 1
    Orch->>InterAgent: node_check_interactions(state)
    InterAgent-->>Orch: {interactions: [...], stage_errors: [...]}
    Note over Orch: PipelineState["interactions"] updated

    %% Stage 2
    Orch->>RiskAg: node_assess_risk(state)
    RiskAg-->>Orch: {risk: {composite_risk_score, risk_level, hard_stop, explanation, ...}}
    Note over Orch: PipelineState["risk"] updated

    %% Stage 3
    Orch->>TrialAg: node_find_trials(state)
    TrialAg-->>Orch: {trials: [{nct_id, title, status, phase, ...}]}
    Note over Orch: PipelineState["trials"] updated

    %% Stage 4
    Orch->>RAGAg: node_search_literature(state)
    RAGAg-->>Orch: {literature: {question, answer, grounded, cited_sources, ...}}
    Note over Orch: PipelineState["literature"] updated

    %% Stage 5
    loop Up to 2 LLM Retries + 1 Fallback
        Orch->>RepAg: node_write_report(state)
        RepAg-->>Orch: {report: {report_md, summary, citations}, report_attempts: n+1}
        Note over Orch: PipelineState["report"] updated

        %% Stage 6
        Orch->>ValAg: node_validate(state)
        ValAg-->>Orch: {validation: {passed, errors, warnings, checks}}
        Note over Orch: PipelineState["validation"] evaluated
    end

    Orch->>User: Return final validated payload (writes report.md & report.json)
```

---

## 4. Drug Interaction & Grounded Evidence Verification Pipeline

To eliminate hallucinations, the Interaction Agent refuses to rely solely on generative LLM memory. It queries official FDA drug labels via OpenFDA and verifies that any finding quotes real text from the label.

```mermaid
flowchart TD
    Start(["Input: Drug A, Drug B"]) --> RxCUI["RxNav API: get_rxcuis([Drug A, Drug B])"]
    RxCUI --> OpenFDA["OpenFDA API: Fetch 'drug_interactions' section for Drug A & Drug B"]

    OpenFDA --> CheckLabels{"Are labels available for both drugs?"}

    CheckLabels -- "Neither available" --> UnknownResult["Set severity: 'unknown'<br/>interaction_found: False<br/>confidence: 0.0"]
    CheckLabels -- "At least one available" --> Truncate["Cap text to MAX_LABEL_CHARS (8,000 chars per drug)"]

    Truncate --> PromptLLM["Prompt Ollama (format='json'):<br/>Detect direct interaction or drug CLASS matches<br/>(e.g., 'oral anticoagulants', 'statins')"]

    PromptLLM --> ParseJSON{"Valid JSON returned?"}
    ParseJSON -- "No / Parse Failure" --> UnknownResult

    ParseJSON -- "Yes" --> CheckFlag{"interaction_found == true?"}

    CheckFlag -- "False" --> NormalizeNone["Force severity: 'none'<br/>mechanism: ''<br/>description: ''<br/>confidence: clamped [0.0, 1.0]"]

    CheckFlag -- "True" --> CheckQuote{"Is evidence_quote supplied<br/>and >= 15 chars?"}
    CheckQuote -- "No" --> DowngradeUnknown["Downgrade severity to 'unknown'<br/>interaction_found: False<br/>Mark as unverified"]

    CheckQuote -- "Yes" --> QuoteInLabel{"Does quote exist in label text?<br/>(_quote_is_supported with whitespace/quote normalization)"}
    QuoteInLabel -- "No (Hallucinated quote)" --> DowngradeUnknown
    QuoteInLabel -- "Yes (Genuine quote)" --> VerifiedResult["Keep finding:<br/>interaction_found: True<br/>severity: validated severity<br/>evidence: exact quote<br/>source: 'openfda+llm'"]

    NormalizeNone --> Output(["Final Interaction Record"])
    DowngradeUnknown --> Output
    UnknownResult --> Output
    VerifiedResult --> Output
```

---

## 5. Clinical Trial Semantic Search Pipeline

The trial matching pipeline interfaces with ClinicalTrials.gov API v2, filtering active studies and parsing protocol sections.

```mermaid
flowchart LR
    subgraph QueryConstruction ["1. Query Construction"]
        InputCond["Condition (e.g. 'Atrial Fibrillation')"]
        InputInterv["Interventions / Drugs (e.g. 'Warfarin')"]
        InputPhases["Phases Filter (e.g. PHASE2, PHASE3)"]
        InputStatus["Overall Status (Default: RECRUITING)"]
    end

    subgraph APIRequest ["2. ClinicalTrials.gov API v2"]
        Endpoint["GET https://clinicaltrials.gov/api/v2/studies"]
        Params["params: query.cond, filter.advanced (AREA[Phase]), filter.overallStatus"]
    end

    subgraph ProtocolParsing ["3. Study Protocol Normalization"]
        RawJSON["Raw Studies Payload"]
        IDMod["identificationModule (nctId, briefTitle)"]
        StatusMod["statusModule (overallStatus)"]
        DesignMod["designModule (phases, studyType)"]
        CondMod["conditionsModule (conditions)"]
        EligMod["eligibilityModule (criteria, min/max age, sex)"]
        ArmsMod["armsInterventionsModule (interventions)"]
    end

    subgraph PatientScoring ["4. Eligibility & Scoring Engine"]
        MatchScore["Eligibility Score Calculation"]
        InclusionCheck["Inclusion / Exclusion Analysis"]
        StructuredTrial["Structured Trial Object\n{nct_id, title, status, phase, eligibility_match_score, reason}"]
    end

    InputCond --> Params
    InputInterv --> Params
    InputPhases --> Params
    InputStatus --> Params
    Params --> Endpoint
    Endpoint --> RawJSON

    RawJSON --> IDMod & StatusMod & DesignMod & CondMod & EligMod & ArmsMod
    IDMod & StatusMod & DesignMod & CondMod & EligMod & ArmsMod --> MatchScore
    MatchScore --> InclusionCheck --> StructuredTrial
```

---

## 6. RAG Subsystem: Ingestion & Hybrid Retrieval Pipeline

The RAG architecture supports scheduled offline ingestion from PubMed and real-time retrieval for clinical literature queries.

```mermaid
flowchart TD
    subgraph IngestionPipeline ["A. Ingestion Pipeline (pubmed_ingest.py)"]
        SearchTerm["Query Search Term (e.g. 'warfarin amoxicillin')"] --> ESearch["NCBI ESearch (esearch.fcgi)"]
        ESearch --> PMIDs["Matching PMIDs"]
        PMIDs --> EFetch["NCBI EFetch (efetch.fcgi XML)"]
        EFetch --> XMLParse["XML Parser (title, abstract, journal, year)"]
        XMLParse --> TextCombine["Full Text = Title + Abstract"]
        TextCombine --> SpacyChunk["spaCy Sentence Splitter\n(300 words chunk, 50 words overlap)"]
        SpacyChunk --> DeterministicUUID["Deterministic UUID5 (pubmed:pmid:index)"]
        DeterministicUUID --> LocalEmbed["Ollama nomic-embed-text (768d vectors)"]
        LocalEmbed --> BatchUpsert["Qdrant Batch Upsert\n(Collection: clinical_documents)"]
    end

    subgraph RetrievalPipeline ["B. Real-Time Retrieval Pipeline (retriever.py / rag_agent.py)"]
        UserQuery["Clinical Question + Drug Names Context"] --> EmbedQuery["Ollama nomic-embed-text: Embed Query"]
        EmbedQuery --> QdrantSearch["Qdrant Cosine Similarity Search\n(Filter: source=='pubmed', min_score=0.0)"]
        QdrantSearch --> TopChunks["Top K Chunks (title, url, text, score)"]
        TopChunks --> NumberedContext["Format Numbered Context:\n[1] Title (URL)\nChunk Text..."]
        NumberedContext --> LLMPrompt["LLM Grounded Prompting:\nAnswer using ONLY numbered sources"]
        LLMPrompt --> ExtractCites["Extract & Verify Citations:\nvalid: [1..k], invalid: [>k or <1]"]
        ExtractCites --> GroundedCheck{"Invalid citations present?"}
        GroundedCheck -- "Yes" --> DiscardAnswer["Discard answer:\n'cited sources were not retrieved'"]
        GroundedCheck -- "No" --> GroundedOutput["Grounded Answer + Verified Bibliography"]
    end

    BatchUpsert -.-> QdrantSearch
```

---

## 7. Deterministic Risk Scoring Engine Decision Matrix

Risk calculation separates deterministic medical safety scoring from generative language synthesis. The LLM only explains the score; it is mathematically prevented from calculating or modifying it.

```mermaid
flowchart TD
    subgraph InteractionScoring ["1. Interaction Severity Weights"]
        Contra["Contraindicated: +10.0 pts (HARD STOP)"]
        Major["Major: +6.0 pts"]
        Moderate["Moderate: +3.0 pts"]
        Minor["Minor: +1.0 pts"]
        UnknownSev["Unknown: +1.5 pts"]
        NoneSev["None: +0.0 pts"]
    end

    subgraph PatientContextScoring ["2. Patient Risk Modifiers"]
        AgeCheck{"Age >= 65?"}
        AgeCheck -- "Yes" --> AgePts["+1.0 pt (Age factor)"]
        AgeCheck -- "No" --> AgeZero["+0.0 pts"]

        RenalCheck{"Renal Impairment"}
        RenalCheck -->|mild| RenMild["+0.5 pts"]
        RenalCheck -->|moderate| RenMod["+1.5 pts"]
        RenalCheck -->|severe| RenSev["+3.0 pts"]
        RenalCheck -->|normal| RenNorm["+0.0 pts"]

        HepaticCheck{"Hepatic Impairment"}
        HepaticCheck -->|mild| HepMild["+0.5 pts"]
        HepaticCheck -->|moderate| HepMod["+1.5 pts"]
        HepaticCheck -->|severe| HepSev["+3.0 pts"]
        HepaticCheck -->|normal| HepNorm["+0.0 pts"]

        ComorbCheck["Comorbidities Count"]
        ComorbCheck --> ComorbPts["+0.5 pts per comorbidity\n(Hard Capped at 2.0 pts)"]
    end

    subgraph ScoreAggregation ["3. Score Aggregation & Risk Tiering"]
        Sum["Raw Score = Sum of all weights"]
        ClampScore["Composite Risk Score = min(Raw Score, 10.0)"]

        TierDecision{"Score Range"}
        TierDecision -->|Score >= 8.0 or Hard Stop| TierCritical["Level: CRITICAL"]
        TierDecision -->|6.0 <= Score < 8.0| TierElevated["Level: ELEVATED"]
        TierDecision -->|3.0 <= Score < 6.0| TierModerate["Level: MODERATE"]
        TierDecision -->|Score < 3.0| TierLow["Level: LOW"]
    end

    subgraph ExplanationSynthesis ["4. LLM Explanation Layer"]
        PromptSynth["LLM Prompt: Explain WHY score is X based ONLY on structured factors"]
        FinalRisk["Final Risk Assessment Object\n{composite_risk_score, risk_level, hard_stop, contributing_factors, explanation}"]
    end

    InteractionScoring --> Sum
    AgePts & AgeZero & RenMild & RenMod & RenSev & RenNorm & HepMild & HepMod & HepSev & HepNorm & ComorbPts --> Sum
    Sum --> ClampScore --> TierDecision
    TierCritical & TierElevated & TierModerate & TierLow --> PromptSynth
    PromptSynth --> FinalRisk
```

---

## 8. Validator Agent & Anti-Hallucination Gate

Every generated report must pass an 8-rule deterministic validation gate before release. If any hard check fails, the report is rejected and routed back to the orchestrator for regeneration.

```mermaid
flowchart TD
    DraftReport["Input: Draft report_md + Raw Pipeline State Data"] --> VSuite["Validator Audit Suite (validator_agent.py)"]

    subgraph Checks ["8 Deterministic Validation Checks"]
        C1{"1. Structure Check:\nAre all 5 required headings present?\nIs medical disclaimer present?"}
        C2{"2. NCT ID Whitelist:\nDoes every NCTxxxxxx in report\nexist in retrieved trial data?"}
        C3{"3. Number Grounding:\nDo all numbers in Summary exist in\nsource text, trial counts, or interaction totals?"}
        C4{"4. Risk Level Alignment:\nDoes the stated risk level match\nactual risk_level exactly?"}
        C5{"5. Hard-Stop Consistency:\nDoes contraindication mention in summary\nalign with hard_stop flag?"}
        C6{"6. Drug Name Whitelist:\nDo drug name suffixes in summary\nappear in input drug list?"}
        C7{"7. Pair Completeness:\nIs every requested drug interaction\npair explicitly reported in Markdown?"}
        C8{"8. Citation Integrity:\nAre all [n] literature citations valid\nand traceable to retrieved URLs?"}
    end

    VSuite --> C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7 --> C8

    C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 -- "Any Hard Check Fails" --> Fail["passed: False\nRecord specific error strings in validation['errors']"]
    C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 -- "All Hard Checks Pass" --> Pass["passed: True\nRecord non-blocking items in validation['warnings']"]

    Fail --> RouteAction{"Action:"}
    RouteAction -->|attempts < 2| Regenerate["Regenerate report with LLM Summary"]
    RouteAction -->|attempts >= 2| Fallback["Apply Deterministic Summary Fallback"]
    RouteAction -->|Fallback fails| Banner["Attach Loud Warning Banner:\n'VALIDATION FAILED — do not rely on this report'"]

    Pass --> Release["Release clean report.md & report.json"]
```
