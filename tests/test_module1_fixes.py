import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from cv_assurance.data.ingester import DatasetIngester, IngestedDataset, IngestedSample
from cv_assurance.data.duplicates import DuplicateDetector
from cv_assurance.data.ood_detector import OODDetector
from scripts.evaluate_attacks import compute_detailed_binary_metrics


class TestModule1IngestionAndEvaluationFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "images").mkdir()
        (self.root / "labels").mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_image(self, name, width, height, value=120):
        image = np.full((height, width, 3), value, dtype=np.uint8)
        path = self.root / "images" / name
        self.assertTrue(cv2.imwrite(str(path), image))
        return path

    def test_yolo_normalized_boxes_use_actual_dimensions_and_multiple_objects(self):
        self._write_image("scene.jpg", 200, 100)
        (self.root / "labels" / "scene.txt").write_text(
            "1 0.5 0.5 0.5 0.4\n2 0.25 0.5 0.2 0.2\n",
            encoding="utf-8",
        )

        dataset = DatasetIngester.ingest_yolo(str(self.root))

        self.assertEqual(len(dataset.samples), 1)
        sample = dataset.samples[0]
        self.assertEqual((sample.width, sample.height), (200, 100))
        self.assertEqual(len(sample.boxes), 2)
        first, second = sample.boxes
        self.assertAlmostEqual(first.x, 50.0)
        self.assertAlmostEqual(first.y, 30.0)
        self.assertAlmostEqual(first.width, 100.0)
        self.assertAlmostEqual(first.height, 40.0)
        self.assertAlmostEqual(second.x, 30.0)
        self.assertAlmostEqual(second.y, 40.0)
        self.assertAlmostEqual(second.width, 40.0)
        self.assertAlmostEqual(second.height, 20.0)

    def test_yolo_malformed_labels_are_skipped_and_missing_images_are_not_invented(self):
        self._write_image("valid.png", 80, 40)
        (self.root / "labels" / "valid.txt").write_text(
            "bad label\n0 not-a-number 0.5 0.2 0.2\n0 0.5 0.5 0.2 0.2\n",
            encoding="utf-8",
        )
        (self.root / "labels" / "missing.txt").write_text(
            "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
        )

        dataset = DatasetIngester.ingest_yolo(str(self.root))

        self.assertEqual(len(dataset.samples), 1)
        self.assertEqual(len(dataset.samples[0].boxes), 1)

    def test_yolo_missing_metadata_is_explicitly_unavailable(self):
        self._write_image("scene.jpg", 20, 10)
        (self.root / "labels" / "scene.txt").write_text(
            "0 0.5 0.5 0.5 0.5\n", encoding="utf-8"
        )

        sample = DatasetIngester.ingest_yolo(str(self.root)).samples[0]

        self.assertIsNone(sample.contributor_id)
        self.assertIsNone(sample.batch_id)
        self.assertIsNone(sample.source_id)

    def test_yolo_metadata_is_preserved_without_index_inference(self):
        self._write_image("scene.jpg", 20, 10)
        (self.root / "labels" / "scene.txt").write_text(
            "0 0.5 0.5 0.5 0.5\n", encoding="utf-8"
        )
        (self.root / "metadata.json").write_text(json.dumps({
            "images": {
                "scene.jpg": {
                    "contributor_id": "contributor-real",
                    "batch_id": "batch-7",
                    "source_id": "camera-2",
                }
            }
        }), encoding="utf-8")

        sample = DatasetIngester.ingest_yolo(str(self.root)).samples[0]

        self.assertEqual(sample.contributor_id, "contributor-real")
        self.assertEqual(sample.batch_id, "batch-7")
        self.assertEqual(sample.source_id, "camera-2")

    def test_ood_reports_reference_vs_target_or_relative_mode(self):
        def features(path):
            return np.array([float(path), 0.0])

        target = type("Dataset", (), {"samples": [type("S", (), {"image_path": str(i), "sample_id": str(i), "file_name": str(i), "contributor_id": None, "batch_id": None})() for i in range(5)]})()
        reference = type("Dataset", (), {"samples": [type("S", (), {"image_path": str(i), "sample_id": "r" + str(i), "file_name": str(i), "contributor_id": None, "batch_id": None})() for i in range(5)]})()
        detector = OODDetector()

        with patch.object(detector, "extract_features", side_effect=features):
            relative = detector.analyze(target)
            compared = detector.analyze(target, reference_dataset=reference)

        self.assertEqual(relative.analysis_mode, "relative_dataset_anomaly")
        self.assertFalse(relative.trusted_reference_used)
        self.assertEqual(compared.analysis_mode, "reference_vs_target")
        self.assertTrue(compared.trusted_reference_used)
        self.assertEqual(compared.reference_sample_count, 5)

    def test_metrics_include_false_negative_and_detection_rate(self):
        metrics = compute_detailed_binary_metrics({"a", "b"}, {"a", "c"}, {"a", "b", "c", "d"})

        self.assertEqual(metrics["TP"], 1)
        self.assertEqual(metrics["FP"], 1)
        self.assertEqual(metrics["FN"], 1)
        self.assertEqual(metrics["TN"], 1)
        self.assertEqual(metrics["false_negative_rate"], 0.5)
        self.assertEqual(metrics["detection_rate"], 0.5)

    def test_duplicate_evidence_keeps_same_and_cross_contributor_cases_distinct(self):
        base = np.zeros((80, 80, 3), dtype=np.uint8)
        cv2.rectangle(base, (10, 10), (60, 60), (220, 120, 40), -1)
        paths = []
        for name, image in (("a.jpg", base), ("b.jpg", base.copy()), ("c.jpg", base.copy())):
            path = self.root / "images" / name
            self.assertTrue(cv2.imwrite(str(path), image))
            paths.append(path)
        samples = [
            IngestedSample(sample_id="a", image_path=str(paths[0]), file_name="a.jpg", width=80, height=80, contributor_id="A"),
            IngestedSample(sample_id="b", image_path=str(paths[1]), file_name="b.jpg", width=80, height=80, contributor_id="A"),
            IngestedSample(sample_id="c", image_path=str(paths[2]), file_name="c.jpg", width=80, height=80, contributor_id="B"),
        ]
        dataset = IngestedDataset(name="duplicates", format="test", root_dir=str(self.root), categories={}, samples=samples, total_samples=3, total_annotations=0)

        result = DuplicateDetector().analyze(dataset)

        self.assertGreaterEqual(result.duplicate_pairs_count, 3)
        self.assertGreaterEqual(result.cross_contributor_pairs_count, 2)
        contributor_a = next(item for item in result.contributor_flooding_stats if item.contributor_id == "A")
        self.assertTrue(contributor_a.is_flooding_suspected)


if __name__ == "__main__":
    unittest.main()
