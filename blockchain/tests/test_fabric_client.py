import os
import unittest
import tempfile
import hashlib
from blockchain.client.fabric_client import FabricClient
from blockchain.client.models import AssuranceEventType


class TestFabricClient(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_file = os.path.join(self.temp_dir.name, "test_ledger.json")
        self.client = FabricClient(ledger_storage_path=self.ledger_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_status_query(self):
        status = self.client.get_status()
        self.assertEqual(status.status, "CONNECTED")
        self.assertEqual(status.channel_id, "assurancechannel")
        self.assertGreaterEqual(status.ledger_height, 1)

    def test_register_contributor(self):
        evt = self.client.register_contributor(
            contributor_id="contributor_test",
            org_msp="ContributorOrgMSP",
            metadata={"role": "sensor_provider"}
        )
        self.assertEqual(evt.event_type, AssuranceEventType.CONTRIBUTOR_REGISTERED)
        self.assertEqual(evt.asset_id, "contributor_test")
        self.assertIsNotNone(evt.tx_id)

    def test_register_dataset_manifest(self):
        manifest_h = hashlib.sha256(b"SAMPLE_MANIFEST_JSON").hexdigest()
        evt = self.client.register_dataset(
            dataset_id="DATASET_001",
            version="1.0.0",
            canonical_manifest_hash=manifest_h,
            contributor_id="contributor_test",
            sample_count=50
        )
        self.assertEqual(evt.event_type, AssuranceEventType.DATASET_REGISTERED)
        self.assertEqual(evt.manifest_hash, manifest_h)

    def test_record_and_verify_inference(self):
        img_h = hashlib.sha256(b"image_bytes").hexdigest()
        mod_d = hashlib.sha256(b"model_weights").hexdigest()
        prep_h = hashlib.sha256(b"prep_config").hexdigest()
        bind_h = hashlib.sha256(b"canonical_binding").hexdigest()

        evt = self.client.record_inference(
            record_id="REC-001",
            image_hash=img_h,
            model_digest=mod_d,
            preprocessing_hash=prep_h,
            binding_hash=bind_h,
            nonce="nonce_123",
            sequence_number=1,
            contributor_id="contributor_test"
        )
        self.assertEqual(evt.event_type, AssuranceEventType.INFERENCE_RECORDED)

        # Verify match
        res_match = self.client.verify_artifact("REC-001", bind_h)
        self.assertTrue(res_match["anchor_found"])
        self.assertTrue(res_match["match"])

        # Verify tamper detection on altered hash
        res_tamper = self.client.verify_artifact("REC-001", "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
        self.assertTrue(res_tamper["anchor_found"])
        self.assertFalse(res_tamper["match"])

    def test_asset_history(self):
        self.client.register_contributor("contributor_hist")
        history = self.client.get_asset_history("contributor_hist")
        self.assertGreaterEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
