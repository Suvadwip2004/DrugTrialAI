import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Settings2 } from 'lucide-react';
import { apiClient, getApiBaseUrl, setApiBaseUrl } from '../api/client';

function StatusDot({ state }) {
  const color =
    state === 'ok' ? 'bg-emerald-500' : state === 'warn' ? 'bg-amber-500' : 'bg-rose-500';
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

export function HealthStatusBar() {
  const [health, setHealth] = useState(null);
  const [offline, setOffline] = useState(false);
  const [checking, setChecking] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [apiDraft, setApiDraft] = useState(getApiBaseUrl());

  const refresh = useCallback(async () => {
    setChecking(true);
    try {
      const data = await apiClient.checkHealth();
      setHealth(data);
      setOffline(false);
    } catch {
      setHealth(null);
      setOffline(true);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 30000);
    return () => clearInterval(timer);
  }, [refresh]);

  const ollamaStatus = health?.services?.ollama ?? 'unknown';
  const qdrantStatus = health?.services?.qdrant ?? 'unknown';

  const saveBaseUrl = () => {
    setApiBaseUrl(apiDraft);
    setShowConfig(false);
    refresh();
  };

  return (
    <div className="relative flex flex-wrap items-center gap-2">
      <div className="inline-flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs">
        <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
          <StatusDot state={offline ? 'err' : 'ok'} />
          API: {offline ? 'Offline' : 'Online'}
        </span>
        <span className="text-slate-300">|</span>
        <span className="inline-flex items-center gap-1.5 text-slate-600">
          <StatusDot
            state={
              ollamaStatus === 'connected' ? 'ok' : offline ? 'err' : 'warn'
            }
          />
          Ollama: {offline ? '—' : ollamaStatus}
        </span>
        <span className="text-slate-300">|</span>
        <span className="inline-flex items-center gap-1.5 text-slate-600">
          <StatusDot
            state={
              qdrantStatus === 'connected' ? 'ok' : offline ? 'err' : 'warn'
            }
          />
          Qdrant: {offline ? '—' : qdrantStatus}
        </span>
      </div>

      <button
        type="button"
        onClick={refresh}
        title="Refresh service status"
        className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:bg-slate-50 transition-colors"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${checking ? 'animate-spin' : ''}`} />
      </button>

      <button
        type="button"
        onClick={() => setShowConfig((v) => !v)}
        title="Configure Backend API URL"
        className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:bg-slate-50 transition-colors"
      >
        <Settings2 className="h-3.5 w-3.5" />
      </button>

      {showConfig && (
        <div className="absolute right-0 top-10 z-30 w-80 rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <div className="text-xs font-semibold text-slate-900 mb-1">Backend API Base URL</div>
          <p className="text-[11px] text-slate-500 mb-2">
            Leave empty to use the Vite dev proxy (<code>/api</code> → <code>localhost:8000</code>).
          </p>
          <input
            type="text"
            value={apiDraft}
            onChange={(e) => setApiDraft(e.target.value)}
            placeholder="http://localhost:8000"
            className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-mono text-slate-900 focus:border-sky-500 focus:outline-none"
          />
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowConfig(false)}
              className="rounded-md px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={saveBaseUrl}
              className="rounded-md bg-sky-600 px-3 py-1 text-xs font-medium text-white hover:bg-sky-700"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
