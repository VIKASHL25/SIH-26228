import React from 'react';
import { ShieldCheck, Play, RefreshCw, Radio, HardDrive, AlertCircle } from 'lucide-react';
import { useAssurance } from '../../context/AssuranceContext';

export const Topbar: React.FC = () => {
  const { mode, setMode, isAuditing, runFullAudit, refreshAllData, error } = useAssurance();

  return (
    <header className="h-16 bg-[#0a0f1d] border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-30 shadow-md">
      {/* Title & Brand */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.25)]">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-wide text-white font-sans">
                CV Integrity Assurance Console
              </h1>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-700/40">
                SIH-26228
              </span>
            </div>
            <p className="text-[11px] text-slate-400 tracking-tight">
              Multi-Contributor Pipeline Forensics & Cryptographic Audit
            </p>
          </div>
        </div>

        {/* Air-Gapped Status Badges */}
        <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-slate-800">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs font-mono font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>AIR-GAPPED</span>
          </div>

          <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono">
            <HardDrive className="w-3.5 h-3.5 text-slate-400" />
            <span>LOCAL</span>
          </div>
        </div>
      </div>

      {/* Center/Right Controls */}
      <div className="flex items-center gap-4">
        {error && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-rose-400 bg-rose-950/50 border border-rose-800/50 px-2.5 py-1 rounded">
            <AlertCircle className="w-3.5 h-3.5" />
            <span className="truncate max-w-xs">{error}</span>
          </div>
        )}

        {/* Mode Toggle: Live vs Benchmark */}
        <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setMode('benchmark')}
            className={`px-3 py-1 rounded text-xs font-medium tracking-wide transition-all ${
              mode === 'benchmark'
                ? 'bg-cyan-600 text-white shadow-sm font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            BENCHMARK DEMO
          </button>
          <button
            onClick={() => setMode('live')}
            className={`px-3 py-1 rounded text-xs font-medium tracking-wide transition-all flex items-center gap-1.5 ${
              mode === 'live'
                ? 'bg-cyan-600 text-white shadow-sm font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Radio className="w-3 h-3 text-emerald-400" />
            LIVE SCAN
          </button>
        </div>

        {/* Refresh & Run Audit Actions */}
        <button
          onClick={refreshAllData}
          disabled={isAuditing}
          className="p-2 text-slate-400 hover:text-cyan-300 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg transition-colors"
          title="Reload local reports"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <button
          onClick={runFullAudit}
          disabled={isAuditing}
          className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-lg shadow-cyan-950/40 border border-cyan-400/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isAuditing ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>AUDITING PIPELINE...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>RUN FULL AUDIT</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
