const SEVERITY_STYLES = {
  contraindicated: 'bg-rose-100 text-rose-900 border-rose-300',
  critical: 'bg-rose-100 text-rose-900 border-rose-300',
  major: 'bg-orange-100 text-orange-900 border-orange-300',
  elevated: 'bg-orange-100 text-orange-900 border-orange-300',
  moderate: 'bg-amber-100 text-amber-900 border-amber-300',
  minor: 'bg-sky-100 text-sky-900 border-sky-300',
  low: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  none: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  unknown: 'bg-slate-100 text-slate-700 border-slate-300',
};

export function SeverityBadge({ level, size = 'sm' }) {
  const normalized = (level || 'unknown').toLowerCase();
  const style = SEVERITY_STYLES[normalized] ?? SEVERITY_STYLES.unknown;
  const padding = size === 'md' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[11px]';

  return (
    <span
      className={`inline-flex items-center rounded-full border font-semibold uppercase tracking-wide ${padding} ${style}`}
    >
      {normalized}
    </span>
  );
}
