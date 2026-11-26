import { AlertCircle, CheckCircle2, ShieldAlert, XCircle } from 'lucide-react';

const CHECK_LABELS = {
  sections_present: 'All 5 Required Sections Present',
  disclaimer_present: 'Clinical Disclaimer Included',
  summary_present: 'Executive Summary Non-Empty',
  trial_ids_valid: 'NCT Trial IDs Whitelisted',
  summary_numbers_grounded: 'Summary Numbers Grounded',
  risk_level_consistent: 'Risk Tier Aligned',
  hard_stop_consistent: 'Hard-Stop Flag Consistent',
  drug_names_grounded: 'Drug Names Whitelisted',
  all_pairs_covered: 'All Input Drug Pairs Reported',
  citations_valid: 'Literature Citations Verified',
};

export function ValidationPanel({
  validated,
  validation,
  reportAttempts,
  usedFallbackSummary,
  stageErrors,
}) {
  const checkEntries = Object.entries(validation?.checks ?? {});

  return (
    <div
      className={`rounded-xl border p-5 ${
        validated
          ? 'border-emerald-200 bg-emerald-50/50'
          : 'border-rose-300 bg-rose-50/70'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {validated ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-rose-600 shrink-0" />
          )}
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              {validated
                ? 'Audit Validation Passed'
                : 'Validation Failed — Review Errors Before Relying on Report'}
            </h3>
            <p className="text-xs text-slate-600">
              Attempts: <span className="font-mono font-medium">{reportAttempts}</span> · Summary
              mode:{' '}
              <span className="font-mono font-medium">
                {usedFallbackSummary ? 'Deterministic Fallback' : 'Grounded LLM'}
              </span>
            </p>
          </div>
        </div>
      </div>

      {checkEntries.length > 0 && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
          {checkEntries.map(([key, passed]) => (
            <div
              key={key}
              className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs ${
                passed
                  ? 'border-emerald-200/80 bg-white text-slate-700'
                  : 'border-rose-300 bg-rose-100/70 text-rose-900 font-medium'
              }`}
            >
              {passed ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-rose-600 shrink-0" />
              )}
              <span className="truncate">{CHECK_LABELS[key] ?? key.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      )}

      {validation?.errors && validation.errors.length > 0 && (
        <div className="mt-3 rounded-lg border border-rose-300 bg-white p-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-rose-700 mb-1">
            Validation Errors
          </div>
          <ul className="space-y-1 text-xs text-rose-800 list-disc pl-4">
            {validation.errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {(validation?.warnings?.length > 0 || stageErrors.length > 0) && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-800 mb-1">
            <AlertCircle className="h-3.5 w-3.5" />
            Warnings &amp; Stage Isolation Notes
          </div>
          <ul className="space-y-1 text-xs text-amber-900 list-disc pl-4">
            {validation?.warnings?.map((w, i) => (
              <li key={`w-${i}`}>{w}</li>
            ))}
            {stageErrors.map((e, i) => (
              <li key={`s-${i}`}>Stage error: {e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
