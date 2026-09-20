import React from 'react';
import { X, ShieldAlert, FileText, CheckCircle2, AlertTriangle } from 'lucide-react';
import { AssuranceFinding } from '../../types';
import { SeverityBadge } from '../common/SeverityBadge';
import { DispositionBadge } from '../common/DispositionBadge';
import { ConfidenceMeter } from '../common/ConfidenceMeter';

interface Props {
  finding: AssuranceFinding | null;
  onClose: () => void;
}

export const FindingDetailModal: React.FC<Props> = ({ finding, onClose }) => {
  if (!finding) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#0e1424] border border-slate-700/80 rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <SeverityBadge severity={finding.severity} size="md" />
            <span className="font-mono text-xs text-slate-400">
              {finding.finding_id}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 overflow-y-auto space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-white tracking-wide">
              {finding.title}
            </h2>
            <p className="text-sm text-slate-300 mt-2 leading-relaxed bg-slate-900/80 p-3 rounded-lg border border-slate-800/80">
              {finding.human_readable_reason}
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                Affected Asset
              </span>
              <code className="text-xs text-cyan-300 font-mono font-medium block truncate">
                {finding.affected_asset}
              </code>
            </div>

            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                Recommended Action
              </span>
              <DispositionBadge disposition={finding.recommended_disposition} size="sm" />
            </div>
          </div>

          {/* Confidence Assessment */}
          <div className="bg-slate-900/40 p-3.5 rounded-lg border border-slate-800">
            <ConfidenceMeter
              score={finding.confidence_score}
              semantics={finding.confidence_semantics || 'heuristic_evidence_score'}
            />
            <p className="text-[11px] text-slate-400 mt-2 italic">
              {finding.confidence_semantics?.includes('heuristic')
                ? 'Score reflects deterministic heuristic feature deviation; not a calibrated Bayesian probability.'
                : 'Score verified under current operational baseline bounds.'}
            </p>
          </div>

          {/* Supporting Evidence Technical Breakdown */}
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 font-mono">
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              <span>Supporting Forensics Evidence</span>
            </div>
            <pre className="bg-[#080c16] border border-slate-800 p-3.5 rounded-lg text-xs font-mono text-cyan-300/90 overflow-x-auto max-h-60 leading-relaxed select-all">
              {JSON.stringify(finding.supporting_evidence, null, 2)}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/60 flex justify-between items-center text-xs text-slate-400">
          <span>Category: <strong className="text-slate-200 font-mono">{finding.category}</strong></span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-md transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
