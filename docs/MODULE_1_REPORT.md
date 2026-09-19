# Module 1 Final Technical Report: Training-Data Integrity Assurance & Reproducible Attack Pipeline

**Smart India Hackathon Problem Statement 26228**  
*Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines*  
**Module**: Module 1 (Training-Data Integrity Assurance)  
**Status**: Completed & Frozen  

---

## 1. Objective

Module 1 establishes a rigorous, defensible training-data integrity assurance framework for multi-contributor computer vision pipelines. It replaces synthetic toy generation with a standardized aerial benchmark based on the official VisDrone-DET dataset, partitions data across multiple contributors without leakage, injects controlled adversarial attacks and legitimate operational shifts, freezes detector decision thresholds on unseen clean calibration data, and evaluates detectors against ground-truth manifests.

---

## 2. Dataset Used: VisDrone-DET Aerial Benchmark

- **Source**: AISKYEYE / Tianjin University VisDrone-DET Drone Surveillance Benchmark.
- **Operational Relevance**: Representative of real-world defense, border security, and reconnaissance drone viewpoints.
- **Taxonomy**: 11 aerial object categories (`pedestrian`, `people`, `bicycle`, `car`, `van`, `truck`, `tricycle`, `awning-tricycle`, `bus`, `motor`, `others`).
- **Benchmark Partitioning**:
  - **Clean Calibration Partition (25%)**: 20 unseen clean images used exclusively to compute empirical score distributions and freeze decision thresholds into `calibration/`.
  - **Clean Test Partition (25%)**: 28 clean images assigned to Contributor A (`contributor_A`) to evaluate clean baseline retention and false-alarm rates.
  - **Attack Test Partition (50%)**: Disjoint pool partitioned across adversarial contributors (B, C, D) and benign environmental drift (`contributor_drift`).
  - **Leakage Invariant**: Verified zero overlap by source image ID between Calibration and Test: $\text{Calibration} \cap \text{Test} = \emptyset$.

---

## 3. Attack Scenarios Implemented

| # | Attack Scenario | Threat Vector | Mechanism & Parameters | Assigned Contributor |
| :-: | :--- | :--- | :--- | :-: |
| 1 | **Random Label Flipping** | Semantic poisoning | Replaces ground-truth category with randomly sampled valid class ($p \in [0.05, 0.10]$). | `contributor_B` |
| 2 | **Systematic Mislabelling** | Targeted semantic bias | Structured confusion mappings: `car` $\to$ `van`, `pedestrian` $\to$ `people`, `truck` $\to$ `bus`, `bicycle` $\to$ `motor`. | `contributor_B` |
| 3 | **Near-Duplicate Flooding** | Pipeline overload / bias | Injects paired near-duplicate scenes under JPEG compression ($Q \in [35, 55]$), contrast scaling, and Gaussian blur ($k=5$). | `contributor_C` |
| 4 | **OOD Anomaly Insertion** | Domain contamination | Inserts non-aerial domain imagery (deep space, cellular microscopy, marine macro). | `contributor_C` |
| 5 | **Corner Trigger (BadNets)** | Spatial backdoor | Inserts $16 \times 16$ high-contrast checkerboard/patch in corner zones ($\text{opacity} = 0.90$). | `contributor_D` |
| 6 | **Blended Trigger** | Stealthy watermark | Blends cross watermark pattern across full image ($\alpha = 0.18$). | `contributor_D` |
| 7 | **Spectral Trigger** | Frequency-domain backdoor | Injects high-frequency conjugate carrier spikes into 2D Fourier spectrum ($\text{magnitude} = 14.0$). | `contributor_D` |
| 8 | **Operational Drift** | Benign environmental shift | Applies illumination shifts, defocus/motion blur, and sensor noise floor variations (`is_attacked=False`, `is_shifted=True`). | `contributor_drift` |

---

## 4. Assurance Detectors Implemented

1. **DuplicateDetector (`cv_assurance.data.duplicates`)**:
   - Three-Tier Verification: Tier 1 SHA-256 byte hashing, Tier 2 dual perceptual hash (pHash + dHash) candidate filtering, and Tier 3 Structural Similarity (SSIM $\ge 0.82$) and normalized pixel MAE ($\le 0.15$) confirmation.
   - Computes contributor-level flooding ratios and flags clusters of $\ge 2$ duplicate samples.

