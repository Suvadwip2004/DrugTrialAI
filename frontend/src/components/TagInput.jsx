import { useState } from 'react';
import { Plus, X } from 'lucide-react';

export function TagInput({
  label,
  values,
  onChange,
  placeholder = 'Type and press Enter...',
  hint,
  badgeColor = 'sky',
}) {
  const [draft, setDraft] = useState('');

  const addItems = (raw) => {
    const parts = raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (parts.length === 0) return;

    const existingLower = new Set(values.map((v) => v.toLowerCase()));
    const next = [...values];
    for (const part of parts) {
      if (!existingLower.has(part.toLowerCase())) {
        next.push(part);
        existingLower.add(part.toLowerCase());
      }
    }
    onChange(next);
    setDraft('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addItems(draft);
    } else if (e.key === 'Backspace' && !draft && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  };

  const removeItem = (idx) => {
    onChange(values.filter((_, i) => i !== idx));
  };

  const chipClasses =
    badgeColor === 'sky'
      ? 'bg-sky-50 text-sky-900 border-sky-200'
      : 'bg-slate-100 text-slate-800 border-slate-200';

  return (
    <div>
      <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
        {label}
      </label>
      <div className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-500/20 transition-all">
        <div className="flex flex-wrap items-center gap-1.5">
          {values.map((val, idx) => (
            <span
              key={`${val}-${idx}`}
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium ${chipClasses}`}
            >
              {val}
              <button
                type="button"
                onClick={() => removeItem(idx)}
                className="rounded hover:bg-black/10 p-0.5 transition-colors"
                aria-label={`Remove ${val}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="min-w-[140px] flex-1 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none bg-transparent py-0.5"
          />
          <button
            type="button"
            onClick={() => addItems(draft)}
            disabled={!draft.trim()}
            className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-40 disabled:pointer-events-none shrink-0"
          >
            <Plus className="h-3.5 w-3.5" />
            Add
          </button>
        </div>
      </div>
      {hint && <p className="mt-1 text-[11px] text-slate-500">{hint}</p>}
    </div>
  );
}
