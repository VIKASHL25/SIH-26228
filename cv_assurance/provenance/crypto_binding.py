import os
import time
import uuid
import json
import secrets
import hashlib
import hmac
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ..model.hasher import ModelHasher

# Default secret key explicitly marked for local air-gapped demonstration
DEMO_SECRET_KEY = "DEMO_ONLY_AIRGAPPED_HMAC_SECRET_DO_NOT_USE_IN_PROD"


class PreprocessingConfig(BaseModel):
    """
    Canonical preprocessing configuration model binding computer vision
    inference transformation parameters into cryptographic digests.
    """
    resolution: List[int] = Field(default_factory=lambda: [640, 640])
    resize_method: str = "letterbox"
    normalization: Dict[str, List[float]] = Field(
        default_factory=lambda: {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225]
        }
    )
    channel_ordering: str = "RGB"
    confidence_threshold: float = 0.50
    nms_iou_threshold: Optional[float] = 0.45
    max_detections: Optional[int] = 300
    version: str = "1.0.0"
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    def canonical_json(self) -> str:
        """Deterministically serializes configuration to canonical JSON string."""
        return json.dumps(self.model_dump(), sort_keys=True, separators=(',', ':'))

    def compute_hash(self) -> str:
        """Computes SHA-256 digest of canonical configuration."""
        return hashlib.sha256(self.canonical_json().encode('utf-8')).hexdigest()


class InferenceOutputPrediction(BaseModel):
    """
    Individual object detection inference prediction with bounding box,
    confidence score, and taxonomy metadata.
    """
    box: List[float]  # [x, y, w, h] or [x1, y1, x2, y2]
    confidence: float
    category_id: int
    category_name: str

    def canonical_dict(self) -> Dict[str, Any]:
        """Returns rounded, normalized representation for deterministic hashing."""
        return {
            "box": [round(float(c), 4) for c in self.box],
            "category_id": int(self.category_id),
            "category_name": str(self.category_name).strip(),
            "confidence": round(float(self.confidence), 6)
        }


class ProtectedInferenceRecord(BaseModel):
    """
    Tamper-evident inference assurance record binding input image, model digest,
    preprocessing configuration, and predictions via SHA-256 and HMAC signatures.
    """
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

    # Extended metadata fields for enhanced auditability
    timestamp_iso: Optional[str] = None
    preprocessing_config: Optional[Dict[str, Any]] = None
    predictions_hash_sha256: Optional[str] = None
    secret_key_id: Optional[str] = "default"


class ProvenanceVerificationResult(BaseModel):
    """
    Verification output detailing tamper detection status, individual field
    integrity checks, and replay protection evidence.
    """
    record_id: str
    verification_passed: bool
    tamper_detected: bool
    replay_detected: bool = False
    tampered_fields: List[str] = Field(default_factory=list)
    details: str
    field_verifications: Dict[str, bool] = Field(default_factory=dict)


class ReplayRecordEntry(BaseModel):
    """Entry stored in the replay protection registry."""
    record_id: str
    nonce: str
    sequence_number: int
    timestamp_utc: float
    binding_hash_sha256: str
    registered_at_iso: str


