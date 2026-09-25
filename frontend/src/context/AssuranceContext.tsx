import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  AssuranceReport,
  EvaluationReport,
  DatasetManifest,
  Module2BenchmarkReport,
  DistributionShiftResult,
  VisualEvidencePanel,
  CoverageResponse,
  AssuranceFinding,
  ContributorProfile
} from '../types';
import { api } from '../services/api';

export type NavigationTab =
  | 'overview'
  | 'data'
  | 'model'
  | 'inference'
  | 'shift'
  | 'contributors'
  | 'audit'
  | 'blockchain'
  | 'findings'
  | 'reports'
  | 'coverage';

interface AssuranceContextType {
  mode: 'live' | 'benchmark';
  setMode: (m: 'live' | 'benchmark') => void;
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  report: AssuranceReport | null;
  benchmarkData: EvaluationReport | null;
  manifest: DatasetManifest | null;
  modelBenchmark: Module2BenchmarkReport | null;
  shiftResult: DistributionShiftResult | null;
  visualEvidence: VisualEvidencePanel[];
  coverage: CoverageResponse | null;
  selectedFinding: AssuranceFinding | null;
  setSelectedFinding: (f: AssuranceFinding | null) => void;
  selectedContributor: ContributorProfile | null;
  setSelectedContributor: (c: ContributorProfile | null) => void;
  isLoading: boolean;
  isAuditing: boolean;
  error: string | null;
  runFullAudit: () => Promise<void>;
  refreshAllData: () => Promise<void>;
}

const AssuranceContext = createContext<AssuranceContextType | undefined>(undefined);

