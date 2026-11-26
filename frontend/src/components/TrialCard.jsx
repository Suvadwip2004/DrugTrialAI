import { AlertTriangle, ExternalLink, FlaskConical } from 'lucide-react';

export function TrialCard({ trial, showEligibilityScore = true }) {
  const nctId = trial.nct_id || 'Unknown';
  const matchPct = Math.round(Math.max(0, Math.min(1, trial.eligibility_match_score ?? 0)) * 100);

  const scoreColor =
    matchPct >= 75
      ? 'bg-emerald-500 text-emerald-700'
      : matchPct >= 45
        ? 'bg-amber-500 text-amber-700'
        : 'bg-slate-400 text-slate-600';

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-slate-300 transition-colors">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {trial.nct_id ? (
              <a
                href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-md bg-sky-50 border border-sky-200 px-2 py-0.5 text-xs font-semibold font-mono text-sky-800 hover:bg-sky-100 transition-colors"
              >
                {nctId}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-600">
                No NCT ID
              </span>
            )}

            {trial.status && (
              <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 uppercase">
                {trial.status.replace(/_/g, ' ')}
              </span>
            )}

            {(trial.phase && trial.phase.length > 0 ? trial.phase : ['NA']).map((p) => (
              <span
                key={p}
                className="rounded-full bg-slate-100 border border-slate-200 px-2 py-0.5 text-[11px] font-mono text-slate-700"
              >
                {p}
              </span>
            ))}
          </div>

          <h4 className="text-sm font-semibold text-slate-900 leading-snug pt-1">
            {trial.title || 'Untitled Clinical Study'}
          </h4>
        </div>

        {showEligibilityScore && (
          <div className="shrink-0 w-28 text-right">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">
              Match Score
            </div>
            <div className={`text-lg font-bold font-mono ${scoreColor.split(' ')[1]}`}>
              {matchPct}%
            </div>
            <div className="mt-1 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-full ${scoreColor.split(' ')[0]}`}
                style={{ width: `${matchPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {trial.conditions && trial.conditions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {trial.conditions.slice(0, 6).map((cond, idx) => (
            <span
              key={`${cond}-${idx}`}
              className="inline-flex items-center gap-1 rounded bg-slate-50 border border-slate-200 px-2 py-0.5 text-xs text-slate-600"
            >
              <FlaskConical className="h-3 w-3 text-slate-400" />
              {cond}
            </span>
          ))}
        </div>
      )}

      {trial.reason && (
        <p className="mt-3 text-xs leading-relaxed text-slate-700">
          <span className="font-semibold text-slate-900">Eligibility Rationale: </span>
          {trial.reason}
        </p>
      )}

      {trial.potential_concerns && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/80 p-2.5 text-xs text-amber-900">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Potential Exclusions / Concerns: </span>
            {trial.potential_concerns}
          </div>
        </div>
      )}
    </div>
  );
}