class ReplayProtectionRegistry:
    """
    Lightweight, air-gapped, offline replay protection registry.
    Stores and validates seen inference records by record_id, nonce, sequence, and binding hash.
    Supports file-backed persistence (JSON) or in-memory tracking without any external database.
    """
    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file
        self.entries: List[ReplayRecordEntry] = []
        self._seen_record_ids = set()
        self._seen_nonces = set()
        self._seen_binding_hashes = set()
        self._last_sequence_number = 0
        if self.registry_file and os.path.exists(self.registry_file):
            self.load()

    def load(self) -> None:
        """Loads registry entries from local JSON file."""
        if not self.registry_file or not os.path.exists(self.registry_file):
            return
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.entries = [ReplayRecordEntry(**item) for item in data]
            self._seen_record_ids = {e.record_id for e in self.entries}
            self._seen_nonces = {e.nonce for e in self.entries}
            self._seen_binding_hashes = {e.binding_hash_sha256 for e in self.entries}
            if self.entries:
                self._last_sequence_number = max(e.sequence_number for e in self.entries)
        except Exception:
            self.entries = []

    def save(self) -> None:
        """Saves registry entries atomically to local JSON file."""
        if not self.registry_file:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.registry_file)), exist_ok=True)
        tmp_file = f"{self.registry_file}.tmp.{os.getpid()}"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump([e.model_dump() for e in self.entries], f, indent=2)
        os.replace(tmp_file, self.registry_file)

    def check_replay(self, record: ProtectedInferenceRecord) -> Tuple[bool, Optional[str]]:
        """
        Checks whether the given record constitutes a duplicate or replay attack.
        Returns (is_replayed, evidence_reason).
        """
        if record.record_id in self._seen_record_ids:
            return True, f"Record ID '{record.record_id}' was already registered and accepted in previous inference."
        if record.nonce in self._seen_nonces:
            return True, f"Nonce '{record.nonce}' was already used in a previous inference record (nonce reuse attack)."
        if record.binding_hash_sha256 in self._seen_binding_hashes:
            return True, f"Binding hash '{record.binding_hash_sha256}' already exists in registry (duplicate payload replay)."
        return False, None

    def register(self, record: ProtectedInferenceRecord) -> bool:
        """
        Registers an accepted record into the replay registry.
        Returns True if registration succeeded, False if record is replayed.
        """
        is_replay, _ = self.check_replay(record)
        if is_replay:
            return False
        entry = ReplayRecordEntry(
            record_id=record.record_id,
            nonce=record.nonce,
            sequence_number=record.sequence_number,
            timestamp_utc=record.timestamp_utc,
            binding_hash_sha256=record.binding_hash_sha256,
            registered_at_iso=datetime.now(timezone.utc).isoformat()
        )
        self.entries.append(entry)
        self._seen_record_ids.add(record.record_id)
        self._seen_nonces.add(record.nonce)
        self._seen_binding_hashes.add(record.binding_hash_sha256)
        if record.sequence_number > self._last_sequence_number:
            self._last_sequence_number = record.sequence_number
        self.save()
        return True

    def clear(self) -> None:
        """Clears all registry records (useful for clean testing)."""
        self.entries = []
        self._seen_record_ids.clear()
        self._seen_nonces.clear()
        self._seen_binding_hashes.clear()
        self._last_sequence_number = 0
        if self.registry_file and os.path.exists(self.registry_file):
            try:
                os.remove(self.registry_file)
            except OSError:
                pass


