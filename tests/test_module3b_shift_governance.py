"""
Module 3B Test Suite - Distribution Shift, Governance, Tamper-Evident Audit Trail,
and Complete End-to-End Integration.

Tests cover:
  A. DistributionShiftDetector: NO_SHIFT, OPERATIONAL_DRIFT, SUSPICIOUS_MANIPULATION
  B. TamperEvidentAuditChain: append, verify, tamper detection, persistence
  C. AssuranceEngine: end-to-end governance pipeline integration
  D. AssuranceReport schema completeness
  E. EnvironmentalFeatureExtractor with real images
"""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cv_assurance.shift.distribution_test import (
    DistributionShiftDetector, DistributionShiftResult
)
from cv_assurance.shift.environmental import (
    EnvironmentalFeatureExtractor, EnvironmentalShiftMetrics
)
from cv_assurance.governance.audit_chain import (
    TamperEvidentAuditChain, AuditEvent, GENESIS_PREVIOUS_HASH
)
from cv_assurance.governance.report_schema import (
    AssuranceFinding, AssuranceReport, SeverityLevel,
    RecommendedDisposition, AuditChainSummary
)
from cv_assurance.governance.engine import AssuranceEngine


def _make_shift_metrics(
    terrain_texture_contrast=15.0,
    terrain_color_hist_energy=0.02,
    mean_brightness=120.0,
    contrast_std=40.0,
    hsv_value_mean=120.0,
    low_light_ratio=0.01,
    overexposure_ratio=0.01,
    noise_floor_std=2.0,
    blur_laplacian_variance=600.0,
    psnr_estimate=45.0,
    hue_mean=55.0,
    saturation_mean=80.0,
    green_vegetation_index=5.0
):
    return EnvironmentalShiftMetrics(
        terrain_texture_contrast=terrain_texture_contrast,
        terrain_color_hist_energy=terrain_color_hist_energy,
        mean_brightness=mean_brightness,
        contrast_std=contrast_std,
        hsv_value_mean=hsv_value_mean,
        low_light_ratio=low_light_ratio,
        overexposure_ratio=overexposure_ratio,
        noise_floor_std=noise_floor_std,
        blur_laplacian_variance=blur_laplacian_variance,
        psnr_estimate=psnr_estimate,
        hue_mean=hue_mean,
        saturation_mean=saturation_mean,
        green_vegetation_index=green_vegetation_index
    )


class _FakeDataset:
    class _S:
        def __init__(self, image_path):
            self.image_path = image_path

    def __init__(self, paths):
        self.samples = [self._S(p) for p in paths]
        self.name = "FakeDataset"


# ---------------------------------------------------------------------------
# Part A - Distribution Shift Detector
# ---------------------------------------------------------------------------