2. **LabelIntegrityAnalyzer (`cv_assurance.data.label_integrity`)**:
   - Feature-space vs label disagreement analyzer combining object ROI color moments, texture energy, and aspect ratio.
   - Dual-gated decision: requires either strong k-NN neighborhood consensus ($\ge 0.80$) or moderate consensus supported by positive class centroid distance margin ($d_{\text{given}} - d_{\text{suggested}} \ge \text{margin}$).

3. **OODDetector (`cv_assurance.data.ood_detector`)**:
   - Unsupervised Isolation Forest and Local Outlier Factor (LOF) on extracted color and spatial frequency moments.
   - Treats anomalies as operational flags rather than intentional malicious attacks.

4. **DataBackdoorDetector (`cv_assurance.data.backdoor_data`)**:
   - Spatial corner patch detector with multi-scale sliding window and localized Laplacian variance filtering ($\ge 1000.0$).
   - High-pass spatial autocorrelation filter for alpha-blended watermarks (residual threshold $\ge 0.18$).
   - 2D FFT Fourier radial power spectrum peak prominence analyzer using calibrated Z-score threshold ($Z \ge 6.12$).

5. **ContributorRiskAggregator (`cv_assurance.data.contributor_risk`)**:
   - Volume-normalized and confidence-weighted composite scoring ($0.0$ to $1.0$).
   - Weights: Backdoors ($0.40$), Label Manipulation ($0.30$), Duplicate Flooding ($0.20$), OOD Anomalies ($0.10$).
   - Assigns explainable risk tiers: `CRITICAL` ($\ge 0.50$), `HIGH` ($\ge 0.28$), `MEDIUM` ($\ge 0.12$), `CLEAN` ($< 0.12$).

6. **DistributionShiftDetector (`cv_assurance.shift.distribution_test`)**:
   - Domain feature extraction across 4 dimensions: Terrain, Illumination, Sensor noise, and Season (vegetation index).
   - Two-sample Kolmogorov-Smirnov (KS) test and Wasserstein distance to detect natural operational drift.

---

## 5. Contributor-Level Risk Assessment & Operational Drift Handling

- **Clean Contributor Protection**: Contributor A is confirmed as `CLEAN` (risk score: $0.0161 \le 0.12$). Zero clean contributors are quarantined (clean false alarm rate = $0.0\%$).
- **Compromised Contributor Isolation**: Contributors B, C, and D are all quarantined as `CRITICAL` ($100\%$ detection rate).
- **Operational Drift Separation**: Operational shifts (`contributor_drift`) are classified as `OPERATIONAL_DRIFT` (drift score: $0.75$). Rather than being misidentified as an adversary, the governance layer assigns `MEDIUM` monitoring disposition with recommendation `MAINTAIN_IN_TRAINING_WITH_DOMAIN_ADAPTATION`.

---

## 6. Final Empirical Benchmark Metrics

Evaluated on `data/dataset_manifest.json` (64 samples) using frozen calibration thresholds from `calibration/` ($N=20$ unseen clean samples):

```
==============================================================================
                     EVALUATION METRICS TABLE
==============================================================================
Attack / Anomaly Category   |  TP |  FP |  FN |   Prec | Recall |     F1 |    FPR
------------------------------------------------------------------------------
Near-Duplicate Flooding     |   8 |   0 |   0 |   1.00 |   1.00 |   1.00 |   0.00
Label Manipulation          |   7 |   7 |   1 |   0.50 |   0.88 |   0.64 |   0.12
OOD Anomaly Insertion       |   3 |   1 |   1 |   0.75 |   0.75 |   0.75 |   0.02
  - Corner Patch Trigger    |   3 |   2 |   0 |   0.60 |   1.00 |   0.75 |   0.03
  - Blended Watermark       |   3 |   0 |   0 |   1.00 |   1.00 |   1.00 |   0.00
  - Spectral FFT Spike      |   2 |   1 |   0 |   0.67 |   1.00 |   0.80 |   0.02
Backdoor Triggers (All)     |   8 |   3 |   0 |   0.73 |   1.00 |   0.84 |   0.05
------------------------------------------------------------------------------
MACRO AVERAGE (Core 4)      |   - |   - |   - |   0.74 |   0.91 |   0.81 |      -
==============================================================================

[+] Contributor-Level Risk Evaluation:
  - Total Evaluated Contributors:       5
  - Clean Contributors Correctly Kept:  2 / 2 (100.0%)
  - Compromised Contributors Flagged:   3 / 3 (100.0%)
  - Clean Contributor False Alarm Rate: 0.0%

Contributor Integrity Risk Profiles:
  * contributor_A     => Risk: [CLEAN   ] Score: 0.0161 | Flagged: 1/28 (Clean Reference Baseline)
  * contributor_B     => Risk: [CRITICAL] Score: 0.6000 | Flagged: 7/8  (Label Manipulation Attacker)
  * contributor_C     => Risk: [CRITICAL] Score: 0.6167 | Flagged: 12/12(Near-Duplicate Flood & OOD Attacker)
  * contributor_D     => Risk: [CRITICAL] Score: 0.6000 | Flagged: 8/8  (Backdoor & Trigger Poisoner)
  * contributor_drift => Risk: [MEDIUM  ] Score: 0.1688 | Flagged: 3/8  (Benign Operational Environmental Drift)

[+] Operational Distribution Shift Assessment:
  - Material Operational Shift Detected: True
  - Shift Classification:                OPERATIONAL_DRIFT
  - Overall Drift Score:                 0.75
  - Findings: Natural operational environmental drift observed across 3 dimensions (illumination/season/terrain).
```

