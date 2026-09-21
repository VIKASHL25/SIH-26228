import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Union, Tuple

from .models import AssuranceEvent, AssuranceEventType
from .fabric_client import FabricClient
from .merkle import MerkleTree, MerkleProof

from cv_assurance.model.hasher import ModelHasher
from cv_assurance.provenance.crypto_binding import ProtectedInferenceRecord
from cv_assurance.governance.report_schema import AssuranceReport


class BlockchainAnchorService:
    """
    Non-intrusive domain adapter bridging CV Assurance engine outputs to Hyperledger Fabric.
    Preserves all existing cryptographic pipelines while providing immutable on-chain anchoring.
    """

    def __init__(self, fabric_client: Optional[FabricClient] = None):
        self.client = fabric_client or FabricClient()
        self.model_hasher = ModelHasher()

    # -------------------------------------------------------------
    # MODULE 1: DATASET & CONTRIBUTOR ANCHORS
    # -------------------------------------------------------------

    def anchor_dataset(
        self,
        dataset_id: str,
        manifest_path: str,
        contributor_id: str,
        version: str = "1.0.0",
        sample_count: int = 0
    ) -> AssuranceEvent:
        """Anchors dataset manifest SHA-256 fingerprint on blockchain."""
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(manifest_path, "rb") as f:
            manifest_hash = hashlib.sha256(f.read()).hexdigest()

        return self.client.register_dataset(
            dataset_id=dataset_id,
            version=version,
            canonical_manifest_hash=manifest_hash,
            contributor_id=contributor_id,
            sample_count=sample_count,
            metadata={"manifest_file": os.path.basename(manifest_path)}
        )

    def anchor_contributor_risk(
        self,
        contributor_id: str,
        risk_score: float,
        risk_level: str,
        dominant_factor: str,
        disposition: str,
        affected_dataset: Optional[str] = None,
        evidence_summary: Optional[str] = None
    ) -> AssuranceEvent:
        """Anchors contributor risk profiling finding and quarantine disposition."""
        now = time.time()
        event = AssuranceEvent(
            event_id=f"EVT-RISK-{contributor_id}-{int(now)}",
            event_type=(
                AssuranceEventType.QUARANTINE_RECORDED
                if disposition == "QUARANTINE" else
                AssuranceEventType.CONTRIBUTOR_RISK_RECORDED
            ),
            asset_id=contributor_id,
            contributor_id=contributor_id,
            severity="CRITICAL" if risk_level == "CRITICAL" else ("HIGH" if risk_level == "HIGH" else "MEDIUM"),
            disposition=disposition,
            timestamp_utc=now,
            metadata={
                "risk_score": round(float(risk_score), 4),
                "risk_level": risk_level,
                "dominant_factor": dominant_factor,
                "affected_dataset": affected_dataset,
                "evidence_summary": evidence_summary
            }
        )
        return self.client.record_assurance_event(event)

    # -------------------------------------------------------------
    # MODULE 2: MODEL INTEGRITY ANCHORS
    # -------------------------------------------------------------

    def anchor_model_registration(
        self,
        model_path: str,
        model_id: str,
        version: str = "1.0.0",
        author_org: Optional[str] = None
    ) -> AssuranceEvent:
        """Computes SHA-256 via existing ModelHasher and anchors trusted reference model."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model artifact not found: {model_path}")

        trusted_digest = self.model_hasher.compute_file_sha256(model_path)
        file_size = os.path.getsize(model_path)

        return self.client.register_model(
            model_id=model_id,
            version=version,
            trusted_digest_sha256=trusted_digest,
            author_org=author_org or "AssuranceAuthorityMSP",
            metadata={
                "model_filename": os.path.basename(model_path),
                "file_size_bytes": file_size
            }
        )

    def anchor_model_verification(
        self,
        model_id: str,
        version: str,
        current_model_path: str,
        trusted_digest_sha256: str
    ) -> AssuranceEvent:
        """Anchors model verification outcome or tampering detection."""
        current_digest = self.model_hasher.compute_file_sha256(current_model_path)
        is_match = (current_digest.lower() == trusted_digest_sha256.lower())

        now = time.time()
        event_type = (
            AssuranceEventType.MODEL_VERIFIED
            if is_match else
            AssuranceEventType.MODEL_TAMPER_DETECTED
        )

        event = AssuranceEvent(
            event_id=f"EVT-MODVER-{model_id}-{int(now)}",
            event_type=event_type,
            asset_id=model_id,
            model_version=version,
            model_hash=current_digest,
            severity="INFO" if is_match else "CRITICAL",
            disposition="ACCEPT" if is_match else "QUARANTINE",
            timestamp_utc=now,
            metadata={
                "trusted_digest_sha256": trusted_digest_sha256,
                "current_digest_sha256": current_digest,
                "match": is_match
            }
        )
        return self.client.record_assurance_event(event)

    # -------------------------------------------------------------
    # MODULE 3A: PROTECTED INFERENCE ANCHORS
    # -------------------------------------------------------------

    def anchor_inference_record(
        self,
        record: Union[ProtectedInferenceRecord, Dict[str, Any]],
        contributor_id: Optional[str] = None
    ) -> AssuranceEvent:
        """Anchors a single ProtectedInferenceRecord binding hash onto the ledger."""
        if isinstance(record, dict):
            rec_id = record["record_id"]
            img_h = record["image_hash_sha256"]
            mod_d = record["model_digest_sha256"]
            prep_h = record["preprocessing_config_hash"]
            bind_h = record["binding_hash_sha256"]
            nonce = record.get("nonce", "")
            seq = record.get("sequence_number", 0)
            hmac_ref = record.get("hmac_signature", "")[:16] + "..."
        else:
            rec_id = record.record_id
            img_h = record.image_hash_sha256
            mod_d = record.model_digest_sha256
            prep_h = record.preprocessing_config_hash
            bind_h = record.binding_hash_sha256
            nonce = record.nonce
            seq = record.sequence_number
            hmac_ref = record.hmac_signature[:16] + "..."

        return self.client.record_inference(
            record_id=rec_id,
            image_hash=img_h,
            model_digest=mod_d,
            preprocessing_hash=prep_h,
            binding_hash=bind_h,
            nonce=nonce,
            sequence_number=seq,
            hmac_ref=hmac_ref,
            contributor_id=contributor_id
        )

    def anchor_inference_batch(
        self,
        records: List[Union[ProtectedInferenceRecord, Dict[str, Any]]],
        batch_id: Optional[str] = None
    ) -> Tuple[AssuranceEvent, MerkleTree]:
        """
        Batches high-volume inference bindings into a single Merkle tree root transaction.
        """
        if not records:
            raise ValueError("Inference record batch cannot be empty")

        binding_hashes = [
            (r["binding_hash_sha256"] if isinstance(r, dict) else r.binding_hash_sha256)
            for r in records
        ]

        merkle_tree = MerkleTree(binding_hashes)
        now = time.time()
        bid = batch_id or f"BATCH-{int(now)}-{len(records)}"

        event = AssuranceEvent(
            event_id=f"EVT-BATCH-{bid}",
            event_type=AssuranceEventType.INFERENCE_RECORDED,
            asset_id=bid,
            merkle_root=merkle_tree.root,
            batch_size=len(records),
            sequence_number=records[0]["sequence_number"] if isinstance(records[0], dict) else records[0].sequence_number,
            timestamp_utc=now,
            metadata={
                "batch_id": bid,
                "first_record_id": records[0]["record_id"] if isinstance(records[0], dict) else records[0].record_id,
                "last_record_id": records[-1]["record_id"] if isinstance(records[-1], dict) else records[-1].record_id,
                "record_count": len(records)
            }
        )
        anchored_evt = self.client.record_assurance_event(event)
        return anchored_evt, merkle_tree

    # -------------------------------------------------------------
    # MODULE 3B & GOVERNANCE: REPORT & AUDIT ANCHORS
    # -------------------------------------------------------------

    def anchor_governance_report(
        self,
        report: Union[AssuranceReport, Dict[str, Any]],
        report_file_path: Optional[str] = None
    ) -> AssuranceEvent:
        """Anchors off-chain AssuranceReport SHA-256 fingerprint & audit chain root."""
        if isinstance(report, dict):
            report_id = report.get("report_id", f"RPT-{int(time.time())}")
            overall_disp = report.get("overall_disposition", "ACCEPT")
            audit_hash = report.get("audit_trail_hash", "0" * 64)
            health_score = report.get("overall_health_score", 100.0)
            json_str = json.dumps(report, sort_keys=True)
        else:
            report_id = report.report_id
            overall_disp = report.overall_disposition.value if hasattr(report.overall_disposition, 'value') else str(report.overall_disposition)
            audit_hash = report.audit_trail_hash
            health_score = report.overall_health_score
            json_str = json.dumps(report.model_dump(), sort_keys=True)

        report_sha256 = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        now = time.time()

        event = AssuranceEvent(
            event_id=f"EVT-REPORT-{report_id}",
            event_type=AssuranceEventType.ASSURANCE_REPORT_RECORDED,
            asset_id=report_id,
            report_hash=report_sha256,
            audit_root_hash=audit_hash,
            disposition=overall_disp,
            severity="CRITICAL" if overall_disp == "QUARANTINE" else ("HIGH" if overall_disp == "REVIEW" else "INFO"),
            timestamp_utc=now,
            metadata={
                "report_id": report_id,
                "health_score": health_score,
                "report_file": os.path.basename(report_file_path) if report_file_path else None
            }
        )
        return self.client.record_assurance_event(event)

    def anchor_audit_chain_batch(
        self,
        chain_length: int,
        latest_event_hash: str,
        audit_batch_id: Optional[str] = None
    ) -> AssuranceEvent:
        """Anchors TamperEvidentAuditChain head state onto the blockchain."""
        now = time.time()
        bid = audit_batch_id or f"AUDIT-BATCH-{int(now)}"

        event = AssuranceEvent(
            event_id=f"EVT-AUDIT-{bid}",
            event_type=AssuranceEventType.AUDIT_BATCH_ANCHORED,
            asset_id=bid,
            audit_root_hash=latest_event_hash,
            batch_size=chain_length,
            timestamp_utc=now,
            metadata={
                "chain_length": chain_length,
                "latest_event_hash": latest_event_hash
            }
        )
        return self.client.record_assurance_event(event)