class CryptographicProvenanceEngine:
    """
    Creates and verifies tamper-evident cryptographic bindings for inference records.
    Binds input image bytes, model digests, preprocessing parameters, predictions,
    and freshness tokens using SHA-256, HMAC-SHA256, and offline replay protection.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        replay_registry: Optional[ReplayProtectionRegistry] = None
    ):
        if secret_key is not None:
            self.secret_key = secret_key.encode('utf-8')
            self.is_demo_key = False
        elif os.environ.get("CV_INFERENCE_SECRET_KEY"):
            self.secret_key = os.environ["CV_INFERENCE_SECRET_KEY"].encode('utf-8')
            self.is_demo_key = False
        else:
            self.secret_key = DEMO_SECRET_KEY.encode('utf-8')
            self.is_demo_key = True

        self.replay_registry = replay_registry

    @staticmethod
    def hash_string(data: str) -> str:
        """Computes SHA-256 hex digest of string data."""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def hash_image_bytes(data: bytes) -> str:
        """Computes SHA-256 hex digest of raw image bytes."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_image_file(image_path: str) -> str:
        """Computes chunked streaming SHA-256 digest of an image file."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image for provenance binding not found: {image_path}")
        sha256 = hashlib.sha256()
        with open(image_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def resolve_model_hash(model_path_or_hash: str) -> str:
        """
        Resolves model SHA-256 digest using ModelHasher if a file path is passed,
        or returns the digest string directly if a 64-char hex digest is provided.
        """
        if os.path.isfile(model_path_or_hash):
            return ModelHasher.compute_file_sha256(model_path_or_hash)
        return model_path_or_hash.strip().lower()

    @classmethod
    def canonicalize_predictions(
        cls,
        predictions: List[InferenceOutputPrediction]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Sorts predictions deterministically and formats float precision.
        Returns (sorted_canonical_dicts, canonical_json_string).
        """
        canonical_list = [p.canonical_dict() for p in predictions]
        # Deterministic sort: category_id, category_name, confidence desc, box
        canonical_list.sort(
            key=lambda p: (
                p["category_id"],
                p["category_name"],
                -p["confidence"],
                p["box"]
            )
        )
        canonical_json = json.dumps(canonical_list, sort_keys=True, separators=(',', ':'))
        return canonical_list, canonical_json

    @classmethod
    def compute_predictions_hash(
        cls,
        predictions: List[InferenceOutputPrediction]
    ) -> str:
        """Computes SHA-256 digest of canonical predictions."""
        _, canonical_json = cls.canonicalize_predictions(predictions)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    @classmethod
    def canonicalize_config(
        cls,
        config: Union[Dict[str, Any], PreprocessingConfig]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Serializes preprocessing config deterministically to canonical JSON.
        Returns (config_dict, canonical_json_string).
        """
        if isinstance(config, PreprocessingConfig):
            cfg_dict = config.model_dump()
        elif isinstance(config, dict):
            cfg_dict = config
        else:
            cfg_dict = dict(config)

        canonical_json = json.dumps(cfg_dict, sort_keys=True, separators=(',', ':'), default=str)
        return cfg_dict, canonical_json

    @classmethod
    def compute_config_hash(
        cls,
        config: Union[Dict[str, Any], PreprocessingConfig]
    ) -> str:
        """Computes SHA-256 digest of canonical preprocessing configuration."""
        _, canonical_json = cls.canonicalize_config(config)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def compute_binding_hash(
        self,
        image_hash: str,
        model_hash: str,
        config_hash: str,
        predictions: Union[List[InferenceOutputPrediction], str],
        timestamp: float,
        nonce: str,
        seq_num: int
    ) -> str:
        """
        Creates a canonical binding string and returns its SHA-256 digest.
        Payload: image_hash|model_hash|config_hash|preds_json|timestamp|nonce|seq_num
        """
        if isinstance(predictions, str):
            preds_repr = predictions
        else:
            _, preds_repr = self.canonicalize_predictions(predictions)

        canonical_str = f"{image_hash.lower()}|{model_hash.lower()}|{config_hash.lower()}|{preds_repr}|{timestamp}|{nonce}|{seq_num}"
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

    def compute_signature(self, binding_hash: str) -> str:
        """Computes HMAC-SHA256 authentication tag over the binding digest."""
        return hmac.new(self.secret_key, binding_hash.encode('utf-8'), hashlib.sha256).hexdigest()

    def verify_signature(self, binding_hash: str, signature: str) -> bool:
        """Constant-time HMAC comparison to prevent timing attacks."""
        expected_sig = self.compute_signature(binding_hash)
        return hmac.compare_digest(expected_sig, signature)

    def create_protected_record(
        self,
        image_path_or_hash: Union[str, bytes],
        model_hash: str,
        config_dict: Optional[Union[Dict[str, Any], PreprocessingConfig]] = None,
        predictions: Optional[List[InferenceOutputPrediction]] = None,
        sequence_number: int = 1,
        nonce: Optional[str] = None,
        timestamp_utc: Optional[float] = None
    ) -> ProtectedInferenceRecord:
        """
        Creates a new cryptographically bound ProtectedInferenceRecord.
        """
        # 1. Resolve image hash
        if isinstance(image_path_or_hash, bytes):
            img_hash = self.hash_image_bytes(image_path_or_hash)
        elif isinstance(image_path_or_hash, str) and os.path.isfile(image_path_or_hash):
            img_hash = self.hash_image_file(image_path_or_hash)
        else:
            img_hash = str(image_path_or_hash).strip()

        # 2. Resolve model hash
        m_hash = self.resolve_model_hash(model_hash)

        # 3. Canonicalize Preprocessing Configuration
        if config_dict is None:
            config_dict = PreprocessingConfig().model_dump()
        cfg_dict, _ = self.canonicalize_config(config_dict)
        cfg_hash = self.compute_config_hash(cfg_dict)

        # 4. Canonicalize Predictions
        if predictions is None:
            predictions = []
        _, preds_canonical_json = self.canonicalize_predictions(predictions)
        preds_hash = self.compute_predictions_hash(predictions)

        # 5. Timestamp and Nonce (CSPRNG)
        ts = timestamp_utc if timestamp_utc is not None else time.time()
        ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        generated_nonce = nonce if nonce is not None else secrets.token_hex(16)
        rec_id = f"INF-REC-{uuid.uuid4().hex[:8].upper()}"

        # 6. Compute Binding Hash & HMAC Signature
        binding_h = self.compute_binding_hash(
            img_hash, m_hash, cfg_hash, preds_canonical_json, ts, generated_nonce, sequence_number
        )
        sig = self.compute_signature(binding_h)

        return ProtectedInferenceRecord(
            record_id=rec_id,
            timestamp_utc=ts,
            timestamp_iso=ts_iso,
            nonce=generated_nonce,
            sequence_number=sequence_number,
            image_hash_sha256=img_hash,
            model_digest_sha256=m_hash,
            preprocessing_config_hash=cfg_hash,
            preprocessing_config=cfg_dict,
            predictions=predictions,
            predictions_hash_sha256=preds_hash,
            binding_hash_sha256=binding_h,
            hmac_signature=sig,
            secret_key_id="demo" if self.is_demo_key else "configured"
        )

    def verify_record(
        self,
        record: ProtectedInferenceRecord,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        model_path: Optional[str] = None,
        expected_model_hash: Optional[str] = None,
        expected_config: Optional[Union[Dict[str, Any], PreprocessingConfig]] = None,
        expected_sequence_number: Optional[int] = None,
        original_record: Optional[ProtectedInferenceRecord] = None,
        replay_registry: Optional[ReplayProtectionRegistry] = None,
        check_replay: bool = True,
        register_if_valid: bool = False
    ) -> ProvenanceVerificationResult:
        """
        Verifies the cryptographic integrity and authenticity of a protected record.
        Checks binding hash, HMAC signature, image match, model digest match,
        preprocessing config, predictions, sequence number, and replay status.
        """
        tampered_fields: List[str] = []
        field_verifications: Dict[str, bool] = {}
        replay_detected = False

        # 1. Image Integrity Verification
        if image_bytes is not None:
            actual_img_hash = self.hash_image_bytes(image_bytes)
            if actual_img_hash.lower() != record.image_hash_sha256.lower():
                tampered_fields.append("image_hash_sha256")
                field_verifications["image_integrity"] = False
            else:
                field_verifications["image_integrity"] = True
        elif image_path is not None:
            try:
                actual_img_hash = self.hash_image_file(image_path)
                if actual_img_hash.lower() != record.image_hash_sha256.lower():
                    tampered_fields.append("image_hash_sha256")
                    field_verifications["image_integrity"] = False
                else:
                    field_verifications["image_integrity"] = True
            except Exception:
                tampered_fields.append("image_hash_sha256")
                field_verifications["image_integrity"] = False

        # 2. Model Integrity Verification
        if model_path is not None:
            try:
                actual_model_hash = ModelHasher.compute_file_sha256(model_path)
                if actual_model_hash.lower() != record.model_digest_sha256.lower():
                    tampered_fields.append("model_digest_sha256")
                    field_verifications["model_integrity"] = False
                else:
                    field_verifications["model_integrity"] = True
            except Exception:
                tampered_fields.append("model_digest_sha256")
                field_verifications["model_integrity"] = False
        elif expected_model_hash is not None:
            if expected_model_hash.strip().lower() != record.model_digest_sha256.lower():
                tampered_fields.append("model_digest_sha256")
                field_verifications["model_integrity"] = False
            else:
                field_verifications["model_integrity"] = True

        # 3. Preprocessing Config Verification
        if record.preprocessing_config is not None:
            cfg_h = self.compute_config_hash(record.preprocessing_config)
            if cfg_h.lower() != record.preprocessing_config_hash.lower():
                tampered_fields.append("preprocessing_config")
                field_verifications["preprocessing_config"] = False
            else:
                field_verifications["preprocessing_config"] = True

        if expected_config is not None:
            exp_cfg_h = self.compute_config_hash(expected_config)
            if exp_cfg_h.lower() != record.preprocessing_config_hash.lower():
                if "preprocessing_config" not in tampered_fields:
                    tampered_fields.append("preprocessing_config")
                field_verifications["preprocessing_config"] = False

        # 4. Predictions Integrity Verification
        if record.predictions_hash_sha256 is not None:
            recomputed_preds_hash = self.compute_predictions_hash(record.predictions)
            if recomputed_preds_hash.lower() != record.predictions_hash_sha256.lower():
                tampered_fields.append("predictions")
                field_verifications["predictions"] = False
            else:
                field_verifications["predictions"] = True

        # 5. Sequence Number Check
        if expected_sequence_number is not None:
            if record.sequence_number != expected_sequence_number:
                tampered_fields.append("sequence_number")
                field_verifications["sequence_number"] = False
            else:
                field_verifications["sequence_number"] = True

        # 6. Reference Record Comparison (if provided)
        if original_record is not None:
            if record.image_hash_sha256 != original_record.image_hash_sha256:
                if "image_hash_sha256" not in tampered_fields:
                    tampered_fields.append("image_hash_sha256")
            if record.model_digest_sha256 != original_record.model_digest_sha256:
                if "model_digest_sha256" not in tampered_fields:
                    tampered_fields.append("model_digest_sha256")
            if record.preprocessing_config_hash != original_record.preprocessing_config_hash:
                if "preprocessing_config_hash" not in tampered_fields:
                    tampered_fields.append("preprocessing_config_hash")
            if record.timestamp_utc != original_record.timestamp_utc:
                if "timestamp_utc" not in tampered_fields:
                    tampered_fields.append("timestamp_utc")
            if record.nonce != original_record.nonce:
                if "nonce" not in tampered_fields:
                    tampered_fields.append("nonce")
            if record.sequence_number != original_record.sequence_number:
                if "sequence_number" not in tampered_fields:
                    tampered_fields.append("sequence_number")
            if record.predictions != original_record.predictions:
                if "predictions" not in tampered_fields:
                    tampered_fields.append("predictions")
            if record.binding_hash_sha256 != original_record.binding_hash_sha256:
                if "binding_hash_sha256" not in tampered_fields:
                    tampered_fields.append("binding_hash_sha256")
            if record.hmac_signature != original_record.hmac_signature:
                if "hmac_signature" not in tampered_fields:
                    tampered_fields.append("hmac_signature")

        # 7. Recompute Canonical Binding Hash
        _, preds_canonical_json = self.canonicalize_predictions(record.predictions)
        expected_binding = self.compute_binding_hash(
            record.image_hash_sha256,
            record.model_digest_sha256,
            record.preprocessing_config_hash,
            preds_canonical_json,
            record.timestamp_utc,
            record.nonce,
            record.sequence_number
        )

        binding_matches = (expected_binding.lower() == record.binding_hash_sha256.lower())
        field_verifications["binding_hash"] = binding_matches
        if not binding_matches:
            if "binding_hash_sha256" not in tampered_fields:
                tampered_fields.append("binding_hash_sha256")

        # 8. Verify HMAC Signature
        # Check signature against expected binding hash and stored binding hash
        sig_matches = self.verify_signature(expected_binding, record.hmac_signature)
        field_verifications["hmac_signature"] = sig_matches
        if not sig_matches:
            if "hmac_signature" not in tampered_fields:
                tampered_fields.append("hmac_signature")

        # 9. Offline Replay Protection Check
        registry = replay_registry or self.replay_registry
        if registry is not None and check_replay:
            is_replay, replay_reason = registry.check_replay(record)
            if is_replay:
                replay_detected = True
                field_verifications["replay_check"] = False
                tampered_fields.append("replay_detected")
            else:
                field_verifications["replay_check"] = True

        # 10. Synthesize Final Verification Outcome
        verification_passed = (len(tampered_fields) == 0 and not replay_detected)
        tamper_detected = not verification_passed

        if verification_passed:
            details = (
                "Record verification SUCCEEDED. Cryptographic binding among input image, "
                "model digest, preprocessing configuration, and predictions is unbroken and authenticated."
            )
            if register_if_valid and registry is not None:
                registry.register(record)
        else:
            tamper_reasons = []
            if replay_detected:
                tamper_reasons.append("REPLAY DETECTED (duplicate record_id, nonce, or binding hash)")
            if any(f in tampered_fields for f in ["hmac_signature", "binding_hash_sha256"]):
                tamper_reasons.append("Cryptographic binding digest or HMAC signature mismatch")
            if any(f in tampered_fields for f in ["image_hash_sha256", "model_digest_sha256", "preprocessing_config", "predictions"]):
                tamper_reasons.append(f"Content alteration on: {[f for f in tampered_fields if f not in ['hmac_signature', 'binding_hash_sha256', 'replay_detected']]}")
            if any(f in tampered_fields for f in ["timestamp_utc", "nonce", "sequence_number"]):
                tamper_reasons.append(f"Freshness metadata altered: {[f for f in tampered_fields if f in ['timestamp_utc', 'nonce', 'sequence_number']]}")

            details = f"TAMPERING DETECTED! Violations: {'; '.join(tamper_reasons) if tamper_reasons else ', '.join(tampered_fields)}."

        return ProvenanceVerificationResult(
            record_id=record.record_id,
            verification_passed=verification_passed,
            tamper_detected=tamper_detected,
            replay_detected=replay_detected,
            tampered_fields=tampered_fields,
            details=details,
            field_verifications=field_verifications
        )
