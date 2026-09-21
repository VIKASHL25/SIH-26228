import hashlib
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class AssuranceEventType(str, Enum):
    DATASET_REGISTERED = "DATASET_REGISTERED"
    CONTRIBUTOR_REGISTERED = "CONTRIBUTOR_REGISTERED"
    DATASET_ASSESSED = "DATASET_ASSESSED"
    CONTRIBUTOR_RISK_RECORDED = "CONTRIBUTOR_RISK_RECORDED"
    MODEL_REGISTERED = "MODEL_REGISTERED"
    MODEL_VERIFIED = "MODEL_VERIFIED"
    MODEL_TAMPER_DETECTED = "MODEL_TAMPER_DETECTED"
    INFERENCE_RECORDED = "INFERENCE_RECORDED"
    INFERENCE_VERIFIED = "INFERENCE_VERIFIED"
    INFERENCE_TAMPER_DETECTED = "INFERENCE_TAMPER_DETECTED"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    SHIFT_ASSESSMENT_RECORDED = "SHIFT_ASSESSMENT_RECORDED"
    ASSURANCE_REPORT_RECORDED = "ASSURANCE_REPORT_RECORDED"
    AUDIT_BATCH_ANCHORED = "AUDIT_BATCH_ANCHORED"
    QUARANTINE_RECORDED = "QUARANTINE_RECORDED"


class AssuranceEvent(BaseModel):
    """
    Standardized cryptographic assurance event payload anchored on Hyperledger Fabric.
    """
    event_id: str
    event_type: AssuranceEventType
    asset_id: str
    contributor_id: Optional[str] = None
    dataset_version: Optional[str] = None
    model_version: Optional[str] = None
    image_hash: Optional[str] = None
    model_hash: Optional[str] = None
    manifest_hash: Optional[str] = None
    preprocessing_hash: Optional[str] = None
    inference_hash: Optional[str] = None
    prediction_hash: Optional[str] = None
    binding_hash: Optional[str] = None
    report_hash: Optional[str] = None
    audit_root_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    batch_size: Optional[int] = None
    severity: Optional[str] = None
    disposition: Optional[str] = None
    sequence_number: Optional[int] = None
    timestamp_utc: float = Field(default_factory=lambda: time.time())
    timestamp_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    software_version: str = "1.0.0"
    previous_event_id: Optional[str] = None
    tx_id: Optional[str] = None
    block_number: Optional[int] = None
    signer_msp: Optional[str] = "AssuranceAuthorityMSP"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def canonical_json(self) -> str:
        """
        Deterministically serializes event into sorted JSON for cryptographic hashing.
        Excludes transient ledger metadata (tx_id, block_number).
        """
        data = self.model_dump()
        data.pop("tx_id", None)
        data.pop("block_number", None)
        return json.dumps(data, sort_keys=True, separators=(',', ':'))

    def compute_event_hash(self) -> str:
        """Computes SHA-256 fingerprint of the canonical event representation."""
        return hashlib.sha256(self.canonical_json().encode('utf-8')).hexdigest()


class BlockchainStatus(BaseModel):
    """Network connection, channel height, and ledger telemetry."""
    status: str  # "CONNECTED", "DISCONNECTED", "LOCAL_EMULATED", "UNAVAILABLE"
    network_type: str = "Hyperledger Fabric (Permissioned/Air-Gapped)"
    channel_id: str = "assurancechannel"
    chaincode_name: str = "assurance_contract"
    chaincode_version: str = "1.0.0"
    ledger_height: int = 0
    total_transactions: int = 0
    active_peers: List[str] = Field(default_factory=lambda: [
        "peer0.assurance.mod.mil",
        "peer0.contributor.mod.mil"
    ])
    endorsing_organizations: List[str] = Field(default_factory=lambda: [
        "AssuranceAuthorityMSP",
        "ContributorOrgMSP",
        "ModelAuthorityMSP"
    ])
    connected_msp: str = "AssuranceAuthorityMSP"
    mode: str = "OFFLINE_AIR_GAPPED"
    last_block_hash: Optional[str] = None
    timestamp_utc: float = Field(default_factory=lambda: time.time())


class DualVerificationResult(BaseModel):
    """
    Combined verification result comparing Layer 1 (Local Cryptography)
    and Layer 2 (Hyperledger Fabric Immutable Ledger Anchor).
    """
    asset_id: str
    asset_type: str  # "INFERENCE_RECORD", "MODEL", "DATASET", "REPORT"
    local_verification_passed: bool
    local_tamper_detected: bool
    local_details: str

    blockchain_anchor_found: bool
    blockchain_hash_matched: bool
    registered_blockchain_hash: Optional[str] = None
    current_computed_hash: Optional[str] = None
    anchored_tx_id: Optional[str] = None
    anchored_block_number: Optional[int] = None
    anchored_timestamp_iso: Optional[str] = None
    anchored_by_msp: Optional[str] = None

    final_assurance_status: str  # "TRUST_VERIFIED", "TAMPER_DETECTED", "MODEL_SUBSTITUTED", "UNANCHORED", "QUARANTINED"
    recommended_disposition: str  # "ACCEPT", "REVIEW", "QUARANTINE"
    discrepancy_reason: Optional[str] = None
