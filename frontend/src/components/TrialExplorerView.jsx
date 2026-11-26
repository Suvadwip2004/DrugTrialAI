import { useState } from 'react';
import { AlertCircle, FlaskConical, Loader2, Search } from 'lucide-react';
import { apiClient, ApiError } from '../api/client';
import { PHASE_OPTIONS, TRIAL_STATUS_OPTIONS } from '../data/presets';
import { TrialCard } from './TrialCard';

export function TrialExplorerView() {
  const [condition, setCondition] = useState('Atrial Fibrillation');
  const [intervention, setIntervention] = useState('Warfarin');
  const [status, setStatus] = useState('RECRUITING');
  const [phases, setPhases] = useState(['PHASE2', 'PHASE3']);
  const [pageSize, setPageSize] = useState(10);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [trials, setTrials] = useState(null);

  const togglePhase = (phase) => {
    setPhases((prev) =>
      prev.includes(phase) ? prev.filter((p) => p !== phase) : [...prev, phase]
    );
  };

  const handleSearch = async () => {
    if (!condition.trim() && !intervention.trim()) {
      setError('Provide at least a condition or an intervention drug.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.searchTrials({
        condition: condition.trim() || undefined,
        intervention: intervention.trim() || undefined,
        phases: phases.length > 0 ? phases : undefined,
        status,
        page_size: pageSize,
      });
      setTrials(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to search clinical trials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="h-4 w-4 text-sky-600" />
          <h2 className="text-base font-semibold text-slate-900">
            ClinicalTrials.gov v2 Direct Search
          </h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Queries <code className="text-slate-700">GET /api/v1/trials/search</code> against live
          ClinicalTrials.gov study records.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Condition
            </label>
            <input
              type="text"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              placeholder="e.g. Atrial Fibrillation"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Intervention / Drug
            </label>
            <input
              type="text"
              value={intervention}
              onChange={(e) => setIntervention(e.target.value)}
              placeholder="e.g. Warfarin"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Recruitment Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            >
              {TRIAL_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Max Results
            </label>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            >
              {[5, 10, 20, 30, 50].map((n) => (
                <option key={n} value={n}>
                  {n} trials
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Trial Phases
            </span>
            <div className="flex flex-wrap gap-1.5">
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
          </div>

          <button
            type="button"
            onClick={handleSearch}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-sky-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching ClinicalTrials.gov...
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Search Trials
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {trials && (
        <div className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Found {trials.length} Clinical Trial{trials.length === 1 ? '' : 's'}
          </div>
          {trials.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
              No studies matched those filters. Try broadening the phase or status criteria.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {trials.map((t, idx) => (
                <TrialCard key={t.nct_id ?? idx} trial={t} showEligibilityScore={false} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
