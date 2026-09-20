import React, { useState } from 'react';
import { 
  FileText, 
  Download, 
  Copy, 
  Printer, 
  RefreshCw, 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Layers, 
  FileCode,
  Info,
  Calendar,
  Hash
} from 'lucide-react';
import { useAssurance } from '../context/AssuranceContext';
import { DispositionBadge } from '../components/common/DispositionBadge';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { HashDisplay } from '../components/common/HashDisplay';

export const ReportsPage: React.FC = () => {
  const { report, runFullAudit, isAuditing, mode } = useAssurance();
  const [copySuccess, setCopySuccess] = useState(false);
  const [activeTab, setActiveTab] = useState<'formatted' | 'raw_json'>('formatted');

  const handleDownload = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CV_Assurance_Report_${report.report_id || 'RPT'}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopy = () => {
    if (!report) return;
    navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  if (!report) {
    return (
      <div className="text-center py-20 bg-slate-900/40 rounded-xl border border-slate-800">
        <FileText className="w-10 h-10 text-slate-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-white">No Assurance Report Generated</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
          Execute a full pipeline assurance evaluation to generate an authenticated compliance report.
        </p>
        <button
          onClick={runFullAudit}
          disabled={isAuditing}
          className="mt-5 px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-all inline-flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isAuditing ? 'animate-spin' : ''}`} />
          Generate Assurance Report
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden print:hidden">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-1">
            <FileText className="w-4 h-4" />
            Formal Compliance Artifact • PS 26228
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            Assurance Evaluation Report
            <span className="text-xs font-mono px-2.5 py-1 bg-cyan-950/70 border border-cyan-800/60 text-cyan-300 rounded-md">
              {report.report_id}
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic cryptographic evaluation report ready for compliance verification and defense audit.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setActiveTab(activeTab === 'formatted' ? 'raw_json' : 'formatted')}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-all"
          >
            <FileCode className="w-4 h-4 text-cyan-400" />
            {activeTab === 'formatted' ? 'View Raw JSON' : 'View Formatted'}
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-all"
          >
            <Copy className="w-4 h-4 text-slate-400" />
            {copySuccess ? 'Copied!' : 'Copy JSON'}
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-all"
          >
            <Download className="w-4 h-4 text-cyan-400" />
            Export JSON
          </button>

          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition-all shadow-lg shadow-cyan-900/20"
          >
            <Printer className="w-4 h-4" />
            Print / PDF
          </button>
        </div>
      </div>

      {activeTab === 'raw_json' ? (
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 font-mono text-xs text-slate-300 overflow-x-auto max-h-[80vh]">
          <pre>{JSON.stringify(report, null, 2)}</pre>
        </div>
      ) : (
        /* Printable Formatted Report View */
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 sm:p-10 space-y-8 shadow-2xl print:bg-white print:text-black print:border-none print:shadow-none print:p-0">
          
          {/* Report Top Header */}
          <div className="border-b border-slate-800 print:border-gray-300 pb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <div className="text-xs font-mono uppercase tracking-widest text-cyan-400 print:text-cyan-800 mb-1">
                National Security AI Assurance Directive • SIH-26228
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white print:text-black tracking-tight">
                Computer Vision Integrity Audit Report
              </h2>
              <div className="flex flex-wrap items-center gap-4 mt-2 text-xs font-mono text-slate-400 print:text-gray-600">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  Generated: {report.generated_at_utc}
                </span>
                <span>System Version: {report.system_version || '1.0.0'}</span>
                <span>Mode: {mode.toUpperCase()}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 print:text-gray-500 block">
                  Overall Verdict
                </span>
                <div className="mt-1">
                  <DispositionBadge disposition={report.overall_disposition} size="lg" />
                </div>
              </div>
            </div>
          </div>

          {/* Section 1: Executive Verdict & Health Scoring */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="p-5 rounded-xl bg-slate-950/60 print:bg-gray-50 border border-slate-800 print:border-gray-200">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 print:text-gray-600 block">
                System Health Score
              </span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className={`text-4xl font-bold font-mono ${
                  report.overall_health_score >= 80 ? 'text-emerald-400 print:text-emerald-700' :
                  report.overall_health_score >= 50 ? 'text-amber-400 print:text-amber-700' :
                  'text-rose-400 print:text-rose-700'
                }`}>
                  {report.overall_health_score.toFixed(1)}
                </span>
                <span className="text-sm text-slate-500 font-mono">/ 100</span>
              </div>
              <p className="text-xs text-slate-400 print:text-gray-600 mt-2">
                Weighted algorithmic penalization derived from critical triggers, parameter anomalies, and provenance violations.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-slate-950/60 print:bg-gray-50 border border-slate-800 print:border-gray-200">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 print:text-gray-600 block">
                Findings Summary
              </span>
              <div className="flex items-center gap-3 mt-3">
                <div className="text-center flex-1">
                  <span className="text-xs text-rose-400 font-bold block">CRITICAL</span>
                  <span className="text-xl font-bold text-white print:text-black font-mono">{report.summary_counts.CRITICAL}</span>
                </div>
                <div className="text-center flex-1">
                  <span className="text-xs text-amber-400 font-bold block">HIGH</span>
                  <span className="text-xl font-bold text-white print:text-black font-mono">{report.summary_counts.HIGH}</span>
                </div>
                <div className="text-center flex-1">
                  <span className="text-xs text-yellow-400 font-bold block">MEDIUM</span>
                  <span className="text-xl font-bold text-white print:text-black font-mono">{report.summary_counts.MEDIUM}</span>
                </div>
                <div className="text-center flex-1">
                  <span className="text-xs text-blue-400 font-bold block">LOW</span>
                  <span className="text-xl font-bold text-white print:text-black font-mono">{report.summary_counts.LOW}</span>
                </div>
              </div>
              <div className="text-xs text-slate-400 print:text-gray-600 mt-2 text-center">
                Total anomalies flagged: {report.findings.length}
              </div>
            </div>

            <div className="p-5 rounded-xl bg-slate-950/60 print:bg-gray-50 border border-slate-800 print:border-gray-200">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 print:text-gray-600 block">
                Audit Trail Digest
              </span>
              <div className="mt-3">
                <HashDisplay hash={report.audit_trail_hash || 'SHA256:0000000000000000'} truncateLength={16} />
              </div>
              <p className="text-xs text-slate-400 print:text-gray-600 mt-2">
                Cryptographic head digest binding the chronological evaluation ledger.
              </p>
            </div>
          </div>

          {/* Section 2: Detailed Findings Table */}
          <div className="space-y-4">
            <h3 className="text-base font-bold text-white print:text-black uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-cyan-400 print:text-cyan-700" />
              Detailed Integrity Findings & Dispositions
            </h3>

            <div className="overflow-x-auto rounded-lg border border-slate-800 print:border-gray-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 print:bg-gray-100 text-slate-400 print:text-gray-700 font-mono border-b border-slate-800 print:border-gray-200">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Category</th>
                    <th className="p-3">Finding Description</th>
                    <th className="p-3">Affected Asset</th>
                    <th className="p-3">Disposition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 print:divide-gray-200">
                  {report.findings.map((f) => (
                    <tr key={f.finding_id} className="hover:bg-slate-850/40 print:hover:bg-transparent">
                      <td className="p-3 font-mono text-cyan-400 print:text-cyan-800 font-medium whitespace-nowrap">
                        {f.finding_id}
                      </td>
                      <td className="p-3">
                        <SeverityBadge severity={f.severity} size="sm" />
                      </td>
                      <td className="p-3 font-mono text-slate-300 print:text-gray-700 uppercase">
                        {f.category.replace('_', ' ')}
                      </td>
                      <td className="p-3 text-slate-200 print:text-gray-800 max-w-md">
                        <div className="font-semibold text-white print:text-black mb-0.5">{f.title}</div>
                        <div className="text-[11px] text-slate-400 print:text-gray-600 leading-snug">
                          {f.human_readable_reason}
                        </div>
                      </td>
                      <td className="p-3 font-mono text-slate-300 print:text-gray-700 whitespace-nowrap">
                        {f.affected_asset}
                      </td>
                      <td className="p-3">
                        <DispositionBadge disposition={f.recommended_disposition} size="sm" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 3: Evaluated Attack Classes */}
          <div className="space-y-3">
            <h3 className="text-base font-bold text-white print:text-black uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400 print:text-cyan-700" />
              Evaluated Threat Surface Coverage
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {(report.supported_attack_classes || [
                'Trigger & Backdoor Injection (BadNets, Watermark, FFT)',
                'Label Manipulation & Systematic Flipping',
                'Near-Duplicate Dataset Flooding (Perceptual Hash & SSIM)',
                'Out-of-Distribution Insertion (Isolation Forest)',
                'Model Parameter & Weight Substitution Tampering',
                'Inference Record Cryptographic Provenance & Replay'
              ]).map((cls, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-950/50 print:bg-gray-50 border border-slate-800 print:border-gray-200 text-xs flex items-center gap-2 text-slate-300 print:text-gray-800">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <span>{cls}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Section 4: Known Operational Limitations & Boundary Disclosures */}
          <div className="space-y-3 pt-4 border-t border-slate-800 print:border-gray-200">
            <h3 className="text-base font-bold text-white print:text-black uppercase tracking-wider flex items-center gap-2">
              <Info className="w-4 h-4 text-cyan-400 print:text-cyan-700" />
              Declared Limitations & Cryptographic Boundaries
            </h3>
            <div className="p-4 rounded-xl bg-slate-950/70 print:bg-gray-50 border border-slate-800 print:border-gray-200 text-xs text-slate-300 print:text-gray-700 space-y-2">
              {(report.known_limitations || [
                'SHA-256 verification proves byte-level equivalence to reference artifact; it does not prove the reference artifact itself is free from initial compromise.',
                'Data integrity detector metrics are heuristic indicators derived from spatial, perceptual, and frequency analysis, not mathematical certainties.',
                'Operational distribution shift monitors proxy physical features (illumination, blur, edge density), not ground truth semantic weather or terrain classifications.',
                'Cryptographic provenance authenticates signed inference records post-hoc; it does not prevent adversarial host-memory alteration during live GPU execution.'
              ]).map((lim, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="text-cyan-400 print:text-cyan-700 font-mono font-bold">•</span>
                  <span>{lim}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Report Footer / Signature */}
          <div className="pt-6 border-t border-slate-800 print:border-gray-300 flex flex-col sm:flex-row justify-between items-center text-xs font-mono text-slate-500 print:text-gray-500 gap-2">
            <span>Air-Gapped Security Directive SIH-26228</span>
            <span>Deterministic SHA-256 Audit Trail • Zero External Dependencies</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
