// Common type definitions for Trustworthy CV Assurance Platform

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type RecommendedDisposition = 'ACCEPT' | 'REVIEW' | 'QUARANTINE';

export interface AssuranceFinding {
  finding_id: string;
  category: 'data_integrity' | 'model_integrity' | 'inference_provenance' | 'distribution_shift' | 'governance';
  title: string;
  human_readable_reason: string;
  supporting_evidence: Record<string, any>;
  confidence_score: number;
  confidence_semantics?: string;
  severity: SeverityLevel;
  affected_asset: string;
  recommended_disposition: RecommendedDisposition;
}

export interface AuditEvent {
  event_id: string;
  sequence_index: number;
  timestamp_utc: number;
  timestamp_iso: string;
  event_type: string;
  affected_asset: string;
  event_summary: string;
  event_data: Record<string, any>;
  previous_event_hash: string;
  current_event_hash: string;
}

export interface AuditChainSummary {
  chain_length: number;
  latest_event_hash: string;
  verification_status: 'VERIFIED_UNBROKEN' | 'TAMPERED';
  verification_details: string;
  events: AuditEvent[];
}

export interface ProvenanceAuditSummary {
  total_records_evaluated: number;
  verified_passed_count: number;
  tamper_detected_count: number;
  replay_detected_count: number;
  evaluated_records: Array<{
    record_id: string;
    passed: boolean;
    tamper_detected: boolean;
    replay_detected: boolean;
    sequence_violation: boolean;
    details: string;
    tampered_fields: string[];
  }>;
}

export interface AssuranceReport {
  report_id: string;
  generated_at_utc: string;
  system_version: string;
  overall_health_score: number;
  overall_disposition: RecommendedDisposition;
  supported_attack_classes: string[];
  known_limitations: string[];
  summary_counts: {
    total_findings: number;
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  findings: AssuranceFinding[];
  audit_trail_hash: string;
  audit_chain?: AuditChainSummary;
  provenance_summary?: ProvenanceAuditSummary;
}

// Module 1 Types
export interface BenchmarkMetrics {
  TP: number;
  FP: number;
  TN: number;
  FN: number;
  precision: number;
  recall: number;
  f1_score: number;
  specificity: number;
  false_positive_rate: number;
  accuracy: number;
}

export interface ContributorProfile {
  contributor_id: string;
  total_samples: number;
  flagged_samples: number;
  risk_score: number;
  risk_level: 'CLEAN' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  dominant_factor: string;
  recommended_action: string;
  explanation: string;
}

export interface EvaluationReport {
  timestamp: string;
  dataset: {
    name: string;
    format: string;
    total_samples: number;
    total_annotations: number;
  };
  calibration: Record<string, any>;
  metrics: {
    near_duplicate_flooding: BenchmarkMetrics;
    label_manipulation: BenchmarkMetrics;
    ood_insertion: BenchmarkMetrics;
    trigger_families: {
      corner_patch: BenchmarkMetrics;
      blended_watermark: BenchmarkMetrics;
      spectral_fft_spike: BenchmarkMetrics;
      composite_triggers: BenchmarkMetrics;
    };
    macro_summary: {
      macro_precision: number;
      macro_recall: number;
      macro_f1: number;
    };
  };
  contributors: {
    total_contributors: number;
    clean_contributors_correctly_kept: number;
    compromised_contributors_flagged: number;
    clean_contributor_fpr: number;
    compromised_detection_rate: number;
    profiles: ContributorProfile[];
  };
  distribution_shift: {
    material_shift_detected: boolean;
    shift_classification: string;
    overall_drift_score: number;
    summary: string;
  };
  reproducibility: Record<string, any>;
  limitations: string[];
}

export interface ManifestSample {
  sample_id: string;
  original_image: string;
  current_image: string;
  contributor: string;
  batch_id: string;
  attack_type: string;
  is_attacked: number;
  is_shifted: number;
  shift_type: string | null;
  original_label: string;
  modified_label: string;
  boxes: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    category_id: number;
    category_name: string;
  }>;
}

