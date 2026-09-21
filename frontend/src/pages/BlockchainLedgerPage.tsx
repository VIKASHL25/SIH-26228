import React, { useState, useEffect } from 'react';
import {
  Link2,
  ShieldCheck,
  ShieldAlert,
  Layers,
  Database,
  Cpu,
  KeyRound,
  FileCheck2,
  RotateCcw,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Copy,
  Check,
  Zap,
  Activity,
  Box,
  Fingerprint
} from 'lucide-react';
import { api } from '../services/api';
import {
  BlockchainStatus,
  BlockchainEvent,
  DualVerificationResult,
  TamperSimulationResult,
  ReplaySimulationResult
} from '../types';
import { HashDisplay } from '../components/common/HashDisplay';

export const BlockchainLedgerPage: React.FC = () => {
  const [status, setStatus] = useState<BlockchainStatus | null>(null);
  const [events, setEvents] = useState<BlockchainEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<BlockchainEvent | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [dualResult, setDualResult] = useState<DualVerificationResult | null>(null);
  const [tamperResult, setTamperResult] = useState<TamperSimulationResult | null>(null);
  const [replayResult, setReplayResult] = useState<ReplaySimulationResult | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedTx, setCopiedTx] = useState<string | null>(null);

  const loadBlockchainData = async () => {
    setIsLoading(true);
    try {
      const [statusRes, eventsRes] = await Promise.all([
        api.getBlockchainStatus(),
        api.getBlockchainEvents({ limit: 50 })
      ]);
      setStatus(statusRes);
      setEvents(eventsRes);
    } catch (err) {
      console.error('Failed to load blockchain ledger data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadBlockchainData();
  }, []);

  const handleCopyTx = (txId: string) => {
    navigator.clipboard.writeText(txId);
    setCopiedTx(txId);
    setTimeout(() => setCopiedTx(null), 2000);
  };

  const handleVerifyActiveInference = async () => {
    setIsVerifying(true);
    setTamperResult(null);
    setReplayResult(null);
    try {
      // Fetch latest clean demo record and dual verify
      const demoData = await api.getDemoInferenceRecords();
      const res = await api.verifyInferenceOnBlockchain(demoData.clean_record);
      setDualResult(res);
      await loadBlockchainData();
    } catch (err: any) {
      console.error('Verification failed:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSimulateTampering = async () => {
    setIsVerifying(true);
    setDualResult(null);
    setReplayResult(null);
    try {
      const res = await api.simulateInferenceTampering();
      setTamperResult(res);
      setDualResult(res.verification_result);
      await loadBlockchainData();
    } catch (err) {
      console.error('Tampering simulation failed:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSimulateReplay = async () => {
    setIsVerifying(true);
    setDualResult(null);
    setTamperResult(null);
    try {
      const res = await api.simulateReplayAttack();
      setReplayResult(res);
      await loadBlockchainData();
    } catch (err) {
      console.error('Replay simulation failed:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  const filteredEvents = events.filter(evt => {
    const matchesType = activeFilter === 'ALL' || evt.event_type === activeFilter;
    const matchesSearch =
      searchQuery === '' ||
      evt.event_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      evt.asset_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (evt.tx_id && evt.tx_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (evt.contributor_id && evt.contributor_id.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Header & Telemetry */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 p-5 rounded-xl backdrop-blur-md">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <Link2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                Hyperledger Fabric Evidence Ledger
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Permissioned / Air-Gapped
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Immutable decentralized evidence anchor for multi-contributor datasets, model weights, inference provenance, and audit trails.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                status?.status === 'CONNECTED'
                  ? 'bg-emerald-400 animate-pulse'
                  : status?.status === 'LOCAL_EMULATED'
                  ? 'bg-amber-400'
                  : 'bg-rose-400'
              }`}
            />
            <span className="font-mono text-slate-300">
              {status?.status || 'OFFLINE'}
            </span>
          </div>

          <button
            onClick={loadBlockchainData}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 transition-colors font-medium"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-[#0a0f1d] border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Ledger Height</span>
            <Box className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-300">
            #{status?.ledger_height ?? 1}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Blocks verified</div>
        </div>

        <div className="bg-[#0a0f1d] border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Committed Transactions</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300">
            {status?.total_transactions ?? events.length}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Assurance events anchored</div>
        </div>

        <div className="bg-[#0a0f1d] border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Channel ID</span>
            <Layers className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-sm font-bold font-mono text-emerald-300 truncate">
            {status?.channel_id || 'assurancechannel'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Consortium Network</div>
        </div>

        <div className="bg-[#0a0f1d] border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Submitting Authority</span>
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-sm font-bold font-mono text-indigo-300 truncate">
            {status?.connected_msp || 'AssuranceAuthorityMSP'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Indian Army DGIS</div>
        </div>
      </div>

      {/* Interactive Forensics Control Panel */}
      <div className="bg-slate-900/50 border border-slate-800 p-5 rounded-xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              Live Blockchain Dual-Verification & Attack Testing Console
            </h2>
            <p className="text-xs text-slate-400">
              Demonstrate mathematical independence: Layer 1 Local Cryptographic verification combined with Layer 2 Immutable Fabric Evidence Ledger.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 pt-2">
          <button
            onClick={handleVerifyActiveInference}
            disabled={isVerifying}
            className="flex items-center gap-2 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-cyan-900/20 transition-all cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            {isVerifying ? 'Verifying on Ledger...' : 'Verify Clean Pipeline on Blockchain'}
          </button>

          <button
            onClick={handleSimulateTampering}
            disabled={isVerifying}
            className="flex items-center gap-2 px-4 py-2.5 bg-rose-600/90 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-rose-950/20 transition-all cursor-pointer"
          >
            <ShieldAlert className="w-4 h-4" />
            Simulate Inference Tampering Attack
          </button>

          <button
            onClick={handleSimulateReplay}
            disabled={isVerifying}
            className="flex items-center gap-2 px-4 py-2.5 bg-amber-600/90 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-amber-950/20 transition-all cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            Simulate Replay Attack Detection
          </button>
        </div>

        {/* Dual Verification Result Card */}
        {dualResult && (
          <div
            className={`mt-4 p-4 rounded-xl border ${
              dualResult.final_assurance_status === 'TRUST_VERIFIED'
                ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-950/20 border-rose-500/40 text-rose-300'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                {dualResult.final_assurance_status === 'TRUST_VERIFIED' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                )}
                <div>
                  <div className="font-bold text-sm flex items-center gap-2">
                    Dual Verification Outcome: {dualResult.final_assurance_status}
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        dualResult.recommended_disposition === 'ACCEPT'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      }`}
                    >
                      DISPOSITION: {dualResult.recommended_disposition}
                    </span>
                  </div>
                  {dualResult.discrepancy_reason && (
                    <div className="text-xs text-rose-400 mt-1 font-mono">
                      {dualResult.discrepancy_reason}
                    </div>
                  )}
                </div>
              </div>

              {dualResult.anchored_tx_id && (
                <div className="text-right">
                  <div className="text-[10px] text-slate-400">Committed Fabric Tx</div>
                  <div className="font-mono text-xs text-cyan-300 flex items-center gap-1">
                    {dualResult.anchored_tx_id.slice(0, 16)}...
                    <button
                      onClick={() => handleCopyTx(dualResult.anchored_tx_id!)}
                      className="p-1 hover:text-slate-100"
                      title="Copy Tx ID"
                    >
                      {copiedTx === dualResult.anchored_tx_id ? (
                        <Check className="w-3 h-3 text-emerald-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Layer 1 vs Layer 2 Comparison Table */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 text-xs font-mono">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="text-[11px] font-sans font-semibold text-slate-300 mb-1 flex items-center justify-between">
                  <span>Layer 1: Local Cryptography</span>
                  <span>{dualResult.local_verification_passed ? '✓ PASS' : '✗ FAIL'}</span>
                </div>
                <div className="space-y-1 text-slate-400 text-[11px]">
                  <div>HMAC Validation: {dualResult.local_verification_passed ? 'VALID' : 'TAMPERED / MISMATCH'}</div>
                  <div>Details: {dualResult.local_details}</div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="text-[11px] font-sans font-semibold text-slate-300 mb-1 flex items-center justify-between">
                  <span>Layer 2: Hyperledger Fabric</span>
                  <span>{dualResult.blockchain_hash_matched ? '✓ MATCH' : '✗ MISMATCH'}</span>
                </div>
                <div className="space-y-1 text-slate-400 text-[11px]">
                  <div>Registered Anchor: {dualResult.registered_blockchain_hash ? `${dualResult.registered_blockchain_hash.slice(0, 20)}...` : 'NONE'}</div>
                  <div>Current Binding: {dualResult.current_computed_hash ? `${dualResult.current_computed_hash.slice(0, 20)}...` : 'N/A'}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Events Filter & Explorer */}
      <div className="bg-[#0a0f1d] border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-cyan-400" />
              Immutable Blockchain Assurance Events ({filteredEvents.length})
            </h3>
            <p className="text-xs text-slate-400">
              Query verified blocks and transactions committed to the air-gapped Hyperledger Fabric ledger.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search event ID, asset ID, Tx..."
                className="pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500 w-52 sm:w-64"
              />
            </div>

            <select
              value={activeFilter}
              onChange={e => setActiveFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Event Types</option>
              <option value="INFERENCE_RECORDED">Inference Recorded</option>
              <option value="MODEL_REGISTERED">Model Registered</option>
              <option value="DATASET_REGISTERED">Dataset Registered</option>
              <option value="CONTRIBUTOR_REGISTERED">Contributor Registered</option>
              <option value="ASSURANCE_REPORT_RECORDED">Report Recorded</option>
              <option value="QUARANTINE_RECORDED">Quarantine Recorded</option>
            </select>
          </div>
        </div>

        {/* Events Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 font-mono text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4">Event ID</th>
                <th className="py-2.5 px-4">Event Type</th>
                <th className="py-2.5 px-4">Asset ID</th>
                <th className="py-2.5 px-4">Transaction ID</th>
                <th className="py-2.5 px-4">Block #</th>
                <th className="py-2.5 px-4">Timestamp (UTC)</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400 font-sans">
                    No matching blockchain events found.
                  </td>
                </tr>
              ) : (
                filteredEvents.map(evt => (
                  <tr key={evt.event_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-4 text-cyan-300 font-medium">
                      {evt.event_id}
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          evt.event_type.includes('TAMPER') || evt.event_type.includes('QUARANTINE')
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : evt.event_type.includes('REGISTERED')
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        }`}
                      >
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-slate-300 truncate max-w-xs">
                      {evt.asset_id}
                    </td>
                    <td className="py-2.5 px-4 text-slate-400">
                      {evt.tx_id ? `${evt.tx_id.slice(0, 14)}...` : '-'}
                    </td>
                    <td className="py-2.5 px-4 text-amber-300">
                      #{evt.block_number ?? 1}
                    </td>
                    <td className="py-2.5 px-4 text-slate-400">
                      {evt.timestamp_iso ? evt.timestamp_iso.replace('T', ' ').slice(0, 19) : '-'}
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedEvent(evt)}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded text-[10px] transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Event Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#0a0f1d] border border-slate-700 rounded-xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Link2 className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Blockchain Event: {selectedEvent.event_id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-200 text-sm font-mono p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="grid grid-cols-2 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-400">Event Type:</span>
                  <div className="text-cyan-300 font-bold">{selectedEvent.event_type}</div>
                </div>
                <div>
                  <span className="text-slate-400">Asset Identifier:</span>
                  <div className="text-slate-200 truncate">{selectedEvent.asset_id}</div>
                </div>
                <div>
                  <span className="text-slate-400">Block Height:</span>
                  <div className="text-amber-300">#{selectedEvent.block_number ?? 1}</div>
                </div>
                <div>
                  <span className="text-slate-400">Transaction ID:</span>
                  <div className="text-slate-300 truncate">{selectedEvent.tx_id}</div>
                </div>
                <div>
                  <span className="text-slate-400">Submitting MSP:</span>
                  <div className="text-indigo-300">{selectedEvent.signer_msp || 'AssuranceAuthorityMSP'}</div>
                </div>
                <div>
                  <span className="text-slate-400">Timestamp:</span>
                  <div className="text-slate-300">{selectedEvent.timestamp_iso}</div>
                </div>
              </div>

              {/* Cryptographic Fingerprints */}
              <div className="space-y-2">
                {selectedEvent.binding_hash && (
                  <div>
                    <div className="text-[11px] text-slate-400 mb-0.5">Inference Binding Hash (SHA-256):</div>
                    <HashDisplay hash={selectedEvent.binding_hash} />
                  </div>
                )}
                {selectedEvent.model_hash && (
                  <div>
                    <div className="text-[11px] text-slate-400 mb-0.5">Model Weights Hash (SHA-256):</div>
                    <HashDisplay hash={selectedEvent.model_hash} />
                  </div>
                )}
                {selectedEvent.manifest_hash && (
                  <div>
                    <div className="text-[11px] text-slate-400 mb-0.5">Dataset Manifest Hash (SHA-256):</div>
                    <HashDisplay hash={selectedEvent.manifest_hash} />
                  </div>
                )}
                {selectedEvent.report_hash && (
                  <div>
                    <div className="text-[11px] text-slate-400 mb-0.5">Off-Chain Report Hash (SHA-256):</div>
                    <HashDisplay hash={selectedEvent.report_hash} />
                  </div>
                )}
              </div>

              {/* Raw JSON Payload */}
              <div>
                <div className="text-[11px] text-slate-400 mb-1 font-sans">Full Committed Payload:</div>
                <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-[10px] text-slate-300 overflow-x-auto max-h-48">
                  {JSON.stringify(selectedEvent, null, 2)}
                </pre>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg font-medium"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
