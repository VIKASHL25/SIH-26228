import os
import shutil
import tempfile
import unittest

import torch

from cv_assurance.model.hasher import ModelHasher
from cv_assurance.model.model_loader import DummyCVModel
from cv_assurance.model.whitebox_analyzer import WhiteBoxAnalyzer


class TestModule2ModelIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.reference = os.path.join(cls.root, "demo_assets", "sample_model.pt")

    def test_hash_matches_and_detects_byte_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_path = os.path.join(tmp, "copy.pt")
            shutil.copyfile(self.reference, copy_path)
            hasher = ModelHasher()
            digest = hasher.compute_file_sha256(self.reference)
            self.assertEqual(hasher.compute_file_sha256(copy_path), digest)
            with open(copy_path, "ab") as handle:
                handle.write(b"tamper")
            result = hasher.inspect_model(copy_path, reference_sha256=digest)
            self.assertFalse(result.reference_match)
            self.assertFalse(result.integrity_verified)

    def test_whitebox_and_blackbox_fallback_contracts(self):
        whitebox = WhiteBoxAnalyzer().analyze_weights(self.reference)
        self.assertTrue(whitebox.access_granted)
        self.assertIn("WHITE-BOX AVAILABLE", whitebox.assessment_notes)
        unavailable = WhiteBoxAnalyzer().analyze_weights("missing-model.pt")
        self.assertFalse(unavailable.access_granted)
        self.assertIn("does not exist", unavailable.assessment_notes)

    def test_loaded_model_analysis_is_supported(self):
        model = DummyCVModel()
        result = WhiteBoxAnalyzer().analyze_model(model)
        self.assertTrue(result.access_granted)
        self.assertGreater(result.total_layers_analyzed, 0)


if __name__ == "__main__":
    unittest.main()
