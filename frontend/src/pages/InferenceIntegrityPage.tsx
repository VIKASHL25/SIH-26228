import React, { useState, useEffect } from 'react';
import {
  KeyRound,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  FileCheck,
  Layers,
  Image,
  Cpu,
  Hash,
  Clock,
  RotateCcw,
  Bug,
  CheckCircle2,
  XCircle,
  AlertOctagon
} from 'lucide-react';
import { api } from '../services/api';
import { ProtectedInferenceRecord, ProvenanceVerificationResult } from '../types';
import { HashDisplay } from '../components/common/HashDisplay';

export const InferenceIntegrityPage: React.FC = () => {
  const [demoData, setDemoData] = useState<{
    clean_record: ProtectedInferenceRecord;
    clean_chain: ProtectedInferenceRecord[];
    tampered_scenarios: Record<string, ProtectedInferenceRecord>;
  } | null>(null);

  const [currentRecord, setCurrentRecord] = useState<ProtectedInferenceRecord | null>(null);
  const [verificationResult, setVerificationResult] = useState<ProvenanceVerificationResult | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [chainResult, setChainResult] = useState<any | null>(null);
  const [isVerifyingChain, setIsVerifyingChain] = useState<boolean>(false);
  const [selectedScenario, setSelectedScenario] = useState<string>('clean');

  // Load authentic demo records from backend
  useEffect(() => {
    const loadDemoRecords = async () => {
      try {
        const data = await api.getDemoInferenceRecords();
        setDemoData(data);
        setCurrentRecord(data.clean_record);
      } catch (err) {
        console.error('Failed to load demo inference records:', err);
      }
    };
    loadDemoRecords();
  }, []);

  const handleVerifyRecord = async (recordToVerify?: ProtectedInferenceRecord) => {
    const rec = recordToVerify || currentRecord;
    if (!rec) return;

    setIsVerifying(true);
    setVerificationResult(null);
    try {
      const res = await api.verifyInferenceRecord(rec);
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({
        record_id: rec.record_id,
        verification_passed: false,
        tamper_detected: true,
        replay_detected: false,
        sequence_violation: false,
        tampered_fields: ['payload'],
        details: `Verification failed: ${err.message}`,
        field_verifications: {}
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleVerifyChain = async () => {
    if (!demoData?.clean_chain) return;

    setIsVerifyingChain(true);
    setChainResult(null);
    try {
      const res = await api.verifyInferenceChain(demoData.clean_chain);
      setChainResult(res);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsVerifyingChain(false);
    }
  };

  const applyScenario = (key: string) => {
    setSelectedScenario(key);
    setVerificationResult(null);
    if (key === 'clean' && demoData?.clean_record) {
      setCurrentRecord(demoData.clean_record);
    } else if (demoData?.tampered_scenarios[key]) {
      setCurrentRecord(demoData.tampered_scenarios[key]);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">
                Inference Provenance & Cryptographic Output Integrity
              </h1>
              <p className="text-xs text-slate-400">
                Cryptographic binding of Input Hash + Model Digest + Config + Predictions + HMAC-SHA256 & Replay Protection
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleVerifyRecord()}
              disabled={isVerifying || !currentRecord}
              className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm border border-cyan-400/30 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{isVerifying ? 'VERIFYING...' : 'VERIFY CURRENT RECORD'}</span>
            </button>
            <button
              onClick={handleVerifyChain}
              disabled={isVerifyingChain}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-4 py-2 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isVerifyingChain ? 'CHECKING CHAIN...' : 'VERIFY INFERENCE CHAIN'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Forensic Evidence Chain Visualization */}
      <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl">
        <div className="text-xs font-mono uppercase text-slate-400 mb-4 flex items-center gap-2">
          <span>Cryptographic Chain-of-Custody Flow</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 text-center text-xs font-mono">
          {/* Step 1: Input Image */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <Image className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">INPUT IMAGE</span>
            <span className="text-[10px] text-slate-400">Raw Pixels</span>
          </div>

          {/* Step 2: Input Hash */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <Hash className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">INPUT HASH</span>
            <span className="text-[10px] text-cyan-300">SHA-256</span>
          </div>

          {/* Step 3: Model Digest */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <Cpu className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">MODEL DIGEST</span>
            <span className="text-[10px] text-cyan-300">Weights SHA</span>
          </div>

          {/* Step 4: Preprocessing */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <Layers className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">CONFIG</span>
            <span className="text-[10px] text-slate-400">Canonical JSON</span>
          </div>

          {/* Step 5: Inference Execution */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <Cpu className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">INFERENCE</span>
            <span className="text-[10px] text-slate-400">Local Enclave</span>
          </div>

          {/* Step 6: Prediction Bboxes */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <FileCheck className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">PREDICTIONS</span>
            <span className="text-[10px] text-slate-400">Sorted JSON</span>
          </div>

          {/* Step 7: Cryptographic Binding */}
          <div className="bg-[#080c16] border border-cyan-500/40 p-2.5 rounded-lg flex flex-col items-center justify-between bg-cyan-950/20">
            <KeyRound className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-cyan-300 font-semibold text-[11px]">BINDING HASH</span>
            <span className="text-[10px] text-cyan-400 font-bold">HMAC-SHA256</span>
          </div>

          {/* Step 8: Replay Registry */}
          <div className="bg-[#080c16] border border-slate-800 p-2.5 rounded-lg flex flex-col items-center justify-between">
            <Clock className="w-4 h-4 text-cyan-400 mb-1" />
            <span className="text-white font-semibold text-[11px]">NONCE / SEQ</span>
            <span className="text-[10px] text-slate-400">Replay Registry</span>
          </div>
        </div>
      </div>

      {/* Interactive Tampering Simulation Controls */}
      <div className="bg-[#0c1220] border border-slate-800 p-4 rounded-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Bug className="w-4 h-4 text-amber-400" />
              <span>Forensic Tampering & Replay Simulation Testbed</span>
            </h3>
            <p className="text-[11px] text-slate-400">
              Select an authentic signed record or inject controlled adversarial modifications to test tamper detection
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => applyScenario('clean')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              selectedScenario === 'clean'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50 shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            ✓ Authentic Record (Clean)
          </button>
          <button
            onClick={() => applyScenario('tampered_predictions')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              selectedScenario === 'tampered_predictions'
                ? 'bg-rose-950 text-rose-300 border border-rose-500/50 shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            ✗ Altered Predictions (BBox Tampered)
          </button>
          <button
            onClick={() => applyScenario('tampered_model_digest')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              selectedScenario === 'tampered_model_digest'
                ? 'bg-rose-950 text-rose-300 border border-rose-500/50 shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            ✗ Model Digest Substitution
          </button>
          <button
            onClick={() => applyScenario('replayed_nonce')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              selectedScenario === 'replayed_nonce'
                ? 'bg-rose-950 text-rose-300 border border-rose-500/50 shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            ✗ Replay Attack (Duplicate Nonce)
          </button>
          <button
            onClick={() => applyScenario('sequence_violation')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              selectedScenario === 'sequence_violation'
                ? 'bg-rose-950 text-rose-300 border border-rose-500/50 shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            ✗ Sequence Discontinuity (Seq Jump)
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in fade-in duration-200 ${
            verificationResult.verification_passed
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
          }`}
        >
          <div className="flex items-start gap-3">
            {verificationResult.verification_passed ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertOctagon className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono font-bold text-sm">
                  {verificationResult.verification_passed
                    ? 'CRYPTOGRAPHIC BINDING VERIFIED: NO TAMPERING DETECTED'
                    : 'INTEGRITY VIOLATION DETECTED: RECORD TAMPERED OR REPLAYED'}
                </h3>
              </div>
              <p className="text-xs text-slate-300 mt-1">
                {verificationResult.details}
              </p>
            </div>
          </div>

          {/* Violated Fields Pill */}
          {verificationResult.tampered_fields && verificationResult.tampered_fields.length > 0 && (
            <div className="text-right shrink-0">
              <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                Violated Fields:
              </span>
              <div className="flex flex-wrap gap-1 justify-end">
                {verificationResult.tampered_fields.map(f => (
                  <span key={f} className="font-mono text-xs px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-700">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Current Inference Record Dossier */}
      {currentRecord && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Metadata Breakdown */}
          <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl space-y-4">
            <h3 className="text-sm font-semibold text-white tracking-wide">
              Record Header & Cryptographic Tokens
            </h3>

            <div className="space-y-3 text-xs font-mono">
              <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded border border-slate-800">
                <span className="text-slate-400">Record ID:</span>
                <span className="text-white font-bold select-all">{currentRecord.record_id}</span>
              </div>

              <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded border border-slate-800">
                <span className="text-slate-400">Sequence Number:</span>
                <span className="text-cyan-300 font-bold">#{currentRecord.sequence_number}</span>
              </div>

              <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded border border-slate-800">
                <span className="text-slate-400">Freshness Nonce:</span>
                <span className="text-slate-300 select-all truncate max-w-xs">{currentRecord.nonce}</span>
              </div>

              <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded border border-slate-800">
                <span className="text-slate-400">Input Image SHA-256:</span>
                <HashDisplay hash={currentRecord.image_hash_sha256} truncateLength={16} />
              </div>

              <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded border border-slate-800">
                <span className="text-slate-400">Model Digest SHA-256:</span>
                <HashDisplay hash={currentRecord.model_digest_sha256} truncateLength={16} />
              </div>

              <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded border border-slate-800">
                <span className="text-slate-400">HMAC-SHA256 Signature:</span>
                <HashDisplay hash={currentRecord.hmac_signature} truncateLength={16} />
              </div>
            </div>
          </div>

          {/* Predictions & Raw Payload */}
          <div className="bg-[#0c1220] border border-slate-800 p-5 rounded-xl space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-sm font-semibold text-white tracking-wide">
                  Bound Object Detection Predictions
                </h3>
                <span className="text-xs font-mono text-cyan-400">
                  {currentRecord.predictions.length} Detections
                </span>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {currentRecord.predictions.map((p, idx) => (
                  <div key={idx} className="bg-slate-900/80 border border-slate-800 p-2.5 rounded text-xs font-mono flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-white uppercase">{p.category_name}</span>
                      <span className="text-slate-400 ml-2">Conf: {(p.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <code className="text-cyan-300 text-[11px]">
                      box: [{p.box.map(b => b.toFixed(1)).join(', ')}]
                    </code>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800">
              <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                Canonical Binding Digest
              </span>
              <div className="p-2 bg-black/60 rounded border border-slate-800 font-mono text-xs text-cyan-300 break-all select-all">
                {currentRecord.binding_hash_sha256}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Record Chain Verification Results */}
      {chainResult && (
        <div className="bg-[#0c1220] border border-slate-800 rounded-xl overflow-hidden animate-in fade-in duration-200">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">
                Inference Sequence Chain Verification ({chainResult.total_records} Records)
              </h3>
            </div>
            <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded border ${
              chainResult.chain_valid ? 'bg-emerald-950 text-emerald-300 border-emerald-700' : 'bg-rose-950 text-rose-300 border-rose-700'
            }`}>
              CHAIN STATUS: {chainResult.status}
            </span>
          </div>

          <div className="divide-y divide-slate-800/60 font-mono text-xs">
            {chainResult.evaluated_records.map((rec: any, idx: number) => (
              <div key={idx} className="p-3.5 flex items-center justify-between hover:bg-slate-900/40">
                <div className="flex items-center gap-3">
                  <span className="text-slate-500 font-bold">#{rec.sequence_number}</span>
                  <span className="text-white font-medium">{rec.record_id}</span>
                  <span className="text-slate-400 text-[11px]">Nonce: {rec.nonce.substring(0, 12)}...</span>
                </div>
                <div>
                  {rec.verification_passed ? (
                    <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      PASS
                    </span>
                  ) : (
                    <span className="text-rose-400 flex items-center gap-1 font-semibold">
                      <XCircle className="w-3.5 h-3.5" />
                      FAIL
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