---

## 7. Representative Findings & Evidence (Live Detector Output)

Findings generated via `python scripts/show_module1_results.py`:

```text
--- [1. Representative Finding: Label Manipulation] ---
Sample ID:        sample_00030
Contributor:      contributor_B
Detection:        Semantic Mislabelling (Annotated: 'truck' -> Inferred: 'car')
Reason/Evidence:  k-NN neighborhood consensus 100% and centroid margin -0.0136 indicate 'car' instead of 'truck'
Confidence:       0.70 (MEDIUM)
Severity:         MEDIUM
Disposition:      HOLD_FOR_EXPERT_ANNOTATION_REVIEW

--- [2. Representative Finding: Near-Duplicate Flooding] ---
Sample ID:        sample_00037
Related Sample:   sample_00038 (Paired File: sample_00038.jpg)
Contributor:      contributor_C
Detection:        Near-Duplicate Sample Flooding (Confirmed Structural & Pixel Match)
Reason/Evidence:  Confirmed near-duplicate pair with SSIM=0.9892 (threshold >= 0.82) and Pixel MAE=0.0311 (threshold <= 0.15)
Confidence:       0.98
Severity:         HIGH
Disposition:      DEDUPLICATE_AND_DOWNWEIGHT_SUBMISSION_BATCH

--- [3. Representative Finding: Out-Of-Distribution (OOD) Insertion] ---
Sample ID:        sample_00045
Contributor:      contributor_C
Detection:        Out-Of-Distribution Visual Domain Anomaly
Reason/Evidence:  Isolation Forest feature anomaly score 1.000 exceeded threshold (0.65); abnormal color moments & texture entropy
Confidence:       0.85
Severity:         MEDIUM
Disposition:      FLAG_AS_NON_MALICIOUS_OPERATIONAL_ANOMALY

--- [4. Representative Finding: Corner Patch Trigger (BadNets Backdoor)] ---
Sample ID:        sample_00049
Contributor:      contributor_D
Detection:        Corner Patch Backdoor Trigger (High-Contrast Checkerboard/Pattern)
Reason/Evidence:  Checkerboard trigger patch detected at [624, 0, 16, 16] (Laplacian variance: 11030); bounding box location: [624, 0, 16, 16]
Confidence:       1.00
Severity:         CRITICAL
Disposition:      QUARANTINE_SAMPLE_AND_PERFORM_PROVENANCE_AUDIT

--- [5. Representative Finding: Blended Watermark Trigger] ---
Sample ID:        sample_00050
Contributor:      contributor_D
Detection:        Alpha-Blended Watermark Backdoor Trigger (Spatial Autocorrelation Residual)
Reason/Evidence:  Spatial high-pass watermark cross pattern detected (line energy ratio: 0.982)
Confidence:       0.95
Severity:         CRITICAL
Disposition:      QUARANTINE_SAMPLE_AND_PERFORM_PROVENANCE_AUDIT

--- [6. Representative Finding: Spectral FFT Spike Trigger] ---
Sample ID:        sample_00051
Contributor:      contributor_D
Detection:        Spectral Frequency Carrier Backdoor (Fourier Domain Anomaly)
Reason/Evidence:  High-frequency 2D Fourier spectral spike detected (peak prominence z-score: 6.28, ratio z-score: -0.07)
Confidence:       1.00
Severity:         CRITICAL
Disposition:      QUARANTINE_SAMPLE_AND_PERFORM_PROVENANCE_AUDIT

--- [7. Operational Distribution Shift Assessment] ---
Classification:       OPERATIONAL_DRIFT
Drift score:          0.75
Affected dimensions:  terrain, illumination, season
  * terrain       : KS-statistic=0.113, Wasserstein=5.18 [SHIFT DETECTED]
  * illumination  : KS-statistic=0.109, Wasserstein=8.27 [SHIFT DETECTED]
  * sensor        : KS-statistic=0.078, Wasserstein=0.55 [NORMAL]
  * season        : KS-statistic=0.053, Wasserstein=10.98 [SHIFT DETECTED]
Evidence:             Natural operational environmental drift observed across 3 dimensions (illumination/season/terrain).
Disposition:          MAINTAIN_IN_TRAINING_WITH_DOMAIN_ADAPTATION (Operational drift, NOT an attack)

--- [8. Contributor-Level: Clean Contributor Profile] ---
Contributor:      contributor_A
Risk Level:       [CLEAN]
Risk Score:       0.0161 (Clean baseline <= 0.12)
Flagged Volume:   1 / 28 samples flagged
Dominant Factor:  Label Manipulation
Reason/Evidence:  Sample-level variation remains within expected baseline noise tolerances.
Disposition:      ACCEPT: Contributor data passes integrity verification standards.

--- [9. Contributor-Level: Compromised Contributor Profile] ---
Contributor:      contributor_B
Risk Level:       [CRITICAL]
Risk Score:       0.6000 (Exceeds critical cutoff >= 0.5)
Flagged Volume:   7 / 8 samples flagged (88%)
Dominant Factor:  Label Manipulation
Reason/Evidence:  Critical risk driven by Label Manipulation (Trigger score: 0.5, Label score: 1.0).
Disposition:      QUARANTINE_CONTRIBUTOR: Immediate batch isolation and forensic provenance audit.
```

