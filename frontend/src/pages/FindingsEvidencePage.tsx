import React, { useState } from 'react';
import { 
  ShieldAlert, 
  Search, 
  Filter, 
  Eye, 
  AlertTriangle, 
  FileText, 
  Layers, 
  CheckCircle2, 
  ExternalLink,
  ChevronRight,
  Sparkles,
  Camera
} from 'lucide-react';
import { useAssurance } from '../context/AssuranceContext';
import { AssuranceFinding, SeverityLevel } from '../types';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { DispositionBadge } from '../components/common/DispositionBadge';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import { ImageForensicViewer } from '../components/evidence/ImageForensicViewer';

export const FindingsEvidencePage: React.FC = () => {
  const { report, visualEvidence, setSelectedFinding, isLoading } = useAssurance();

  const [activeView, setActiveView] = useState<'findings' | 'visual_panels'>('findings');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  const findings = report?.findings || [];

  // Filter findings
  const filteredFindings = findings.filter(f => {
    const matchesSearch = 
      f.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.finding_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.affected_asset.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.human_readable_reason.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesSeverity = selectedSeverity === 'ALL' || f.severity === selectedSeverity;
    const matchesCategory = selectedCategory === 'ALL' || f.category === selectedCategory;

    return matchesSearch && matchesSeverity && matchesCategory;
  });

  const criticalCount = findings.filter(f => f.severity === 'CRITICAL').length;
  const highCount = findings.filter(f => f.severity === 'HIGH').length;
  const mediumLowCount = findings.filter(f => f.severity === 'MEDIUM' || f.severity === 'LOW').length;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-1">
            <ShieldAlert className="w-4 h-4" />
            Comprehensive Forensics & Anomaly Intelligence
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            Findings & Evidence Explorer
            <span className="text-xs font-mono px-2.5 py-1 bg-cyan-950/70 border border-cyan-800/60 text-cyan-300 rounded-md">
              {findings.length} Discovered Findings
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Correlated audit anomalies spanning data poisoning, backdoor triggers, model parameter discrepancies, 
            inference signature tampering, and operational environmental drift.
          </p>
        </div>

        {/* View Switcher Toggle */}
        <div className="flex items-center p-1 bg-slate-950 border border-slate-800 rounded-lg">
          <button
            onClick={() => setActiveView('findings')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeView === 'findings'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Structured Findings ({findings.length})
          </button>
          <button
            onClick={() => setActiveView('visual_panels')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeView === 'visual_panels'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            Visual Evidence ({visualEvidence.length})
          </button>
        </div>
      </div>

      {/* Metric Counters Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">Total Findings</span>
          <div className="text-2xl font-bold text-white mt-1">{findings.length}</div>
          <div className="text-xs text-slate-500 mt-1">Across 4 pipeline stages</div>
        </div>

        <div className="bg-rose-950/20 border border-rose-800/40 p-4 rounded-xl">
          <span className="text-[11px] font-mono text-rose-400 uppercase tracking-wider block">Critical Risk</span>
          <div className="text-2xl font-bold text-rose-300 mt-1">{criticalCount}</div>
          <div className="text-xs text-rose-400/70 mt-1">Mandatory quarantine</div>
        </div>

        <div className="bg-amber-950/20 border border-amber-800/40 p-4 rounded-xl">
          <span className="text-[11px] font-mono text-amber-400 uppercase tracking-wider block">High Risk</span>
          <div className="text-2xl font-bold text-amber-300 mt-1">{highCount}</div>
          <div className="text-xs text-amber-400/70 mt-1">Requires manual sign-off</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
          <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider block">Visual Panels</span>
          <div className="text-2xl font-bold text-cyan-300 mt-1">{visualEvidence.length}</div>
          <div className="text-xs text-slate-500 mt-1">High-res forensic artifacts</div>
        </div>
      </div>

      {/* Main View Area */}
      {activeView === 'visual_panels' ? (
        <div className="space-y-4">
          <div className="bg-slate-900/40 border border-slate-800 p-4 rounded-xl flex items-center justify-between text-xs text-slate-300">
            <span className="flex items-center gap-2">
              <Camera className="w-4 h-4 text-cyan-400" />
              Generated 6-Artifact Visual Evidence Gallery (Near-Duplicate, Label Flip, OOD, BadNets Corner, Watermark, Spectral FFT)
            </span>
            <span className="font-mono text-slate-500">Rendered via OpenCV & Matplotlib</span>
          </div>
          <ImageForensicViewer panels={visualEvidence} />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
            <div className="flex items-center gap-2 flex-1 relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
              <input
                type="text"
                placeholder="Search findings by title, ID, asset or rationale..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-md text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400 font-mono">Severity:</span>
                <select
                  value={selectedSeverity}
                  onChange={(e) => setSelectedSeverity(e.target.value)}
                  className="bg-slate-950 border border-slate-700/80 rounded-md px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="ALL">All Severities</option>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400 font-mono">Category:</span>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-slate-950 border border-slate-700/80 rounded-md px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="ALL">All Categories</option>
                  <option value="data_integrity">Data Integrity</option>
                  <option value="model_integrity">Model Integrity</option>
                  <option value="inference_provenance">Inference Provenance</option>
                  <option value="distribution_shift">Distribution Shift</option>
                  <option value="governance">Governance</option>
                </select>
              </div>
            </div>
          </div>

          {/* Findings List */}
          {filteredFindings.length === 0 ? (
            <div className="text-center py-16 bg-slate-900/40 rounded-xl border border-slate-800/60 text-slate-400 text-sm">
              No assurance findings match current filter criteria.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3.5">
              {filteredFindings.map((finding) => (
                <div
                  key={finding.finding_id}
                  onClick={() => setSelectedFinding(finding)}
                  className="group bg-slate-900/80 hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/40 p-4 sm:p-5 rounded-xl transition-all cursor-pointer shadow-sm hover:shadow-cyan-950/20"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                      <SeverityBadge severity={finding.severity} size="sm" />
                      <DispositionBadge disposition={finding.recommended_disposition} size="sm" />
                      <span className="font-mono text-xs text-slate-400 font-semibold">
                        {finding.finding_id}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-400 font-mono">
                        {finding.category.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="w-32 hidden sm:block">
                        <ConfidenceMeter score={finding.confidence_score} semantics={finding.confidence_semantics} />
                      </div>
                      <span className="text-xs text-cyan-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-1 font-medium">
                        Inspect Evidence
                        <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>

                  <div className="mt-3.5 space-y-2">
                    <h3 className="text-sm sm:text-base font-semibold text-white group-hover:text-cyan-200 transition-colors">
                      {finding.title}
                    </h3>
                    <p className="text-xs sm:text-sm text-slate-300 line-clamp-2 leading-relaxed">
                      {finding.human_readable_reason}
                    </p>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-800/40 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-400">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">Asset:</span>
                      <span className="text-slate-300 font-medium">{finding.affected_asset}</span>
                    </div>
                    {finding.confidence_semantics && (
                      <span className="text-[11px] text-slate-500 italic">
                        {finding.confidence_semantics}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FindingsEvidencePage;
