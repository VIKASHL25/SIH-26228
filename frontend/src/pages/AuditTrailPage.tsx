import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  Database, 
  Link2, 
  FileText, 
  AlertTriangle, 
  Clock, 
  Search,
  CheckCircle2,
  XCircle,
  Hash,
  Layers,
  FileCode,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import { AuditEvent } from '../types';
import { HashDisplay } from '../components/common/HashDisplay';

export const AuditTrailPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [originalEvents, setOriginalEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<{
    isValid: boolean;
    status: string;
    message: string;
    brokenIndex: number | null;
    latestHash: string;
  } | null>(null);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEventType, setSelectedEventType] = useState<string>('ALL');
  const [tamperedIndex, setTamperedIndex] = useState<number | null>(null);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [rawJsonModalOpen, setRawJsonModalOpen] = useState(false);

  // Load audit trail on mount
  useEffect(() => {
    fetchAuditTrail();
  }, []);

  const fetchAuditTrail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.verifyAuditChain();
      setEvents(res.events);
      setOriginalEvents(JSON.parse(JSON.stringify(res.events)));
      setVerificationResult({
        isValid: res.is_valid,
        status: res.verification_status,
        message: res.message,
        brokenIndex: res.broken_event_index,
        latestHash: res.latest_event_hash
      });
      setTamperedIndex(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit chain');
    } finally {
      setLoading(false);
    }
  };

  const verifyLedger = async (chainToVerify?: AuditEvent[]) => {
    setVerifying(true);
    try {
      const currentList = chainToVerify || events;
      const res = await api.verifyAuditChain(currentList);
      setVerificationResult({
        isValid: res.is_valid,
        status: res.verification_status,
        message: res.message,
        brokenIndex: res.broken_event_index,
        latestHash: res.latest_event_hash
      });
    } catch (err: any) {
      setError(err.message || 'Ledger verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const simulateTampering = (targetIndex: number = 2) => {
    if (events.length <= targetIndex) return;

    // Mutate the event payload in memory without recalculating the chained hashes
    const mutated = JSON.parse(JSON.stringify(events)) as AuditEvent[];
    mutated[targetIndex].event_summary = "[MALICIOUS ALTERATION] Verdict overwritten to ACCEPT. Evidence suppressed.";
    mutated[targetIndex].event_data = {
      ...mutated[targetIndex].event_data,
      tampered: true,
      adversarial_injection: "Bypass quarantine"
    };

    setEvents(mutated);
    setTamperedIndex(targetIndex);
    verifyLedger(mutated);
  };

  const restoreLedger = () => {
    setEvents(JSON.parse(JSON.stringify(originalEvents)));
    setTamperedIndex(null);
    verifyLedger(originalEvents);
  };

  const filteredEvents = events.filter(e => {
    const matchesSearch = 
      e.event_summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.affected_asset.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.current_event_hash.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesType = selectedEventType === 'ALL' || e.event_type === selectedEventType;
    return matchesSearch && matchesType;
  });

  const eventTypes = Array.from(new Set(events.map(e => e.event_type)));

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-1">
            <Link2 className="w-4 h-4" />
            Cryptographic Integrity • Module 3C
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            Tamper-Evident Audit Ledger
            <span className="text-xs font-mono px-2.5 py-1 bg-cyan-950/70 border border-cyan-800/60 text-cyan-300 rounded-md">
              SHA-256 Chained
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Append-only cryptographically linked audit journal tracking all dataset evaluations, model assessments, 
            inference verifications, and governance verdicts from Genesis block to current Head.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => verifyLedger()}
            disabled={verifying}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-cyan-900/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${verifying ? 'animate-spin' : ''}`} />
            Verify Ledger
          </button>

          {tamperedIndex === null ? (
            <button
              onClick={() => simulateTampering(2)}
              className="flex items-center gap-2 px-4 py-2 bg-amber-950/50 hover:bg-amber-900/60 border border-amber-600/50 text-amber-300 rounded-lg text-sm font-medium transition-all"
              title="Simulate retroactive payload alteration in ledger block #2 to test verification failure"
            >
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Simulate Tampering (Block #2)
            </button>
          ) : (
            <button
              onClick={restoreLedger}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-600/50 text-emerald-300 rounded-lg text-sm font-medium transition-all"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Restore Original Ledger
            </button>
          )}

          <button
            onClick={() => setRawJsonModalOpen(true)}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-all"
          >
            <FileCode className="w-4 h-4 text-slate-400" />
            Raw Ledger JSON
          </button>
        </div>
      </div>

      {/* Verification Status Card */}
      {verificationResult && (
        <div className={`p-5 rounded-xl border transition-all ${
          verificationResult.isValid 
            ? 'bg-emerald-950/20 border-emerald-800/50 shadow-lg shadow-emerald-950/10' 
            : 'bg-rose-950/30 border-rose-700/60 shadow-lg shadow-rose-950/20 animate-pulse-subtle'
        }`}>
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className={`p-2.5 rounded-lg border mt-0.5 ${
                verificationResult.isValid 
                  ? 'bg-emerald-900/40 border-emerald-700/60 text-emerald-400' 
                  : 'bg-rose-900/50 border-rose-600/70 text-rose-400'
              }`}>
                {verificationResult.isValid ? (
                  <ShieldCheck className="w-6 h-6" />
                ) : (
                  <ShieldAlert className="w-6 h-6" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <span className={`text-base font-bold uppercase tracking-wider ${
                    verificationResult.isValid ? 'text-emerald-300' : 'text-rose-300'
                  }`}>
                    {verificationResult.status}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-800 border border-slate-700 text-slate-300">
                    Chain Depth: {events.length} Blocks
                  </span>
                  {tamperedIndex !== null && (
                    <span className="text-xs px-2 py-0.5 rounded font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      SIMULATION ACTIVE: BLOCK #{tamperedIndex} MUTATED
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-300 mt-1">
                  {verificationResult.message}
                </p>
                {verificationResult.brokenIndex !== null && (
                  <div className="mt-2 text-xs font-mono text-rose-400 flex items-center gap-2 bg-rose-950/60 px-3 py-1.5 rounded border border-rose-900/50 inline-flex">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    Cryptographic cascade broken at Sequence #{verificationResult.brokenIndex}: Stored previous hash does not match recomputed hash of predecessor.
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-slate-900/80 px-4 py-2.5 rounded-lg border border-slate-800/80 font-mono text-xs w-full lg:w-auto">
              <div>
                <span className="text-slate-500 uppercase tracking-widest text-[10px] block">Ledger Head Digest</span>
                <HashDisplay hash={verificationResult.latestHash} truncateLength={16} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        <div className="flex items-center gap-2 flex-1 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by summary, event type, asset or hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-md text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Event Type:</span>
          <select
            value={selectedEventType}
            onChange={(e) => setSelectedEventType(e.target.value)}
            className="bg-slate-950 border border-slate-700/80 rounded-md px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Event Types ({events.length})</option>
            {eventTypes.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Ledger Chain Timeline */}
      {loading ? (
        <div className="text-center py-16 bg-slate-900/40 rounded-xl border border-slate-800/60">
          <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin mx-auto mb-3" />
          <p className="text-slate-400 text-sm">Verifying cryptographic hash sequence...</p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/30 rounded-xl border border-slate-800/60 text-slate-500 text-sm">
          No audit events match current search filter.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2 text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>Cryptographic Chain Timeline (Genesis → Head)</span>
            <span>{filteredEvents.length} Linked Blocks</span>
          </div>

          <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-800">
            {filteredEvents.map((evt, idx) => {
              const isGenesis = evt.sequence_index === 0;
              const isTampered = tamperedIndex === evt.sequence_index;
              const isBrokenHere = verificationResult?.brokenIndex === evt.sequence_index;
              const isExpanded = expandedEventId === evt.event_id;

              return (
                <div 
                  key={evt.event_id || idx}
                  className={`relative group rounded-xl border transition-all ${
                    isTampered 
                      ? 'bg-amber-950/30 border-amber-600/70 shadow-lg shadow-amber-950/20' 
                      : isBrokenHere
                      ? 'bg-rose-950/40 border-rose-600/80 shadow-lg shadow-rose-950/30'
                      : 'bg-slate-900/80 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  {/* Timeline Node Indicator */}
                  <div className={`absolute -left-6 sm:-left-8 top-5 w-5 sm:w-6 h-5 sm:h-6 rounded-full border flex items-center justify-center -translate-x-1/2 shadow-md ${
                    isTampered
                      ? 'bg-amber-950 border-amber-500 text-amber-400'
                      : isBrokenHere
                      ? 'bg-rose-950 border-rose-500 text-rose-400 animate-pulse'
                      : isGenesis
                      ? 'bg-cyan-950 border-cyan-500 text-cyan-400'
                      : 'bg-slate-900 border-emerald-500/70 text-emerald-400'
                  }`}>
                    {isTampered || isBrokenHere ? (
                      <XCircle className="w-3.5 h-3.5" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                  </div>

                  {/* Header Row */}
                  <div className="p-4 sm:p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-slate-800/60">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${
                        isGenesis 
                          ? 'bg-cyan-950/80 border-cyan-700/60 text-cyan-300' 
                          : 'bg-slate-800 border-slate-700 text-slate-300'
                      }`}>
                        #{evt.sequence_index}
                      </span>

                      <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-slate-950 border border-slate-800 text-slate-200">
                        {evt.event_type}
                      </span>

                      <span className="text-xs text-slate-400 font-mono">
                        Asset: <span className="text-slate-200">{evt.affected_asset}</span>
                      </span>

                      {isTampered && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40 uppercase">
                          Tampered in Memory
                        </span>
                      )}

                      {isBrokenHere && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 uppercase">
                          Chain Linkage Broken
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      {evt.timestamp_iso || new Date(evt.timestamp_utc * 1000).toISOString()}
                    </div>
                  </div>

                  {/* Content Body */}
                  <div className="p-4 sm:p-5 space-y-4">
                    <p className={`text-sm ${isTampered ? 'text-amber-200 font-medium' : 'text-slate-200'}`}>
                      {evt.event_summary}
                    </p>

                    {/* Hash Pair Linkage Display */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs font-mono">
                        <div className="text-[10px] uppercase text-slate-500 tracking-wider mb-1 flex items-center justify-between">
                          <span>Previous Block Hash (prev_entry_hash)</span>
                          {isGenesis && <span className="text-cyan-400 text-[10px]">GENESIS ZERO SEED</span>}
                        </div>
                        <HashDisplay hash={evt.previous_event_hash} truncateLength={18} />
                      </div>

                      <div className={`p-2.5 rounded-lg border text-xs font-mono ${
                        isTampered || isBrokenHere
                          ? 'bg-rose-950/20 border-rose-800/50'
                          : 'bg-slate-950/70 border-slate-800/80'
                      }`}>
                        <div className="text-[10px] uppercase text-slate-500 tracking-wider mb-1 flex items-center justify-between">
                          <span>Current Block Digest (entry_hash)</span>
                          <span className="text-emerald-400 text-[10px]">SHA-256</span>
                        </div>
                        <HashDisplay hash={evt.current_event_hash} truncateLength={18} />
                      </div>
                    </div>

                    {/* Collapsible Details */}
                    <div>
                      <button
                        onClick={() => setExpandedEventId(isExpanded ? null : evt.event_id)}
                        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 font-mono transition-colors"
                      >
                        {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        {isExpanded ? 'Hide Payload Event Data' : 'View Payload Event Data'}
                      </button>

                      {isExpanded && (
                        <div className="mt-3 p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-60">
                          <pre>{JSON.stringify(evt.event_data, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Educational Explainer Box */}
      <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Info className="w-4 h-4 text-cyan-400" />
          Cryptographic Tamper-Evidence Principle (Hackathon Defense)
        </h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          The <strong className="text-slate-300 font-semibold">TamperEvidentAuditChain</strong> guarantees that audit events 
          cannot be altered, reordered, deleted, or retroactively inserted without breaking the cryptographic linkage. 
          Each block contains a canonical SHA-256 hash of its payload plus the hash of the preceding block: 
          <code className="text-cyan-300 mx-1 bg-slate-950 px-1 py-0.5 rounded">H_i = SHA256(H_i-1 || Payload_i)</code>. 
          If an adversary alters a historical verdict, every downstream block hash becomes invalid during automated walk verification.
        </p>
      </div>

      {/* Raw JSON Modal */}
      {rawJsonModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-mono text-white">
                <FileCode className="w-4 h-4 text-cyan-400" />
                Audit Ledger Canonical JSON Export
              </div>
              <button
                onClick={() => setRawJsonModalOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 font-mono text-xs text-slate-300 bg-slate-950">
              <pre>{JSON.stringify(events, null, 2)}</pre>
            </div>
            <div className="p-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(events, null, 2));
                  alert('Audit ledger JSON copied to clipboard');
                }}
                className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-mono font-medium transition-all"
              >
                Copy to Clipboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditTrailPage;
