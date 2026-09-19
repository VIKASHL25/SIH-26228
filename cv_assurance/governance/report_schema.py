from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class RecommendedDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"

class AssuranceFinding(BaseModel):
    finding_id: str
    category: str  # "data_integrity", "model_integrity", "distribution_shift", "inference_provenance"
    title: str
    human_readable_reason: str
    supporting_evidence: Dict[str, Any]
    confidence_score: float  # 0.0 to 1.0
    severity: SeverityLevel
    affected_asset: str  # dataset path, sample id, model path, or record id
    recommended_disposition: RecommendedDisposition

class AuditChainSummary(BaseModel):
    chain_length: int
    latest_event_hash: str
    verification_status: str  # "VERIFIED_UNBROKEN" or "TAMPERED"
    verification_details: str
    events: List[Dict[str, Any]] = Field(default_factory=list)

class ProvenanceAuditSummary(BaseModel):
    total_records_evaluated: int
    verified_passed_count: int
    tamper_detected_count: int
    replay_detected_count: int
    evaluated_records: List[Dict[str, Any]] = Field(default_factory=list)

class AssuranceReport(BaseModel):
    report_id: str
    generated_at_utc: str
    system_version: str = "1.0.0"
    overall_health_score: float  # 0.0 to 100.0
    overall_disposition: RecommendedDisposition
    supported_attack_classes: List[str]
    known_limitations: List[str]
    summary_counts: Dict[str, int]
    findings: List[AssuranceFinding]
    audit_trail_hash: str
    audit_chain: Optional[AuditChainSummary] = None
    provenance_summary: Optional[ProvenanceAuditSummary] = None
