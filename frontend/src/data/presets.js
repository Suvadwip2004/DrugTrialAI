export const CLINICAL_PRESETS = [
  {
    id: 'afib-warfarin',
    label: 'AFib + Anticoagulation',
    subtitle: 'Warfarin + Amoxicillin (68y, Moderate CKD)',
    request: {
      drugs: ['Warfarin', 'Amoxicillin'],
      condition: 'Atrial Fibrillation',
      patient_context: {
        age: 68,
        sex: 'male',
        renal_function: 'moderate_impairment',
        hepatic_function: 'normal',
        comorbidities: ['Chronic Kidney Disease Stage 3', 'Hypertension'],
      },
      phases: ['PHASE2', 'PHASE3'],
    },
  },
  {
    id: 'acs-dapt',
    label: 'ACS + Antiplatelet + PPI',
    subtitle: 'Clopidogrel + Omeprazole + Aspirin',
    request: {
      drugs: ['Clopidogrel', 'Omeprazole', 'Aspirin'],
      condition: 'Acute Coronary Syndrome',
      patient_context: {
        age: 64,
        sex: 'female',
        renal_function: 'mild_impairment',
        hepatic_function: 'normal',
        comorbidities: ['Coronary Artery Disease', 'GERD'],
      },
      phases: ['PHASE3', 'PHASE4'],
    },
  },
  {
    id: 'statin-macrolide',
    label: 'Hyperlipidemia + Infection',
    subtitle: 'Atorvastatin + Clarithromycin',
    request: {
      drugs: ['Atorvastatin', 'Clarithromycin'],
      condition: 'Hyperlipidemia',
      patient_context: {
        age: 72,
        sex: 'male',
        renal_function: 'normal',
        hepatic_function: 'mild_impairment',
        comorbidities: ['Type 2 Diabetes', 'Hypertension'],
      },
      phases: ['PHASE2', 'PHASE3'],
    },
  },
];

export const ORGAN_FUNCTION_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'mild_impairment', label: 'Mild Impairment (+0.5 pts)' },
  { value: 'moderate_impairment', label: 'Moderate Impairment (+1.5 pts)' },
  { value: 'severe_impairment', label: 'Severe Impairment (+3.0 pts)' },
];

export const PHASE_OPTIONS = [
  { value: 'EARLY_PHASE1', label: 'Early Phase 1' },
  { value: 'PHASE1', label: 'Phase 1' },
  { value: 'PHASE2', label: 'Phase 2' },
  { value: 'PHASE3', label: 'Phase 3' },
  { value: 'PHASE4', label: 'Phase 4' },
  { value: 'NA', label: 'N/A' },
];

export const TRIAL_STATUS_OPTIONS = [
  { value: 'RECRUITING', label: 'Recruiting' },
  { value: 'NOT_YET_RECRUITING', label: 'Not Yet Recruiting' },
  { value: 'ACTIVE_NOT_RECRUITING', label: 'Active, Not Recruiting' },
  { value: 'ENROLLING_BY_INVITATION', label: 'Enrolling by Invitation' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'SUSPENDED', label: 'Suspended' },
  { value: 'TERMINATED', label: 'Terminated' },
  { value: 'WITHDRAWN', label: 'Withdrawn' },
];

export const PIPELINE_STAGES = [
  {
    id: 'check_interactions',
    title: 'Drug Interaction Extraction',
    detail: 'Resolving RxCUIs via NLM RxNav & verifying verbatim OpenFDA package insert quotes',
  },
  {
    id: 'assess_risk',
    title: 'Deterministic Risk Scoring',
    detail: 'Computing 0–10 composite score from severity weights, age, organ function & comorbidities',
  },
  {
    id: 'find_trials',
    title: 'Clinical Trial Matching',
    detail: 'Querying ClinicalTrials.gov v2 and scoring protocol eligibility against patient context',
  },
  {
    id: 'search_literature',
    title: 'Hybrid RAG Literature Search',
    detail: 'Embedding query with nomic-embed-text and verifying Qdrant PubMed citations',
  },
  {
    id: 'write_report',
    title: 'Structured Report Assembly',
    detail: 'Generating deterministic factual sections & grounded executive summary',
  },
  {
    id: 'validate',
    title: '8-Point Anti-Hallucination Gate',
    detail: 'Auditing NCT IDs, numeric consistency, risk tier alignment, and citation integrity',
  },
];
