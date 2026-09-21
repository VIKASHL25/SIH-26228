import os
import json
import hashlib
from typing import Dict, Any, Optional, Union

from .models import DualVerificationResult
from .fabric_client import FabricClient
from .merkle import MerkleTree, MerkleProof

from cv_assurance.model.hasher import ModelHasher
from cv_assurance.provenance.crypto_binding import (
    CryptographicProvenanceEngine,
    ProtectedInferenceRecord,
    ProvenanceVerificationResult
)


class BlockchainDualVerifier:
    """
    Dual-Layer Verification Engine:
    Layer 1: Local cryptographic verification (SHA-256, HMAC-SHA256, nonce/sequence checks).
    Layer 2: Immutable permissioned blockchain evidence verification (Hyperledger Fabric).
    """

    def __init__(
        self,
        fabric_client: Optional[FabricClient] = None,
        provenance_engine: Optional[CryptographicProvenanceEngine] = None
    ):
        self.client = fabric_client or FabricClient()
        self.prov_engine = provenance_engine or CryptographicProvenanceEngine()
        self.model_hasher = ModelHasher()

    def verify_inference_record_dual(
        self,
        record: Union[ProtectedInferenceRecord, Dict[str, Any]],
        image_bytes_or_path: Optional[Union[bytes, str]] = None
    ) -> DualVerificationResult:
        """
        Executes Layer 1 local HMAC/SHA256 verification and Layer 2 blockchain ledger verification.
        """
        # Convert dict to model if needed
        rec_obj = ProtectedInferenceRecord(**record) if isinstance(record, dict) else record

        # --- LAYER 1: LOCAL CRYPTOGRAPHIC VERIFICATION ---
        img_b = image_bytes_or_path if isinstance(image_bytes_or_path, bytes) else None
        img_p = image_bytes_or_path if isinstance(image_bytes_or_path, str) and os.path.exists(image_bytes_or_path) else None

        local_result: ProvenanceVerificationResult = self.prov_engine.verify_record(
            record=rec_obj,
            image_bytes=img_b,
            image_path=img_p
        )

        rec_id = rec_obj.record_id
        current_binding = rec_obj.binding_hash_sha256

        # --- LAYER 2: BLOCKCHAIN ANCHOR VERIFICATION ---
        ledger_res = self.client.verify_artifact(rec_id, current_binding)

        anchor_found = ledger_res.get("anchor_found", False)
        ledger_matched = ledger_res.get("match", False)
        registered_hash = ledger_res.get("registered_hash")

        # Determine combined status
        if local_result.verification_passed and anchor_found and ledger_matched:
            final_status = "TRUST_VERIFIED"
            disposition = "ACCEPT"
            reason = None
        elif not anchor_found:
            final_status = "UNANCHORED"
            disposition = "REVIEW"
            reason = "Local cryptography passed, but no immutable blockchain anchor exists on the ledger."
        elif not ledger_matched:
            final_status = "TAMPER_DETECTED"
            disposition = "QUARANTINE"
            reason = (
                f"CRITICAL INTEGRITY VIOLATION: Current binding ({current_binding[:16]}...) "
                f"does not match immutable blockchain anchor ({registered_hash[:16]}...)."
            )
        else:
            final_status = "LOCAL_VERIFICATION_FAILED"
            disposition = "QUARANTINE"
            reason = f"Local cryptographic checks failed: {local_result.details}"

        return DualVerificationResult(
            asset_id=rec_id,
            asset_type="INFERENCE_RECORD",
            local_verification_passed=local_result.verification_passed,
            local_tamper_detected=local_result.tamper_detected,
            local_details=local_result.details,
            blockchain_anchor_found=anchor_found,
            blockchain_hash_matched=ledger_matched,
            registered_blockchain_hash=registered_hash,
            current_computed_hash=current_binding,
            anchored_tx_id=ledger_res.get("tx_id"),
            anchored_block_number=ledger_res.get("block_number"),
            anchored_timestamp_iso=ledger_res.get("timestamp_iso"),
            anchored_by_msp=ledger_res.get("signer_msp"),
            final_assurance_status=final_status,
            recommended_disposition=disposition,
            discrepancy_reason=reason
        )

    def verify_model_dual(
        self,
        model_id: str,
        current_model_path: str,
        expected_version: str = "1.0.0"
    ) -> DualVerificationResult:
        """
        Verifies local model artifact SHA-256 against the immutable registered blockchain digest.
        """
        if not os.path.exists(current_model_path):
            return DualVerificationResult(
                asset_id=model_id,
                asset_type="MODEL",
                local_verification_passed=False,
                local_tamper_detected=True,
                local_details=f"Model artifact not found: {current_model_path}",
                blockchain_anchor_found=False,
                blockchain_hash_matched=False,
                final_assurance_status="FILE_NOT_FOUND",
                recommended_disposition="QUARANTINE",
                discrepancy_reason="Local model file missing"
            )

        current_sha256 = self.model_hasher.compute_file_sha256(current_model_path)

        ledger_res = self.client.verify_artifact(model_id, current_sha256)
        anchor_found = ledger_res.get("anchor_found", False)
        ledger_matched = ledger_res.get("match", False)
        registered_hash = ledger_res.get("registered_hash")

        if anchor_found and ledger_matched:
            final_status = "TRUST_VERIFIED"
            disposition = "ACCEPT"
            reason = None
        elif not anchor_found:
            final_status = "UNANCHORED"
            disposition = "REVIEW"
            reason = f"Model {model_id} has not been registered on the blockchain ledger."
        else:
            final_status = "MODEL_SUBSTITUTED"
            disposition = "QUARANTINE"
            reason = (
                f"MODEL SUBSTITUTION DETECTED: Current weights SHA-256 ({current_sha256[:16]}...) "
                f"differs from registered trusted blockchain digest ({registered_hash[:16]}...)."
            )

        return DualVerificationResult(
            asset_id=model_id,
            asset_type="MODEL",
            local_verification_passed=True,
            local_tamper_detected=not ledger_matched,
            local_details=f"SHA-256 computed: {current_sha256}",
            blockchain_anchor_found=anchor_found,
            blockchain_hash_matched=ledger_matched,
            registered_blockchain_hash=registered_hash,
            current_computed_hash=current_sha256,
            anchored_tx_id=ledger_res.get("tx_id"),
            anchored_block_number=ledger_res.get("block_number"),
            anchored_timestamp_iso=ledger_res.get("timestamp_iso"),
            anchored_by_msp=ledger_res.get("signer_msp"),
            final_assurance_status=final_status,
            recommended_disposition=disposition,
            discrepancy_reason=reason
        )

    def verify_report_dual(
        self,
        report_id: str,
        report_dict_or_path: Union[Dict[str, Any], str]
    ) -> DualVerificationResult:
        """
        Verifies off-chain assurance report file integrity against the on-chain report fingerprint.
        """
        if isinstance(report_dict_or_path, str):
            if not os.path.exists(report_dict_or_path):
                raise FileNotFoundError(f"Report file not found: {report_dict_or_path}")
            with open(report_dict_or_path, "r", encoding="utf-8") as f:
                report_dict = json.load(f)
        else:
            report_dict = report_dict_or_path

        report_json = json.dumps(report_dict, sort_keys=True)
        current_hash = hashlib.sha256(report_json.encode('utf-8')).hexdigest()

        ledger_res = self.client.verify_artifact(report_id, current_hash)
        anchor_found = ledger_res.get("anchor_found", False)
        ledger_matched = ledger_res.get("match", False)
        registered_hash = ledger_res.get("registered_hash")

        if anchor_found and ledger_matched:
            final_status = "TRUST_VERIFIED"
            disposition = "ACCEPT"
            reason = None
        elif not anchor_found:
            final_status = "UNANCHORED"
            disposition = "REVIEW"
            reason = f"Report {report_id} has not been anchored to the blockchain."
        else:
            final_status = "REPORT_TAMPERED"
            disposition = "QUARANTINE"
            reason = (
                f"REPORT TAMPERING DETECTED: Off-chain report contents have been modified. "
                f"Current hash ({current_hash[:16]}...) != On-Chain anchor ({registered_hash[:16]}...)."
            )

        return DualVerificationResult(
            asset_id=report_id,
            asset_type="REPORT",
            local_verification_passed=True,
            local_tamper_detected=not ledger_matched,
            local_details=f"Report SHA-256: {current_hash}",
            blockchain_anchor_found=anchor_found,
            blockchain_hash_matched=ledger_matched,
            registered_blockchain_hash=registered_hash,
            current_computed_hash=current_hash,
            anchored_tx_id=ledger_res.get("tx_id"),
            anchored_block_number=ledger_res.get("block_number"),
            anchored_timestamp_iso=ledger_res.get("timestamp_iso"),
            anchored_by_msp=ledger_res.get("signer_msp"),
            final_assurance_status=final_status,
            recommended_disposition=disposition,
            discrepancy_reason=reason
        )
