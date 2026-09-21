import os
import unittest
import tempfile
import hashlib
from blockchain.client.fabric_client import FabricClient
from blockchain.client.anchor_service import BlockchainAnchorService
from blockchain.client.verifier import BlockchainDualVerifier

from cv_assurance.provenance.crypto_binding import (
    CryptographicProvenanceEngine,
    PreprocessingConfig,
    InferenceOutputPrediction,
    ProtectedInferenceRecord
)


class TestDualVerifier(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_file = os.path.join(self.temp_dir.name, "test_ledger.json")
        self.client = FabricClient(ledger_storage_path=self.ledger_file)
        self.anchor_service = BlockchainAnchorService(self.client)
        self.prov_engine = CryptographicProvenanceEngine()
        self.verifier = BlockchainDualVerifier(self.client, self.prov_engine)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dual_verification_clean_record(self):
        preds = [
            InferenceOutputPrediction(box=[10.0, 10.0, 50.0, 50.0], confidence=0.95, category_id=1, category_name="car")
        ]
        rec = self.prov_engine.create_protected_record(
            image_path_or_hash=b"TEST_IMAGE_BYTES_CLEAN",
            model_hash="fdab8c003aa41f4c3795f97f" * 2,
            predictions=preds,
            sequence_number=1,
            nonce="nonce_test_001"
        )

        # 1. Anchor to blockchain
        self.anchor_service.anchor_inference_record(rec, contributor_id="contributor_A")

        # 2. Dual verify
        res = self.verifier.verify_inference_record_dual(rec, image_bytes_or_path=b"TEST_IMAGE_BYTES_CLEAN")
        self.assertTrue(res.local_verification_passed)
        self.assertTrue(res.blockchain_anchor_found)
        self.assertTrue(res.blockchain_hash_matched)
        self.assertEqual(res.final_assurance_status, "TRUST_VERIFIED")
        self.assertEqual(res.recommended_disposition, "ACCEPT")

    def test_dual_verification_detects_tampered_predictions(self):
        preds = [
            InferenceOutputPrediction(box=[10.0, 10.0, 50.0, 50.0], confidence=0.95, category_id=1, category_name="car")
        ]
        rec = self.prov_engine.create_protected_record(
            image_path_or_hash=b"TEST_IMAGE_BYTES_CLEAN",
            model_hash="fdab8c003aa41f4c3795f97f" * 2,
            predictions=preds,
            sequence_number=1,
            nonce="nonce_test_002"
        )
        self.anchor_service.anchor_inference_record(rec, contributor_id="contributor_A")

        # Tampered copy
        tampered_rec = ProtectedInferenceRecord(
            record_id=rec.record_id,
            timestamp_utc=rec.timestamp_utc,
            nonce=rec.nonce,
            sequence_number=rec.sequence_number,
            image_hash_sha256=rec.image_hash_sha256,
            model_digest_sha256=rec.model_digest_sha256,
            preprocessing_config_hash=rec.preprocessing_config_hash,
            predictions=[InferenceOutputPrediction(box=[99.0, 99.0, 50.0, 50.0], confidence=0.99, category_id=2, category_name="truck")],
            binding_hash_sha256=hashlib.sha256(b"ALTERED_BINDING").hexdigest(),
            hmac_signature=rec.hmac_signature
        )

        res = self.verifier.verify_inference_record_dual(tampered_rec, image_bytes_or_path=b"TEST_IMAGE_BYTES_CLEAN")
        self.assertFalse(res.local_verification_passed)
        self.assertTrue(res.blockchain_anchor_found)
        self.assertFalse(res.blockchain_hash_matched)
        self.assertEqual(res.final_assurance_status, "TAMPER_DETECTED")
        self.assertEqual(res.recommended_disposition, "QUARANTINE")


if __name__ == "__main__":
    unittest.main()
