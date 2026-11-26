import { useState } from 'react';
import { Activity, FlaskConical, Pill, ShieldCheck } from 'lucide-react';
import { AnalysisWorkspace } from './components/AnalysisWorkspace';
import { DrugExplorerView } from './components/DrugExplorerView';
import { HealthStatusBar } from './components/HealthStatusBar';
import { TrialExplorerView } from './components/TrialExplorerView';

export function App() {
  const [activeTab, setActiveTab] = useState('analyze');

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Clinical Navigation Bar */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4 py-3.5">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-600 text-white shadow-sm">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-base font-bold tracking-tight text-slate-900">
                    DrugTrialAI
                  </h1>
                  <span className="rounded-full bg-sky-50 border border-sky-200 px-2 py-0.5 text-[10px] font-mono font-semibold text-sky-800">
                    v0.1.0
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  Autonomous Drug Interaction, Risk &amp; Clinical Trial Decision Support
                </p>
              </div>
            </div>

            <HealthStatusBar />
          </div>

          {/* Primary Navigation Tabs */}
          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {[
              { id: 'analyze', label: 'Multi-Agent Case Analysis', icon: Activity },
              { id: 'drugs', label: 'DDI & FDA Label Explorer', icon: Pill },
              { id: 'trials', label: 'Clinical Trials Search', icon: FlaskConical },
            ].map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold whitespace-nowrap transition-colors ${
                    active
                      ? 'border-sky-600 text-sky-700'
                      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'analyze' && <AnalysisWorkspace />}
        {activeTab === 'drugs' && <DrugExplorerView />}
        {activeTab === 'trials' && <TrialExplorerView />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 mt-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span>
            DrugTrialAI · Local-First Stack (LangGraph · Ollama · Qdrant · RxNav · OpenFDA ·
            ClinicalTrials.gov)
          </span>
          <span>Research &amp; clinical decision-support reference only</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
