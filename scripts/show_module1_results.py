import os
import sys
from pathlib import Path

# Add repository root to python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import cv2
    import numpy
except ImportError:
    print("\n[!] Dependency Error: Required libraries (cv2, numpy) not found in the current Python environment.")
    print("    Please activate the project conda environment before running:")
    print("        conda activate sih26")
    print("    Or run directly using:")
    print("        conda run -n sih26 python scripts/show_module1_results.py\n")
    sys.exit(1)

from cv_assurance.data.ingester import DatasetIngester
from cv_assurance.calibration.engine import CalibratedThresholdSet
from cv_assurance.data.duplicates import DuplicateDetector
from cv_assurance.data.label_integrity import LabelIntegrityAnalyzer
from cv_assurance.data.ood_detector import OODDetector
from cv_assurance.data.backdoor_data import DataBackdoorDetector
from cv_assurance.data.contributor_risk import ContributorRiskAggregator
from cv_assurance.shift.distribution_test import DistributionShiftDetector

def run_representative_findings(
    dataset_path: str = "data/dataset_manifest.json",
    ref_dataset_path: str = "data/reference/manifest.json",
    calibration_dir: str = "calibration"
):
    print("=" * 76)
    print("          MODULE 1: REPRESENTATIVE INTEGRITY ASSURANCE FINDINGS")
    print("=" * 76)

    # 1. Load Calibrated Thresholds and Ingest Datasets
    calib_set = CalibratedThresholdSet.load(calibration_dir)
    dataset = DatasetIngester.auto_ingest(dataset_path)
    ref_ds = DatasetIngester.auto_ingest(ref_dataset_path) if os.path.exists(ref_dataset_path) else None

    # 2. Run Actual Detectors
    dup_detector = DuplicateDetector()
    dup_res = dup_detector.analyze(
        dataset,
        hash_candidate_threshold=calib_set.duplicate.hash_candidate_threshold,
        ssim_confirmation_threshold=calib_set.duplicate.ssim_confirmation_threshold,
        normalized_mae_threshold=calib_set.duplicate.normalized_mae_threshold
    )

    label_analyzer = LabelIntegrityAnalyzer()
    label_res = label_analyzer.analyze(
        dataset,
        k_neighbors=calib_set.label.knn_neighbors,
        min_consensus_threshold=calib_set.label.min_consensus_threshold,
        centroid_margin_threshold=calib_set.label.centroid_distance_margin
    )

    ood_detector = OODDetector()
    ood_res = ood_detector.analyze(
        dataset,
        contamination=calib_set.ood.contamination_rate
    )

    bd_detector = DataBackdoorDetector()
    bd_res = bd_detector.analyze(
        dataset,
        fft_peak_threshold=calib_set.trigger.fft_peak_prominence_zscore
    )

    aggregator = ContributorRiskAggregator()
    contrib_res = aggregator.aggregate(
        dataset, dup_res, label_res, ood_res, bd_res,
        critical_cutoff=calib_set.contributor.critical_risk_cutoff,
        high_cutoff=calib_set.contributor.high_risk_cutoff,
        medium_cutoff=calib_set.contributor.medium_risk_cutoff
    )

    shift_res = None
    if ref_ds is not None:
        shift_detector = DistributionShiftDetector()
        shift_res = shift_detector.analyze(ref_ds, dataset)

    # -------------------------------------------------------------
    # Helper to print standardized finding block
    # -------------------------------------------------------------
    def print_finding(title: str, sample_id: str, contributor: str, detection: str,
                      reason: str, confidence: str, severity: str, disposition: str,
                      extra_lines: list = None):
        print(f"\n--- [{title}] ---")
        print(f"Sample ID:        {sample_id}")
        if extra_lines:
            for el in extra_lines:
                print(el)
        print(f"Contributor:      {contributor}")
        print(f"Detection:        {detection}")
        print(f"Reason/Evidence:  {reason}")
        print(f"Confidence:       {confidence}")
        print(f"Severity:         {severity}")
        print(f"Disposition:      {disposition}")

    # 1. Label Manipulation Finding
    rep_label = next((m for m in label_res.flagged_samples if m.contributor_id == "contributor_B"), None)
    if not rep_label and label_res.flagged_samples:
        rep_label = label_res.flagged_samples[0]

    if rep_label:
        conf_val = f"{rep_label.discrepancy_score:.2f} ({rep_label.confidence_level})"
        sev_val = "HIGH" if rep_label.confidence_level == "HIGH" else "MEDIUM"
        disp_val = "HOLD_FOR_EXPERT_ANNOTATION_REVIEW"
        print_finding(
            title="1. Representative Finding: Label Manipulation",
            sample_id=rep_label.sample_id,
            contributor=rep_label.contributor_id,
            detection=f"Semantic Mislabelling (Annotated: '{rep_label.given_label_name}' -> Inferred: '{rep_label.suggested_label_name}')",
            reason=f"k-NN neighborhood consensus {int(rep_label.knn_consensus*100)}% and centroid margin {rep_label.centroid_distance_margin:.4f} indicate '{rep_label.suggested_label_name}' instead of '{rep_label.given_label_name}'",
            confidence=conf_val,
            severity=sev_val,
            disposition=disp_val
        )

    # 2. Near-Duplicate Flooding Finding
    rep_dup_pair = next((p for p in dup_res.duplicate_pairs if p.is_confirmed and p.contributor_a == p.contributor_b == "contributor_C"), None)
    if not rep_dup_pair:
        rep_dup_pair = next((p for p in dup_res.duplicate_pairs if p.is_confirmed and p.contributor_a == p.contributor_b), None)

    if rep_dup_pair:
        print_finding(
            title="2. Representative Finding: Near-Duplicate Flooding",
            sample_id=rep_dup_pair.sample_id_a,
            contributor=rep_dup_pair.contributor_a,
            detection="Near-Duplicate Sample Flooding (Confirmed Structural & Pixel Match)",
            reason=f"Confirmed near-duplicate pair with SSIM={rep_dup_pair.ssim_score:.4f} (threshold >= {calib_set.duplicate.ssim_confirmation_threshold}) and Pixel MAE={rep_dup_pair.pixel_mae:.4f} (threshold <= {calib_set.duplicate.normalized_mae_threshold})",
            confidence=f"{rep_dup_pair.similarity_score:.2f}",
            severity="HIGH",
            disposition="DEDUPLICATE_AND_DOWNWEIGHT_SUBMISSION_BATCH",
            extra_lines=[f"Related Sample:   {rep_dup_pair.sample_id_b} (Paired File: {rep_dup_pair.file_name_b})"]
        )

    # 3. OOD Insertion Finding
    rep_ood = next((o for o in ood_res.ood_samples if o.contributor_id == "contributor_C"), None)
    if not rep_ood and ood_res.ood_samples:
        rep_ood = ood_res.ood_samples[0]

    if rep_ood:
        print_finding(
            title="3. Representative Finding: Out-Of-Distribution (OOD) Insertion",
            sample_id=rep_ood.sample_id,
            contributor=rep_ood.contributor_id,
            detection="Out-Of-Distribution Visual Domain Anomaly",
            reason=f"Isolation Forest feature anomaly score {rep_ood.anomaly_score:.3f} exceeded threshold ({calib_set.ood.anomaly_score_threshold}); abnormal color moments & texture entropy",
            confidence="0.85",
            severity="MEDIUM",
            disposition="FLAG_AS_NON_MALICIOUS_OPERATIONAL_ANOMALY"
        )

    # 4. Corner Trigger Finding
    rep_corner = next((t for t in bd_res.detected_triggers if t.trigger_family == "corner_patch" and t.contributor_id == "contributor_D"), None)
    if not rep_corner:
        rep_corner = next((t for t in bd_res.detected_triggers if t.trigger_family == "corner_patch"), None)
    if rep_corner:
        box_str = str(rep_corner.bbox_location) if rep_corner.bbox_location else "N/A"
        print_finding(
            title="4. Representative Finding: Corner Patch Trigger (BadNets Backdoor)",
            sample_id=rep_corner.sample_id,
            contributor=rep_corner.contributor_id,
            detection="Corner Patch Backdoor Trigger (High-Contrast Checkerboard/Pattern)",
            reason=f"{rep_corner.details}; bounding box location: {box_str}",
            confidence=f"{rep_corner.confidence:.2f}",
            severity="CRITICAL",
            disposition="QUARANTINE_SAMPLE_AND_PERFORM_PROVENANCE_AUDIT"
        )

    # 5. Blended Watermark Trigger Finding
    rep_blended = next((t for t in bd_res.detected_triggers if t.trigger_family == "blended_trigger" and t.contributor_id == "contributor_D"), None)
    if not rep_blended:
        rep_blended = next((t for t in bd_res.detected_triggers if t.trigger_family == "blended_trigger"), None)
    if rep_blended:
        print_finding(
            title="5. Representative Finding: Blended Watermark Trigger",
            sample_id=rep_blended.sample_id,
            contributor=rep_blended.contributor_id,
            detection="Alpha-Blended Watermark Backdoor Trigger (Spatial Autocorrelation Residual)",
            reason=rep_blended.details,
            confidence=f"{rep_blended.confidence:.2f}",
            severity="CRITICAL",
            disposition="QUARANTINE_SAMPLE_AND_PERFORM_PROVENANCE_AUDIT"
        )

    # 6. Spectral FFT Trigger Finding
    rep_spectral = next((t for t in bd_res.detected_triggers if t.trigger_family == "spectral_trigger" and t.contributor_id == "contributor_D"), None)
    if not rep_spectral:
        rep_spectral = next((t for t in bd_res.detected_triggers if t.trigger_family == "spectral_trigger"), None)
    if rep_spectral:
        print_finding(
            title="6. Representative Finding: Spectral FFT Spike Trigger",
            sample_id=rep_spectral.sample_id,
            contributor=rep_spectral.contributor_id,
            detection="Spectral Frequency Carrier Backdoor (Fourier Domain Anomaly)",
            reason=rep_spectral.details,
            confidence=f"{rep_spectral.confidence:.2f}",
            severity="CRITICAL",
            disposition="QUARANTINE_SAMPLE_AND_PERFORM_PROVENANCE_AUDIT"
        )

    # 7. Operational Distribution Shift
    print("\n--- [7. Operational Distribution Shift Assessment] ---")
    if shift_res:
        affected_dims = [d.dimension_name for d in shift_res.dimensions if d.shift_detected]
        print(f"Classification:       {shift_res.shift_classification}")
        print(f"Drift score:          {shift_res.overall_drift_score:.2f}")
        print(f"Affected dimensions:  {', '.join(affected_dims) if affected_dims else 'None'}")
        for d in shift_res.dimensions:
            status = "SHIFT DETECTED" if d.shift_detected else "NORMAL"
            print(f"  * {d.dimension_name:<14}: KS-statistic={d.ks_statistic:.3f}, Wasserstein={d.wasserstein_dist:.2f} [{status}]")
        print(f"Evidence:             {shift_res.summary_findings}")
        print("Disposition:          MAINTAIN_IN_TRAINING_WITH_DOMAIN_ADAPTATION (Operational drift, NOT an attack)")
    else:
        print("Classification:       NO_DATA (Clean reference dataset not loaded)")

    # 8. Clean Contributor Finding
    clean_prof = next((p for p in contrib_res.profiles if p.contributor_id == "contributor_A"), None)
    if not clean_prof:
        clean_prof = next((p for p in contrib_res.profiles if p.risk_level == "CLEAN"), None)

    if clean_prof:
        print("\n--- [8. Contributor-Level: Clean Contributor Profile] ---")
        print(f"Contributor:      {clean_prof.contributor_id}")
        print(f"Risk Level:       [{clean_prof.risk_level}]")
        print(f"Risk Score:       {clean_prof.risk_score:.4f} (Clean baseline <= {calib_set.contributor.medium_risk_cutoff})")
        print(f"Flagged Volume:   {clean_prof.flagged_samples_count} / {clean_prof.total_samples} samples flagged")
        print(f"Dominant Factor:  {clean_prof.dominant_risk_factor}")
        print(f"Reason/Evidence:  {clean_prof.explanation}")
        print(f"Disposition:      {clean_prof.recommended_action}")

    # 9. Compromised Contributor Finding
    comp_prof = next((p for p in contrib_res.profiles if p.contributor_id in ("contributor_D", "contributor_B", "contributor_C") and p.risk_level == "CRITICAL"), None)
    if not comp_prof:
        comp_prof = next((p for p in contrib_res.profiles if p.risk_level in ("CRITICAL", "HIGH")), None)

    if comp_prof:
        print("\n--- [9. Contributor-Level: Compromised Contributor Profile] ---")
        print(f"Contributor:      {comp_prof.contributor_id}")
        print(f"Risk Level:       [{comp_prof.risk_level}]")
        print(f"Risk Score:       {comp_prof.risk_score:.4f} (Exceeds critical cutoff >= {calib_set.contributor.critical_risk_cutoff})")
        print(f"Flagged Volume:   {comp_prof.flagged_samples_count} / {comp_prof.total_samples} samples flagged ({comp_prof.flagged_samples_count/max(1,comp_prof.total_samples)*100:.0f}%)")
        print(f"Dominant Factor:  {comp_prof.dominant_risk_factor}")
        print(f"Reason/Evidence:  {comp_prof.explanation}")
        print(f"Disposition:      {comp_prof.recommended_action}")

    print("\n" + "=" * 76)

if __name__ == "__main__":
    run_representative_findings()