class TestDistributionShiftDetector(unittest.TestCase):

    def setUp(self):
        self.detector = DistributionShiftDetector()

    def _run_detector(self, ref_metrics_list, tgt_metrics_list):
        ref_ds = _FakeDataset([f"img_{i}.jpg" for i in range(len(ref_metrics_list))])
        tgt_ds = _FakeDataset([f"tgt_{i}.jpg" for i in range(len(tgt_metrics_list))])
        ref_iter = iter(ref_metrics_list)
        tgt_iter = iter(tgt_metrics_list)

        def _mock_extract(image_path):
            try:
                if image_path.startswith("img_"):
                    return next(ref_iter)
                else:
                    return next(tgt_iter)
            except StopIteration:
                return None

        with patch.object(self.detector.extractor, "extract_metrics", side_effect=_mock_extract):
            return self.detector.analyze(ref_ds, tgt_ds)

    def test_01_no_shift_identical_distributions(self):
        metrics = [_make_shift_metrics() for _ in range(20)]
        result = self._run_detector(metrics[:10], metrics[10:])
        self.assertIsInstance(result, DistributionShiftResult)
        self.assertEqual(result.shift_classification, "NO_SHIFT")
        self.assertFalse(result.material_shift_detected)
        self.assertEqual(result.overall_drift_score, 0.0)

    def test_02_operational_drift_multi_dimension(self):
        ref = [_make_shift_metrics(mean_brightness=120.0, green_vegetation_index=10.0) for _ in range(25)]
        tgt = [_make_shift_metrics(mean_brightness=20.0, green_vegetation_index=-30.0) for _ in range(25)]
        result = self._run_detector(ref, tgt)
        self.assertIn(result.shift_classification, ("OPERATIONAL_DRIFT", "SUSPICIOUS_MANIPULATION"))
        self.assertTrue(result.material_shift_detected)
        self.assertGreater(result.overall_drift_score, 0.0)
        self.assertEqual(len(result.dimensions), 4)

    def test_02b_benign_environmental_change_is_not_suspicious(self):
        ref = [_make_shift_metrics(mean_brightness=120.0, green_vegetation_index=10.0) for _ in range(30)]
        tgt = [_make_shift_metrics(mean_brightness=35.0, green_vegetation_index=-20.0) for _ in range(30)]
        result = self._run_detector(ref, tgt)
        self.assertEqual(result.shift_classification, "OPERATIONAL_DRIFT")
        self.assertIn("proxi", result.evidence_details["feature_semantics"].lower())

    def test_03_suspicious_manipulation_isolated_sensor(self):
        ref = [_make_shift_metrics(noise_floor_std=2.0) for _ in range(25)]
        tgt = [_make_shift_metrics(noise_floor_std=35.0) for _ in range(25)]
        result = self._run_detector(ref, tgt)
        self.assertIn(result.shift_classification, ("SUSPICIOUS_MANIPULATION",))
        self.assertTrue(result.material_shift_detected)

    def test_04_dimension_details_structure(self):
        metrics = [_make_shift_metrics() for _ in range(12)]
        result = self._run_detector(metrics[:6], metrics[6:])
        dim_names = {d.dimension_name for d in result.dimensions}
        self.assertEqual(dim_names, {"terrain", "illumination", "sensor", "season"})

    def test_05_insufficient_samples_returns_no_shift(self):
        ref_ds = _FakeDataset([])
        tgt_ds = _FakeDataset([])
        result = self.detector.analyze(ref_ds, tgt_ds)
        self.assertEqual(result.shift_classification, "NO_SHIFT")
        self.assertFalse(result.material_shift_detected)
        self.assertEqual(len(result.dimensions), 0)
        self.assertEqual(result.confidence_score, 0.0)
        self.assertEqual(result.sample_sufficiency, "insufficient")

    def test_06_evidence_details_populated(self):
        ref = [_make_shift_metrics(mean_brightness=50.0) for _ in range(15)]
        tgt = [_make_shift_metrics(mean_brightness=200.0) for _ in range(15)]
        result = self._run_detector(ref, tgt)
        self.assertIn("illumination", result.evidence_details)
        self.assertIn("ks_stat", result.evidence_details["illumination"])
        self.assertIn("p_value", result.evidence_details["illumination"])
        self.assertIn("wasserstein_distance", result.evidence_details["illumination"])
        self.assertEqual(result.evidence_details["illumination"]["feature_is_proxy"], True)

    def test_07_confidence_score_in_valid_range(self):
        metrics = [_make_shift_metrics() for _ in range(12)]
        result = self._run_detector(metrics[:6], metrics[6:])
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)
        self.assertEqual(result.confidence_semantics, "heuristic_evidence_derived_not_calibrated")

    def test_08_drift_score_bounded(self):
        ref = [_make_shift_metrics(mean_brightness=10.0, noise_floor_std=1.0) for _ in range(20)]
        tgt = [_make_shift_metrics(mean_brightness=250.0, noise_floor_std=50.0) for _ in range(20)]
        result = self._run_detector(ref, tgt)
        self.assertGreaterEqual(result.overall_drift_score, 0.0)
        self.assertLessEqual(result.overall_drift_score, 1.0)


