import { useEffect, useState } from 'react';
import { CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { PIPELINE_STAGES } from '../data/presets';

export function PipelineProgress({ isRunning }) {
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    if (!isRunning) {
      setElapsedSec(0);
      return;
    }
    const start = Date.now();
    const timer = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - start) / 1000));
    }, 500);
    return () => clearInterval(timer);
  }, [isRunning]);

  if (!isRunning) return null;

  const activeIndex = Math.min(PIPELINE_STAGES.length - 1, Math.floor(elapsedSec / 6));

  return (
    <div className="rounded-xl border border-sky-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2.5">
          <Loader2 className="h-5 w-5 animate-spin text-sky-600" />
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Executing 6-Stage LangGraph Pipeline...
            </h3>
            <p className="text-xs text-slate-500">
              Sequential local inference on Ollama + live federal APIs (RxNav, OpenFDA, ClinicalTrials.gov, Qdrant)
            </p>
          </div>
        </div>
        <div className="inline-flex items-center gap-1.5 rounded-lg bg-sky-50 border border-sky-200 px-3 py-1 text-xs font-mono font-semibold text-sky-800">
          <Clock className="h-3.5 w-3.5" />
          {elapsedSec}s elapsed
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {PIPELINE_STAGES.map((stage, idx) => {
          const done = idx < activeIndex;
          const active = idx === activeIndex;
          return (
            <div
              key={stage.id}
              className={`rounded-lg border p-3 transition-colors ${
                active
                  ? 'border-sky-400 bg-sky-50/70'
                  : done
                    ? 'border-emerald-200 bg-emerald-50/40'
                    : 'border-slate-200 bg-slate-50/50 opacity-70'
              }`}
            >
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-900">
                {done ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                ) : active ? (
                  <Loader2 className="h-4 w-4 animate-spin text-sky-600 shrink-0" />
                ) : (
                  <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 text-[10px] font-mono text-slate-500 shrink-0">
                    {idx + 1}
                  </span>
                )}
                <span>
                  {idx + 1}. {stage.title}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-600 leading-snug pl-6">{stage.detail}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
