import os
import json
import tempfile
import unittest
from pathlib import Path

from cv_assurance.provenance.crypto_binding import (
    CryptographicProvenanceEngine,
    InferenceOutputPrediction,
    ProtectedInferenceRecord,
    PreprocessingConfig,
    ReplayProtectionRegistry,
    DEMO_SECRET_KEY
)
from cv_assurance.model.hasher import ModelHasher


class TestModule3AProvenance(unittest.TestCase):
    """
    Focused test suite for Module 3A:
    Inference Provenance & Cryptographic Output Integrity.
    Covers scenarios A through J with offline temporary fixtures.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.td = Path(self.temp_dir.name)

        # 1. Create a dummy test image
        self.img_path = str(self.td / "test_input.jpg")
        with open(self.img_path, "wb") as f:
            f.write(b"IMAGE_HEADER_BYTES_1234567890_PIXEL_DATA_RGB")

        # 2. Create a dummy model file
        self.model_path = str(self.td / "test_model.pt")
        with open(self.model_path, "wb") as f:
            f.write(b"MODEL_WEIGHT_TENSORS_CHECKPOINT_BYTES_987654321")

        # 3. Reference predictions
        self.preds = [
            InferenceOutputPrediction(box=[100.0, 150.0, 50.0, 80.0], confidence=0.923456, category_id=1, category_name="pedestrian"),
            InferenceOutputPrediction(box=[220.0, 300.0, 120.0, 90.0], confidence=0.887654, category_id=4, category_name="car")
        ]

        # 4. Standard engine and registry
        self.engine = CryptographicProvenanceEngine(secret_key="TEST_SUITE_SECURE_HMAC_KEY_128BIT")
        self.registry_file = str(self.td / "replay_registry.json")
        self.registry = ReplayProtectionRegistry(self.registry_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_scenario_a_valid_record_passes(self):
        """Scenario A: Valid protected record -> verification passes."""
        model_hash = ModelHasher.compute_file_sha256(self.model_path)
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash=model_hash,
            config_dict=PreprocessingConfig(resolution=[640, 640], confidence_threshold=0.5),
            predictions=self.preds,
            sequence_number=1
        )

        res = self.engine.verify_record(
            record,
            image_path=self.img_path,
            model_path=self.model_path,
            replay_registry=self.registry
        )

        self.assertTrue(res.verification_passed)
        self.assertFalse(res.tamper_detected)
        self.assertFalse(res.replay_detected)
        self.assertEqual(len(res.tampered_fields), 0)
        self.assertTrue(res.field_verifications.get("binding_hash"))
        self.assertTrue(res.field_verifications.get("hmac_signature"))
        self.assertTrue(res.field_verifications.get("image_integrity"))
        self.assertTrue(res.field_verifications.get("model_integrity"))

    def test_02_scenario_b_modify_input_image_fails(self):
        """Scenario B: Modify input image -> verification fails."""
        model_hash = ModelHasher.compute_file_sha256(self.model_path)
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash=model_hash,
            predictions=self.preds
        )

        # Create modified image with tampered pixel bytes
        tampered_img_path = str(self.td / "tampered_img.jpg")
        with open(tampered_img_path, "wb") as f:
            f.write(b"TAMPERED_IMAGE_BYTES_ADVERSARIAL_PATCH_INJECTED")

        # Verify against modified image on disk
        res = self.engine.verify_record(record, image_path=tampered_img_path)
        self.assertFalse(res.verification_passed)
        self.assertTrue(res.tamper_detected)
        self.assertIn("image_hash_sha256", res.tampered_fields)

        # Also verify tampering the record's image hash directly
        tampered_rec = record.model_copy(deep=True)
        tampered_rec.image_hash_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
        res2 = self.engine.verify_record(tampered_rec, original_record=record)
        self.assertFalse(res2.verification_passed)
        self.assertTrue(res2.tamper_detected)
        self.assertIn("image_hash_sha256", res2.tampered_fields)

    def test_03_scenario_c_modify_model_hash_fails(self):
        """Scenario C: Modify model hash -> verification fails."""
        model_hash = ModelHasher.compute_file_sha256(self.model_path)
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash=model_hash,
            predictions=self.preds
        )

        # Alter model file on disk
        tampered_model_path = str(self.td / "backdoored_model.pt")
        with open(tampered_model_path, "wb") as f:
            f.write(b"POISONED_MODEL_WEIGHTS_TROJAN_NEURONS_ACTIVE")

        res = self.engine.verify_record(record, model_path=tampered_model_path)
        self.assertFalse(res.verification_passed)
        self.assertTrue(res.tamper_detected)
        self.assertIn("model_digest_sha256", res.tampered_fields)

        # Also alter record model digest field directly
        tampered_rec = record.model_copy(deep=True)
        tampered_rec.model_digest_sha256 = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        res2 = self.engine.verify_record(tampered_rec, original_record=record)
        self.assertFalse(res2.verification_passed)
        self.assertTrue(res2.tamper_detected)
        self.assertIn("model_digest_sha256", res2.tampered_fields)

    def test_04_scenario_d_modify_preprocessing_config_fails(self):
        """Scenario D: Modify preprocessing config -> verification fails."""
        cfg = PreprocessingConfig(resolution=[640, 640], confidence_threshold=0.50)
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            config_dict=cfg,
            predictions=self.preds
        )

        # 1. Tamper stored config dictionary (e.g. adversary lowers confidence threshold to 0.05)
        tampered_rec = record.model_copy(deep=True)
        tampered_rec.preprocessing_config["confidence_threshold"] = 0.05

        res = self.engine.verify_record(tampered_rec)
        self.assertFalse(res.verification_passed)
        self.assertTrue(res.tamper_detected)
        self.assertIn("preprocessing_config", res.tampered_fields)

        # 2. Tamper preprocessing config hash directly
        tampered_rec2 = record.model_copy(deep=True)
        tampered_rec2.preprocessing_config_hash = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        res2 = self.engine.verify_record(tampered_rec2, original_record=record)
        self.assertFalse(res2.verification_passed)
        self.assertTrue(res2.tamper_detected)
        self.assertIn("preprocessing_config_hash", res2.tampered_fields)

    def test_05_scenario_e_modify_prediction_fails(self):
        """Scenario E: Modify prediction -> verification fails."""
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            predictions=self.preds
        )

        # 1. Modify confidence score
        tampered_rec1 = record.model_copy(deep=True)
        tampered_rec1.predictions[0].confidence = 0.10
        res1 = self.engine.verify_record(tampered_rec1)
        self.assertFalse(res1.verification_passed)
        self.assertTrue(res1.tamper_detected)
        self.assertIn("predictions", res1.tampered_fields)

        # 2. Modify bounding box coordinates
        tampered_rec2 = record.model_copy(deep=True)
        tampered_rec2.predictions[0].box = [0.0, 0.0, 10.0, 10.0]
        res2 = self.engine.verify_record(tampered_rec2)
        self.assertFalse(res2.verification_passed)
        self.assertTrue(res2.tamper_detected)
        self.assertIn("predictions", res2.tampered_fields)

        # 3. Modify category label
        tampered_rec3 = record.model_copy(deep=True)
        tampered_rec3.predictions[0].category_name = "tank_decoy"
        res3 = self.engine.verify_record(tampered_rec3)
        self.assertFalse(res3.verification_passed)
        self.assertTrue(res3.tamper_detected)
        self.assertIn("predictions", res3.tampered_fields)

    def test_06_scenario_f_modify_timestamp_fails(self):
        """Scenario F: Modify timestamp -> verification fails."""
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            predictions=self.preds
        )

        tampered_rec = record.model_copy(deep=True)
        # Shift timestamp backwards
        tampered_rec.timestamp_utc -= 3600.0

        res = self.engine.verify_record(tampered_rec, original_record=record)
        self.assertFalse(res.verification_passed)
        self.assertTrue(res.tamper_detected)
        self.assertIn("timestamp_utc", res.tampered_fields)

    def test_07_scenario_g_modify_nonce_fails(self):
        """Scenario G: Modify nonce -> verification fails."""
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            predictions=self.preds
        )

        tampered_rec = record.model_copy(deep=True)
        tampered_rec.nonce = "tampered_nonce_abcdef123456"

        res = self.engine.verify_record(tampered_rec, original_record=record)
        self.assertFalse(res.verification_passed)
        self.assertTrue(res.tamper_detected)
        self.assertIn("nonce", res.tampered_fields)

    def test_08_scenario_h_modify_sequence_number_fails(self):
        """Scenario H: Modify sequence number -> verification fails."""
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            predictions=self.preds,
            sequence_number=10
        )

        tampered_rec = record.model_copy(deep=True)
        tampered_rec.sequence_number = 999

        res = self.engine.verify_record(tampered_rec, original_record=record)
        self.assertFalse(res.verification_passed)
        self.assertTrue(res.tamper_detected)
        self.assertIn("sequence_number", res.tampered_fields)

    def test_09_scenario_i_modify_hmac_fails(self):
        """Scenario I: Modify HMAC/binding hash -> verification fails."""
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            predictions=self.preds
        )

        # 1. Modify HMAC signature
        tampered_rec1 = record.model_copy(deep=True)
        tampered_rec1.hmac_signature = "bad_forged_hmac_signature_000000000000000000000000000000000000"
        res1 = self.engine.verify_record(tampered_rec1)
        self.assertFalse(res1.verification_passed)
        self.assertTrue(res1.tamper_detected)
        self.assertIn("hmac_signature", res1.tampered_fields)

        # 2. Modify binding hash
        tampered_rec2 = record.model_copy(deep=True)
        tampered_rec2.binding_hash_sha256 = "0000111122223333444455556666777788889999aaaabbbbccccddddeeeeffff"
        res2 = self.engine.verify_record(tampered_rec2)
        self.assertFalse(res2.verification_passed)
        self.assertTrue(res2.tamper_detected)
        self.assertIn("binding_hash_sha256", res2.tampered_fields)

    def test_10_scenario_j_replay_detection(self):
        """Scenario J: Replay the same record -> replay is detected."""
        record = self.engine.create_protected_record(
            image_path_or_hash=self.img_path,
            model_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            predictions=self.preds,
            sequence_number=1
        )

        # First verification & registration -> must pass
        res1 = self.engine.verify_record(
            record,
            replay_registry=self.registry,
            register_if_valid=True
        )
        self.assertTrue(res1.verification_passed)
        self.assertFalse(res1.replay_detected)

        # Replay attempt with exact same record -> must detect replay
        res2 = self.engine.verify_record(
            record,
            replay_registry=self.registry
        )
        self.assertFalse(res2.verification_passed)
        self.assertTrue(res2.tamper_detected)
        self.assertTrue(res2.replay_detected)
        self.assertIn("replay_detected", res2.tampered_fields)

        # Replay attempt where adversary generates new record_id but reuses nonce
        spoofed_rec = record.model_copy(deep=True)
        spoofed_rec.record_id = "INF-REC-SPOOFED01"
        res3 = self.engine.verify_record(
            spoofed_rec,
            replay_registry=self.registry
        )
        self.assertFalse(res3.verification_passed)
        self.assertTrue(res3.replay_detected)

    def test_11_prediction_order_canonicalization(self):
        """Verify that logically identical predictions with different orders produce deterministic binding."""
        preds_a = [
            InferenceOutputPrediction(box=[10, 20, 30, 40], confidence=0.9, category_id=1, category_name="car"),
            InferenceOutputPrediction(box=[50, 60, 70, 80], confidence=0.8, category_id=2, category_name="truck")
        ]
        preds_b = [
            InferenceOutputPrediction(box=[50, 60, 70, 80], confidence=0.8, category_id=2, category_name="truck"),
            InferenceOutputPrediction(box=[10, 20, 30, 40], confidence=0.9, category_id=1, category_name="car")
        ]

        h_a = CryptographicProvenanceEngine.compute_predictions_hash(preds_a)
        h_b = CryptographicProvenanceEngine.compute_predictions_hash(preds_b)
        self.assertEqual(h_a, h_b)

    def test_12_secret_key_environment_override(self):
        """Verify secret key loading from environment variable CV_INFERENCE_SECRET_KEY."""
        os.environ["CV_INFERENCE_SECRET_KEY"] = "ENV_AIRGAPPED_HMAC_KEY_999"
        try:
            custom_engine = CryptographicProvenanceEngine()
            self.assertFalse(custom_engine.is_demo_key)
            self.assertEqual(custom_engine.secret_key, b"ENV_AIRGAPPED_HMAC_KEY_999")
        finally:
            del os.environ["CV_INFERENCE_SECRET_KEY"]

        # Default fallback is demo key
        default_engine = CryptographicProvenanceEngine()
        self.assertTrue(default_engine.is_demo_key)
        self.assertEqual(default_engine.secret_key, DEMO_SECRET_KEY.encode('utf-8'))


if __name__ == "__main__":
    unittest.main()