export const AssuranceProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<'live' | 'benchmark'>('benchmark');
  const [activeTab, setActiveTab] = useState<NavigationTab>('overview');

  const [report, setReport] = useState<AssuranceReport | null>(null);
  const [benchmarkData, setBenchmarkData] = useState<EvaluationReport | null>(null);
  const [manifest, setManifest] = useState<DatasetManifest | null>(null);
  const [modelBenchmark, setModelBenchmark] = useState<Module2BenchmarkReport | null>(null);
  const [shiftResult, setShiftResult] = useState<DistributionShiftResult | null>(null);
  const [visualEvidence, setVisualEvidence] = useState<VisualEvidencePanel[]>([]);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);

  const [selectedFinding, setSelectedFinding] = useState<AssuranceFinding | null>(null);
  const [selectedContributor, setSelectedContributor] = useState<ContributorProfile | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refreshAllData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [bData, mData, mBenchmark, sData, vData, cData] = await Promise.allSettled([
        api.getBenchmarkSummary(),
        api.getBenchmarkManifest(),
        api.getModelBenchmark(),
        api.analyzeDistributionShift(),
        api.getVisualEvidenceList(),
        api.getCoverageMatrix()
      ]);

      if (bData.status === 'fulfilled') setBenchmarkData(bData.value);
      if (mData.status === 'fulfilled') setManifest(mData.value);
      if (mBenchmark.status === 'fulfilled') setModelBenchmark(mBenchmark.value);
      if (sData.status === 'fulfilled') setShiftResult(sData.value);
      if (vData.status === 'fulfilled') setVisualEvidence(vData.value);
      if (cData.status === 'fulfilled') setCoverage(cData.value);

      // Synthesize default benchmark report into AssuranceReport format for benchmark mode
      if (bData.status === 'fulfilled' && bData.value) {
        const evalRpt = bData.value;
        const initialFindings: AssuranceFinding[] = [];

        // Add contributor findings
        evalRpt.contributors.profiles.forEach(p => {
          if (p.risk_level === 'CRITICAL' || p.risk_level === 'HIGH') {
            initialFindings.push({
              finding_id: `FND-CONTRIB-${p.contributor_id.toUpperCase()}`,
              category: 'data_integrity',
              title: `High Risk Contributor: ${p.contributor_id}`,
              human_readable_reason: p.explanation,
              supporting_evidence: { ...p, confidence_semantics: "heuristic_evidence_score_not_calibrated_probability" },
              confidence_score: p.risk_score,
              severity: p.risk_level === 'CRITICAL' ? 'CRITICAL' : 'HIGH',
              affected_asset: `Contributor:${p.contributor_id}`,
              recommended_disposition: p.risk_level === 'CRITICAL' ? 'QUARANTINE' : 'REVIEW'
            });
          }
        });

        // Add shift finding
        if (evalRpt.distribution_shift.material_shift_detected) {
          initialFindings.push({
            finding_id: 'FND-SHIFT-OPERATIONAL',
            category: 'distribution_shift',
            title: `Distribution Shift Detected: ${evalRpt.distribution_shift.shift_classification}`,
            human_readable_reason: evalRpt.distribution_shift.summary,
            supporting_evidence: evalRpt.distribution_shift,
            confidence_score: evalRpt.distribution_shift.overall_drift_score,
            severity: 'MEDIUM',
            affected_asset: evalRpt.dataset.name,
            recommended_disposition: 'REVIEW'
          });
        }

        // Add model substituted finding
        if (mBenchmark.status === 'fulfilled' && mBenchmark.value.substituted) {
          const sub = mBenchmark.value.substituted;
          initialFindings.push({
            finding_id: 'FND-MDL-SUBSTITUTED',
            category: 'model_integrity',
            title: 'Model Substitution & SHA-256 Digest Mismatch',
            human_readable_reason: 'Candidate model digest differs from trusted reference baseline.',
            supporting_evidence: sub,
            confidence_score: 1.0,
            severity: 'CRITICAL',
            affected_asset: sub.model_path,
            recommended_disposition: 'QUARANTINE'
          });
        }

        const primaryFindings = initialFindings.filter(f => !f.finding_id.startsWith('FND-CONTRIB-'));
        const critFindings = primaryFindings.filter(f => f.severity === 'CRITICAL');
        const highFindings = primaryFindings.filter(f => f.severity === 'HIGH');
        const medFindings = primaryFindings.filter(f => f.severity === 'MEDIUM');
        const lowFindings = primaryFindings.filter(f => f.severity === 'LOW');

        let penalty = 0;
        critFindings.forEach((_, idx) => { penalty += idx === 0 ? 18 : (idx === 1 ? 12 : 6); });
        highFindings.forEach((_, idx) => { penalty += idx === 0 ? 10 : (idx === 1 ? 6 : 3); });
        medFindings.forEach((_, idx) => { penalty += idx === 0 ? 5 : 3; });
        lowFindings.forEach(() => { penalty += 2; });

        const critCount = initialFindings.filter(f => f.severity === 'CRITICAL').length;
        const highCount = initialFindings.filter(f => f.severity === 'HIGH').length;
        const medCount = initialFindings.filter(f => f.severity === 'MEDIUM').length;

        const calcHealth = Math.max(0, Math.round((100 - penalty) * 10) / 10);

        setReport({
          report_id: 'RPT-BENCHMARK-SIH26228',
          generated_at_utc: evalRpt.timestamp,
          system_version: '1.0.0',
          overall_health_score: calcHealth,
          overall_disposition: critCount > 0 ? 'QUARANTINE' : highCount > 0 ? 'REVIEW' : 'ACCEPT',
          supported_attack_classes: [
            "Trigger Patch Injection (BadNets Corner Checkerboard)",
            "Fourier 2D FFT Periodic Carrier Spikes",
            "Alpha-Blended Spatial Watermarks",
            "Random Label Flipping & Systematic Mislabelling",
            "Near-Duplicate Image Flooding (SSIM + MAE)",
            "Out-Of-Distribution (OOD) Domain Contamination",
            "Model SHA-256 Digest Substitution & Weight Tampering",
            "White-Box Layer Parameter Norm & Dead Neuron Sparsity",
            "Operational Environmental Drift (Terrain, Illumination, Sensor, Season)",
            "Inference Cryptographic Provenance & Replay Detection"
          ],
          known_limitations: evalRpt.limitations || [],
          summary_counts: {
            total_findings: initialFindings.length,
            CRITICAL: critCount,
            HIGH: highCount,
            MEDIUM: medCount,
            LOW: 0
          },
          findings: initialFindings,
          audit_trail_hash: 'a3f8c7901b22e4d5678ef991002341ab8872619cd3000f2e1a49479b1836a992'
        });
      }
    } catch (err: any) {
      console.error('Data initialization error:', err);
      setError(err.message || 'Failed to initialize assurance environment');
    } finally {
      setIsLoading(false);
    }
  };

  const runFullAudit = async () => {
    setIsAuditing(true);
    setError(null);
    try {
      const liveReport = await api.runAssurance();
      setReport(liveReport);
      setMode('live');
    } catch (err: any) {
      console.error('Audit execution error:', err);
      setError(`Audit execution failed: ${err.message}`);
    } finally {
      setIsAuditing(false);
    }
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  return (
    <AssuranceContext.Provider
      value={{
        mode,
        setMode,
        activeTab,
        setActiveTab,
        report,
        benchmarkData,
        manifest,
        modelBenchmark,
        shiftResult,
        visualEvidence,
        coverage,
        selectedFinding,
        setSelectedFinding,
        selectedContributor,
        setSelectedContributor,
        isLoading,
        isAuditing,
        error,
        runFullAudit,
        refreshAllData
      }}
    >
      {children}
    </AssuranceContext.Provider>
  );
};

export const useAssurance = () => {
  const context = useContext(AssuranceContext);
  if (!context) {
    throw new Error('useAssurance must be used within an AssuranceProvider');
  }
  return context;
};
