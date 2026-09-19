import os
import time
import uuid
import json
import hashlib
import hmac
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class InferenceOutputPrediction(BaseModel):
    box: List[float] # [x, y, w, h]
    confidence: float
    category_id: int
    category_name: str

class ProtectedInferenceRecord(BaseModel):
    record_id: str
    timestamp_utc: float
    nonce: str
    sequence_number: int
    image_hash_sha256: str
    model_digest_sha256: str
    preprocessing_config_hash: str
    predictions: List[InferenceOutputPrediction]
    binding_hash_sha256: str
    hmac_signature: str

class ProvenanceVerificationResult(BaseModel):
    record_id: str
    verification_passed: bool
    tamper_detected: bool
    tampered_fields: List[str]
    details: str

class CryptographicProvenanceEngine:
    """Creates & verifies tamper-evident cryptographic bindings for inference records."""
    
    def __init__(self, secret_key: str = "DEFAULT_AIRGAPPED_HMAC_SECRET_KEY"):
        self.secret_key = secret_key.encode('utf-8')

    @staticmethod
    def hash_string(data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def hash_image_file(image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image for provenance binding not found: {image_path}")
        sha256 = hashlib.sha256()
        with open(image_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compute_binding_hash(
        self,
        image_hash: str,
        model_hash: str,
        config_hash: str,
        predictions: List[InferenceOutputPrediction],
        timestamp: float,
        nonce: str,
        seq_num: int
    ) -> str:
        # Create canonical representation of predictions
        preds_json = json.dumps([p.model_dump() for p in predictions], sort_keys=True)
        canonical_str = f"{image_hash}|{model_hash}|{config_hash}|{preds_json}|{timestamp}|{nonce}|{seq_num}"
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

    def compute_signature(self, binding_hash: str) -> str:
        return hmac.new(self.secret_key, binding_hash.encode('utf-8'), hashlib.sha256).hexdigest()

    def create_protected_record(
        self,
        image_path_or_hash: str,
        model_hash: str,
        config_dict: Dict[str, Any],
        predictions: List[InferenceOutputPrediction],
        sequence_number: int = 1
    ) -> ProtectedInferenceRecord:
        
        if os.path.isfile(image_path_or_hash):
            img_hash = self.hash_image_file(image_path_or_hash)
        else:
            img_hash = image_path_or_hash

        cfg_hash = self.hash_string(json.dumps(config_dict, sort_keys=True))
        ts = time.time()
        nonce = uuid.uuid4().hex
        rec_id = f"INF-REC-{uuid.uuid4().hex[:8].upper()}"

        binding_h = self.compute_binding_hash(
            img_hash, model_hash, cfg_hash, predictions, ts, nonce, sequence_number
        )
        sig = self.compute_signature(binding_h)

        return ProtectedInferenceRecord(
            record_id=rec_id,
            timestamp_utc=ts,
            nonce=nonce,
            sequence_number=sequence_number,
            image_hash_sha256=img_hash,
            model_digest_sha256=model_hash,
            preprocessing_config_hash=cfg_hash,
            predictions=predictions,
            binding_hash_sha256=binding_h,
            hmac_signature=sig
        )

    def verify_record(self, record: ProtectedInferenceRecord) -> ProvenanceVerificationResult:
        tampered_fields = []
        
        # 1. Recompute binding hash
        expected_binding = self.compute_binding_hash(
            record.image_hash_sha256,
            record.model_digest_sha256,
            record.preprocessing_config_hash,
            record.predictions,
            record.timestamp_utc,
            record.nonce,
            record.sequence_number
        )

        if expected_binding != record.binding_hash_sha256:
            tampered_fields.append("binding_hash_sha256")

        # 2. Recompute HMAC signature
        expected_sig = self.compute_signature(expected_binding)
        if expected_sig != record.hmac_signature:
            tampered_fields.append("hmac_signature")

        is_valid = (len(tampered_fields) == 0)
        
        if is_valid:
            details = "Record verification succeeded. Cryptographic binding among input image, model hash, config, and output is unbroken."
        else:
            details = f"TAMPERING DETECTED! Cryptographic binding failed on fields: {', '.join(tampered_fields)}. Record may have been altered, substituted, or replayed."

        return ProvenanceVerificationResult(
            record_id=record.record_id,
            verification_passed=is_valid,
            tamper_detected=not is_valid,
            tampered_fields=tampered_fields,
            details=details
        )
