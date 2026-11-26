import { useState } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Code2, Copy, Download, FileText } from 'lucide-react';

export function ReportPanel({ result }) {
  const [viewMode, setViewMode] = useState('rendered');
  const [copied, setCopied] = useState(false);

  const jsonText = JSON.stringify(result, null, 2);

  const handleCopy = async () => {
    const content = viewMode === 'json' ? jsonText : result.report_md;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const downloadFile = (content, filename, mime) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3">
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5">
          <button
            type="button"
            onClick={() => setViewMode('rendered')}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              viewMode === 'rendered'
                ? 'bg-sky-600 text-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            Rendered Report
          </button>
          <button
            type="button"
            onClick={() => setViewMode('markdown')}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              viewMode === 'markdown'
                ? 'bg-sky-600 text-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Code2 className="h-3.5 w-3.5" />
            Raw report.md
          </button>
          <button
            type="button"
            onClick={() => setViewMode('json')}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              viewMode === 'json'
                ? 'bg-sky-600 text-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Code2 className="h-3.5 w-3.5" />
            Audit report.json
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-600" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                Copy
              </>
            )}
          </button>
          <button
            type="button"
            onClick={() => downloadFile(result.report_md, 'report.md', 'text/markdown')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" />
            report.md
          </button>
          <button
            type="button"
            onClick={() => downloadFile(jsonText, 'report.json', 'application/json')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" />
            report.json
          </button>
        </div>
      </div>

      <div className="p-6 max-h-[700px] overflow-auto">
        {viewMode === 'rendered' && (
          <div className="markdown-report text-sm">
            <Markdown remarkPlugins={[remarkGfm]}>{result.report_md}</Markdown>
          </div>
        )}
        {viewMode === 'markdown' && (
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-800 bg-slate-50 rounded-lg p-4 border border-slate-200">
            {result.report_md}
          </pre>
        )}
        {viewMode === 'json' && (
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed bg-slate-950 text-slate-100 rounded-lg p-4 overflow-x-auto">
            {jsonText}
          </pre>
        )}
      </div>
    </div>
  );
}
