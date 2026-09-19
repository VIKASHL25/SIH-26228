# Module 1 Capability & Assurance Coverage Statement
**Smart India Hackathon Problem Statement 26228**
*Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines*

---

## 📋 Coverage Mapping: PS Section 2.2.1 (Training-Data Integrity)

| Capability Requirement (PS 2.2.1) | Status | Detection Method | Evaluation & Ground Truth Benchmark | Assumptions & Operational Scope |
| :--- | :---: | :--- | :--- | :--- |
| **Trigger & Backdoor Injection** | **`SUPPORTED`** | **Layered Spatial & Spectral Detection**: Multi-scale sliding window in border zones with variance and Laplacian edge density checks (`CornerTrigger`), 2D FFT Fourier radial conjugate peak prominence analysis (`SpectralTrigger`), and spatial high-pass residual autocorrelation (`BlendedTrigger`). | Evaluated against deterministic ground-truth poisoned samples (BadNets corner checkerboards, alpha-blended watermarks, and Fourier sinusoidal carrier perturbations). | Assumes backdoor triggers introduce localized spatial edge anomalies, high-contrast patch transitions, or periodic frequency-domain carrier peaks. |
| **Label Flipping** | **`SUPPORTED`** | **Feature-Space k-NN Consensus & Centroid Distance**: Object ROI and context feature extraction combined with k-NN neighborhood consensus and class centroid margin discrepancy $d(\mathbf{x}, \mathbf{c}_{\text{given}}) - d(\mathbf{x}, \mathbf{c}_{\text{candidate}})$. | Evaluated on controlled random label flips (5%–10%) across official VisDrone aerial classes (`pedestrian`, `car`, `van`, `truck`, `bus`, `motor`). | Assumes semantic classes have coherent feature distributions and clusters with $\ge 5$ samples per class. |
| **Systematic Mislabelling** | **`SUPPORTED`** | **Contributor Confusion Matrix Analytics**: Aggregates per-contributor class transitions, computes confusion concentration ratios, and flags statistically significant class confusion matrices (e.g. `car` $\to$ `van`, `pedestrian` $\to$ `people`). | Evaluated against structured semantic confusion attack mappings embedded in Contributor B submissions. | Distinguishes isolated human annotation noise from systematic bias or adversary confusion attacks. |
| **Near-Duplicate Flooding** | **`SUPPORTED`** | **Three-Tier Verification**: Tier 1 SHA-256 exact byte matching, Tier 2 dual perceptual hash (pHash + dHash) candidate filtering, and Tier 3 Structural Similarity (SSIM) and normalized pixel MAE confirmation. | Evaluated on transformed near-duplicates generated via JPEG compression degradation, brightness/contrast scaling, rotation, crop/resize, and Gaussian blur. | Distinguishes benign similar aerial textures from confirmed duplicate sample flooding; aggregates flooding concentration per contributor. |
| **Out-Of-Distribution (OOD) Insertion** | **`SUPPORTED`** | **Isolation Forest & Feature Density Scoring**: Evaluates multi-channel color moments, texture energy, and Laplacian edge sharpness in feature space to identify out-of-domain samples. | Evaluated on non-aerial visual domain samples (deep-space imagery, cellular microscopy, marine macro textures, thermal radiometry). | Treated as an **operational anomaly signal**, not automatically marked as malicious tampering; governance layer distinguishes anomalies from attacks. |
| **Contributor Risk Aggregation** | **`SUPPORTED`** | **Volume-Normalized & Confidence-Weighted Scoring**: Normalizes sample-level findings by contributor volume, weights evidence by detector confidence, incorporates systematic confusion/flooding flags, and produces explainable risk tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `CLEAN`). | Evaluated against multi-contributor partitioning: Contributor A (Clean), Contributor B (Label manipulation), Contributor C (Flooding & OOD), Contributor D (Backdoor triggers). | Guaranteed retention of clean contributors as `CLEAN` / `ACCEPT` under natural baseline variation. |

---

## 🔬 Benchmark Methodology & Anti-Leakage Protocol

### 1. Three-Way Split Architecture
To prevent evaluation inflation and data leakage:
- **Clean Calibration Partition (25%)**: Unseen clean images used solely to calibrate detector score distributions and freeze thresholds into `calibration/*.json`.
- **Clean Test Partition (25%)**: Unseen clean images evaluated as negative samples during final evaluation.
- **Attack Test Partition (50%)**: Transformed into controlled attack variants across Contributors A, B, C, and D.
- **Leakage Invariant**: Partitioning is executed strictly on **Original Source Image ID** before applying any attack transformation:
  $$\text{Calibration} \cap \text{Clean Test} = \emptyset \quad \text{and} \quad \text{Calibration} \cap \text{Attack Test} = \emptyset$$

### 2. Threshold Calibration Protocol
Thresholds are computed empirically on the Clean Calibration partition:
- Percentile-based background cutoffs (e.g. 98th/99th percentile of clean score distributions).
- Frozen into versioned JSON configuration files (`duplicate_thresholds.json`, `label_thresholds.json`, `ood_thresholds.json`, `trigger_thresholds.json`, `contributor_thresholds.json`).
- Applied without modification to the unseen evaluation partitions.

---

## ⚠️ Known Limitations & Unsupported Scenarios

1. **Unconstrained Physical Adversarial Camouflage**: The current training-data integrity module detects digital data poisoning, trigger patches, spectral carrier noise, near-duplicates, label flips, and OOD insertions. Physical adversarial camouflage patterns painted onto 3D objects in the physical world without digital manipulation are evaluated in downstream model-level testing (Module 2).
2. **Extreme Class Imbalance**: In datasets with classes containing fewer than 3 samples, k-NN consensus falls back to centroid distance margins.
3. **Severe Perspective Warping**: Near-duplicate detection confirms duplicates with up to $\pm 10^\circ$ rotation, mild crop, compression, and contrast shifts; extreme 3D homography changes may require keypoint-based affine matching (ORB/SIFT).