export interface DatasetManifest {
  dataset_name: string;
  dataset_version: string;
  seed: number;
  total_samples: number;
  attack_summary: Record<string, number>;
  contributor_summary: Record<string, number>;
  samples: ManifestSample[];
}

// Module 2 Types
export interface LayerStatistic {
  layer_name: string;
  shape: number[];
  mean_weight: number;
  std_weight: number;
  l2_norm: number;
  zero_ratio: number;
  anomaly_flag: boolean;
}

export interface WhiteBoxAnalysisResult {
  model_path: string;
  access_granted: boolean;
  total_layers_analyzed: number;
  dead_neurons_ratio: number;
  weight_anomaly_score: number;
  parameter_anomaly_risk: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNAVAILABLE';
  layer_stats: LayerStatistic[];
  assessment_notes: string;
}

export interface ModelIntegrityScenario {
  scenario: string;
  model_path: string;
  sha256: string;
  reference_sha256: string;
  reference_hash_match: boolean;
  model_type: string;
  whitebox_available: boolean;
  weight_anomaly_score: number;
  dead_neurons_ratio: number;
  trigger_prediction_change_rate: number;
  trigger_target_rate: number;
  trigger_confidence_change: number;
  fingerprint_prediction_agreement: number;
  fingerprint_confidence_deviation: number;
  fingerprint_entropy_deviation: number;
  fingerprint_behavioral_deviation_score: number;
  fingerprint_behavior_detected: boolean;
  parameter_anomaly_detected: boolean;
  trigger_behavior_detected: boolean;
  backdoor_like_behavior: string;
  evidence_score: number;
  confidence: string;
  disposition: string;
  severity: SeverityLevel;
  recommended_disposition: RecommendedDisposition;
  affected_layer: string;
  findings: string[];
}

export type Module2BenchmarkReport = Record<string, ModelIntegrityScenario>;

// Module 3A Types
export interface InferenceOutputPrediction {
  box: number[];
  confidence: number;
  category_id: number;
  category_name: string;
}

export interface ProtectedInferenceRecord {
  record_id: string;
  timestamp_utc: number;
  timestamp_iso?: string;
  nonce: string;
  sequence_number: number;
  image_hash_sha256: string;
  model_digest_sha256: string;
  preprocessing_config_hash: string;
  preprocessing_config?: Record<string, any>;
  predictions: InferenceOutputPrediction[];
  predictions_hash_sha256?: string;
  inference_config?: Record<string, any>;
  inference_config_hash_sha256?: string;
  binding_hash_sha256: string;
  hmac_signature: string;
  secret_key_id?: string;
}

export interface ProvenanceVerificationResult {
  record_id: string;
  verification_passed: boolean;
  tamper_detected: boolean;
  replay_detected: boolean;
  sequence_violation: boolean;
  tampered_fields: string[];
  details: string;
  field_verifications: Record<string, boolean>;
}

// Module 3B Types
export interface ShiftDimensionDetail {
  dimension_name: 'terrain' | 'illumination' | 'sensor' | 'season' | string;
  feature_name: string;
  feature_is_proxy: boolean;
  ks_statistic: number;
  p_value: number;
  wasserstein_dist: number;
  shift_detected: boolean;
  description: string;
}

export interface DistributionShiftResult {
  reference_sample_count: number;
  target_sample_count: number;
  overall_drift_score: number;
  material_shift_detected: boolean;
  shift_classification: 'NO_SHIFT' | 'OPERATIONAL_DRIFT' | 'SUSPICIOUS_MANIPULATION';
  confidence_score: number;
  sample_sufficiency: string;
  dimensions: ShiftDimensionDetail[];
  summary_findings: string;
  evidence_details: Record<string, any>;
}

// Visual Evidence Panel
export interface VisualEvidencePanel {
  id: string;
  title: string;
  category: string;
  image_url: string;
  metrics: Record<string, any>;
  description: string;
}

