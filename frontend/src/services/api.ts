import {
  AssuranceReport,
  EvaluationReport,
  DatasetManifest,
  Module2BenchmarkReport,
  WhiteBoxAnalysisResult,
  ProtectedInferenceRecord,
  ProvenanceVerificationResult,
  DistributionShiftResult,
  VisualEvidencePanel,
  CoverageResponse,
  AuditEvent,
  BlockchainStatus,
  BlockchainEvent,
  DualVerificationResult,
  TamperSimulationResult,
  ReplaySimulationResult
} from '../types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response, fallbackMessage: string): Promise<T> {
  if (!res.ok) {
    let errorDetail = fallbackMessage;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || fallbackMessage;
    } catch {
      // Ignore parse failure
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // System Health
  async getHealth(): Promise<{ status: string; system: string; mode: string; environment: string; version: string }> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse(res, 'Failed to fetch system health');
  },

  // Module 1 Benchmark & Data
  async getBenchmarkSummary(): Promise<EvaluationReport> {
    const res = await fetch(`${API_BASE}/benchmark/summary`);
    return handleResponse<EvaluationReport>(res, 'Failed to fetch evaluation benchmark report');
  },

  async getBenchmarkManifest(): Promise<DatasetManifest> {
    const res = await fetch(`${API_BASE}/benchmark/manifest`);
    return handleResponse<DatasetManifest>(res, 'Failed to fetch benchmark dataset manifest');
  },

  // Full Assurance Run
  async runAssurance(params?: {
    dataset_path?: string;
    model_path?: string;
    ref_dataset_path?: string;
    reference_model_hash?: string;
    reference_model_path?: string;
    inference_record_path?: string;
  }): Promise<AssuranceReport> {
    const res = await fetch(`${API_BASE}/run_assurance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params || {})
    });
    return handleResponse<AssuranceReport>(res, 'Assurance pipeline execution failed');
  },

  // Module 2 Model Integrity
  async getModelBenchmark(): Promise<Module2BenchmarkReport> {
    const res = await fetch(`${API_BASE}/model/benchmark`);
    return handleResponse<Module2BenchmarkReport>(res, 'Failed to load model benchmark scenarios');
  },

  async analyzeModelWhitebox(modelPath: string, referenceModelPath?: string): Promise<WhiteBoxAnalysisResult> {
    const res = await fetch(`${API_BASE}/model/whitebox`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_path: modelPath, reference_model_path: referenceModelPath })
    });
    return handleResponse<WhiteBoxAnalysisResult>(res, 'White-box parameter analysis failed');
  },

  async hashModel(modelPath: string, referenceHash?: string) {
    const res = await fetch(`${API_BASE}/model/hash`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_path: modelPath, reference_hash: referenceHash })
    });
    return handleResponse(res, 'Model hashing failed');
  },

  // Module 3A Inference Provenance
  async verifyInferenceRecord(record: ProtectedInferenceRecord | Record<string, any>): Promise<ProvenanceVerificationResult> {
    const res = await fetch(`${API_BASE}/inference/verify_record`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record)
    });
    return handleResponse<ProvenanceVerificationResult>(res, 'Inference record verification failed');
  },

  async verifyInferenceChain(records: (ProtectedInferenceRecord | Record<string, any>)[]): Promise<{
    chain_valid: boolean;
    total_records: number;
    status: string;
    evaluated_records: Array<{
      record_id: string;
      sequence_number: number;
      timestamp_utc: number;
      nonce: string;
      verification_passed: boolean;
      tamper_detected: boolean;
      replay_detected: boolean;
      sequence_violation: boolean;
      tampered_fields: string[];
      details: string;
    }>;
  }> {
    const res = await fetch(`${API_BASE}/inference/verify_chain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(records)
    });
    return handleResponse(res, 'Inference chain verification failed');
  },

  async getDemoInferenceRecords(): Promise<{
    clean_record: ProtectedInferenceRecord;
    clean_chain: ProtectedInferenceRecord[];
    tampered_scenarios: Record<string, ProtectedInferenceRecord>;
  }> {
    const res = await fetch(`${API_BASE}/inference/demo_records`);
    return handleResponse(res, 'Failed to fetch demo inference records');
  },

  // Module 3B Distribution Shift
  async analyzeDistributionShift(): Promise<DistributionShiftResult> {
    const res = await fetch(`${API_BASE}/shift/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return handleResponse<DistributionShiftResult>(res, 'Distribution shift analysis failed');
  },

  // Audit Trail
  async verifyAuditChain(events?: AuditEvent[]): Promise<{
    is_valid: boolean;
    verification_status: string;
    message: string;
    broken_event_index: number | null;
    total_events: number;
    latest_event_hash: string;
    events: AuditEvent[];
  }> {
    const res = await fetch(`${API_BASE}/audit/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: events ? JSON.stringify(events) : undefined
    });
    return handleResponse(res, 'Audit chain verification failed');
  },

  // Visual Evidence & Capability Coverage
  async getVisualEvidenceList(): Promise<VisualEvidencePanel[]> {
    const res = await fetch(`${API_BASE}/visual_evidence/list`);
    return handleResponse<VisualEvidencePanel[]>(res, 'Failed to load visual evidence artifacts');
  },

  async getCoverageMatrix(): Promise<CoverageResponse> {
    const res = await fetch(`${API_BASE}/coverage`);
    return handleResponse<CoverageResponse>(res, 'Failed to load system coverage matrix');
  },

  // -------------------------------------------------------------
  // Hyperledger Fabric Blockchain Evidence Ledger API
  // -------------------------------------------------------------
  async getBlockchainStatus(): Promise<BlockchainStatus> {
    const res = await fetch(`${API_BASE}/blockchain/status`);
    return handleResponse<BlockchainStatus>(res, 'Failed to fetch blockchain network status');
  },

  async getBlockchainEvents(params?: {
    event_type?: string;
    asset_id?: string;
    contributor_id?: string;
    limit?: number;
  }): Promise<BlockchainEvent[]> {
    const query = new URLSearchParams();
    if (params?.event_type) query.append('event_type', params.event_type);
    if (params?.asset_id) query.append('asset_id', params.asset_id);
    if (params?.contributor_id) query.append('contributor_id', params.contributor_id);
    if (params?.limit) query.append('limit', params.limit.toString());

    const res = await fetch(`${API_BASE}/blockchain/events?${query.toString()}`);
    return handleResponse<BlockchainEvent[]>(res, 'Failed to fetch blockchain events');
  },

  async getBlockchainEventById(eventId: string): Promise<BlockchainEvent> {
    const res = await fetch(`${API_BASE}/blockchain/event/${eventId}`);
    return handleResponse<BlockchainEvent>(res, `Failed to load blockchain event ${eventId}`);
  },

  async getBlockchainAssetHistory(assetId: string): Promise<BlockchainEvent[]> {
    const res = await fetch(`${API_BASE}/blockchain/history/${assetId}`);
    return handleResponse<BlockchainEvent[]>(res, `Failed to load blockchain history for asset ${assetId}`);
  },

  async anchorInferenceOnBlockchain(record: any, contributorId?: string): Promise<BlockchainEvent> {
    const res = await fetch(`${API_BASE}/blockchain/anchor/inference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record, contributor_id: contributorId })
    });
    return handleResponse<BlockchainEvent>(res, 'Failed to anchor inference record to blockchain');
  },

  async verifyInferenceOnBlockchain(record: any): Promise<DualVerificationResult> {
    const res = await fetch(`${API_BASE}/blockchain/verify/inference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record })
    });
    return handleResponse<DualVerificationResult>(res, 'Blockchain inference verification failed');
  },

  async verifyModelOnBlockchain(modelId: string, modelPath?: string, expectedVersion: string = '1.0.0'): Promise<DualVerificationResult> {
    const res = await fetch(`${API_BASE}/blockchain/verify/model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId, model_path: modelPath, expected_version: expectedVersion })
    });
    return handleResponse<DualVerificationResult>(res, 'Blockchain model verification failed');
  },

  async simulateInferenceTampering(): Promise<TamperSimulationResult> {
    const res = await fetch(`${API_BASE}/blockchain/simulate_tampering`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return handleResponse<TamperSimulationResult>(res, 'Inference tampering simulation failed');
  },

  async simulateReplayAttack(): Promise<ReplaySimulationResult> {
    const res = await fetch(`${API_BASE}/blockchain/simulate_replay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return handleResponse<ReplaySimulationResult>(res, 'Replay attack simulation failed');
  }
};

