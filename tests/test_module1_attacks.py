import os
import json
import shutil
import unittest
import numpy as np
import cv2
from pathlib import Path

from cv_assurance.data.ingester import BoundingBox, IngestedSample, IngestedDataset, DatasetIngester
from cv_assurance.data.visdrone import VISDRONE_CATEGORIES, VisDroneIngester, VisDroneBenchmarkSynthesizer
from cv_assurance.attacks.manifest import AttackSampleRecord, GroundTruthManifest, ManifestValidator
from cv_assurance.attacks.label_attacks import LabelFlippingAttack, SystematicMislabellingAttack
from cv_assurance.attacks.duplicate_attacks import NearDuplicateFloodingAttack
from cv_assurance.attacks.ood_attacks import OODInsertionAttack
from cv_assurance.attacks.trigger_attacks import CornerTriggerAttack, BlendedTriggerAttack, SpectralTriggerAttack
from cv_assurance.attacks.distribution_shift import DistributionShiftGenerator
from cv_assurance.attacks.pipeline import MultiContributorPipeline
from scripts.evaluate_attacks import run_evaluation

class TestModule1AttacksAndBenchmark(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(__file__).parent / "tmp_test_benchmark"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a sample synthetic aerial image and bounding boxes
        cls.sample_img, cls.sample_boxes = VisDroneBenchmarkSynthesizer.generate_aerial_sample(1, width=320, height=320, seed=42)

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_label_flipping_attack(self):
        atk = LabelFlippingAttack(categories=VISDRONE_CATEGORIES, seed=42)
        res = atk.apply(self.sample_img, self.sample_boxes)
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "label_flip")
        self.assertIsNotNone(res.original_label)
        self.assertIsNotNone(res.modified_label)
        self.assertNotEqual(res.original_label_id, res.modified_label_id)
        self.assertIn(res.modified_label_id, VISDRONE_CATEGORIES)

    def test_02_systematic_mislabelling_attack(self):
        atk = SystematicMislabellingAttack(categories=VISDRONE_CATEGORIES, seed=42)
        # Create box with car (id=4)
        car_box = [BoundingBox(x=50, y=50, width=40, height=40, category_id=4, category_name="car")]
        res = atk.apply(self.sample_img, car_box)
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "systematic_mislabel")
        self.assertEqual(res.original_label_id, 4)
        self.assertEqual(res.modified_label_id, 5) # Car -> Van
        self.assertEqual(res.modified_label, "van")

    def test_03_near_duplicate_flooding_attack(self):
        atk = NearDuplicateFloodingAttack(transformation="jpeg_compression", seed=42)
        res = atk.apply(self.sample_img, self.sample_boxes, original_sample_id="ref_001")
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "near_duplicate_flood")
        self.assertEqual(res.parameters["transformation"], "jpeg_compression")
        self.assertIn("jpeg_quality", res.parameters)
        self.assertEqual(res.modified_image.shape, self.sample_img.shape)

    def test_04_ood_insertion_attack(self):
        atk = OODInsertionAttack(seed=42)
        res = atk.apply(self.sample_img, self.sample_boxes)
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "ood_insertion")
        self.assertEqual(res.modified_label_id, -1)
        self.assertIn("ood_domain", res.parameters)
        self.assertEqual(res.modified_image.shape, self.sample_img.shape)

    def test_05_corner_trigger_attack(self):
        atk = CornerTriggerAttack(trigger_size=16, position="top_right", opacity=0.9, seed=42)
        res = atk.apply(self.sample_img, self.sample_boxes)
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "corner_trigger")
        self.assertEqual(res.parameters["position"], "top_right")
        self.assertEqual(len(res.parameters["bbox"]), 4)

    def test_06_blended_trigger_attack(self):
        atk = BlendedTriggerAttack(alpha=0.15, pattern_type="watermark_cross", seed=42)
        res = atk.apply(self.sample_img, self.sample_boxes)
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "blended_trigger")
        self.assertEqual(res.parameters["alpha"], 0.15)
        self.assertEqual(res.modified_image.shape, self.sample_img.shape)

    def test_07_spectral_trigger_attack(self):
        atk = SpectralTriggerAttack(frequency_strength=12.0, seed=42)
        res = atk.apply(self.sample_img, self.sample_boxes)
        
        self.assertTrue(res.is_attacked)
        self.assertEqual(res.attack_type, "spectral_trigger")
        self.assertIn("frequency_carrier", res.parameters)
        self.assertEqual(res.modified_image.shape, self.sample_img.shape)

    def test_08_distribution_shift_generator(self):
        gen = DistributionShiftGenerator(shift_type="illumination", severity=1.0, seed=42)
        res = gen.apply(self.sample_img, self.sample_boxes)
        
        self.assertFalse(res.is_attacked) # Operational drift, not attack
        self.assertEqual(res.parameters["shift_type"], "illumination")

    def test_09_reproducibility(self):
        atk1 = NearDuplicateFloodingAttack(transformation="brightness_contrast", seed=1234)
        res1 = atk1.apply(self.sample_img, self.sample_boxes)

        atk2 = NearDuplicateFloodingAttack(transformation="brightness_contrast", seed=1234)
        res2 = atk2.apply(self.sample_img, self.sample_boxes)

        self.assertEqual(res1.parameters, res2.parameters)
        np.testing.assert_array_equal(res1.modified_image, res2.modified_image)

    def test_10_manifest_validation(self):
        manifest = GroundTruthManifest(
            dataset_name="Test_Manifest",
            seed=42,
            samples=[
                AttackSampleRecord(
                    sample_id="s1",
                    original_image="reference/images/ref_01.jpg",
                    current_image="reference/images/ref_01.jpg",
                    contributor="contributor_A",
                    attack_type="clean",
                    is_attacked=False
                ),
                AttackSampleRecord(
                    sample_id="s2",
                    original_image="reference/images/ref_02.jpg",
                    current_image="attacks/corner_trigger/s2.jpg",
                    contributor="contributor_D",
                    attack_type="corner_trigger",
                    is_attacked=True,
                    parameters={"trigger_type": "corner_patch", "bbox": [10, 10, 16, 16]}
                )
            ]
        )

        is_valid, errors = ManifestValidator.validate(manifest)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalidate manifest
        bad_manifest = GroundTruthManifest(
            dataset_name="Bad_Manifest",
            seed=42,
            samples=[
                AttackSampleRecord(
                    sample_id="s1",
                    original_image="",
                    current_image="attacks/corner_trigger/s1.jpg",
                    contributor="contributor_D",
                    attack_type="invalid_attack_name",
                    is_attacked=True
                )
            ]
        )
        bad_valid, bad_errors = ManifestValidator.validate(bad_manifest)
        self.assertFalse(bad_valid)
        self.assertGreater(len(bad_errors), 0)

    def test_11_end_to_end_pipeline_and_evaluation(self):
        pipeline_dir = self.test_dir / "pipeline_run"
        
        # 1. Synthesize reference set
        paths = VisDroneBenchmarkSynthesizer.generate_synthetic_visdrone_dataset(
            output_dir=str(pipeline_dir / "raw_visdrone"),
            num_train=16,
            num_val=4,
            seed=42
        )
        ref_ds = VisDroneIngester.ingest_visdrone(paths["train_root"], seed=42)

        # 2. Build multi-contributor benchmark
        pipeline = MultiContributorPipeline(output_dir=str(pipeline_dir / "benchmark"), seed=42)
        manifest = pipeline.build_benchmark(ref_ds)

        self.assertGreater(manifest.total_samples, 0)
        self.assertTrue((pipeline_dir / "benchmark" / "ground_truth" / "attack_manifest.json").exists())
        self.assertTrue((pipeline_dir / "benchmark" / "dataset_manifest.json").exists())

        # 3. Evaluate detector metrics
        report = run_evaluation(
            dataset_path=str(pipeline_dir / "benchmark" / "dataset_manifest.json"),
            ground_truth_manifest_path=str(pipeline_dir / "benchmark" / "ground_truth" / "attack_manifest.json"),
            ref_dataset_path=str(pipeline_dir / "benchmark" / "reference" / "manifest.json"),
            output_metrics_json=str(pipeline_dir / "metrics.json")
        )

        self.assertIn("metrics", report)
        self.assertIn("contributors", report)
        self.assertTrue(os.path.exists(pipeline_dir / "metrics.json"))

if __name__ == "__main__":
    unittest.main()
