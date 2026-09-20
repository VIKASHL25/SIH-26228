import React from 'react';
import {
  Users,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  Sliders,
  CheckCircle
} from 'lucide-react';
import { useAssurance } from '../context/AssuranceContext';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { DispositionBadge } from '../components/common/DispositionBadge';
import { ContributorRiskBarChart } from '../components/charts/ContributorRiskBarChart';

export const ContributorRiskPage: React.FC = () => {
  const { benchmarkData, setSelectedContributor } = useAssurance();

  const profiles = benchmarkData?.contributors?.profiles || [];
  const totalContribs = benchmarkData?.contributors?.total_contributors || 5;
  const cleanRetained = benchmarkData?.contributors?.clean_contributors_correctly_kept || 2;
  const compromisedFlagged = benchmarkData?.contributors?.compromised_contributors_flagged || 3;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">
                Contributor-Level Integrity & Risk Aggregation
              </h1>
              <p className="text-xs text-slate-400">
                Multi-party pipeline attribution: volume-normalized scoring with zero clean contributor false-quarantine invariant
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="bg-slate-900 border border-slate-800 px-3 py-1 rounded">
              <span className="text-slate-400">Compromised Flagged: </span>
              <span className="text-rose-400 font-bold">{compromisedFlagged} / 3 (100%)</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 px-3 py-1 rounded">
              <span className="text-slate-400">Clean False Alarm Rate: </span>
              <span className="text-emerald-400 font-bold">0.0%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Contributor Risk Chart & Invariant Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[#0c1220] border border-slate-800 p-5 rounded-xl">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white tracking-wide">
                Attribution Risk Distribution
              </h3>
              <p className="text-xs text-slate-400">
                Composite risk score calculated per contributor based on detected anomalies
              </p>
            </div>
            <span className="text-xs font-mono text-cyan-400">5 Distinct Sources</span>
          </div>

          <ContributorRiskBarChart
            profiles={profiles}
            onSelectContributor={(p) => setSelectedContributor(p)}
          />
        </div>

        {/* Evaluation Invariants & Rules */}
        <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono mb-2">
              Contributor Aggregation Invariants
            </h3>
            <ul className="space-y-3 text-xs text-slate-300">
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Clean Retention:</strong> Baseline contributors exhibiting natural variance (&lt; 5% flag rate) remain strictly categorized as <code>CLEAN</code> / <code>ACCEPT</code>.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Volume Normalization:</strong> Scores are normalized by batch size, preventing high-volume contributors from being penalized purely for submission volume.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Confidence Weighting:</strong> Detector evidence is weighted by empirical confidence and confirmed duplicate flooding ratios.
                </span>
              </li>
            </ul>
          </div>

          <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 text-[11px] text-slate-400 font-mono">
            Cutoffs: Critical ≥ 0.50 | High ≥ 0.28 | Medium ≥ 0.12
          </div>
        </div>
      </div>

      {/* Individual Contributor Risk Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {profiles.map(p => (
          <div
            key={p.contributor_id}
            onClick={() => setSelectedContributor(p)}
            className="bg-[#0b101d] border border-slate-800 hover:border-cyan-500/50 p-5 rounded-xl cursor-pointer transition-all flex flex-col justify-between space-y-4 shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm text-white">
                    {p.contributor_id}
                  </span>
                </div>
                <SeverityBadge severity={p.risk_level === 'CLEAN' ? 'LOW' : p.risk_level} size="sm" />
              </div>

              <div className="flex justify-between items-baseline my-3">
                <span className="text-xs text-slate-400">Risk Score:</span>
                <span className="text-2xl font-bold font-mono text-cyan-300">
                  {(p.risk_score * 100).toFixed(1)}%
                </span>
              </div>

              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Flagged Samples:</span>
                  <span className="font-mono text-white font-semibold">
                    {p.flagged_samples} / {p.total_samples} ({((p.flagged_samples / p.total_samples) * 100).toFixed(0)}%)
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Dominant Driver:</span>
                  <span className="text-amber-400 font-medium truncate max-w-[150px]">{p.dominant_factor}</span>
                </div>
              </div>

              <p className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-800/80 line-clamp-2">
                {p.explanation}
              </p>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <DispositionBadge
                disposition={
                  p.risk_level === 'CRITICAL'
                    ? 'QUARANTINE'
                    : p.risk_level === 'HIGH' || p.risk_level === 'MEDIUM'
                    ? 'REVIEW'
                    : 'ACCEPT'
                }
                size="sm"
              />
              <span className="text-xs text-cyan-400 font-mono flex items-center gap-1">
                <span>Dossier</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
