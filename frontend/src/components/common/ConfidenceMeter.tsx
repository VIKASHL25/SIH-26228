import React from 'react';

interface Props {
  score: number; // 0.0 to 1.0
  semantics?: string;
  showPercent?: boolean;
}

export const ConfidenceMeter: React.FC<Props> = ({
  score,
  semantics = 'heuristic_evidence_score',
  showPercent = true
}) => {
  const normalized = Math.max(0, Math.min(1, score || 0));
  const percent = Math.round(normalized * 100);

  const getColor = () => {
    if (normalized >= 0.8) return 'bg-rose-500';
    if (normalized >= 0.5) return 'bg-amber-500';
    if (normalized > 0.2) return 'bg-cyan-500';
    return 'bg-emerald-500';
  };

  const isHeuristic = semantics.includes('heuristic') || semantics.includes('derived');

  return (
    <div className="w-full">
      <div className="flex justify-between items-center text-xs mb-1">
        <span className="text-slate-400 text-[11px] flex items-center gap-1">
          {isHeuristic ? (
            <span className="text-amber-400/80 font-mono text-[10px] uppercase">[Heuristic Score]</span>
          ) : (
            <span className="text-slate-400 font-mono text-[10px] uppercase">[Confidence]</span>
          )}
        </span>
        {showPercent && (
          <span className="font-mono font-medium text-slate-200">
            {percent}%
          </span>
        )}
      </div>
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
        <div
          className={`h-full ${getColor()} transition-all duration-500 rounded-full`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};
