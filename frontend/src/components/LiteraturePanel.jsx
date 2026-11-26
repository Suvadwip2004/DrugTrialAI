import { BookOpen, CheckCircle2, ExternalLink, Info } from 'lucide-react';

export function LiteraturePanel({ literature, citations }) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <BookOpen className="h-4 w-4 text-sky-600" />
            PubMed Hybrid RAG Evidence
          </div>

          {literature && (
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase ${
                literature.grounded
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : 'border-slate-200 bg-slate-100 text-slate-600'
              }`}
            >
              {literature.grounded ? (
                <>
                  <CheckCircle2 className="h-3 w-3" />
                  Grounded Citations
                </>
              ) : (
                <>
                  <Info className="h-3 w-3" />
                  No Grounded Match
                </>
              )}
            </span>
          )}
        </div>

        {!literature ? (
          <p className="text-sm text-slate-500">
            Literature search did not return a payload (Qdrant may be offline or unpopulated).
          </p>
        ) : (
          <div className="space-y-4">
            {literature.question && (
              <div className="rounded-lg bg-slate-50 border border-slate-200/80 px-3.5 py-2 text-xs text-slate-600">
                <span className="font-semibold text-slate-800">RAG Query: </span>
                {literature.question}
              </div>
            )}

            <p className="text-sm leading-relaxed text-slate-700">{literature.answer}</p>

            {literature.cited_sources && literature.cited_sources.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Cited PubMed Sources ({literature.cited_sources.length})
                </div>
                <div className="space-y-2">
                  {literature.cited_sources.map((src, idx) => (
                    <div
                      key={`${src.url}-${idx}`}
                      className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="font-medium text-slate-900">
                          [{idx + 1}] {src.title}
                        </div>
                        {src.url && (
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-sky-700 hover:underline font-mono"
                          >
                            {src.url}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      <span className="shrink-0 rounded bg-white border border-slate-200 px-2 py-0.5 font-mono text-[11px] text-slate-600">
                        score {(src.score ?? 0).toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {literature.all_sources &&
              literature.all_sources.length > (literature.cited_sources?.length ?? 0) && (
                <details className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
                  <summary className="cursor-pointer text-xs font-semibold text-slate-600">
                    Retrieved Context Chunks ({literature.all_sources.length})
                  </summary>
                  <div className="mt-2 space-y-1.5">
                    {literature.all_sources.map((src, idx) => (
                      <div key={idx} className="flex items-center justify-between gap-2 text-xs text-slate-600">
                        <span className="truncate">{src.title}</span>
                        <span className="font-mono text-[11px] text-slate-400 shrink-0">
                          {(src.score ?? 0).toFixed(3)}
                        </span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
          </div>
        )}
      </div>

      {citations && citations.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
            Full Audit Citations ({citations.length})
          </div>
          <div className="divide-y divide-slate-100">
            {citations.map((c, idx) => (
              <div key={idx} className="py-2 first:pt-0 last:pb-0 flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="rounded bg-slate-100 border border-slate-200 px-1.5 py-0.5 font-mono text-[10px] uppercase text-slate-600 shrink-0">
                    {c.type}
                  </span>
                  <span className="text-slate-800 truncate">{c.label}</span>
                </div>
                {c.url && (
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sky-700 hover:underline shrink-0"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
