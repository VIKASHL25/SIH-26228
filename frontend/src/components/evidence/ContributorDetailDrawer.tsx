import React from 'react';
import { X, User, ShieldAlert, AlertTriangle, CheckCircle, Package } from 'lucide-react';
import { ContributorProfile } from '../../types';
import { useAssurance } from '../../context/AssuranceContext';
import { DispositionBadge } from '../common/DispositionBadge';

interface Props {
  profile: ContributorProfile | null;
  onClose: () => void;
}

export const ContributorDetailDrawer: React.FC<Props> = ({ profile, onClose }) => {
  const { manifest } = useAssurance();

  if (!profile) return null;

  const contributorSamples = manifest?.samples?.filter(s => s.contributor === profile.contributor_id) || [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#0c1220] border-l border-slate-800 w-full max-w-lg h-full flex flex-col shadow-2xl overflow-hidden">
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/70 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white tracking-wide font-mono">
                {profile.contributor_id}
              </h2>
              <span className="text-xs text-slate-400">
                Contributor Risk Dossier
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Risk Level Banner */}
          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-mono uppercase text-slate-400">
                Risk Assessment Score
              </span>
              <span className="text-xl font-bold font-mono text-cyan-400">
                {(profile.risk_score * 100).toFixed(1)}%
              </span>
            </div>

            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mb-3">
              <div
                className={`h-full rounded-full ${
                  profile.risk_level === 'CRITICAL'
                    ? 'bg-rose-500'
                    : profile.risk_level === 'HIGH'
                    ? 'bg-orange-500'
                    : profile.risk_level === 'MEDIUM'
                    ? 'bg-amber-500'
                    : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, profile.risk_score * 100)}%` }}
              />
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Assigned Risk Tier:</span>
              <span className="font-mono font-semibold text-rose-400">
                {profile.risk_level}
              </span>
            </div>
          </div>

          {/* Sample Statistics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 block mb-1">
                Total Submissions
              </span>
              <span className="text-lg font-bold font-mono text-white">
                {profile.total_samples}
              </span>
            </div>
            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 block mb-1">
                Flagged Anomalies
              </span>
              <span className="text-lg font-bold font-mono text-amber-400">
                {profile.flagged_samples}
              </span>
            </div>
          </div>

          {/* Explanation & Action */}
          <div className="space-y-3">
            <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-800">
              <span className="text-xs font-semibold text-slate-300 block mb-1">
                Dominant Risk Driver
              </span>
              <p className="text-xs font-mono text-cyan-300">
                {profile.dominant_factor}
              </p>
            </div>

            <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-800">
              <span className="text-xs font-semibold text-slate-300 block mb-1">
                Technical Evidence Rationale
              </span>
              <p className="text-xs text-slate-300 leading-relaxed">
                {profile.explanation}
              </p>
            </div>

            <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-800">
              <span className="text-xs font-semibold text-slate-300 block mb-2">
                Governance Recommendation
              </span>
              <p className="text-xs text-amber-300 font-mono leading-relaxed mb-2">
                {profile.recommended_action}
              </p>
              <DispositionBadge
                disposition={
                  profile.risk_level === 'CRITICAL'
                    ? 'QUARANTINE'
                    : profile.risk_level === 'HIGH' || profile.risk_level === 'MEDIUM'
                    ? 'REVIEW'
                    : 'ACCEPT'
                }
              />
            </div>
          </div>

          {/* Submitted Samples Preview */}
          {contributorSamples.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 font-mono">
                <Package className="w-3.5 h-3.5 text-cyan-400" />
                <span>Associated Manifest Samples ({contributorSamples.length})</span>
              </div>
              <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                {contributorSamples.map(sample => (
                  <div
                    key={sample.sample_id}
                    className="bg-[#080c16] border border-slate-800 p-2.5 rounded text-xs flex justify-between items-center"
                  >
                    <div>
                      <span className="font-mono text-cyan-300 font-medium block">
                        {sample.sample_id}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        Attack Type: <code className="text-amber-400 font-mono">{sample.attack_type}</code>
                      </span>
                    </div>
                    <div>
                      {sample.is_attacked ? (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                          ATTACKED
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                          CLEAN
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/70 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium transition-colors"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
};
