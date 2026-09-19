import os
import shutil
import unittest
import numpy as np
import cv2
from pathlib import Path

from cv_assurance.data.ingester import BoundingBox, IngestedSample, IngestedDataset
from cv_assurance.data.visdrone import VISDRONE_CATEGORIES, VisDroneBenchmarkSynthesizer
from cv_assurance.calibration.engine import CalibratedThresholdSet, DuplicateThresholdConfig
from cv_assurance.data.duplicates import DuplicateDetector
from cv_assurance.data.label_integrity import LabelIntegrityAnalyzer
from cv_assurance.data.backdoor_data import DataBackdoorDetector
from cv_assurance.data.ood_detector import OODDetector
from cv_assurance.data.contributor_risk import ContributorRiskAggregator
from cv_assurance.attacks.duplicate_attacks import NearDuplicateFloodingAttack
from cv_assurance.attacks.trigger_attacks import CornerTriggerAttack, BlendedTriggerAttack, SpectralTriggerAttack
from scripts.validate_benchmark import validate_benchmark_suite

class TestCalibrationAndDetectorRemediation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(__file__).parent / "tmp_calib_test"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate two distinct clean aerial images
        cls.img1, cls.boxes1 = VisDroneBenchmarkSynthesizer.generate_aerial_sample(1, seed=101)
        cls.img2, cls.boxes2 = VisDroneBenchmarkSynthesizer.generate_aerial_sample(2, seed=102)

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_calibration_engine_save_load(self):
        calib = CalibratedThresholdSet()
        calib.duplicate.ssim_confirmation_threshold = 0.85
        calib.calibration_sample_count = 50
        
        out_dir = self.test_dir / "calib_test_cfg"
        calib.save(str(out_dir))
        
        loaded = CalibratedThresholdSet.load(str(out_dir))
        self.assertEqual(loaded.duplicate.ssim_confirmation_threshold, 0.85)
        self.assertEqual(loaded.calibration_sample_count, 50)

    def test_02_duplicate_detector_ssim_confirmation(self):
        detector = DuplicateDetector()
        
        # 1. Distinct images should have lower SSIM
        ssim_distinct = detector.compute_ssim(self.img1, self.img2)
        self.assertLess(ssim_distinct, 0.75)

        # 2. Transformed near-duplicate should have high SSIM
        atk = NearDuplicateFloodingAttack(transformation="jpeg_compression", seed=42)
        res = atk.apply(self.img1, self.boxes1)
        ssim_duplicate = detector.compute_ssim(self.img1, res.modified_image)
        self.assertGreaterEqual(ssim_duplicate, 0.80)

    def test_03_label_integrity_multi_evidence(self):
        analyzer = LabelIntegrityAnalyzer()
        feat = analyzer.extract_roi_and_context_features(str(self.test_dir / "dummy.jpg"), self.boxes1)
        # Should return None gracefully for missing path
        self.assertIsNone(feat)

    def test_04_corner_trigger_detection(self):
        detector = DataBackdoorDetector()
        atk = CornerTriggerAttack(trigger_size=20, position="top_right", opacity=0.95, seed=42)
        res = atk.apply(self.img1, self.boxes1)

        result = detector.detect_corner_patch(res.modified_image)
        self.assertIsNotNone(result)
        conf, bbox, details = result
        self.assertGreaterEqual(conf, 0.65)
        self.assertEqual(len(bbox), 4)

    def test_05_blended_trigger_detection(self):
        detector = DataBackdoorDetector()
        atk = BlendedTriggerAttack(alpha=0.20, pattern_type="watermark_cross", seed=42)
        res = atk.apply(self.img1, self.boxes1)

        score, is_blended = detector.detect_blended_watermark(res.modified_image)
        self.assertTrue(is_blended)
        self.assertGreater(score, 0.5)

    def test_06_spectral_trigger_detection(self):
        detector = DataBackdoorDetector()
        atk = SpectralTriggerAttack(frequency_strength=16.0, seed=42)
        res = atk.apply(self.img1, self.boxes1)

        hf_r, peak_z, is_spike = detector.detect_fft_spectral_anomaly(res.modified_image)
        self.assertGreaterEqual(peak_z, 3.5)

    def test_07_contributor_risk_clean_retention(self):
        # Create dataset where Contributor A has only clean samples
        clean_samples = [
            IngestedSample(
                sample_id=f"c_{i}",
                image_path="dummy.jpg",
                file_name=f"c_{i}.jpg",
                width=640,
                height=640,
                boxes=[BoundingBox(x=10, y=10, width=50, height=50, category_id=4, category_name="car")],
                contributor_id="contributor_A"
            )
            for i in range(10)
        ]
        ds = IngestedDataset(
            name="TestClean",
            format="manifest",
            root_dir=".",
            categories={4: "car"},
            samples=clean_samples,
            total_samples=10,
            total_annotations=10
        )

        from cv_assurance.data.duplicates import DuplicateAnalysisResult
        from cv_assurance.data.label_integrity import LabelIntegrityResult
        from cv_assurance.data.ood_detector import OODAnalysisResult
        from cv_assurance.data.backdoor_data import DataBackdoorResult

        dup_res = DuplicateAnalysisResult(total_samples=10, duplicate_pairs_count=0, duplicate_samples_count=0, flooding_risk_score=0.0)
        lbl_res = LabelIntegrityResult(total_samples=10, suspicious_samples_count=0, mislabelling_rate=0.0, systematic_pattern_detected=False)
        ood_res = OODAnalysisResult(total_samples=10, ood_samples_count=0, ood_ratio=0.0, contamination_level=0.05, ood_samples=[])
        bd_res = DataBackdoorResult(total_samples=10, poisoned_samples_count=0, poisoning_rate=0.0)

        agg = ContributorRiskAggregator()
        res = agg.aggregate(ds, dup_res, lbl_res, ood_res, bd_res)

        self.assertEqual(len(res.profiles), 1)
        profile_a = res.profiles[0]
        self.assertEqual(profile_a.risk_level, "CLEAN")
        self.assertIn("ACCEPT", profile_a.recommended_action)

if __name__ == "__main__":
    unittest.main()
