# Trustworthy Computer Vision Integrity Assurance Framework

[![MoD DGIS](https://img.shields.io/badge/Ministry_of_Defence-Indian_Army_DGIS-navy?style=for-the-badge)](README.md)
[![Air-Gapped Ready](https://img.shields.io/badge/Environment-Air--Gapped_%2F_Offline-emerald?style=for-the-badge)](README.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge)](README.md)
[![VisDrone Benchmark](https://img.shields.io/badge/Dataset-VisDrone_2019-orange?style=for-the-badge)](README.md)

A model-agnostic, offline-capable computer vision integrity assurance framework that evaluates multi-contributor training datasets (COCO/YOLO/VisDrone), trained models (PyTorch/ONNX), environmental distribution shifts, and protected inference outputs in multi-contributor pipelines.

---

## 🛡️ Key Capabilities

### 1. Training-Data Integrity & Benchmark Pipeline (`cv_assurance.data` & `cv_assurance.attacks`)
- **Dataset Ingestion**: Native support for **COCO** (`annotations.json`), **YOLO** (`images/`, `labels/*.txt`), **VisDrone-DET** (`annotations/*.txt`), and **Assurance Manifests** (`manifest.json`).
- **Reproducible Multi-Contributor Attacks**: Real-world baseline dataset partitioning with controlled attack injection across Contributors A, B, C, and D.
- **Duplicate & Flooding Detection**: Perceptual hashing (pHash, dHash) & SSIM feature matrix analysis to detect exact and near-duplicate sample flooding.
- **Label Flipping & Mislabelling**: Feature-space vs label disagreement analysis using k-NN consensus & centroid distances.
- **Out-Of-Distribution (OOD) Detection**: Isolation Forest & Local Outlier Factor feature-space anomaly detection.
- **Poisoning & Backdoor Injection**: Spatial high-contrast trigger patch search (e.g. BadNets) and FFT high-frequency periodic spectral anomaly detection.
- **Contributor Risk Aggregation**: Aggregates sample-level flags by contributor/batch metadata to assign source-level risk profiles (`CRITICAL`, `HIGH`, `MEDIUM`, `CLEAN`).

### 2. Model Integrity Assessment (`cv_assurance.model`)
- **Cryptographic Model Hash**: SHA-256 weight digests for PyTorch (`.pt`, `.pth`, `.safetensors`) and ONNX (`.onnx`).
- **Behavioral Fingerprinting**: Prediction entropy, confidence distribution, per-class sensitivity, and calibration error.
- **White-Box Parameter Inspection**: Layer-wise L2 norms, dead neuron activation ratios, and weight distribution anomaly scoring.

### 3. Distribution-Shift & Operational Drift (`cv_assurance.shift`)
- **Domain Metrics**: Specific feature extraction across 4 operational dimensions:
  - **Terrain**: Texture contrast & color histogram energy.
  - **Illumination**: Brightness, contrast, HSV value distribution, low-light/overexposure ratios.
  - **Sensor**: Noise floor variance, Laplacian blur estimate, PSNR estimates.
  - **Season/Acquisition**: Green Vegetation Index (ExG) and spectral hue shifts.
- **Statistical Drift Detection**: Kolmogorov-Smirnov test & Wasserstein distance. Distinguishes natural operational drift from suspicious synthetic manipulation.

### 4. Inference Provenance & Cryptographic Binding (`cv_assurance.provenance`)
- **Verifiable Binding**: Cryptographically binds `Input Image Hash` + `Model Weight Hash` + `Preprocessing Config` + `Output BBoxes/Predictions` + `Timestamp & Nonce`.
- **HMAC Signatures & Verification**: Post-hoc verification engine that makes alteration, substitution, or replay attacks immediately detectable.

### 5. AI Assurance Governance & Analyst Dashboard (`cv_assurance.governance` & `app/`)
- **Human-Readable Findings**: Every flag includes title, reason, supporting evidence, confidence score, severity level (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), affected asset, and recommended disposition (`ACCEPT`, `REVIEW`, `QUARANTINE`).
- **Tamper-Evident Audit Trail**: SHA-256 audit digest for complete report reproducibility.
- **Interactive Web Dashboard**: Modern glassmorphic web UI with live REST API backend.

---

## 🎯 Reproducible Assurance Benchmark (Module 1)

### 1. Dataset Selection: VisDrone Benchmark
We selected the official [VisDrone-DET Dataset](https://github.com/VisDrone/VisDrone-Dataset) (AISKYEYE / Tianjin University) as the primary real-world benchmark for multi-contributor aerial assurance.
- **Why VisDrone?**
  1. Real-world drone and aerial surveillance viewpoints representative of defense and border intelligence operational requirements.
  2. Diverse object scales (pedestrians, vehicles, vans, trucks, buses, tricycles) in dense urban and rural environments.
  3. Official comma-delimited bounding box format `<bbox_left>,<bbox_top>,<bbox_width>,<bbox_height>,<score>,<object_category>,<truncation>,<occlusion>`.
  4. Standardized class taxonomy: `pedestrian` (1), `people` (2), `bicycle` (3), `car` (4), `van` (5), `truck` (6), `tricycle` (7), `awning-tricycle` (8), `bus` (9), `motor` (10), `others` (11).

### 2. Conceptual Separation of Data Stages

```
REAL BASELINE / VISDRONE DATA
              │
              ▼
   CLEAN REFERENCE DATASET
              │
   ┌──────────┴──────────┐
   ▼                     ▼
CONTRIBUTOR SPLIT   LEGITIMATE SHIFTS (is_shifted=True, is_attacked=False)
(A, B, C, D)         (Illumination, Blur, Sensor Noise Floor)
   │
   ▼
CONTROLLED ATTACK INJECTION (is_attacked=True, is_shifted=False)
(#1 Label Flip, #2 Systematic Mislabel, #3 Near-Duplicate Flood,
 #4 OOD Insertion, #5 Corner Trigger, #6 Blended, #7 Spectral)
   │
   ▼
GROUND-TRUTH MANIFEST (attack_manifest.json, dataset_manifest.json)
   │
   ▼
EXISTING ASSURANCE DETECTORS
(Duplicate, Label Integrity, OOD, Backdoor, Contributor Risk)
   │
   ▼
ASSURANCE EVALUATION REPORT & DETECTION METRICS (TP, FP, FN, Precision, Recall, F1)
```

| Pipeline Component | Role & Scope |
| :--- | :--- |
| **REAL DATA** | Authentic baseline imagery and annotations (VisDrone-DET / aerial domain). |
| **SYNTHETIC ATTACKS** | Controlled, parameter-tracked integrity manipulations (flips, triggers, near-duplicates) used for evaluation. |
| **GROUND TRUTH** | Immutable machine-readable record (`attack_manifest.json`) capturing exact injection labels and parameters. |
| **DETECTOR OUTPUT** | Algorithmic findings generated by the framework without access to ground truth manifests. |

*Note: Synthetic attacks are controlled evaluation models and do not claim to represent every unconstrained real-world adversarial manipulation.*

### 3. Directory Layout

The benchmark pipeline generates the following portable structure:

```
data/
├── reference/
│   ├── images/                        # Clean reference imagery (ref_*.jpg)
│   └── manifest.json                  # Clean reference manifest
├── contributors/
│   ├── contributor_A/images/          # Contributor A submissions (mostly clean)
│   ├── contributor_B/images/          # Contributor B submissions (label manipulations)
│   ├── contributor_C/images/          # Contributor C submissions (flooding & OOD)
│   └── contributor_D/images/          # Contributor D submissions (backdoor triggers)
├── attacks/
│   ├── label_flip/                    # Isolated random label flipping samples
│   ├── systematic_mislabel/           # Isolated class confusion samples
│   ├── duplicate_flood/               # Isolated near-duplicate flooded samples
│   ├── ood_insertion/                 # Isolated out-of-distribution samples
│   ├── corner_trigger/                # Isolated corner patch backdoor samples
│   ├── blended_trigger/               # Isolated alpha-blended backdoor samples
│   └── spectral_trigger/              # Isolated FFT spectral backdoor samples
├── distribution_shift/
│   ├── illumination/                  # Low-light, flare, dusk operational shifts
│   ├── blur/                          # Defocus & motion blur operational shifts
│   └── noise/                         # Sensor ISO noise floor operational shifts
└── ground_truth/
    ├── attack_manifest.json           # Master Ground-Truth Manifest
    ├── contributor_manifest.json      # Contributor profile manifest
    ├── dataset_manifest.json          # Unified dataset manifest
    └── evaluation_metrics.json        # Evaluated detector performance metrics
```

### 4. Multi-Contributor Integrity Profiles

The clean reference dataset is deterministically partitioned across 4 synthetic contributors using a fixed seed:
- **Contributor A (`contributor_A`)**: Clean reference contributor submitting legitimate, unaltered aerial annotations.
- **Contributor B (`contributor_B`)**: Label Manipulation contributor injecting random label flipping (5%–10%) and systematic semantic confusion (`pedestrian` $\leftrightarrow$ `people`, `car` $\leftrightarrow$ `van`, `truck` $\leftrightarrow$ `bus`, `bicycle` $\leftrightarrow$ `motor`).
- **Contributor C (`contributor_C`)**: Flooding & Anomaly contributor injecting near-duplicate images (JPEG compression, brightness/contrast scaling, rotation, blur) and Out-Of-Distribution (OOD) visual domain insertions.
- **Contributor D (`contributor_D`)**: Backdoor Contamination contributor injecting spatial corner patch triggers (BadNets), alpha-blended watermark triggers, and 2D FFT spectral frequency perturbations.

### 5. Ground-Truth Manifest Schema

Every sample in the benchmark is tracked via `data/ground_truth/attack_manifest.json`:

```json
{
  "dataset_name": "VisDrone_Assurance_Benchmark",
  "dataset_version": "1.0.0",
  "seed": 42,
  "total_samples": 81,
  "samples": [
    {
      "sample_id": "sample_00016",
      "original_image": "reference/images/ref_00016.jpg",
      "current_image": "contributors/contributor_B/images/sample_00016.jpg",
      "contributor": "contributor_B",
      "batch_id": "batch_B_01",
      "attack_type": "systematic_mislabel",
      "is_attacked": true,
      "is_shifted": false,
      "original_label": "car",
      "original_label_id": 4,
      "modified_label": "van",
      "modified_label_id": 5,
      "parameters": {
        "strategy": "semantic_confusion_matrix",
        "confusion_mapping": { "4": 5, "1": 2, "6": 9 },
        "seed": 44
      },
      "source": "VisDrone"
    }
  ]
}
```

---

## 🚀 Quick Start & Reproducibility Commands

### 1. Requirements Installation
Ensure Python 3.10+ is installed. Dependencies run 100% offline without external network or cloud APIs:

```bash
pip install -r requirements.txt
```

### 2. Dataset Preparation (Real VisDrone or Air-Gapped Synthesizer)
If you have downloaded the official VisDrone archive, specify `--source-dir`. In an offline environment without the multi-gigabyte archive, the pipeline automatically generates a high-fidelity VisDrone-compliant aerial benchmark:

```bash
# Option A: Ingest official VisDrone download
python scripts/prepare_dataset.py --source-dir /path/to/VisDrone2019-DET-train --num-train 1000 --num-val 200

# Option B: Generate offline VisDrone-compliant aerial benchmark
python scripts/prepare_dataset.py --output-dir demo_assets/visdrone_raw --num-train 100 --seed 42
```

### 3. Generate Multi-Contributor Attack Benchmark
Run the reproducible attack pipeline with a fixed seed (creates 3-way disjoint partitions: Calibration, Clean Test, and Attack Test):

```bash
python scripts/generate_attacks.py --num-samples 80 --seed 42 --output-dir data
```

### 4. Validate Benchmark Schema & Zero Data Leakage
Verify that there is strict mathematical zero-leakage between Calibration and Test partitions:

```bash
python scripts/validate_benchmark.py --benchmark-dir data
```

### 5. Calibrate Assurance Detectors on Clean Calibration Partition
Freeze detector decision thresholds strictly on unseen clean calibration imagery without peeking at evaluation attacks:

```bash
python scripts/calibrate_detectors.py --calibration-data data/calibration/manifest.json --output-dir calibration
```

### 6. Evaluate Assurance Detectors against Ground Truth
Run the complete calibrated detector evaluation against master ground-truth manifests:

```bash
python scripts/evaluate_attacks.py --dataset data/dataset_manifest.json --ground-truth data/ground_truth/attack_manifest.json --ref-dataset data/reference/manifest.json --calibration-dir calibration --output data/evaluation_report.json
```

#### 📊 Empirical Benchmark Evaluation Results

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
  - Clean Contributors Correctly Kept:  2 / 2 (100%)
  - Compromised Contributors Flagged:   3 / 3 (100%)
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

### 7. Run Full Assurance Governance Analysis
Run master integrity evaluation on the benchmark:

```bash
python -m cv_assurance.cli analyze --dataset data/dataset_manifest.json --ref-dataset data/reference/manifest.json --output-json data/report.json
```

### 6. Launch Interactive Web Dashboard
```bash
python app/server.py
```
Open `http://127.0.0.1:8000` in your web browser.

---

## 🧪 Verification & Unit Tests

Run the complete test suite covering all baseline integrity modules and Module 1 attacks:

```bash
python -m unittest discover -s tests
```

---

## 📁 Repository Architecture

```
SIH-26228/
├── cv_assurance/                  # Core Python Assurance Framework
│   ├── __init__.py
│   ├── attacks/                   # Module 1: Attack & Distribution Shift Framework
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract BaseAttack & AttackResult
│   │   ├── manifest.py            # AttackSampleRecord, GroundTruthManifest, ManifestValidator
│   │   ├── label_attacks.py       # #1 Label Flipping & #2 Systematic Mislabelling
│   │   ├── duplicate_attacks.py   # #3 Near-Duplicate Flooding
│   │   ├── ood_attacks.py         # #4 Out-Of-Distribution Insertion
│   │   ├── trigger_attacks.py     # #5 Corner Trigger, #6 Blended, #7 Spectral
│   │   ├── distribution_shift.py  # Legitimate Operational Distribution Shift Generator
│   │   └── pipeline.py            # Multi-Contributor Pipeline Orchestrator
│   ├── data/                      # Dataset Ingestion & Data Integrity
│   │   ├── ingester.py            # Unified COCO, YOLO, VisDrone, Manifest Loader
│   │   ├── visdrone.py            # VisDrone-DET Ingester, Subsetter & Synthesizer
│   │   ├── duplicates.py          # Perceptual hash & near-duplicate detector
│   │   ├── label_integrity.py     # Label flipping & mislabelling detector
│   │   ├── ood_detector.py        # Out-Of-Distribution data detector
│   │   ├── backdoor_data.py       # Trigger patch & spectral backdoor detector
│   │   └── contributor_risk.py    # Source/batch metadata risk aggregator
│   ├── model/                     # Model Integrity Assessment
│   │   ├── hasher.py              # SHA-256 digest & weight provenance
│   │   ├── fingerprint.py         # Behavioral fingerprint & entropy evaluator
│   │   └── whitebox_analyzer.py   # White-box parameter norm & sparsity analyzer
│   ├── shift/                     # Distribution Shift & Environmental Drift
│   │   ├── environmental.py       # Terrain, Illumination, Sensor, Season metrics
│   │   └── distribution_test.py   # KS-test & Wasserstein drift detector
│   ├── provenance/                # Inference Cryptographic Binding
│   │   └── crypto_binding.py      # HMAC signature & tamper verification engine
│   ├── governance/                # AI Governance & Audit Engine
│   │   ├── report_schema.py       # Finding, Report & Disposition schemas
│   │   └── engine.py              # Master evaluation orchestrator
│   └── cli.py                     # Command-line interface
├── scripts/                       # Reproducible Evaluation & Generation Scripts
│   ├── prepare_dataset.py         # VisDrone preparation & subsetting
│   ├── generate_attacks.py        # Multi-contributor attack generator
│   └── evaluate_attacks.py        # Detector metrics evaluator against ground truth
├── demo_assets/                   # Reference models & synthetic datasets
├── data/                          # Generated Multi-Contributor Benchmark
│   ├── reference/
│   ├── contributors/
│   ├── attacks/
│   ├── distribution_shift/
│   └── ground_truth/
├── app/                           # Glassmorphic Web Dashboard & FastAPI server
├── tests/                         # Unit & Integration tests suite
│   ├── test_all_integrity.py      # Baseline end-to-end assurance tests
│   └── test_module1_attacks.py    # Module 1 Attack & Benchmark tests
├── requirements.txt
└── README.md
```

---

## 📄 License & Air-Gapped Declaration
Developed for Ministry of Defence (MoD) / Indian Army (DGIS) computer vision pipeline assurance challenge. Operated strictly offline with no external network or cloud service dependencies.