# ---------------------------------------------------------------------------
# Part B - Tamper-Evident Audit Chain
# ---------------------------------------------------------------------------

class TestTamperEvidentAuditChain(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.chain_file = os.path.join(self.tmp_dir.name, "audit_chain.json")
        self.chain = TamperEvidentAuditChain(chain_file=self.chain_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_genesis_hash_empty_chain(self):
        self.assertEqual(self.chain.latest_hash, GENESIS_PREVIOUS_HASH)
        self.assertEqual(self.chain.chain_length, 0)

    def test_02_append_single_event(self):
        evt = self.chain.append_event(
            event_type="PIPELINE_INIT",
            affected_asset="dataset/test.json",
            event_summary="Initiated assurance pipeline test run.",
            event_data={"test_run": True}
        )
        self.assertIsInstance(evt, AuditEvent)
        self.assertEqual(self.chain.chain_length, 1)
        self.assertEqual(evt.sequence_index, 0)
        self.assertEqual(evt.previous_event_hash, GENESIS_PREVIOUS_HASH)
        self.assertNotEqual(evt.current_event_hash, GENESIS_PREVIOUS_HASH)
        self.assertEqual(len(evt.current_event_hash), 64)

    def test_03_chain_linking_three_events(self):
        e1 = self.chain.append_event("DATASET_AUDIT", "ds1", "Dataset audit done.")
        e2 = self.chain.append_event("MODEL_AUDIT", "model.pt", "Model audit done.")
        e3 = self.chain.append_event("SHIFT_AUDIT", "ds1", "Shift audit done.")
        self.assertEqual(e2.previous_event_hash, e1.current_event_hash)
        self.assertEqual(e3.previous_event_hash, e2.current_event_hash)
        self.assertEqual(self.chain.chain_length, 3)

    def test_04_verify_unbroken_chain(self):
        for i in range(5):
            self.chain.append_event("TEST_EVENT", f"asset_{i}", f"Event {i}")
        is_valid, msg, broken_idx = self.chain.verify_chain()
        self.assertTrue(is_valid)
        self.assertIsNone(broken_idx)
        self.assertIn("tamper-free", msg.lower())

    def test_05_verify_empty_chain_passes(self):
        is_valid, msg, broken_idx = self.chain.verify_chain()
        self.assertTrue(is_valid)
        self.assertIsNone(broken_idx)

    def test_06_tamper_payload_detected(self):
        self.chain.append_event("EVT_A", "asset", "Original summary.")
        self.chain.append_event("EVT_B", "asset", "Second event.")
        self.chain.events[0].event_summary = "TAMPERED SUMMARY INJECTED"
        is_valid, msg, broken_idx = self.chain.verify_chain()
        self.assertFalse(is_valid)
        self.assertIsNotNone(broken_idx)
        self.assertIn("Tampering", msg)

    def test_07_tamper_hash_detected(self):
        self.chain.append_event("EVT_X", "asset", "Normal event.")
        self.chain.append_event("EVT_Y", "asset", "Second event.")
        self.chain.events[0].current_event_hash = "a" * 64
        is_valid, msg, broken_idx = self.chain.verify_chain()
        self.assertFalse(is_valid)
        self.assertIsNotNone(broken_idx)

    def test_08_persistence_and_reload(self):
        for i in range(4):
            self.chain.append_event("EVT", f"asset_{i}", f"Event {i}", {"idx": i})
        stored_hashes = [e.current_event_hash for e in self.chain.events]
        reloaded = TamperEvidentAuditChain(chain_file=self.chain_file)
        self.assertEqual(reloaded.chain_length, 4)
        for i, evt in enumerate(reloaded.events):
            self.assertEqual(evt.current_event_hash, stored_hashes[i])
        is_valid, msg, _ = reloaded.verify_chain()
        self.assertTrue(is_valid)

    def test_09_export_log_structure(self):
        self.chain.append_event("TEST", "asset", "Summary.", {"key": "val"})
        log = self.chain.export_log()
        self.assertEqual(len(log), 1)
        evt_dict = log[0]
        for field in [
            "event_id", "sequence_index", "timestamp_utc", "timestamp_iso",
            "event_type", "affected_asset", "event_summary",
            "event_data", "previous_event_hash", "current_event_hash"
        ]:
            self.assertIn(field, evt_dict)

    def test_10_clear_and_reset(self):
        self.chain.append_event("EVT", "asset", "Summary.")
        self.chain.clear()
        self.assertEqual(self.chain.chain_length, 0)
        self.assertEqual(self.chain.latest_hash, GENESIS_PREVIOUS_HASH)
        self.assertFalse(os.path.exists(self.chain_file))

    def test_11_deterministic_hash_computation(self):
        h1 = AuditEvent.compute_event_hash(
            event_id="TEST-001",
            sequence_index=0,
            timestamp_utc=1700000000.0,
            timestamp_iso="2023-11-14T00:00:00+00:00",
            event_type="TEST",
            affected_asset="asset.json",
            event_summary="Testing hash determinism.",
            event_data={"k": "v"},
            previous_event_hash="0" * 64
        )
        h2 = AuditEvent.compute_event_hash(
            event_id="TEST-001",
            sequence_index=0,
            timestamp_utc=1700000000.0,
            timestamp_iso="2023-11-14T00:00:00+00:00",
            event_type="TEST",
            affected_asset="asset.json",
            event_summary="Testing hash determinism.",
            event_data={"k": "v"},
            previous_event_hash="0" * 64
        )
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_12_sequence_discontinuity_detected(self):
        self.chain.append_event("EVT_A", "asset", "First.")
        self.chain.append_event("EVT_B", "asset", "Second.")
        self.chain.events[1].sequence_index = 99
        is_valid, msg, broken_idx = self.chain.verify_chain()
        self.assertFalse(is_valid)
        self.assertEqual(broken_idx, 1)


# ---------------------------------------------------------------------------
# Part C - Governance Engine End-to-End (using mock ingestion)
# ---------------------------------------------------------------------------

class TestGovernanceEngineIntegration(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp_dir.name)
        self.dataset_dir = str(self.td / "dataset")
        os.makedirs(self.dataset_dir, exist_ok=True)
        self.chain_file = str(self.td / "audit_chain.json")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _run_with_mocks(self):
        from cv_assurance.data.duplicates import DuplicateAnalysisResult, DuplicatePair
        from cv_assurance.data.label_integrity import LabelIntegrityResult
        from cv_assurance.data.ood_detector import OODAnalysisResult
        engine = AssuranceEngine()

        fake_dataset = MagicMock()
        fake_dataset.name = "mock_dataset"
        fake_dataset.samples = []

        dup_clean = MagicMock()
        dup_clean.duplicate_pairs_count = 0
        dup_clean.duplicate_samples_count = 0
        dup_clean.flooding_risk_score = 0.0
        dup_clean.duplicate_pairs = []

        lbl_clean = MagicMock()
        lbl_clean.suspicious_samples_count = 0
        lbl_clean.mislabelling_rate = 0.0
        lbl_clean.systematic_pattern_detected = False
        lbl_clean.flagged_samples = []

        ood_clean = MagicMock()
        ood_clean.ood_samples_count = 0
        ood_clean.ood_ratio = 0.0
        ood_clean.ood_samples = []

        bd_clean = MagicMock()
        bd_clean.poisoned_samples_count = 0
        bd_clean.poisoning_rate = 0.0
        bd_clean.detected_triggers = []

        contrib_clean = MagicMock()
        contrib_clean.profiles = []

        engine.ingester.auto_ingest = MagicMock(return_value=fake_dataset)
        engine.duplicate_detector.analyze = MagicMock(return_value=dup_clean)
        engine.label_analyzer.analyze = MagicMock(return_value=lbl_clean)
        engine.ood_detector.analyze = MagicMock(return_value=ood_clean)
        engine.backdoor_detector.analyze = MagicMock(return_value=bd_clean)
        engine.risk_aggregator.aggregate = MagicMock(return_value=contrib_clean)

        report = engine.run_full_assurance(
            dataset_path=self.dataset_dir,
            audit_chain_file=self.chain_file
        )
        return engine, report

    def test_01_clean_dataset_produces_accept_disposition(self):
        _, report = self._run_with_mocks()
        self.assertIsInstance(report, AssuranceReport)
        self.assertEqual(report.overall_disposition, RecommendedDisposition.ACCEPT)
        self.assertGreaterEqual(report.overall_health_score, 90.0)

    def test_02_report_has_required_fields(self):
        _, report = self._run_with_mocks()
        self.assertTrue(report.report_id.startswith("RPT-"))
        self.assertIsNotNone(report.generated_at_utc)
        self.assertIsNotNone(report.audit_trail_hash)
        self.assertEqual(len(report.audit_trail_hash), 64)
        self.assertIsInstance(report.findings, list)
        self.assertIsInstance(report.supported_attack_classes, list)
        self.assertGreater(len(report.supported_attack_classes), 0)

    def test_03_audit_chain_embedded_in_report(self):
        _, report = self._run_with_mocks()
        self.assertIsNotNone(report.audit_chain)
        chain_summary = report.audit_chain
        self.assertIsInstance(chain_summary, AuditChainSummary)
        self.assertEqual(chain_summary.verification_status, "VERIFIED_UNBROKEN")
        self.assertGreaterEqual(chain_summary.chain_length, 2)
        self.assertEqual(len(chain_summary.latest_event_hash), 64)

    def test_04_audit_chain_persisted_to_json(self):
        _, report = self._run_with_mocks()
        self.assertTrue(os.path.exists(self.chain_file))
        with open(self.chain_file, "r") as f:
            chain_data = json.load(f)
        self.assertIsInstance(chain_data, list)
        self.assertGreaterEqual(len(chain_data), 2)
        for evt_dict in chain_data:
            self.assertIn("current_event_hash", evt_dict)
            self.assertIn("previous_event_hash", evt_dict)
            self.assertEqual(len(evt_dict["current_event_hash"]), 64)

    def test_05_persisted_chain_passes_independent_verification(self):
        _, report = self._run_with_mocks()
        reloaded_chain = TamperEvidentAuditChain(chain_file=self.chain_file)
        is_valid, msg, broken_idx = reloaded_chain.verify_chain()
        self.assertTrue(is_valid, f"Chain verification failed: {msg}")
        self.assertIsNone(broken_idx)

    def test_06_health_score_in_valid_range(self):
        _, report = self._run_with_mocks()
        self.assertGreaterEqual(report.overall_health_score, 0.0)
        self.assertLessEqual(report.overall_health_score, 100.0)

    def test_07_report_serializable_to_json(self):
        _, report = self._run_with_mocks()
        try:
            dumped = report.model_dump_json(indent=2)
        except AttributeError:
            dumped = report.json(indent=2)
        parsed = json.loads(dumped)
        self.assertIn("report_id", parsed)
        self.assertIn("overall_health_score", parsed)
        self.assertIn("audit_trail_hash", parsed)

    def test_08_summary_counts_consistent_with_findings(self):
        _, report = self._run_with_mocks()
        actual_critical = sum(1 for f in report.findings if f.severity == SeverityLevel.CRITICAL)
        actual_high = sum(1 for f in report.findings if f.severity == SeverityLevel.HIGH)
        self.assertEqual(report.summary_counts.get("CRITICAL", 0), actual_critical)
        self.assertEqual(report.summary_counts.get("HIGH", 0), actual_high)
        self.assertEqual(report.summary_counts.get("total_findings", 0), len(report.findings))


# ---------------------------------------------------------------------------
# Part D - Report Schema Validation
# ---------------------------------------------------------------------------

class TestReportSchema(unittest.TestCase):

    def _make_finding(self, severity=SeverityLevel.HIGH, category="data_integrity"):
        return AssuranceFinding(
            finding_id="FND-TEST-001",
            category=category,
            title="Test Finding",
            human_readable_reason="Detected suspicious activity for testing purposes.",
            supporting_evidence={"evidence_key": "evidence_value"},
            confidence_score=0.92,
            severity=severity,
            affected_asset="test_asset",
            recommended_disposition=RecommendedDisposition.REVIEW
        )

    def test_01_finding_fields_accessible(self):
        f = self._make_finding()
        self.assertEqual(f.finding_id, "FND-TEST-001")
        self.assertEqual(f.severity, SeverityLevel.HIGH)
        self.assertEqual(f.recommended_disposition, RecommendedDisposition.REVIEW)
        self.assertIsInstance(f.supporting_evidence, dict)

    def test_02_severity_enum_values(self):
        for level in [SeverityLevel.CRITICAL, SeverityLevel.HIGH,
                      SeverityLevel.MEDIUM, SeverityLevel.LOW, SeverityLevel.INFO]:
            f = self._make_finding(severity=level)
            self.assertEqual(f.severity, level)

    def test_03_disposition_enum_values(self):
        for disp in [RecommendedDisposition.ACCEPT, RecommendedDisposition.REVIEW,
                     RecommendedDisposition.QUARANTINE]:
            finding = AssuranceFinding(
                finding_id="F-001",
                category="model_integrity",
                title="T",
                human_readable_reason="R",
                supporting_evidence={},
                confidence_score=0.5,
                severity=SeverityLevel.MEDIUM,
                affected_asset="A",
                recommended_disposition=disp
            )
            self.assertEqual(finding.recommended_disposition, disp)

    def test_04_finding_categories_match_spec(self):
        for cat in ["data_integrity", "model_integrity",
                    "distribution_shift", "inference_provenance"]:
            f = self._make_finding(category=cat)
            self.assertEqual(f.category, cat)


# ---------------------------------------------------------------------------
# Part E - Environmental Feature Extractor
# ---------------------------------------------------------------------------

class TestEnvironmentalFeatureExtractor(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp_dir.name)
        self.extractor = EnvironmentalFeatureExtractor()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_test_image(self, filename="test.jpg", color=(120, 80, 60)):
        try:
            import cv2
            import numpy as np
            img = np.full((128, 128, 3), color, dtype=np.uint8)
            path = str(self.td / filename)
            cv2.imwrite(path, img)
            return path
        except ImportError:
            return None

    def test_01_extract_returns_metrics_for_valid_image(self):
        path = self._create_test_image()
        if path is None:
            self.skipTest("cv2 not available")
        metrics = self.extractor.extract_metrics(path)
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics, EnvironmentalShiftMetrics)

    def test_02_all_metric_fields_non_negative(self):
        path = self._create_test_image()
        if path is None:
            self.skipTest("cv2 not available")
        m = self.extractor.extract_metrics(path)
        self.assertGreaterEqual(m.mean_brightness, 0.0)
        self.assertGreaterEqual(m.noise_floor_std, 0.0)
        self.assertGreaterEqual(m.blur_laplacian_variance, 0.0)
        self.assertGreaterEqual(m.terrain_texture_contrast, 0.0)

    def test_03_nonexistent_path_returns_none(self):
        metrics = self.extractor.extract_metrics("/nonexistent/path/image.jpg")
        self.assertIsNone(metrics)

    def test_04_brightness_differs_for_dark_vs_bright_image(self):
        dark_path = self._create_test_image("dark.jpg", color=(10, 10, 10))
        bright_path = self._create_test_image("bright.jpg", color=(230, 230, 230))
        if dark_path is None or bright_path is None:
            self.skipTest("cv2 not available")
        m_dark = self.extractor.extract_metrics(dark_path)
        m_bright = self.extractor.extract_metrics(bright_path)
        self.assertLess(m_dark.mean_brightness, m_bright.mean_brightness)


if __name__ == "__main__":
    unittest.main()
