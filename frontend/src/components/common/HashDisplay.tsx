import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface Props {
  hash: string;
  label?: string;
  truncateLength?: number;
  showCopy?: boolean;
}

export const HashDisplay: React.FC<Props> = ({
  hash,
  label,
  truncateLength = 16,
  showCopy = true
}) => {
  const [copied, setCopied] = useState(false);

  if (!hash) return <span className="text-slate-500 font-mono text-xs">--</span>;

  const displayHash = truncateLength && hash.length > truncateLength
    ? `${hash.substring(0, truncateLength)}...`
    : hash;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="inline-flex items-center gap-1.5 font-mono text-xs text-slate-300 bg-slate-900/80 px-2 py-1 rounded border border-slate-800 hover:border-slate-700 transition-colors">
      {label && <span className="text-slate-400 font-sans text-[11px] mr-1">{label}:</span>}
      <span title={hash} className="text-cyan-300 font-mono select-all">
        {displayHash}
      </span>
      {showCopy && (
        <button
          onClick={handleCopy}
          className="text-slate-400 hover:text-cyan-300 transition-colors ml-1 p-0.5"
          title="Copy full hash digest"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
        </button>
      )}
    </div>
  );
};
