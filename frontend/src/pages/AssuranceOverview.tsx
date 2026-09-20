import React from 'react';
import {
  ShieldAlert,
  Database,
  Cpu,
  KeyRound,
  Compass,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Activity
} from 'lucide-react';
import { useAssurance } from '../context/AssuranceContext';
import { AssuranceHealthGauge } from '../components/charts/AssuranceHealthGauge';
import { DispositionBadge } from '../components/common/DispositionBadge';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { HashDisplay } from '../components/common/HashDisplay';

export const AssuranceOverview: React.FC = () => {
  const { report, benchmarkData, modelBenchmark, shiftResult, setActiveTab, setSelectedFinding } = useAssurance();

  const healthScore = report?.overall_health_score ?? 100;
  const disposition = report?.overall_disposition ?? 'ACCEPT';
  const findings = report?.findings || [];
  const auditHash = report?.audit_trail_hash || '';

  // Calculate Module Findings
  const dataFindings = findings.filter(f => f.category === 'data_integrity');
  const modelFindings = findings.filter(f => f.category === 'model_integrity');
  const shiftFindings = findings.filter(f => f.category === 'distribution_shift');
  const inferenceFindings = findings.filter(f => f.category === 'inference_provenance');

  const getDispositionExplanation = (disp: string) => {
    switch (disp) {
      case 'QUARANTINE':
        return 'Critical integrity breaches detected (compromised contributors, backdoor-like triggers, or model hash substitutions). Pipeline quarantined to prevent contaminated inference outputs.';
      case 'REVIEW':
        return 'Moderate anomalies or operational distribution drift identified. Analyst review is recommended before approving batch downstream.';
      case 'ACCEPT':
      default:
        return 'All pipeline assets pass cryptographic verification and baseline operational tolerances without anomalous findings.';
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Executive Header */}
      <div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-wide font-sans">
              Computer Vision Integrity Assurance
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Evidence-based assurance across data, models, inference and operational distribution.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400">Current Audit Digest:</span>
            <HashDisplay hash={auditHash} truncateLength={18} />
          </div>
        </div>
      </div>

      {/* Top-Level 5 Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Card 1: Overall Health */}
        <div className="bg-[#0c1220] border border-slate-800 p-4 rounded-xl relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">System Health</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="my-2">
            <span className="text-3xl font-bold font-mono text-white">
              {healthScore.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 ml-1">/ 100</span>
          </div>
          <p className="text-[11px] text-slate-400">
            {healthScore < 50 ? 'Significant risk detected' : healthScore < 80 ? 'Moderate warnings' : 'Nominal integrity'}
          </p>
        </div>

        {/* Card 2: Data Integrity */}
        <div
          onClick={() => setActiveTab('data')}
          className="bg-[#0c1220] border border-slate-800 hover:border-slate-700 p-4 rounded-xl cursor-pointer transition-all flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Data Integrity</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="my-2">
            <span className={`text-xl font-bold font-mono ${dataFindings.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {dataFindings.length > 0 ? `${dataFindings.length} FINDINGS` : 'CLEAN'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 truncate">
            {benchmarkData?.dataset?.total_samples ? `${benchmarkData.dataset.total_samples} samples scanned` : 'Dataset verified'}
          </p>
        </div>

        {/* Card 3: Model Integrity */}
        <div
          onClick={() => setActiveTab('model')}
          className="bg-[#0c1220] border border-slate-800 hover:border-slate-700 p-4 rounded-xl cursor-pointer transition-all flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Model Integrity</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="my-2">
            <span className={`text-xl font-bold font-mono ${modelFindings.length > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {modelFindings.length > 0 ? 'ANOMALIES' : 'VERIFIED'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 truncate">
            {modelBenchmark ? 'White-box + Fingerprint' : 'SHA-256 matched'}
          </p>
        </div>

        {/* Card 4: Inference Integrity */}
        <div
          onClick={() => setActiveTab('inference')}
          className="bg-[#0c1220] border border-slate-800 hover:border-slate-700 p-4 rounded-xl cursor-pointer transition-all flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Inference Integrity</span>
            <KeyRound className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="my-2">
            <span className={`text-xl font-bold font-mono ${inferenceFindings.length > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {inferenceFindings.length > 0 ? 'TAMPERED' : 'AUTHENTIC'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            HMAC + Replay Protection
          </p>
        </div>

        {/* Card 5: Distribution Status */}
        <div
          onClick={() => setActiveTab('shift')}
          className="bg-[#0c1220] border border-slate-800 hover:border-slate-700 p-4 rounded-xl cursor-pointer transition-all flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Distribution Status</span>
            <Compass className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="my-2">
            <span className={`text-xl font-bold font-mono ${shiftResult?.material_shift_detected ? 'text-amber-400' : 'text-emerald-400'}`}>
              {shiftResult?.shift_classification || 'NO_SHIFT'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 truncate">
            {shiftResult?.dimensions?.length ? `${shiftResult.dimensions.length} physical proxies` : 'Reference matched'}
          </p>
        </div>
      </div>

      {/* Central Health Gauge & Governance Disposition Banner */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 bg-[#0c1220] border border-slate-800 p-6 rounded-xl">
        {/* Central Radial Gauge */}
        <div className="flex flex-col items-center justify-center p-2 border-b lg:border-b-0 lg:border-r border-slate-800">
          <AssuranceHealthGauge score={healthScore} size={200} />
          <p className="text-xs font-mono text-slate-400 mt-3 text-center">
            Evidence-Fused Assurance Metric
          </p>
        </div>

        {/* Governance Verdict */}
        <div className="lg:col-span-2 flex flex-col justify-center space-y-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs font-mono uppercase text-slate-400">
                Final Governance Disposition
              </span>
              <DispositionBadge disposition={disposition} size="lg" />
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">
              {getDispositionExplanation(disposition)}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-800 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Critical Violations:</span>
              <span className="font-mono font-bold text-rose-400">
                {report?.summary_counts?.CRITICAL || 0}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">High/Medium Warnings:</span>
              <span className="font-mono font-bold text-amber-400">
                {(report?.summary_counts?.HIGH || 0) + (report?.summary_counts?.MEDIUM || 0)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Report Status:</span>
              <span className="font-mono text-cyan-300">
                IMMUTABLE (AIRGAP)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Four Lifecycle Cards Flowing into ASSURANCE ENGINE */}
      <div>
        <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <span>End-to-End Forensics Lifecycle Flow</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
          {/* Node 1: DATA */}
          <div
            onClick={() => setActiveTab('data')}
            className="bg-[#0b101d] border border-slate-800 hover:border-cyan-500/50 p-4 rounded-xl cursor-pointer transition-all"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-cyan-400 font-semibold">STAGE 01</span>
              <Database className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">DATA INTEGRITY</h3>
            <p className="text-xs text-slate-400 mt-1">
              Backdoors, mislabels, duplicate flood & OOD anomalies
            </p>
            <div className="mt-3 flex items-center text-xs text-cyan-400 gap-1 font-mono">
              <span>Inspect Data</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Node 2: MODEL */}
          <div
            onClick={() => setActiveTab('model')}
            className="bg-[#0b101d] border border-slate-800 hover:border-cyan-500/50 p-4 rounded-xl cursor-pointer transition-all"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-cyan-400 font-semibold">STAGE 02</span>
              <Cpu className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">MODEL INTEGRITY</h3>
            <p className="text-xs text-slate-400 mt-1">
              SHA-256 hash match, white-box tensors & backdoor probes
            </p>
            <div className="mt-3 flex items-center text-xs text-cyan-400 gap-1 font-mono">
              <span>Inspect Model</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Node 3: INFERENCE */}
          <div
            onClick={() => setActiveTab('inference')}
            className="bg-[#0b101d] border border-slate-800 hover:border-cyan-500/50 p-4 rounded-xl cursor-pointer transition-all"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-cyan-400 font-semibold">STAGE 03</span>
              <KeyRound className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">INFERENCE PROVENANCE</h3>
            <p className="text-xs text-slate-400 mt-1">
              Image + model digest + predictions HMAC-SHA256 binding
            </p>
            <div className="mt-3 flex items-center text-xs text-cyan-400 gap-1 font-mono">
              <span>Verify Records</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Node 4: ENVIRONMENT */}
          <div
            onClick={() => setActiveTab('shift')}
            className="bg-[#0b101d] border border-slate-800 hover:border-cyan-500/50 p-4 rounded-xl cursor-pointer transition-all"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-cyan-400 font-semibold">STAGE 04</span>
              <Compass className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">ENVIRONMENT SHIFT</h3>
            <p className="text-xs text-slate-400 mt-1">
              Terrain, illumination, sensor noise & season drift tests
            </p>
            <div className="mt-3 flex items-center text-xs text-cyan-400 gap-1 font-mono">
              <span>View Shift</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>
      </div>

      {/* Identified Forensic Findings Table */}
      <div className="bg-[#0c1220] border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">
              Identified Assurance Findings ({findings.length})
            </h3>
          </div>
          <button
            onClick={() => setActiveTab('findings')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1"
          >
            <span>View All Findings</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {findings.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No integrity findings flagged. All systems clean under current rules.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {findings.slice(0, 5).map(f => (
              <div
                key={f.finding_id}
                onClick={() => setSelectedFinding(f)}
                className="p-4 hover:bg-slate-800/40 transition-colors cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} size="sm" />
                    <span className="text-sm font-medium text-white">{f.title}</span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-1">
                    {f.human_readable_reason}
                  </p>
                </div>

                <div className="flex items-center gap-4 text-xs shrink-0">
                  <div className="text-right">
                    <span className="text-slate-400 block text-[11px]">Affected Asset</span>
                    <code className="text-cyan-300 font-mono text-xs">{f.affected_asset}</code>
                  </div>
                  <DispositionBadge disposition={f.recommended_disposition} size="sm" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
