"""
Module 3B Demonstration: Distribution Shift, Governance, Tamper-Evident Audit Trail,
and End-to-End Integrity Assurance Pipeline.

SIH Problem Statement 26228:
"Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs
 in Multi-Contributor Pipelines."
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.shift.distribution_test import (
    DistributionShiftDetector,
    DistributionShiftResult
)
from cv_assurance.shift.environmental import (
    EnvironmentalFeatureExtractor,
    EnvironmentalShiftMetrics
)
from cv_assurance.governance.audit_chain import (
    TamperEvidentAuditChain,
    AuditEvent,
    GENESIS_PREVIOUS_HASH
)
from cv_assurance.governance.report_schema import (
    AssuranceReport,
    AssuranceFinding,
    SeverityLevel,
    RecommendedDisposition,
    AuditChainSummary
)
from cv_assurance.governance.engine import AssuranceEngine


def _make_metric_sample(
    terrain=15.0,
    brightness=120.0,
    sensor_noise=2.0,
    vegetation=5.0
):
    return EnvironmentalShiftMetrics(
        terrain_texture_contrast=terrain,
        terrain_color_hist_energy=0.02,
        mean_brightness=brightness,
        contrast_std=40.0,
        hsv_value_mean=brightness,
        low_light_ratio=0.01,
        overexposure_ratio=0.01,
        noise_floor_std=sensor_noise,
        blur_laplacian_variance=600.0,
        psnr_estimate=45.0,
        hue_mean=55.0,
        saturation_mean=80.0,
        green_vegetation_index=vegetation
    )


class _MockDataset:
    class _Sample:
        def __init__(self, p):
            self.image_path = p
    def __init__(self, paths, name="SyntheticDataset"):
        self.samples = [self._Sample(p) for p in paths]
        self.name = name
    def __getitem__(self, item):
        return self.samples[item]
    def __len__(self):
        return len(self.samples)


def demo_distribution_shift():
    print("\n" + "=" * 76)
    print("  PART 1: DISTRIBUTION SHIFT DETECTION ACROSS 4 ENVIRONMENTAL DOMAINS")
    print("=" * 76)

    detector = DistributionShiftDetector()

    # Case A: NO_SHIFT (Aligned reference vs target)
    ref_clean = [_make_metric_sample(terrain=15.0 + (i % 3), brightness=120.0 + (i % 5), sensor_noise=2.0, vegetation=5.0) for i in range(25)]
    tgt_clean = [_make_metric_sample(terrain=15.0 + (i % 3), brightness=120.0 + (i % 5), sensor_noise=2.0, vegetation=5.0) for i in range(25)]

    ref_iter = iter(ref_clean)
    tgt_iter = iter(tgt_clean)
    def _mock_clean(path):
        try:
            return next(ref_iter) if "ref" in path else next(tgt_iter)
        except StopIteration:
            return None

    with patch.object(detector.extractor, "extract_metrics", side_effect=_mock_clean):
        res_noshift = detector.analyze(
            _MockDataset([f"ref_{i}.jpg" for i in range(25)]),
            _MockDataset([f"tgt_{i}.jpg" for i in range(25)])
        )

    print("\n[Scenario A: Reference vs Aligned Evaluation Dataset]")
    print(f"  Classification:        {res_noshift.shift_classification}")
    print(f"  Material Shift:        {res_noshift.material_shift_detected}")
    print(f"  Overall Drift Score:   {res_noshift.overall_drift_score}")
    print(f"  Summary:               {res_noshift.summary_findings}")

    # Case B: OPERATIONAL_DRIFT (Natural multi-domain transition: night terrain + winter vegetation)
    ref_op = [_make_metric_sample(terrain=15.0, brightness=125.0, sensor_noise=2.1, vegetation=12.0) for _ in range(25)]
    tgt_op = [_make_metric_sample(terrain=38.0, brightness=28.0, sensor_noise=2.3, vegetation=-25.0) for _ in range(25)]

    ref_it2 = iter(ref_op)
    tgt_it2 = iter(tgt_op)
    def _mock_op(path):
        try:
            return next(ref_it2) if "ref" in path else next(tgt_it2)
        except StopIteration:
            return None

    with patch.object(detector.extractor, "extract_metrics", side_effect=_mock_op):
        res_op = detector.analyze(
            _MockDataset([f"ref_{i}.jpg" for i in range(25)]),
            _MockDataset([f"tgt_{i}.jpg" for i in range(25)])
        )

    print("\n[Scenario B: Natural Operational Drift (Low Illumination + Winter Flora)]")
    print(f"  Classification:        {res_op.shift_classification}")
    print(f"  Material Shift:        {res_op.material_shift_detected}")
    print(f"  Overall Drift Score:   {res_op.overall_drift_score}")
    print(f"  Summary:               {res_op.summary_findings}")
    print("  Dimension Breakdown:")
    for d in res_op.dimensions:
        flag = "[SHIFT]" if d.shift_detected else "[OK]   "
        print(f"    * {d.dimension_name:<14} {flag} | KS: {d.ks_statistic:<6} | p-val: {d.p_value:<7} | Wasserstein: {d.wasserstein_dist}")

    # Case C: SUSPICIOUS_MANIPULATION (Isolated abrupt sensor noise floor anomaly)
    ref_adv = [_make_metric_sample(terrain=15.0, brightness=120.0, sensor_noise=2.0, vegetation=5.0) for _ in range(25)]
    tgt_adv = [_make_metric_sample(terrain=15.0, brightness=120.0, sensor_noise=45.0, vegetation=5.0) for _ in range(25)]

    ref_it3 = iter(ref_adv)
    tgt_it3 = iter(tgt_adv)
    def _mock_adv(path):
        try:
            return next(ref_it3) if "ref" in path else next(tgt_it3)
        except StopIteration:
            return None

    with patch.object(detector.extractor, "extract_metrics", side_effect=_mock_adv):
        res_adv = detector.analyze(
            _MockDataset([f"ref_{i}.jpg" for i in range(25)]),
            _MockDataset([f"tgt_{i}.jpg" for i in range(25)])
        )

    print("\n[Scenario C: Synthetic Sensor Injection / Adversarial Noise]")
    print(f"  Classification:        {res_adv.shift_classification}")
    print(f"  Material Shift:        {res_adv.material_shift_detected}")
    print(f"  Overall Drift Score:   {res_adv.overall_drift_score}")
    print(f"  Summary:               {res_adv.summary_findings}")


def demo_audit_chain():
    print("\n" + "=" * 76)
    print("  PART 2: TAMPER-EVIDENT CRYPTOGRAPHIC AUDIT LOG CHAIN")
    print("=" * 76)

    with tempfile.TemporaryDirectory() as td:
        chain_file = os.path.join(td, "audit_chain.json")
        chain = TamperEvidentAuditChain(chain_file=chain_file)

        # 1. Append pipeline lifecycle events
        e1 = chain.append_event(
            event_type="PIPELINE_INIT",
            affected_asset="pipeline_session",
            event_summary="Initialized assurance pipeline execution",
            event_data={"session_id": "SES-9842"}
        )
        e2 = chain.append_event(
            event_type="DATASET_AUDIT",
            affected_asset="evaluation_dataset",
            event_summary="Completed training-data integrity audit across contributors",
            event_data={"samples_count": 60, "flagged_contributors": 1}
        )
        e3 = chain.append_event(
            event_type="SHIFT_AUDIT",
            affected_asset="environmental_domain",
            event_summary="Distribution shift verified: OPERATIONAL_DRIFT",
            event_data={"drift_score": 0.5, "classification": "OPERATIONAL_DRIFT"}
        )
        e4 = chain.append_event(
            event_type="GOVERNANCE_DISPOSITION",
            affected_asset="governance_report",
            event_summary="Final pipeline governance disposition rendered: REVIEW",
            event_data={"health_score": 82.5, "disposition": "REVIEW"}
        )

        print(f"[*] Appended {chain.chain_length} sequential audit events.")
        for evt in chain.events:
            print(f"  [Event #{evt.sequence_index}] {evt.event_type:<24} | Hash: {evt.current_event_hash[:16]}... | Prev: {evt.previous_event_hash[:16]}...")

        # 2. Independent Verification
        is_valid, msg, broken_idx = chain.verify_chain()
        print(f"\n[+] Baseline Chain Integrity Verification:")
        print(f"    Status:            {'[PASS] VERIFIED_UNBROKEN' if is_valid else '[FAIL]'}")
        print(f"    Chain Head Digest: {chain.latest_hash}")
        print(f"    Message:           {msg}")

        # 3. Tamper Detection Demonstration
        print(f"\n[*] Simulating unauthorized alteration to Event #2 payload...")
        with open(chain_file, "r", encoding="utf-8") as f:
            raw_chain = json.load(f)

        # Adversary attempts to clear flagged contributors
        raw_chain[1]["event_data"]["flagged_contributors"] = 0
        with open(chain_file, "w", encoding="utf-8") as f:
            json.dump(raw_chain, f, indent=2)

        tampered_chain = TamperEvidentAuditChain(chain_file=chain_file)
        t_valid, t_msg, t_idx = tampered_chain.verify_chain()
        print(f"[!] Re-verifying tampered chain:")
        print(f"    Tamper Detected:   {not t_valid}")
        print(f"    Broken Event Index: #{t_idx}")
        print(f"    Evidence Reason:   {t_msg}")


def demo_governance_engine():
    print("\n" + "=" * 76)
    print("  PART 3: COMPLETE END-TO-END GOVERNANCE ASSURANCE REPORT")
    print("=" * 76)

    with tempfile.TemporaryDirectory() as td:
        chain_path = os.path.join(td, "governance_audit_chain.json")
        engine = AssuranceEngine()

        # Mock clean components to generate clean baseline report
        fake_ds = MagicMock()
        fake_ds.name = "DefenseMultiContributor_Coco"
        fake_ds.samples = [MagicMock() for _ in range(50)]

        dup_mock = MagicMock(duplicate_pairs_count=0, duplicate_samples_count=0, flooding_risk_score=0.0, duplicate_pairs=[])
        lbl_mock = MagicMock(suspicious_samples_count=0, mislabelling_rate=0.0, systematic_pattern_detected=False, flagged_samples=[])
        ood_mock = MagicMock(ood_samples_count=0, ood_ratio=0.0, ood_samples=[])
        bd_mock = MagicMock(poisoned_samples_count=0, poisoning_rate=0.0, detected_triggers=[])
        cr_mock = MagicMock(profiles=[])

        engine.ingester.auto_ingest = MagicMock(return_value=fake_ds)
        engine.duplicate_detector.analyze = MagicMock(return_value=dup_mock)
        engine.label_analyzer.analyze = MagicMock(return_value=lbl_mock)
        engine.ood_detector.analyze = MagicMock(return_value=ood_mock)
        engine.backdoor_detector.analyze = MagicMock(return_value=bd_mock)
        engine.risk_aggregator.aggregate = MagicMock(return_value=cr_mock)

        report = engine.run_full_assurance(
            dataset_path=os.path.join(td, "dataset.json"),
            audit_chain_file=chain_path
        )

        print(f"[*] Governance Engine Report Generated:")
        print(f"  Report ID:           {report.report_id}")
        print(f"  Generated At:        {report.generated_at_utc}")
        print(f"  Overall Health Score:{report.overall_health_score} / 100.0")
        print(f"  Overall Disposition: {report.overall_disposition.value}")
        print(f"  Audit Trail Hash:    {report.audit_trail_hash}")
        print(f"  Findings Summary:    Total: {report.summary_counts.get('total_findings', 0)}")
        print(f"  Audit Chain Summary: Length: {report.audit_chain.chain_length} | Status: {report.audit_chain.verification_status}")
        print("=" * 76)


if __name__ == "__main__":
    demo_distribution_shift()
    demo_audit_chain()
    demo_governance_engine()
