import os
import unittest
import json
from cv_assurance.data.ingester import DatasetIngester
from cv_assurance.data.duplicates import DuplicateDetector
from cv_assurance.data.label_integrity import LabelIntegrityAnalyzer
from cv_assurance.data.ood_detector import OODDetector
from cv_assurance.data.backdoor_data import DataBackdoorDetector
from cv_assurance.data.contributor_risk import ContributorRiskAggregator
from cv_assurance.model.hasher import ModelHasher
from cv_assurance.model.fingerprint import ModelFingerprinter
from cv_assurance.model.whitebox_analyzer import WhiteBoxAnalyzer
from cv_assurance.shift.distribution_test import DistributionShiftDetector
from cv_assurance.provenance.crypto_binding import CryptographicProvenanceEngine, InferenceOutputPrediction
from cv_assurance.governance.engine import AssuranceEngine

class TestCVAssuranceFramework(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.eval_coco = os.path.join(cls.base_dir, "demo_assets", "eval_coco", "annotations.json")
        cls.ref_coco = os.path.join(cls.base_dir, "demo_assets", "reference_coco", "annotations.json")
        cls.model_pt = os.path.join(cls.base_dir, "demo_assets", "sample_model.pt")

    def test_01_ingester(self):
        ingester = DatasetIngester()
        ds = ingester.auto_ingest(self.eval_coco)
        self.assertGreater(len(ds.samples), 0)
        self.assertEqual(ds.format, "coco")

    def test_02_duplicate_detection(self):
        ingester = DatasetIngester()
        ds = ingester.auto_ingest(self.eval_coco)
        detector = DuplicateDetector()
        res = detector.analyze(ds)
        self.assertGreater(res.duplicate_pairs_count, 0)

    def test_03_label_integrity(self):
        ingester = DatasetIngester()
        ds = ingester.auto_ingest(self.eval_coco)
        analyzer = LabelIntegrityAnalyzer()
        res = analyzer.analyze(ds)
        self.assertGreater(res.suspicious_samples_count, 0)

    def test_04_ood_detection(self):
        ingester = DatasetIngester()
        ds = ingester.auto_ingest(self.eval_coco)
        detector = OODDetector()
        res = detector.analyze(ds)
        self.assertIsNotNone(res.ood_samples_count)

    def test_05_backdoor_trigger_detection(self):
        ingester = DatasetIngester()
        ds = ingester.auto_ingest(self.eval_coco)
        detector = DataBackdoorDetector()
        res = detector.analyze(ds)
        self.assertGreater(res.poisoned_samples_count, 0)

    def test_06_contributor_risk(self):
        ingester = DatasetIngester()
        ds = ingester.auto_ingest(self.eval_coco)
        dup_res = DuplicateDetector().analyze(ds)
        lbl_res = LabelIntegrityAnalyzer().analyze(ds)
        ood_res = OODDetector().analyze(ds)
        bd_res = DataBackdoorDetector().analyze(ds)

        agg = ContributorRiskAggregator()
        res = agg.aggregate(ds, dup_res, lbl_res, ood_res, bd_res)
        self.assertGreater(len(res.profiles), 0)
        # Verify contributor_poison is flagged as CRITICAL
        poison_profile = [p for p in res.profiles if p.contributor_id == "contributor_poison"]
        self.assertTrue(len(poison_profile) > 0)
        self.assertIn(poison_profile[0].risk_level, ["CRITICAL", "HIGH"])

    def test_07_model_hasher_and_whitebox(self):
        hasher = ModelHasher()
        res_hash = hasher.inspect_model(self.model_pt)
        self.assertIsNotNone(res_hash.sha256_digest)
        self.assertEqual(res_hash.format, "pytorch_pt")

        wb = WhiteBoxAnalyzer()
        res_wb = wb.analyze_weights(self.model_pt)
        self.assertTrue(res_wb.access_granted)
        self.assertGreater(res_wb.total_layers_analyzed, 0)

    def test_08_distribution_shift(self):
        ingester = DatasetIngester()
        ref_ds = ingester.auto_ingest(self.ref_coco)
        eval_ds = ingester.auto_ingest(self.eval_coco)

        shift = DistributionShiftDetector()
        res = shift.analyze(ref_ds, eval_ds)
        self.assertTrue(res.material_shift_detected)

    def test_09_inference_provenance(self):
        prov = CryptographicProvenanceEngine()
        model_hash = ModelHasher().compute_file_sha256(self.model_pt)
        preds = [
            InferenceOutputPrediction(box=[200, 200, 240, 280], confidence=0.94, category_id=0, category_name="vehicle_tank")
        ]

        record = prov.create_protected_record(
            image_path_or_hash=self.model_pt,
            model_hash=model_hash,
            config_dict={"resolution": [640, 640]},
            predictions=preds
        )

        v_res = prov.verify_record(record)
        self.assertTrue(v_res.verification_passed)
        self.assertFalse(v_res.tamper_detected)

        # Test tamper detection
        record.predictions[0].confidence = 0.12
        v_res_tampered = prov.verify_record(record)
        self.assertFalse(v_res_tampered.verification_passed)
        self.assertTrue(v_res_tampered.tamper_detected)

    def test_10_full_assurance_engine(self):
        engine = AssuranceEngine()
        report = engine.run_full_assurance(
            dataset_path=self.eval_coco,
            model_path=self.model_pt,
            ref_dataset_path=self.ref_coco
        )

        self.assertIsNotNone(report.report_id)
        self.assertGreater(len(report.findings), 0)
        self.assertIn(report.overall_disposition.value, ["QUARANTINE", "REVIEW", "ACCEPT"])

if __name__ == "__main__":
    unittest.main()
