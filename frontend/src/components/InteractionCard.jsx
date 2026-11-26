import { FileText, Quote, ShieldCheck, ShieldQuestion } from 'lucide-react';
import { SeverityBadge } from './SeverityBadge';

export function InteractionCard({ item }) {
  const confidencePct = Math.round(Math.max(0, Math.min(1, item.confidence ?? 0)) * 100);
  const hasQuote = Boolean(item.evidence && item.evidence.trim().length > 0);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-slate-300 transition-colors">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-slate-900">
              {item.drug_a} <span className="text-slate-400 font-normal">+</span> {item.drug_b}
            </h4>
            <SeverityBadge level={item.severity} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500 font-mono">
            <span>
              RxCUI A: <strong className="text-slate-700">{item.rxcui_a || 'unresolved'}</strong>
            </span>
            <span>
              RxCUI B: <strong className="text-slate-700">{item.rxcui_b || 'unresolved'}</strong>
            </span>
            <span>
              Source: <strong className="text-slate-700">{item.source}</strong>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">
              Confidence
            </div>
            <div className="text-sm font-semibold font-mono text-slate-800">{confidencePct}%</div>
          </div>
          {item.interaction_found ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 border border-amber-200 px-2 py-1 text-xs font-medium text-amber-800">
              <ShieldCheck className="h-3.5 w-3.5" />
              Verified Finding
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 border border-slate-200 px-2 py-1 text-xs font-medium text-slate-600">
              <ShieldQuestion className="h-3.5 w-3.5" />
              {item.severity === 'none' ? 'No Interaction' : 'Unconfirmed'}
            </span>
          )}
        </div>
      </div>

      {item.mechanism && (
        <div className="mt-3 text-sm text-slate-700">
          <span className="font-semibold text-slate-900">Mechanism: </span>
          {item.mechanism}
        </div>
      )}

      {item.description && (
        <div className="mt-1.5 text-sm text-slate-600 leading-relaxed">
          <span className="font-semibold text-slate-800">Clinical Note: </span>
          {item.description}
        </div>
      )}

      {hasQuote ? (
        <div className="mt-3.5 rounded-lg border border-sky-200/80 bg-sky-50/70 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-sky-800 mb-1">
            <Quote className="h-3.5 w-3.5" />
            Verbatim FDA Label Evidence
          </div>
          <p className="text-xs italic leading-relaxed text-slate-700">"{item.evidence}"</p>
        </div>
      ) : (
        <div className="mt-3.5 flex items-center gap-1.5 text-xs text-slate-400">
          <FileText className="h-3.5 w-3.5" />
          <span>No verbatim FDA label quote extracted for this pair.</span>
        </div>
      )}
    </div>
  );
}