---

## 8. Limitations & Scope

1. **Physical World Camouflage**: Module 1 targets digital data poisoning, trigger patches, spectral noise, near-duplicates, label flips, and OOD insertions. Physical adversarial paint on real objects is evaluated in model-level validation (Module 2).
2. **Extreme Class Imbalance**: In classes with $< 3$ samples, k-NN consensus defaults to class centroid distance.
3. **Complex Homography**: Near-duplicate detection supports $\pm 10^\circ$ rotation, crop, blur, and compression. Extreme 3D perspective skewing requires keypoint affine matching.

---

## 9. PS 2.2.1 Coverage Mapping

| PS 2.2.1 Requirement | Status | Module 1 Implementation | Evidence / Artifact |
| :--- | :---: | :--- | :--- |
| **Trigger & Backdoor Detection** | **COMPLETED** | Spatial corner patch scan, FFT radial prominence, spatial residual autocorrelation | `cv_assurance/data/backdoor_data.py`, $F_1 = 0.84$, $100\%$ Recall |
| **Label Manipulation & Flipping** | **COMPLETED** | Object ROI features, k-NN consensus, class centroid distance margin | `cv_assurance/data/label_integrity.py`, $F_1 = 0.64$, $88\%$ Recall |
| **Near-Duplicate Flooding** | **COMPLETED** | 3-tier SHA-256 + pHash/dHash + SSIM/MAE confirmation, contributor cluster tracking | `cv_assurance/data/duplicates.py`, $F_1 = 1.00$, $100\%$ Recall, $0\%$ FPR |
| **OOD Anomaly Detection** | **COMPLETED** | Isolation Forest & color/texture moment outlier scoring | `cv_assurance/data/ood_detector.py`, $F_1 = 0.75$, $75\%$ Recall |
| **Contributor Risk Aggregator** | **COMPLETED** | Volume-normalized composite risk scoring with explainable audit dispositions | `cv_assurance/data/contributor_risk.py`, $100\%$ clean kept, $100\%$ malicious flagged |
| **Operational Drift Separation** | **COMPLETED** | 4-domain feature extraction + KS-test & Wasserstein distance | `cv_assurance/shift/distribution_test.py`, `OPERATIONAL_DRIFT` |
