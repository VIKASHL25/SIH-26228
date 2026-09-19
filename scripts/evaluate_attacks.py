import os
import sys
import json
import argparse
import datetime
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.data.ingester import DatasetIngester, IngestedDataset
from cv_assurance.data.duplicates import DuplicateDetector
from cv_assurance.data.label_integrity import LabelIntegrityAnalyzer
from cv_assurance.data.ood_detector import OODDetector
from cv_assurance.data.backdoor_data import DataBackdoorDetector
from cv_assurance.data.contributor_risk import ContributorRiskAggregator
from cv_assurance.shift.distribution_test import DistributionShiftDetector
from cv_assurance.attacks.manifest import GroundTruthManifest
from cv_assurance.calibration.engine import CalibratedThresholdSet

def compute_detailed_binary_metrics(
    actual_positive: Set[str],
    predicted_positive: Set[str],
    all_samples: Set[str]
) -> Dict[str, Any]:
    tp = len(actual_positive & predicted_positive)
    fp = len(predicted_positive - actual_positive)
    fn = len(actual_positive - predicted_positive)
    tn = len((all_samples - actual_positive) - predicted_positive)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 1.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / len(all_samples) if len(all_samples) > 0 else 0.0

    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "specificity": round(float(specificity), 4),
        "false_positive_rate": round(float(fpr), 4),
        "accuracy": round(float(accuracy), 4)
    }

