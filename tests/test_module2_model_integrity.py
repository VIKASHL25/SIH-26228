import os
import json
import importlib.util
import shutil
import tempfile
import unittest

import torch

from cv_assurance.model.hasher import ModelHasher
from cv_assurance.model.model_loader import DummyCVModel
from cv_assurance.model.fingerprint import ModelFingerprinter
from cv_assurance.model.benchmark import Module2Benchmark
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
        reference_compared = WhiteBoxAnalyzer().analyze_weights(
            self.reference, reference_model_path=self.reference
        )
        self.assertTrue(reference_compared.reference_comparisons)
        self.assertIn("reference_comparison", reference_compared.evidence_basis)
        unavailable = WhiteBoxAnalyzer().analyze_weights("missing-model.pt")
        self.assertFalse(unavailable.access_granted)
        self.assertIn("does not exist", unavailable.assessment_notes)

    def test_loaded_model_analysis_is_supported(self):
        model = DummyCVModel()
        result = WhiteBoxAnalyzer().analyze_model(model)
        self.assertTrue(result.access_granted)
        self.assertGreater(result.total_layers_analyzed, 0)

    def test_supplied_model_path_is_actually_fingerprinted(self):
        dataset = os.path.join(self.root, "demo_assets", "eval_coco")
        images = [
            os.path.join(dataset, name)
            for name in sorted(os.listdir(dataset))
            if name.endswith(".jpg")
        ][:3]
        result = ModelFingerprinter().fingerprint_model(self.reference, images, num_eval=3)
        self.assertEqual(result.access_mode, "pytorch_white_box")
        self.assertEqual(result.total_eval_samples, 3)

    def test_none_never_generates_synthetic_fingerprint(self):
        result = ModelFingerprinter().fingerprint_dummy_or_callable(None, [])
        self.assertEqual(result.access_mode, "unavailable")
        self.assertEqual(result.total_eval_samples, 0)
        self.assertIn("no dummy predictions", result.findings_summary.lower())

    def test_callable_black_box_path_uses_actual_outputs(self):
        dataset = os.path.join(self.root, "demo_assets", "eval_coco")
        images = [
            os.path.join(dataset, name)
            for name in sorted(os.listdir(dataset))
            if name.endswith(".jpg")
        ][:2]

        def predictor(tensor):
            output = torch.zeros((tensor.shape[0], 4), dtype=torch.float32)
            output[:, 2] = 4.0
            return output

        result = ModelFingerprinter().fingerprint_callable(predictor, images, num_eval=2)
        self.assertEqual(result.access_mode, "black_box")
        self.assertEqual(result.total_eval_samples, 2)
        self.assertEqual(result.class_distribution, {"class_2": 1.0})

    def test_unavailable_black_box_never_becomes_a_fingerprint(self):
        dataset = os.path.join(self.root, "demo_assets", "eval_coco")
        images = [os.path.join(dataset, name) for name in sorted(os.listdir(dataset)) if name.endswith(".jpg")][:2]

        def unavailable_predictor(_tensor):
            return None

        result = ModelFingerprinter().fingerprint_callable(unavailable_predictor, images, num_eval=2)
        self.assertFalse(result.execution_available)
        self.assertEqual(result.total_eval_samples, 0)
        self.assertIn("failed", result.findings_summary.lower())

    def test_unsupported_model_format_returns_unavailable(self):
        result = ModelFingerprinter().fingerprint_model(
            os.path.join(self.root, "unsupported.model"), []
        )
        self.assertFalse(result.execution_available)
        self.assertEqual(result.access_mode, "unavailable")
        self.assertIn("UNAVAILABLE", result.findings_summary)

    def test_two_real_pytorch_architectures_produce_reproducible_fingerprints(self):
        dataset = os.path.join(self.root, "demo_assets", "eval_coco")
        images = [os.path.join(dataset, name) for name in sorted(os.listdir(dataset)) if name.endswith(".jpg")][:2]
        torch.manual_seed(7)
        architecture_a = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(3 * 64 * 64, 4))
        architecture_b = torch.nn.Sequential(
            torch.nn.Conv2d(3, 4, kernel_size=3), torch.nn.AdaptiveAvgPool2d((1, 1)),
            torch.nn.Flatten(), torch.nn.Linear(4, 4)
        )
        fingerprinter = ModelFingerprinter()
        first_a = fingerprinter._fingerprint_loaded_model(architecture_a, images, 2, "a", "white_box")
        first_b = fingerprinter._fingerprint_loaded_model(architecture_b, images, 2, "b", "white_box")
        repeat_a = fingerprinter._fingerprint_loaded_model(architecture_a, images, 2, "a", "white_box")
        self.assertTrue(first_a.execution_available)
        self.assertTrue(first_b.execution_available)
        self.assertEqual(first_a.model_dump(), repeat_a.model_dump())
        before_prediction = fingerprinter._predict(architecture_a, images[0])
        with torch.no_grad():
            architecture_a[1].weight.zero_()
            architecture_a[1].bias.zero_()
            architecture_a[1].bias[3] = 8.0
        changed_a = fingerprinter._fingerprint_loaded_model(architecture_a, images, 2, "a", "white_box")
        after_prediction = fingerprinter._predict(architecture_a, images[0])
        self.assertNotEqual(before_prediction[:2], after_prediction[:2])
        self.assertNotEqual(first_a.class_distribution, changed_a.class_distribution)

    def test_activation_statistics_are_collected_and_hooks_removed(self):
        model = torch.nn.Sequential(
            torch.nn.Conv2d(3, 2, kernel_size=3), torch.nn.ReLU(), torch.nn.Flatten(),
            torch.nn.Linear(2 * 62 * 62, 4)
        )
        model.train()
        result = WhiteBoxAnalyzer().analyze_model(model, activation_input=torch.ones((1, 3, 64, 64)))
        self.assertTrue(result.access_granted)
        self.assertTrue(result.activation_statistics)
        self.assertIn("mean", next(iter(result.activation_statistics.values())))
        self.assertTrue(model.training)
        self.assertFalse(any(getattr(module, "_forward_hooks", {}) for module in model.modules()))

    def test_reference_battery_manifest_is_deterministic_and_explicit(self):
        manifest_path = os.path.join(self.root, "demo_assets", "eval_coco", "reference_battery.json")
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["battery_version"], "module2-reference-battery-v1")
        self.assertEqual(manifest["expected_coverage"]["sample_count"], len(manifest["samples"]))
        self.assertEqual(manifest["samples"], sorted(manifest["samples"]))
        self.assertIn("not universal", manifest["expected_coverage"]["coverage_statement"])

    def test_supported_format_claims_are_truthful(self):
        hasher = ModelHasher()
        self.assertEqual(hasher.detect_format("model.onnx"), "onnx")
        self.assertEqual(hasher.detect_format("model.torchscript"), "torchscript")
        self.assertEqual(hasher.detect_format("model.pt"), "pytorch_pt")

    @unittest.skipUnless(importlib.util.find_spec("torch"), "torch is unavailable")
    def test_torchscript_executes_actual_inference_when_available(self):
        dataset = os.path.join(self.root, "demo_assets", "eval_coco")
        images = [os.path.join(dataset, name) for name in sorted(os.listdir(dataset)) if name.endswith(".jpg")][:2]
        model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(3 * 64 * 64, 4))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.torchscript")
            traced = torch.jit.trace(model, torch.zeros((1, 3, 64, 64)))
            traced.save(path)
            result = ModelFingerprinter().fingerprint_model(path, images, num_eval=2)
        self.assertTrue(result.execution_available)
        self.assertEqual(result.access_mode, "torchscript")

    @unittest.skipUnless(
        importlib.util.find_spec("torch") and importlib.util.find_spec("onnx") and importlib.util.find_spec("onnxruntime"),
        "offline ONNX runtime/toolchain is unavailable"
    )
    def test_onnx_executes_actual_inference_when_available(self):
        dataset = os.path.join(self.root, "demo_assets", "eval_coco")
        images = [os.path.join(dataset, name) for name in sorted(os.listdir(dataset)) if name.endswith(".jpg")][:2]
        model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(3 * 64 * 64, 4))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.onnx")
            torch.onnx.export(model, torch.zeros((1, 3, 64, 64)), path, input_names=["input"], output_names=["output"])
            result = ModelFingerprinter().fingerprint_model(path, images, num_eval=2)
        self.assertTrue(result.execution_available)
        self.assertEqual(result.access_mode, "onnx")

    def test_benchmark_clean_and_tampered_scenarios_are_reproducible(self):
        benchmark = Module2Benchmark(self.reference)
        clean = benchmark.evaluate_model("clean", self.reference)
        tampered = os.path.join(self.root, "demo_assets", "tampered_weights_model.pt")
        tampered_result = benchmark.evaluate_model("tampered_weights", tampered)
        self.assertTrue(clean.behavioral_execution_available)
        self.assertTrue(tampered_result.behavioral_execution_available)
        self.assertFalse(tampered_result.reference_hash_match)
        self.assertGreaterEqual(tampered_result.confidence_score, 0.0)
        self.assertLessEqual(tampered_result.confidence_score, 1.0)


if __name__ == "__main__":
    unittest.main()
