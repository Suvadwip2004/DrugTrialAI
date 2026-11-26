import { useState } from 'react';
import {
  Activity,
  AlertCircle,
  BookOpen,
  FileText,
  FlaskConical,
  History,
  Info,
  Pill,
  Play,
  RotateCcw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { apiClient, ApiError } from '../api/client';
import {
  CLINICAL_PRESETS,
  ORGAN_FUNCTION_OPTIONS,
  PHASE_OPTIONS,
} from '../data/presets';
import { InteractionCard } from './InteractionCard';
import { LiteraturePanel } from './LiteraturePanel';
import { PipelineProgress } from './PipelineProgress';
import { ReportPanel } from './ReportPanel';
import { RiskGauge } from './RiskGauge';
import { TagInput } from './TagInput';
import { TrialCard } from './TrialCard';
import { ValidationPanel } from './ValidationPanel';

const HISTORY_KEY = 'drugtrialai_history_v1';

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function AnalysisWorkspace() {
  // Form State
  const [drugs, setDrugs] = useState(['Warfarin', 'Amoxicillin']);
  const [condition, setCondition] = useState('Atrial Fibrillation');
  const [age, setAge] = useState('68');
  const [sex, setSex] = useState('male');
  const [renalFunction, setRenalFunction] = useState('moderate_impairment');
  const [hepaticFunction, setHepaticFunction] = useState('normal');
  const [comorbidities, setComorbidities] = useState([
    'Chronic Kidney Disease Stage 3',
    'Hypertension',
  ]);
  const [phases, setPhases] = useState(['PHASE2', 'PHASE3']);

  // Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [history, setHistory] = useState(loadHistory);

  const applyPreset = (req) => {
    setDrugs(req.drugs);
    setCondition(req.condition ?? '');
    setAge(req.patient_context?.age != null ? String(req.patient_context.age) : '');
    setSex(req.patient_context?.sex ?? '');
    setRenalFunction(req.patient_context?.renal_function ?? 'normal');
    setHepaticFunction(req.patient_context?.hepatic_function ?? 'normal');
    setComorbidities(req.patient_context?.comorbidities ?? []);
    setPhases(req.phases ?? []);
    setError(null);
  };

  const resetForm = () => {
    setDrugs([]);
    setCondition('');
    setAge('');
    setSex('');
    setRenalFunction('normal');
    setHepaticFunction('normal');
    setComorbidities([]);
    setPhases([]);
    setError(null);
  };

  const togglePhase = (phase) => {
    setPhases((prev) =>
      prev.includes(phase) ? prev.filter((p) => p !== phase) : [...prev, phase]
    );
  };

  const handleRunAnalysis = async () => {
    if (drugs.length === 0) {
      setError('Please add at least one medication before running the analysis.');
      return;
    }

    const parsedAge = age.trim() ? Number(age) : undefined;
    if (parsedAge !== undefined && (Number.isNaN(parsedAge) || parsedAge < 0 || parsedAge > 130)) {
      setError('Patient age must be a valid number between 0 and 130.');
      return;
    }

    const payload = {
      drugs,
      condition: condition.trim() || null,
      patient_context: {
        age: parsedAge ?? null,
        sex: sex || null,
        renal_function: renalFunction,
        hepatic_function: hepaticFunction,
        comorbidities,
      },
      phases: phases.length > 0 ? phases : null,
    };

    setIsRunning(true);
    setError(null);

    try {
      const data = await apiClient.analyzeCase(payload);
      setResult(data);
      setActiveTab('overview');

      const entry = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        request: payload,
        response: data,
      };
      const updated = [entry, ...history].slice(0, 8);
      setHistory(updated);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : 'Pipeline execution failed. Check that FastAPI, Ollama, and Qdrant are running.'
      );
    } finally {
      setIsRunning(false);
    }
  };

  const loadFromHistory = (item) => {
    applyPreset(item.request);
    setResult(item.response);
    setActiveTab('overview');
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem(HISTORY_KEY);
  };

  const interactionsFoundCount =
    result?.interaction_analysis.filter((i) => i.interaction_found).length ?? 0;

  return (
    <div className="space-y-6">
      {/* Top Horizontal Clinical Case Input Bar */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
        {/* Header + Horizontal Presets + Clear */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Clinical Case Input</h2>
            <p className="text-xs text-slate-500">
              Configure medication regimen, condition, and patient clinical context
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400 mr-1">
              <Sparkles className="h-3.5 w-3.5 text-sky-600" />
              Presets:
            </span>
            {CLINICAL_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset.request)}
                title={preset.subtitle}
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-900 transition-colors"
              >
                {preset.label}
              </button>
            ))}

            <button
              type="button"
              onClick={resetForm}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 ml-1"
              title="Clear form"
            >
              <RotateCcw className="h-3 w-3" />
              Clear
            </button>
          </div>
        </div>

        {/* Row 1: Drugs, Condition, Age, Sex */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
          <div className="md:col-span-5">
            <TagInput
              label="Medications *"
              values={drugs}
              onChange={setDrugs}
              placeholder="Add drug (e.g. Warfarin)..."
              hint="Press Enter or comma to add. Checked against OpenFDA & RxNav."
            />
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Primary Condition
            </label>
            <input
              type="text"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              placeholder="e.g. Atrial Fibrillation"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
            <p className="mt-1 text-[11px] text-slate-500">Used for ClinicalTrials.gov matching.</p>
          </div>

          <div className="grid grid-cols-2 gap-3 md:col-span-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Age (Years)
              </label>
              <input
                type="number"
                min={0}
                max={130}
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="e.g. 68"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Biological Sex
              </label>
              <select
                value={sex}
                onChange={(e) => setSex(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              >
                <option value="">Unspecified</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
        </div>

        {/* Row 2: Renal, Hepatic, Comorbidities */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
          <div className="md:col-span-3">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Renal Function
            </label>
            <select
              value={renalFunction}
              onChange={(e) => setRenalFunction(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            >
              {ORGAN_FUNCTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Hepatic Function
            </label>
            <select
              value={hepaticFunction}
              onChange={(e) => setHepaticFunction(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            >
              {ORGAN_FUNCTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-6">
            <TagInput
              label="Comorbidities"
              values={comorbidities}
              onChange={setComorbidities}
              placeholder="e.g. Hypertension, Type 2 Diabetes..."
              hint="+0.5 risk pts per comorbidity (capped at +2.0)."
              badgeColor="slate"
            />
          </div>
        </div>

        {/* Row 3: Trial Phases + Run CTA */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 mr-1">
              Trial Phases:
            </span>
            {PHASE_OPTIONS.map((opt) => {
              const active = phases.includes(opt.value);
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => togglePhase(opt.value)}
                  className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                    active
                      ? 'border-sky-500 bg-sky-50 text-sky-800'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={isRunning || drugs.length === 0}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-sky-700 disabled:opacity-50 disabled:pointer-events-none transition-colors"
          >
            <Play className="h-4 w-4 fill-current" />
            {isRunning ? 'Running Multi-Agent Analysis...' : 'Run Full Pipeline Analysis'}
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Horizontal Recent History Strip */}
        {history.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <History className="h-3.5 w-3.5" />
              Recent:
            </span>
            {history.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => loadFromHistory(item)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:border-sky-300 hover:bg-sky-50 transition-colors"
              >
                <span className="font-medium">{item.request.drugs.join(' + ')}</span>
                <span className="text-[10px] font-mono uppercase text-slate-500">
                  ({item.response.risk_assessment?.risk_level ?? 'done'})
                </span>
              </button>
            ))}
            <button
              type="button"
              onClick={clearHistory}
              className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-rose-600 ml-auto"
            >
              <Trash2 className="h-3 w-3" />
              Clear history
            </button>
          </div>
        )}
      </section>

      {/* Pipeline Progress & Results Section */}
      <section className="space-y-5">
        <PipelineProgress isRunning={isRunning} />

        {!result && !isRunning && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-sky-50 text-sky-600 mb-3">
              <Activity className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-900">
              Ready for Multi-Agent Clinical Analysis
            </h3>
            <p className="mt-1.5 max-w-2xl mx-auto text-sm text-slate-500">
              Configure medications and patient clinical parameters in the panel above, or select a
              preset, then click <strong>Run Full Pipeline Analysis</strong> to verify FDA label
              interactions, compute deterministic risk, match recruiting trials, and inspect PubMed
              literature.
            </p>
            <div className="mt-5 inline-flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50/70 px-3.5 py-2 text-xs text-sky-900">
              <Info className="h-4 w-4 text-sky-600 shrink-0" />
              <span>
                Decision-support only: deterministic rules compute safety scores while verbatim
                label quotes &amp; 8-point validation guard against LLM hallucinations.
              </span>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-5">
            {/* Mandatory Decision Support Banner */}
            <div className="flex items-start gap-2.5 rounded-xl border border-sky-200 bg-sky-50/80 px-4 py-3 text-xs text-sky-950">
              <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
              <div>
                <strong>Decision-support only.</strong> This analysis summarizes retrieved FDA
                package inserts, registered clinical trials, and indexed PubMed literature. It does
                not constitute medical advice or replace clinician judgment.
              </div>
            </div>

            {/* Validation Audit Banner */}
            <ValidationPanel
              validated={result.validated}
              validation={result.validation}
              reportAttempts={result.report_attempts}
              usedFallbackSummary={result.used_fallback_summary}
              stageErrors={result.stage_errors}
            />

            {/* Sub-navigation Tabs */}
            <div className="flex flex-wrap gap-1.5 border-b border-slate-200 pb-3">
              {[
                { id: 'overview', label: 'Overview & Risk', icon: Activity },
                {
                  id: 'interactions',
                  label: `Interactions (${interactionsFoundCount}/${result.interaction_analysis.length})`,
                  icon: Pill,
                },
                {
                  id: 'trials',
                  label: `Clinical Trials (${result.matching_trials.length})`,
                  icon: FlaskConical,
                },
                {
                  id: 'literature',
                  label: `Literature (${result.literature?.cited_sources?.length ?? 0})`,
                  icon: BookOpen,
                },
                { id: 'report', label: 'Report & Audit JSON', icon: FileText },
              ].map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors ${
                      active
                        ? 'bg-slate-900 text-white shadow-sm'
                        : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Tab Contents */}
            {activeTab === 'overview' && (
              <div className="space-y-5">
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                    Executive Clinical Summary
                  </div>
                  <p className="text-sm leading-relaxed text-slate-800">{result.summary}</p>
                </div>

                <RiskGauge risk={result.risk_assessment} />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="text-xs text-slate-500">Drug Pairs Checked</div>
                    <div className="mt-1 text-2xl font-bold font-mono text-slate-900">
                      {result.interaction_analysis.length}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5">
                      {interactionsFoundCount} verified interaction(s)
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="text-xs text-slate-500">Matching Trials</div>
                    <div className="mt-1 text-2xl font-bold font-mono text-slate-900">
                      {result.matching_trials.length}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5">
                      {result.condition || 'No condition specified'}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="text-xs text-slate-500">Cited PubMed Sources</div>
                    <div className="mt-1 text-2xl font-bold font-mono text-slate-900">
                      {result.literature?.cited_sources?.length ?? 0}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5">
                      {result.literature?.grounded ? 'Grounded RAG answer' : 'Unconfirmed / Empty'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'interactions' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {result.interaction_analysis.length === 0 ? (
                  <div className="lg:col-span-2 rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
                    At least two drugs are required to evaluate pairwise interactions.
                  </div>
                ) : (
                  result.interaction_analysis.map((item, idx) => (
                    <InteractionCard key={`${item.drug_a}-${item.drug_b}-${idx}`} item={item} />
                  ))
                )}
              </div>
            )}

            {activeTab === 'trials' && (
              <div className="space-y-3">
                {result.matching_trials.length === 0 ? (
                  <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
                    No matching recruiting trials were returned for this condition and phase filter.
                  </div>
                ) : (
                  result.matching_trials.map((trial, idx) => (
                    <TrialCard key={trial.nct_id ?? idx} trial={trial} showEligibilityScore />
                  ))
                )}
              </div>
            )}

            {activeTab === 'literature' && (
              <LiteraturePanel literature={result.literature} citations={result.citations} />
            )}

            {activeTab === 'report' && <ReportPanel result={result} />}
          </div>
        )}
      </section>
    </div>
  );
}
