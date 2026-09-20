import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Fingerprint,
  Layers,
  KeyRound,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Activity,
  Zap,
  Radio
} from 'lucide-react';
import { useAssurance } from '../context/AssuranceContext';
import { HashDisplay } from '../components/common/HashDisplay';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { DispositionBadge } from '../components/common/DispositionBadge';
import { api } from '../services/api';
import { WhiteBoxAnalysisResult } from '../types';

export const ModelIntegrityPage: React.FC = () => {
  const { modelBenchmark } = useAssurance();

  const [selectedScenarioKey, setSelectedScenarioKey] = useState<string>('clean');
  const [whiteboxData, setWhiteboxData] = useState<WhiteBoxAnalysisResult | null>(null);
  const [isLoadingWhitebox, setIsLoadingWhitebox] = useState<boolean>(false);

  const scenario = modelBenchmark ? modelBenchmark[selectedScenarioKey] : null;

  // Load real whitebox tensor inspection when scenario changes
  useEffect(() => {
    if (!scenario?.model_path) return;
    const fetchWhitebox = async () => {
      setIsLoadingWhitebox(true);
      try {
        const res = await api.analyzeModelWhitebox(scenario.model_path, 'demo_assets/sample_model.pt');
        setWhiteboxData(res);
      } catch (err) {
        console.error('Failed to load whitebox data:', err);
      } finally {
        setIsLoadingWhitebox(false);
      }
    };
    fetchWhitebox();
  }, [scenario?.model_path]);

  const scenariosList = [
    { key: 'clean', label: 'Clean Model (Trusted)', desc: 'Valid baseline checkpoint, matching SHA-256' },
    { key: 'tampered_weights', label: 'Tampered Weights', desc: 'Weight perturbation anomaly in conv1 layer' },
    { key: 'behavior_modified', label: 'Behavior Modified', desc: 'Dead neuron sparsity (99.8%) and entropy dislocation' },
    { key: 'substituted', label: 'Model Substitution', desc: 'Completely different model checkpoint substituted' }
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">
                Model Forensics & Checkpoint Integrity
              </h1>
              <p className="text-xs text-slate-400">
                Cryptographic hashing, white-box tensor parameters, behavioral fingerprinting, and trigger probing
              </p>
            </div>
          </div>

          {/* Access Mode Indicator */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">Access Mode:</span>
            <span className="px-2.5 py-1 rounded bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-semibold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              WHITE-BOX (Granted)
            </span>
          </div>
        </div>
      </div>

      {/* Model Scenario Selector Tabs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {scenariosList.map(s => {
          const isSelected = selectedScenarioKey === s.key;
          return (
            <button
              key={s.key}
              onClick={() => setSelectedScenarioKey(s.key)}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                isSelected
                  ? 'bg-[#11192e] border-cyan-500/60 shadow-md shadow-cyan-950/30'
                  : 'bg-[#0b101d] border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-bold font-mono ${isSelected ? 'text-cyan-300' : 'text-slate-300'}`}>
                  {s.label}
                </span>
                {isSelected && <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>}
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2">
                {s.desc}
              </p>
            </button>
          );
        })}
      </div>

      {/* Candidate vs Reference Cryptographic Digest Match */}
      {scenario && (
        <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl space-y-4">
          <div className="flex flex-col md:flex-row justify-between md:items-center pb-3 border-b border-slate-800 gap-2">
            <div>
              <h2 className="text-sm font-semibold text-white tracking-wide">
                Cryptographic File Digest Verification (SHA-256)
              </h2>
              <p className="text-xs text-slate-400">
                Streaming chunked digest comparison against trusted reference model baseline
              </p>
            </div>
            <div className="flex items-center gap-2">
              {scenario.reference_hash_match ? (
                <span className="px-3 py-1 rounded bg-emerald-950/70 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  HASH MATCH (VERIFIED)
                </span>
              ) : (
                <span className="px-3 py-1 rounded bg-rose-950/70 border border-rose-500/40 text-rose-300 text-xs font-mono font-bold flex items-center gap-1.5">
                  <XCircle className="w-4 h-4 text-rose-400" />
                  DIGEST MISMATCH (SUBSTITUTION)
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="bg-slate-900/70 p-3.5 rounded-lg border border-slate-800 space-y-1.5">
              <span className="text-slate-400 text-[11px] uppercase block">Candidate Model SHA-256 Digest</span>
              <div className="text-cyan-300 select-all break-all">{scenario.sha256}</div>
              <span className="text-[11px] text-slate-400 block pt-1">File: {scenario.model_path}</span>
            </div>

            <div className="bg-slate-900/70 p-3.5 rounded-lg border border-slate-800 space-y-1.5">
              <span className="text-slate-400 text-[11px] uppercase block">Reference Baseline SHA-256 Digest</span>
              <div className="text-emerald-400 select-all break-all">{scenario.reference_sha256}</div>
              <span className="text-[11px] text-slate-400 block pt-1">File: demo_assets/sample_model.pt</span>
            </div>
          </div>
        </div>
      )}

      {/* 4 Multi-Tier Model Evidence Cards */}
      {scenario && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Cryptographic Integrity */}
          <div className="bg-[#0b101d] border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <KeyRound className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono uppercase text-white font-semibold">Crypto Hash</span>
              </div>
              <span className={`text-[11px] font-mono font-bold ${scenario.reference_hash_match ? 'text-emerald-400' : 'text-rose-400'}`}>
                {scenario.reference_hash_match ? 'VERIFIED' : 'FAILED'}
              </span>
            </div>
            <div className="my-3">
              <div className="text-xl font-bold font-mono text-white">
                {scenario.reference_hash_match ? '100% MATCH' : 'MISMATCH'}
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                {scenario.reference_hash_match ? 'Zero byte variance from reference' : 'Unauthorized binary substitution'}
              </p>
            </div>
            <div className="text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800">
              Evidence: SHA-256 byte equality
            </div>
          </div>

          {/* Card 2: Behavioral Fingerprint */}
          <div className="bg-[#0b101d] border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Fingerprint className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono uppercase text-white font-semibold">Fingerprint</span>
              </div>
              <span className={`text-[11px] font-mono font-bold ${scenario.fingerprint_behavior_detected ? 'text-rose-400' : 'text-emerald-400'}`}>
                {scenario.fingerprint_behavior_detected ? 'ANOMALOUS' : 'ALIGNED'}
              </span>
            </div>
            <div className="my-3">
              <div className="text-xl font-bold font-mono text-white">
                {(scenario.fingerprint_prediction_agreement * 100).toFixed(0)}% AGREEMENT
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Entropy Dev: {scenario.fingerprint_entropy_deviation.toFixed(2)} bits
              </p>
            </div>
            <div className="text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800">
              Battery: 4-class reference battery
            </div>
          </div>

          {/* Card 3: White-Box Parameter Analysis */}
          <div className="bg-[#0b101d] border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono uppercase text-white font-semibold">Parameters</span>
              </div>
              <span className={`text-[11px] font-mono font-bold ${scenario.parameter_anomaly_detected ? 'text-rose-400' : 'text-emerald-400'}`}>
                {scenario.parameter_anomaly_detected ? 'ANOMALY' : 'NOMINAL'}
              </span>
            </div>
            <div className="my-3">
              <div className="text-xl font-bold font-mono text-white">
                {(scenario.weight_anomaly_score * 100).toFixed(0)}% ANOMALY
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Dead Neurons: {(scenario.dead_neurons_ratio * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800">
              Affected: <code className="text-amber-400">{scenario.affected_layer}</code>
            </div>
          </div>

          {/* Card 4: Backdoor Trigger Probe */}
          <div className="bg-[#0b101d] border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono uppercase text-white font-semibold">Trigger Probe</span>
              </div>
              <span className="text-[11px] font-mono text-slate-400 uppercase">
                [Heuristic]
              </span>
            </div>
            <div className="my-3">
              <div className="text-xl font-bold font-mono text-white">
                {scenario.backdoor_like_behavior}
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Pred Shift Rate: {(scenario.trigger_prediction_change_rate * 100).toFixed(0)}%
              </p>
            </div>
            <div className="text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800">
              Status: Controlled probe test
            </div>
          </div>
        </div>
      )}

      {/* Layer-by-Layer White-Box Parameter Inspection Table */}
      <div className="bg-[#0c1220] border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white tracking-wide">
              White-Box Tensor Parameter Inspection (Layer-by-Layer)
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {whiteboxData?.layer_stats?.length || 0} Layers Analyzed
          </span>
        </div>

        {isLoadingWhitebox ? (
          <div className="p-8 text-center text-slate-400 font-mono text-xs">
            Loading white-box tensor metrics...
          </div>
        ) : whiteboxData?.layer_stats && whiteboxData.layer_stats.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 bg-slate-900/60 text-[11px]">
                  <th className="p-3">Layer Name</th>
                  <th className="p-3">Tensor Shape</th>
                  <th className="p-3 text-right">Mean Weight</th>
                  <th className="p-3 text-right">Std Weight</th>
                  <th className="p-3 text-right">L2 Norm</th>
                  <th className="p-3 text-right">Zero Sparsity</th>
                  <th className="p-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {whiteboxData.layer_stats.map((layer, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3 font-semibold text-cyan-300">{layer.layer_name}</td>
                    <td className="p-3 text-slate-300">[{layer.shape.join(', ')}]</td>
                    <td className="p-3 text-right text-slate-300">{layer.mean_weight.toFixed(5)}</td>
                    <td className="p-3 text-right text-slate-300">{layer.std_weight.toFixed(5)}</td>
                    <td className="p-3 text-right text-slate-300">{layer.l2_norm.toFixed(3)}</td>
                    <td className="p-3 text-right text-slate-300">{(layer.zero_ratio * 100).toFixed(1)}%</td>
                    <td className="p-3 text-center">
                      {layer.anomaly_flag ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-bold">
                          ANOMALY
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                          NOMINAL
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 text-xs font-mono">
            {whiteboxData?.assessment_notes || 'White-box inspection complete.'}
          </div>
        )}
      </div>

      {/* Findings Summary for Scenario */}
      {scenario?.findings && scenario.findings.length > 0 && (
        <div className="bg-[#0c1220] border border-slate-800 p-4 rounded-xl">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono mb-2">
            Assessment Findings Rationale
          </h3>
          <ul className="space-y-1.5 text-xs text-slate-300">
            {scenario.findings.map((f, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-cyan-400 font-mono mt-0.5">•</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
