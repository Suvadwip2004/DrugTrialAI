import { AlertOctagon, ShieldAlert, ShieldCheck } from 'lucide-react';
import { SeverityBadge } from './SeverityBadge';

const LEVEL_COLORS = {
  critical: { bar: 'bg-rose-600', text: 'text-rose-700', bg: 'bg-rose-50 border-rose-200' },
  elevated: { bar: 'bg-orange-500', text: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
  moderate: { bar: 'bg-amber-500', text: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  low: { bar: 'bg-emerald-500', text: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
};

export function RiskGauge({ risk }) {
  if (!risk) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
        No risk assessment payload was returned for this run.
      </div>
    );
  }

  const level = (risk.risk_level || 'low').toLowerCase();
  const theme = LEVEL_COLORS[level] ?? LEVEL_COLORS.low;
  const clampedScore = Math.max(0, Math.min(10, risk.composite_risk_score ?? 0));
  const pct = (clampedScore / 10) * 100;

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {risk.hard_stop && (
        <div className="flex items-center gap-2.5 bg-rose-600 px-5 py-2.5 text-white text-xs font-semibold tracking-wide uppercase">
          <AlertOctagon className="h-4 w-4 shrink-0" />
          <span>Hard Stop Triggered — Contraindicated Drug Combination Detected</span>
        </div>
      )}

      <div className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              {level === 'low' ? (
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
              ) : (
                <ShieldAlert className={`h-4 w-4 ${theme.text}`} />
              )}
              Deterministic Composite Risk
            </div>
            <div className="mt-1 flex items-baseline gap-2.5">
              <span className="text-3xl font-bold tracking-tight text-slate-900 font-mono">
                {clampedScore.toFixed(1)}
              </span>
              <span className="text-sm font-medium text-slate-400 font-mono">/ 10.0</span>
              <SeverityBadge level={level} size="md" />
            </div>
          </div>

          <div className="text-right text-xs text-slate-500">
            <div>Rules Engine</div>
            <div className="font-mono text-slate-700 font-medium">DDI + Age + Organ + Comorbidities</div>
          </div>
        </div>

        <div className="mt-4">
          <div className="h-3 w-full rounded-full bg-slate-100 overflow-hidden flex">
            <div
              className={`h-full transition-all duration-500 ${theme.bar}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-1.5 flex justify-between text-[11px] font-mono text-slate-400">
            <span>0.0 Low</span>
            <span>2.0 Moderate</span>
            <span>5.0 Elevated</span>
            <span>8.0 Critical</span>
            <span>10.0</span>
          </div>
        </div>

        {risk.explanation && (
          <div className={`mt-4 rounded-lg border p-3.5 text-sm leading-relaxed text-slate-700 ${theme.bg}`}>
            {risk.explanation}
          </div>
        )}

        {risk.contributing_factors && risk.contributing_factors.length > 0 && (
          <div className="mt-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Contributing Risk Factors
            </div>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
              {risk.contributing_factors.map((factor, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2 text-xs text-slate-700 bg-slate-50 rounded-md px-2.5 py-1.5 border border-slate-200/80"
                >
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400 shrink-0" />
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