// Capability Coverage
export interface CapabilityCoverageItem {
  capability: string;
  status: 'SUPPORTED' | 'PARTIAL' | 'UNAVAILABLE';
  detection_method: string;
  evidence: string;
  assumptions: string;
  limitations: string;
}

export interface CoverageResponse {
  capabilities: CapabilityCoverageItem[];
  limitations: string[];
  total_capabilities: number;
  supported_count: number;
}

// Blockchain Trust & Evidence Ledger Types
export interface BlockchainStatus {
  status: 'CONNECTED' | 'DISCONNECTED' | 'LOCAL_EMULATED' | 'UNAVAILABLE';
  network_type: string;
  channel_id: string;
  chaincode_name: string;
  chaincode_version: string;
  ledger_height: number;
  total_transactions: number;
  active_peers: string[];
  endorsing_organizations: string[];
  connected_msp: string;
  mode: string;
  last_block_hash?: string;
  timestamp_utc: number;
}

export interface BlockchainEvent {
  event_id: string;
  event_type:
    | 'DATASET_REGISTERED'
    | 'CONTRIBUTOR_REGISTERED'
    | 'DATASET_ASSESSED'
    | 'CONTRIBUTOR_RISK_RECORDED'
    | 'MODEL_REGISTERED'
    | 'MODEL_VERIFIED'
    | 'MODEL_TAMPER_DETECTED'
    | 'INFERENCE_RECORDED'
    | 'INFERENCE_VERIFIED'
    | 'INFERENCE_TAMPER_DETECTED'
    | 'REPLAY_DETECTED'
    | 'SHIFT_ASSESSMENT_RECORDED'
    | 'ASSURANCE_REPORT_RECORDED'
    | 'AUDIT_BATCH_ANCHORED'
    | 'QUARANTINE_RECORDED';
  asset_id: string;
  contributor_id?: string;
  dataset_version?: string;
  model_version?: string;
  image_hash?: string;
  model_hash?: string;
  manifest_hash?: string;
  preprocessing_hash?: string;
  inference_hash?: string;
  prediction_hash?: string;
  binding_hash?: string;
  report_hash?: string;
  audit_root_hash?: string;
  merkle_root?: string;
  batch_size?: number;
  severity?: string;
  disposition?: 'ACCEPT' | 'REVIEW' | 'QUARANTINE';
  sequence_number?: number;
  timestamp_utc: number;
  timestamp_iso: string;
  software_version: string;
  previous_event_id?: string;
  tx_id?: string;
  block_number?: number;
  signer_msp?: string;
  metadata?: Record<string, any>;
}

export interface DualVerificationResult {
  asset_id: string;
  asset_type: 'INFERENCE_RECORD' | 'MODEL' | 'DATASET' | 'REPORT';
  local_verification_passed: boolean;
  local_tamper_detected: boolean;
  local_details: string;

  blockchain_anchor_found: boolean;
  blockchain_hash_matched: boolean;
  registered_blockchain_hash?: string;
  current_computed_hash?: string;
  anchored_tx_id?: string;
  anchored_block_number?: number;
  anchored_timestamp_iso?: string;
  anchored_by_msp?: string;

  final_assurance_status:
    | 'TRUST_VERIFIED'
    | 'TAMPER_DETECTED'
    | 'MODEL_SUBSTITUTED'
    | 'UNANCHORED'
    | 'QUARANTINED'
    | 'LOCAL_VERIFICATION_FAILED';
  recommended_disposition: 'ACCEPT' | 'REVIEW' | 'QUARANTINE';
  discrepancy_reason?: string;
}

export interface TamperSimulationResult {
  original_record_id: string;
  tampered_record: any;
  verification_result: DualVerificationResult;
}

export interface ReplaySimulationResult {
  record_id: string;
  first_submission_passed: boolean;
  replay_attempt_tamper_detected: boolean;
  replay_detected: boolean;
  blockchain_history_count: number;
  latest_anchor_tx: string;
  disposition: 'ACCEPT' | 'REVIEW' | 'QUARANTINE';
}