def run_evaluation(
    dataset_path: str = "data/dataset_manifest.json",
    ground_truth_manifest_path: str = "data/ground_truth/attack_manifest.json",
    ref_dataset_path: str = "data/reference/manifest.json",
    calibration_config_dir: str = "calibration",
    output_metrics_json: str = None
) -> Dict[str, Any]:
    print("=" * 78)
    print("        RIGOROUS TRAINING-DATA INTEGRITY ASSURANCE EVALUATION (MODULE 1)")
    print("=" * 78)
    print(f"[*] Evaluation Dataset:      {dataset_path}")
    print(f"[*] Ground Truth Manifest:   {ground_truth_manifest_path}")
    if ref_dataset_path and os.path.exists(ref_dataset_path):
        print(f"[*] Clean Reference Dataset: {ref_dataset_path}")

    # Load frozen calibrated thresholds if present
    calib_set = CalibratedThresholdSet.load(calibration_config_dir)
    print(f"[*] Calibration Config:      {calibration_config_dir}/ (Frozen on {calib_set.calibration_sample_count} calibration samples)")

    # 1. Ingest evaluation dataset & ground truth
    dataset = DatasetIngester.auto_ingest(dataset_path)
    gt_manifest = GroundTruthManifest.load(ground_truth_manifest_path)

    all_sample_ids = {s.sample_id for s in gt_manifest.samples}

    # Ground truth sets
    gt_duplicates = {s.sample_id for s in gt_manifest.samples if s.attack_type == "near_duplicate_flood"}
    gt_label_flips = {s.sample_id for s in gt_manifest.samples if s.attack_type in ("label_flip", "systematic_mislabel")}
    gt_ood = {s.sample_id for s in gt_manifest.samples if s.attack_type == "ood_insertion"}
    
    # Specific trigger family ground truth sets
    gt_corner_triggers = {s.sample_id for s in gt_manifest.samples if s.attack_type == "corner_trigger"}
    gt_blended_triggers = {s.sample_id for s in gt_manifest.samples if s.attack_type == "blended_trigger"}
    gt_spectral_triggers = {s.sample_id for s in gt_manifest.samples if s.attack_type == "spectral_trigger"}
    gt_all_triggers = gt_corner_triggers | gt_blended_triggers | gt_spectral_triggers

    # 2. Execute Assurance Detectors using Calibrated Thresholds
    print("\n[*] Executing Calibrated Assurance Detectors...")

    # Detector 1: Duplicate Detector (Tier 1 SHA + Tier 2 pHash + Tier 3 SSIM Confirmation)
    dup_detector = DuplicateDetector()
    dup_res = dup_detector.analyze(
        dataset,
        hash_candidate_threshold=calib_set.duplicate.hash_candidate_threshold,
        ssim_confirmation_threshold=calib_set.duplicate.ssim_confirmation_threshold,
        normalized_mae_threshold=calib_set.duplicate.normalized_mae_threshold
    )
    pred_duplicates = set()
    for pair in dup_res.duplicate_pairs:
        if pair.is_confirmed:
            # Near-duplicate FLOODING is a same-contributor attack (one contributor
            # submitting many copies). Cross-contributor similarity (e.g. distribution
            # shift variants vs originals) is a separate concern, not flooding.
            if pair.contributor_a == pair.contributor_b:
                pred_duplicates.add(pair.sample_id_a)
                pred_duplicates.add(pair.sample_id_b)

    # Detector 2: Multi-Evidence Label Integrity Analyzer
    label_analyzer = LabelIntegrityAnalyzer()
    label_res = label_analyzer.analyze(
        dataset,
        k_neighbors=calib_set.label.knn_neighbors,
        min_consensus_threshold=calib_set.label.min_consensus_threshold,
        centroid_margin_threshold=calib_set.label.centroid_distance_margin
    )
    pred_label_flips = {m.sample_id for m in label_res.flagged_samples}

    # Detector 3: OOD Anomaly Detector
    ood_detector = OODDetector()
    ood_res = ood_detector.analyze(
        dataset,
        contamination=calib_set.ood.contamination_rate
    )
    pred_ood = {o.sample_id for o in ood_res.ood_samples}

    # Detector 4: Multi-Family Backdoor Data Detector (calibrated FFT threshold)
    bd_detector = DataBackdoorDetector()
    bd_res = bd_detector.analyze(dataset, fft_peak_threshold=calib_set.trigger.fft_peak_prominence_zscore)
    pred_corner_triggers = {t.sample_id for t in bd_res.detected_triggers if t.trigger_family == "corner_patch"}
    pred_blended_triggers = {t.sample_id for t in bd_res.detected_triggers if t.trigger_family == "blended_trigger"}
    pred_spectral_triggers = {t.sample_id for t in bd_res.detected_triggers if t.trigger_family == "spectral_trigger"}
    pred_all_triggers = {t.sample_id for t in bd_res.detected_triggers}

    # Detector 5: Volume-Normalized Contributor Risk Aggregator
    aggregator = ContributorRiskAggregator()
    contrib_res = aggregator.aggregate(
        dataset, dup_res, label_res, ood_res, bd_res,
        critical_cutoff=calib_set.contributor.critical_risk_cutoff,
        high_cutoff=calib_set.contributor.high_risk_cutoff,
        medium_cutoff=calib_set.contributor.medium_risk_cutoff
    )

    # Detector 6: Distribution Shift Detector
    shift_res = None
    shift_detected = False
    if ref_dataset_path and os.path.exists(ref_dataset_path):
        ref_ds = DatasetIngester.auto_ingest(ref_dataset_path)
        shift_detector = DistributionShiftDetector()
        shift_res = shift_detector.analyze(ref_ds, dataset)
        shift_detected = shift_res.material_shift_detected

    # 3. Compute Rigorous Empirical Metrics
    dup_m = compute_detailed_binary_metrics(gt_duplicates, pred_duplicates, all_sample_ids)
    lbl_m = compute_detailed_binary_metrics(gt_label_flips, pred_label_flips, all_sample_ids)
    ood_m = compute_detailed_binary_metrics(gt_ood, pred_ood, all_sample_ids)
    
    trig_corner_m = compute_detailed_binary_metrics(gt_corner_triggers, pred_corner_triggers, all_sample_ids)
    trig_blend_m = compute_detailed_binary_metrics(gt_blended_triggers, pred_blended_triggers, all_sample_ids)
    trig_spec_m = compute_detailed_binary_metrics(gt_spectral_triggers, pred_spectral_triggers, all_sample_ids)
    trig_composite_m = compute_detailed_binary_metrics(gt_all_triggers, pred_all_triggers, all_sample_ids)

    # Macro & Weighted Averages across 4 core capabilities
    core_metrics = [dup_m, lbl_m, ood_m, trig_composite_m]
    macro_precision = float(np.mean([m["precision"] for m in core_metrics]))
    macro_recall = float(np.mean([m["recall"] for m in core_metrics]))
    macro_f1 = float(np.mean([m["f1_score"] for m in core_metrics]))

    # Contributor Risk Assessment
    gt_clean_contributors = {"contributor_A", "contributor_trusted", "contributor_calibration", "contributor_drift"}
    gt_compromised_contributors = {"contributor_B", "contributor_C", "contributor_D", "contributor_poison"}

    clean_total = len([p for p in contrib_res.profiles if p.contributor_id in gt_clean_contributors])
    compromised_total = len([p for p in contrib_res.profiles if p.contributor_id in gt_compromised_contributors])

    clean_correctly_kept = 0
    compromised_correctly_flagged = 0
    false_contributor_flags = 0

    contributor_table = []
    for p in contrib_res.profiles:
        cid = p.contributor_id
        is_flagged = p.risk_level in ("CRITICAL", "HIGH")

        if cid in gt_clean_contributors:
            if not is_flagged:
                clean_correctly_kept += 1
            else:
                false_contributor_flags += 1
        elif cid in gt_compromised_contributors:
            if is_flagged:
                compromised_correctly_flagged += 1

        contributor_table.append({
            "contributor_id": cid,
            "total_samples": p.total_samples,
            "flagged_samples": p.flagged_samples_count,
            "risk_score": p.risk_score,
            "risk_level": p.risk_level,
            "dominant_factor": p.dominant_risk_factor,
            "recommended_action": p.recommended_action,
            "explanation": p.explanation
        })

    clean_fpr = (false_contributor_flags / clean_total) if clean_total > 0 else 0.0
    compromised_detection_rate = (compromised_correctly_flagged / compromised_total) if compromised_total > 0 else 0.0

    # 4. Display Results in Rich Formatted Tables
    print("\n" + "=" * 78)
    print("                     EVALUATION METRICS TABLE")
    print("=" * 78)
    print(f"{'Attack / Anomaly Category':<27} | {'TP':>3} | {'FP':>3} | {'FN':>3} | {'Prec':>6} | {'Recall':>6} | {'F1':>6} | {'FPR':>6}")
    print("-" * 78)

    rows = [
        ("Near-Duplicate Flooding", dup_m),
        ("Label Manipulation", lbl_m),
        ("OOD Anomaly Insertion", ood_m),
        ("  - Corner Patch Trigger", trig_corner_m),
        ("  - Blended Watermark", trig_blend_m),
        ("  - Spectral FFT Spike", trig_spec_m),
        ("Backdoor Triggers (All)", trig_composite_m)
    ]

    for name, m in rows:
        print(f"{name:<27} | {m['TP']:>3} | {m['FP']:>3} | {m['FN']:>3} | {m['precision']:>6.2f} | {m['recall']:>6.2f} | {m['f1_score']:>6.2f} | {m['false_positive_rate']:>6.2f}")

    print("-" * 78)
    print(f"{'MACRO AVERAGE (Core 4)':<27} | {'-':>3} | {'-':>3} | {'-':>3} | {macro_precision:>6.2f} | {macro_recall:>6.2f} | {macro_f1:>6.2f} | {'-':>6}")
    print("=" * 78)

    print("\n[+] Contributor-Level Risk Evaluation:")
    print(f"  - Total Evaluated Contributors:       {contrib_res.total_contributors}")
    print(f"  - Clean Contributors Correctly Kept:  {clean_correctly_kept} / {clean_total}")
    print(f"  - Compromised Contributors Flagged:   {compromised_correctly_flagged} / {compromised_total} ({int(compromised_detection_rate * 100)}%)")
    print(f"  - Clean Contributor False Alarm Rate: {clean_fpr * 100:.1f}%")

    print("\nContributor Integrity Risk Profiles:")
    for ct in contributor_table:
        print(f"  * {ct['contributor_id']:<16} => Risk: [{ct['risk_level']:<8}] Score: {ct['risk_score']:<6} | Flagged: {ct['flagged_samples']}/{ct['total_samples']}")
        print(f"    Reason: {ct['explanation']}")

    if shift_res:
        print("\n[+] Operational Distribution Shift Assessment:")
        print(f"  - Material Operational Shift Detected: {shift_detected}")
        print(f"  - Shift Classification:                {shift_res.shift_classification}")
        print(f"  - Overall Drift Score:                 {shift_res.overall_drift_score}")
        print(f"  - Findings:                            {shift_res.summary_findings}")

    print("=" * 78)

    final_report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "dataset": {
            "name": dataset.name,
            "format": dataset.format,
            "total_samples": len(all_sample_ids),
            "total_annotations": dataset.total_annotations
        },
        "calibration": calib_set.model_dump(),
        "metrics": {
            "near_duplicate_flooding": dup_m,
            "label_manipulation": lbl_m,
            "ood_insertion": ood_m,
            "trigger_families": {
                "corner_patch": trig_corner_m,
                "blended_watermark": trig_blend_m,
                "spectral_fft_spike": trig_spec_m,
                "composite_triggers": trig_composite_m
            },
            "macro_summary": {
                "macro_precision": round(macro_precision, 4),
                "macro_recall": round(macro_recall, 4),
                "macro_f1": round(macro_f1, 4)
            }
        },
        "contributors": {
            "total_contributors": contrib_res.total_contributors,
            "clean_contributors_correctly_kept": clean_correctly_kept,
            "compromised_contributors_flagged": compromised_correctly_flagged,
            "clean_contributor_fpr": round(clean_fpr, 4),
            "compromised_detection_rate": round(compromised_detection_rate, 4),
            "profiles": contributor_table
        },
        "distribution_shift": {
            "material_shift_detected": shift_detected,
            "shift_classification": shift_res.shift_classification if shift_res else None,
            "overall_drift_score": shift_res.overall_drift_score if shift_res else None,
            "summary": shift_res.summary_findings if shift_res else None
        },
        "reproducibility": {
            "seed": gt_manifest.seed,
            "manifest_version": gt_manifest.dataset_version,
            "clean_calibration_samples": calib_set.calibration_sample_count
        },
        "limitations": [
            "Perceptual hashing and SSIM confirmation assume geometric alignment without arbitrary perspective warping.",
            "k-NN label integrity requires sufficient class representations (>= 5 samples per evaluated category).",
            "Spectral trigger detection is optimized for periodic Fourier carrier frequencies."
        ]
    }

    if output_metrics_json:
        p = Path(output_metrics_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=2)
        print(f"\n[+] Detailed evaluation metrics report exported to: {output_metrics_json}")

    return final_report

def main():
    parser = argparse.ArgumentParser(description="Evaluate Calibrated Assurance Detectors against Ground Truth Manifest")
    parser.add_argument("--dataset", default="data/dataset_manifest.json", help="Path to evaluation dataset manifest")
    parser.add_argument("--ground-truth", default="data/ground_truth/attack_manifest.json", help="Path to ground truth manifest")
    parser.add_argument("--ref-dataset", default="data/reference/manifest.json", help="Path to clean reference manifest")
    parser.add_argument("--calibration-dir", default="calibration", help="Directory containing calibrated thresholds")
    parser.add_argument("--output-json", default="data/ground_truth/final_evaluation_metrics.json", help="Output path for JSON report")
    args = parser.parse_args()

    run_evaluation(
        dataset_path=args.dataset,
        ground_truth_manifest_path=args.ground_truth,
        ref_dataset_path=args.ref_dataset,
        calibration_config_dir=args.calibration_dir,
        output_metrics_json=args.output_json
    )

if __name__ == "__main__":
    main()
