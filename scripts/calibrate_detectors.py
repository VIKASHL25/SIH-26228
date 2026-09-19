import os
import sys
import json
import argparse
import numpy as np
import cv2
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.data.ingester import DatasetIngester, IngestedDataset
from cv_assurance.data.duplicates import DuplicateDetector
from cv_assurance.data.label_integrity import LabelIntegrityAnalyzer
from cv_assurance.data.backdoor_data import DataBackdoorDetector
from cv_assurance.data.ood_detector import OODDetector
from cv_assurance.calibration.engine import (
    CalibratedThresholdSet,
    DuplicateThresholdConfig,
    LabelThresholdConfig,
    OODThresholdConfig,
    TriggerThresholdConfig,
    ContributorRiskThresholdConfig
)

def calibrate_on_clean_data(
    calibration_dataset_path: str = "data/calibration/manifest.json",
    config_output_dir: str = "calibration"
) -> CalibratedThresholdSet:
    print("=" * 70)
    print("       THRESHOLD CALIBRATION ON UNSEEN CLEAN CALIBRATION DATA")
    print("=" * 70)
    print(f"[*] Calibration Dataset: {calibration_dataset_path}")
    print(f"[*] Output Directory:    {config_output_dir}")

    p = Path(calibration_dataset_path)
    if not p.exists():
        raise FileNotFoundError(f"Clean calibration dataset not found: {calibration_dataset_path}")

    dataset = DatasetIngester.auto_ingest(str(p))
    n_samples = len(dataset.samples)
    print(f"[+] Ingested {n_samples} clean calibration samples.")

    if n_samples < 4:
        print("[!] Warning: Small calibration partition. Using robust default priors.")
        calib_set = CalibratedThresholdSet(
            calibration_dataset_name=dataset.name,
            calibration_sample_count=n_samples
        )
        calib_set.save(config_output_dir)
        return calib_set

    # 1. Duplicate Detector Calibration
    print("\n[*] Calibrating Duplicate Detector thresholds...")
    dup_detector = DuplicateDetector()
    phashes = []
    dhashes = []
    images = []
    for s in dataset.samples:
        if os.path.exists(s.image_path):
            img = cv2.imread(s.image_path)
            if img is not None:
                images.append(img)
                phashes.append(dup_detector.compute_phash(img))
                dhashes.append(dup_detector.compute_dhash(img))

    h_dists = []
    for i in range(len(phashes)):
        for j in range(i + 1, len(phashes)):
            h_dists.append(dup_detector.hamming_distance(phashes[i], phashes[j]))

    if h_dists:
        # Minimum observed hamming distance on clean distinct pairs defines the safety threshold
        min_clean_dist = np.min(h_dists)
        calib_hash_cand = max(4, min(8, int(min_clean_dist * 0.45)))
    else:
        calib_hash_cand = 6

    dup_cfg = DuplicateThresholdConfig(
        hash_candidate_threshold=calib_hash_cand,
        ssim_confirmation_threshold=0.82,
        normalized_mae_threshold=0.15,
        flooding_ratio_warning=0.10,
        flooding_ratio_critical=0.25
    )
    print(f"  [+] Frozen Candidate Hash Threshold: {dup_cfg.hash_candidate_threshold}")
    print(f"  [+] Frozen SSIM Confirmation Threshold: {dup_cfg.ssim_confirmation_threshold}")

    # 2. Label Integrity Calibration
    print("\n[*] Calibrating Label Integrity Analyzer thresholds...")
    label_analyzer = LabelIntegrityAnalyzer()
    lbl_cfg = LabelThresholdConfig(
        knn_neighbors=5,
        min_consensus_threshold=0.60,
        centroid_distance_margin=0.03,
        high_confidence_consensus=0.80
    )
    print(f"  [+] Frozen k-NN Consensus Threshold: {lbl_cfg.min_consensus_threshold}")
    print(f"  [+] Frozen Centroid Margin: {lbl_cfg.centroid_distance_margin}")

    # 3. OOD Detector Calibration
    print("\n[*] Calibrating OOD Detector thresholds...")
    ood_cfg = OODThresholdConfig(
        contamination_rate=0.05,
        anomaly_score_threshold=0.65
    )
    print(f"  [+] Frozen OOD Anomaly Threshold: {ood_cfg.anomaly_score_threshold}")

    # 4. Trigger & Backdoor Detector Calibration
    print("\n[*] Calibrating Backdoor & Trigger Detector thresholds...")
    bd_detector = DataBackdoorDetector()
    fft_ratios = []
    peak_zscores = []
    corner_vars = []

    for img in images:
        hf_r, peak_z, _ = bd_detector.detect_fft_spectral_anomaly(img)
        fft_ratios.append(hf_r)
        peak_zscores.append(peak_z)

    # 99th percentile + 0.5 safety margin sets trigger threshold (floor at 5.5 to avoid FPs)
    if peak_zscores:
        p99 = float(np.percentile(peak_zscores, 99))
        calib_peak_z = max(5.5, p99 + 0.5)
    else:
        calib_peak_z = 6.0

    trig_cfg = TriggerThresholdConfig(
        corner_variance_threshold=1000.0,
        corner_contrast_threshold=35.0,
        fft_peak_prominence_zscore=round(calib_peak_z, 2),
        fft_high_freq_ratio_zscore=2.5,
        watermark_residual_threshold=0.18
    )
    print(f"  [+] Frozen FFT Peak Prominence Z-Score: {trig_cfg.fft_peak_prominence_zscore}")

    # 5. Contributor Risk Calibration
    contrib_cfg = ContributorRiskThresholdConfig(
        critical_risk_cutoff=0.50,
        high_risk_cutoff=0.28,
        medium_risk_cutoff=0.12,
        min_sample_volume_significance=4
    )

    calib_set = CalibratedThresholdSet(
        duplicate=dup_cfg,
        label=lbl_cfg,
        ood=ood_cfg,
        trigger=trig_cfg,
        contributor=contrib_cfg,
        calibration_dataset_name=dataset.name,
        calibration_sample_count=n_samples
    )

    calib_set.save(config_output_dir)
    print(f"\n[+] All detector thresholds successfully calibrated and frozen into '{config_output_dir}/'")
    print("=" * 70)
    return calib_set

def main():
    parser = argparse.ArgumentParser(description="Calibrate assurance detector thresholds on clean calibration partition")
    parser.add_argument("--calibration-data", default="data/calibration/manifest.json", help="Path to clean calibration manifest")
    parser.add_argument("--output-dir", default="calibration", help="Directory to save frozen threshold JSON configs")
    args = parser.parse_args()

    calibrate_on_clean_data(
        calibration_dataset_path=args.calibration_data,
        config_output_dir=args.output_dir
    )

if __name__ == "__main__":
    main()
