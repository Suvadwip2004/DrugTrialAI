import { useState } from 'react';
import { AlertCircle, FileSearch, Loader2, Pill, Search } from 'lucide-react';
import { apiClient, ApiError } from '../api/client';
import { TagInput } from './TagInput';
import { InteractionCard } from './InteractionCard';

export function DrugExplorerView() {
  const [ddiDrugs, setDdiDrugs] = useState(['Warfarin', 'Amoxicillin']);
  const [ddiLoading, setDdiLoading] = useState(false);
  const [ddiError, setDdiError] = useState(null);
  const [ddiResults, setDdiResults] = useState(null);

  const [lookupDrug, setLookupDrug] = useState('Warfarin');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState(null);
  const [rxcuiData, setRxcuiData] = useState(null);
  const [labelData, setLabelData] = useState(null);

  const handleCheckDdi = async () => {
    if (ddiDrugs.length < 2) {
      setDdiError('Please enter at least 2 drugs to check pairwise interactions.');
      return;
    }
    setDdiLoading(true);
    setDdiError(null);
    try {
      const res = await apiClient.checkDrugInteractions(ddiDrugs);
      setDdiResults(res);
    } catch (err) {
      setDdiError(err instanceof ApiError ? err.detail : 'Failed to check drug interactions.');
    } finally {
      setDdiLoading(false);
    }
  };

  const handleLookupDrug = async () => {
    const trimmed = lookupDrug.trim();
    if (!trimmed) return;
    setLookupLoading(true);
    setLookupError(null);
    setRxcuiData(null);
    setLabelData(null);

    const [rxcuiRes, labelRes] = await Promise.allSettled([
      apiClient.resolveRxCui(trimmed),
      apiClient.getDrugFdaLabel(trimmed),
    ]);

    if (rxcuiRes.status === 'fulfilled') {
      setRxcuiData(rxcuiRes.value);
    }
    if (labelRes.status === 'fulfilled') {
      setLabelData(labelRes.value);
    }
    if (rxcuiRes.status === 'rejected' && labelRes.status === 'rejected') {
      const reason = rxcuiRes.reason;
      setLookupError(
        reason instanceof ApiError ? reason.detail : `No RxCUI or FDA label found for '${trimmed}'.`
      );
    }
    setLookupLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Horizontal Input Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Pill className="h-4 w-4 text-sky-600" />
            <h2 className="text-base font-semibold text-slate-900">
              Direct Drug-Drug Interaction Check
            </h2>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Calls <code className="text-slate-700">POST /api/v1/drugs/interactions</code> with
            verbatim OpenFDA label quote verification.
          </p>

          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <div className="flex-1">
              <TagInput
                label="Medications (Minimum 2)"
                values={ddiDrugs}
                onChange={setDdiDrugs}
                placeholder="Add drug name (e.g. Aspirin, Lisinopril)..."
              />
            </div>
            <button
              type="button"
              onClick={handleCheckDdi}
              disabled={ddiLoading || ddiDrugs.length < 2}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-sky-700 disabled:opacity-50 disabled:pointer-events-none transition-colors shrink-0"
            >
              {ddiLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Checking...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Check Interactions
                </>
              )}
            </button>
          </div>

          {ddiError && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{ddiError}</span>
            </div>
          )}
        </div>

        <div className="lg:col-span-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <FileSearch className="h-4 w-4 text-sky-600" />
            <h2 className="text-base font-semibold text-slate-900">
              RxCUI &amp; FDA Package Insert Inspector
            </h2>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Queries NLM RxNav (<code>/rxcui</code>) and OpenFDA (<code>/label</code>) directly.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleLookupDrug();
            }}
            className="flex items-end gap-2"
          >
            <div className="flex-1">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Drug Name
              </label>
              <input
                type="text"
                value={lookupDrug}
                onChange={(e) => setLookupDrug(e.target.value)}
                placeholder="Enter drug name (e.g. Warfarin)"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>
            <button
              type="submit"
              disabled={lookupLoading || !lookupDrug.trim()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition-colors shrink-0"
            >
              {lookupLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Inspect'}
            </button>
          </form>

          {lookupError && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{lookupError}</span>
            </div>
          )}
        </div>
      </div>

      {/* Results Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {ddiResults && (
          <div className="lg:col-span-7 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Pairwise Interaction Results ({ddiResults.length})
            </h3>
            {ddiResults.map((item, idx) => (
              <InteractionCard key={`${item.drug_a}-${item.drug_b}-${idx}`} item={item} />
            ))}
          </div>
        )}

        {(rxcuiData || labelData) && (
          <div className={`${ddiResults ? 'lg:col-span-5' : 'lg:col-span-12'} space-y-4`}>
            {rxcuiData && (
              <div className="flex items-center justify-between rounded-xl border border-sky-200 bg-sky-50 px-4 py-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-sky-700 font-semibold">
                    NLM RxNav Concept ID
                  </div>
                  <div className="text-sm font-semibold text-slate-900">{rxcuiData.drug_name}</div>
                </div>
                <span className="rounded-md bg-white border border-sky-200 px-2.5 py-1 font-mono text-sm font-bold text-sky-800">
                  RxCUI: {rxcuiData.rxcui}
                </span>
              </div>
            )}

            {labelData && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  OpenFDA Drug Interactions Section — {labelData.drug_name}
                </div>
                <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap">
                  {labelData.interaction_text}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
