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
- **OOD/Relative Anomaly Detection**: Isolation Forest feature-space anomaly detection. When a clean reference is available, the detector fits on the reference and scores the target; otherwise results are explicitly relative to the evaluated dataset and are not general OOD proof.
- **Poisoning & Backdoor Injection**: Spatial high-contrast trigger patch search (e.g. BadNets) and FFT high-frequency periodic spectral anomaly detection.
- **Contributor Risk Aggregation**: Aggregates sample-level flags by available contributor metadata and reports affected batches. Missing contributor, batch, and source metadata remains unavailable; identities are not inferred from sample order.
- **Evaluation Evidence**: Controlled attack manifests and `scripts/evaluate_attacks.py` report TP/FP/FN, precision, recall, F1, false-positive rate, false-negative rate, and detection rate where ground truth exists. These are controlled-benchmark metrics, not universal field performance.

### 2. Model Integrity Assessment (`cv_assurance.model`)
- **SHA-256 Integrity Verification**: Streaming digests for `.pt`, `.pth`, `.safetensors`, `.onnx`, and TorchScript model artifacts, with trusted-reference comparison.
- **Supported-Format Validation**: Rejects unknown model extensions before integrity assessment; verification never relies on filenames, timestamps, or metadata alone.
- **Secure PyTorch Inspection**: Tensor-only checkpoint inspection where supported, reducing exposure to arbitrary deserialization during metadata and parameter analysis.
- **Substitution & Tampering Detection**: Controlled modified-weight and substituted-model scenarios produce digest mismatches and integrity findings.
- **Behavioral Fingerprinting**: Deterministic reference-battery comparison covering prediction agreement, confidence distributions, entropy, class behavior, and stability.
- **White-Box Analysis**: Layer shapes, means, standard deviations, L2 norms, sparsity/dead-neuron ratios, optional forward-hook activation statistics, anomaly scores, and affected-layer evidence when parameters are accessible. Reference comparisons are reported separately from heuristic thresholds.
- **Black-Box Fallback**: A caller-supplied prediction callable is fingerprinted using its actual outputs; white-box access is explicitly reported unavailable. No dummy predictions are generated.
- **Trigger Probing & Evidence Fusion**: Reproducible corner, blended, and spectral probes identify backdoor-like behavior under tested conditions; findings include evidence, confidence, severity, and `ACCEPT`/`REVIEW`/`QUARANTINE` disposition.
- **Limitations**: SafeTensors supports hashing only; arbitrary PyTorch architecture reconstruction is not automatic; trigger probing is heuristic and not universal backdoor detection; all confidence values are heuristic/evidence-derived, not calibrated probabilities.

Module 2 implementation paths cover the bundled controlled PyTorch benchmark, callable black-box adapters, TorchScript through `torch.jit.load`, and conditional ONNX execution through offline `onnxruntime`. Runtime validation is environment-dependent; this checkout currently lacks the required dependencies, so these paths are IMPLEMENTED BUT NOT RUNTIME-VERIFIED here. Unsupported runtimes report `UNAVAILABLE` rather than producing synthetic predictions. Confidence values are evidence-derived heuristics, not calibrated probabilities. The deterministic reference battery is a controlled 4-class demo-classification fixture, not universal CV coverage.

### 3. Distribution-Shift & Operational Drift (`cv_assurance.shift`)
- **Domain Metrics**: Image-derived proxy feature extraction across 4 operational dimensions:
  - **Terrain**: Texture contrast & color histogram energy.
  - **Illumination**: Brightness, contrast, HSV value distribution, low-light/overexposure ratios.
  - **Sensor**: Noise floor variance, Laplacian blur estimate, PSNR estimates.
  - **Season/Acquisition**: Green Vegetation Index (ExG) and spectral hue shifts.
- **Statistical Drift Detection**: Kolmogorov-Smirnov test & Wasserstein distance. Distinguishes operational drift from suspicious manipulation only under supported evidence rules; confidence is bounded heuristic evidence, not a calibrated probability, and image proxies are not semantic terrain/season classifiers.
- **Shift Evidence and Governance**: Every dimension reports its feature proxy, KS statistic, p-value, Wasserstein distance, shift flag, sample sufficiency, bounded heuristic confidence, affected dataset asset, severity, disposition, and limitations through the JSON assurance report and tamper-evident audit chain.

### 4. Inference Provenance & Cryptographic Binding (`cv_assurance.provenance`)
- **Explicit Binding**: `ProtectedInferenceRecord` binds exact input bytes, model digest, preprocessing configuration, explicit inference configuration, canonical predictions, timestamp, nonce, and sequence through SHA-256 and HMAC-SHA256.
- **Canonicalization & Verification**: Preprocessing and inference configurations are canonicalized independently; modifying either configuration invalidates its hash and the binding digest. Predictions are deterministically sorted and normalized.
- **Replay Protection**: `ReplayProtectionRegistry` detects record-ID, nonce, binding-hash, and sequence reuse. A local JSON registry provides persistence across process restarts.
- **Limitations**: Timestamp checks do not provide trusted-clock guarantees. The HMAC secret must be provisioned securely. Backward-compatible records without inference configuration retain the legacy binding form.

### 5. AI Assurance Governance & Analyst Dashboard (`cv_assurance.governance` & `app/`)
- **Governance Findings**: Finding/report schemas and the master assurance engine expose human-readable reason, supporting evidence, heuristic confidence semantics, severity, affected asset, recommended disposition, known limitations, and a tamper-evident audit-chain summary. Output is machine-readable JSON.
- **Existing Dashboard Components**: `app/server.py` and the static web UI expose the current assurance outputs.
- **Milestone Status**: Governance and dashboard components remain available project infrastructure; final integration and blockchain/tamper-evident ledger completion are future work.

### Project Status

| Area | Status |
| :--- | :--- |
| Module 1 — Training-Data Integrity | **IMPLEMENTED / CONTROLLED-BENCHMARK TESTED** |
| Module 2 — Model Integrity | **IMPLEMENTED / RUNTIME VALIDATION DEPENDS ON LOCAL DEPENDENCIES** |
| Module 3A/3B — Provenance, Shift & Governance | **IMPLEMENTED / MANUALLY RUNTIME-VERIFIED** |
| Blockchain | **NOT USED / OUT OF SCOPE** |
| Final End-to-End Integration | **IMPLEMENTED WITH DOCUMENTED LIMITATIONS** |

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
| **ATTACK GENERATION TRUTH** | Reproducible machine-readable record (`attack_manifest.json`) capturing exact controlled injection labels and parameters; it is not independent real-world ground truth. |
| **DETECTOR OUTPUT** | Algorithmic findings generated by the framework without access to attack manifests. |

*Note: Synthetic attacks are controlled evaluation models and do not claim to represent every unconstrained real-world adversarial manipulation.*

*Module 1 evaluation metrics are labelled synthetic/controlled benchmark metrics. Label-integrity results are heuristic visual-consensus findings unless trusted labels are separately supplied; unavailable independent ground-truth metrics are not manufactured.*

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

### 7. Run Module 2 Model Integrity Benchmark

Run the controlled model-integrity scenarios against the deterministic reference image battery:

```bash
python -m cv_assurance.model.benchmark
```

This demonstrates trusted-model hashing, modified-weight and substitution detection, behavioral fingerprint comparison, white-box evidence, trigger probing, and evidence-oriented findings. It writes `reports/module_2_benchmark.json`.

#### Module 2 Model Integrity Benchmark — Verified Results

| Scenario | Hash Match | Behavioral Deviation | White-Box Evidence | Disposition |
| :--- | :---: | ---: | :--- | :--- |
| Clean | YES | 0.0000 | Available; no anomaly | ACCEPT |
| Tampered weights | NO | 0.3486 | `conv1.weight` affected | QUARANTINE |
| Behavior modified | NO | 0.9244 | `fc1.weight` affected | QUARANTINE |
| Substituted | NO | 0.4438 | `conv1.weight` affected | QUARANTINE |

The trigger probe is evidence of backdoor-like behavior only under the tested trigger battery; these controlled artifacts did not produce a separate positive trigger detection in the verified run.

### 8. Run Full Assurance Governance Analysis
Run master integrity evaluation on the benchmark:

```bash
python -m cv_assurance.cli analyze --dataset data/dataset_manifest.json --ref-dataset data/reference/manifest.json --output-json data/report.json
```

### 9. Launch Interactive Web Dashboard
```bash
python app/server.py
```
Open `http://127.0.0.1:8000` in your web browser.

---

## 🔒 Module 3A — Inference Provenance & Cryptographic Output Integrity

Module 3A provides air-gapped, post-hoc cryptographic provenance and output integrity assurance for computer vision inference pipelines. It eliminates downstream trust assumptions by mathematically binding the entire inference lifecycle into a tamper-evident, authenticated record.

```
Input Image Bytes (SHA-256)
Model File (SHA-256 via ModelHasher)
Preprocessing Configuration (Canonical JSON + SHA-256)
Inference Configuration (Canonical JSON + SHA-256, when supplied)
Inference Predictions (Deterministic sorting + float normalization + SHA-256)
UTC Timestamp + CSPRNG Nonce + Monotonic Sequence Number
      ↓
Canonical Binding Payload:
  image_hash|model_hash|preprocess_hash|inference_hash|predictions_json|timestamp|nonce|sequence_number
      ↓
SHA-256 Binding Digest
      ↓
HMAC-SHA256 Signature (Constant-Time Verification)
      ↓
Protected Inference Record (JSON)
      ↓
Verification & Replay Registry Audit
      ↓
[PASS]  /  [TAMPER DETECTED]  /  [REPLAY DETECTED]
```

### 1. What is Bound
Each protected inference record binds:
1. **Input Image Integrity**: SHA-256 hash calculated over the exact raw input image bytes.
2. **Model Integrity**: Exact SHA-256 weight digest generated via the integrated Module 2 `ModelHasher`.
3. **Preprocessing Configuration**: Full parameterization (`resolution`, `resize_method`, `normalization`, `channel_ordering`, `confidence_threshold`, `nms_iou_threshold`, `max_detections`, `version`), deterministically serialized and hashed.
4. **Inference Configuration**: Caller-supplied execution and post-processing settings such as inference mode, batch size, thresholds, and runtime options, serialized and hashed separately from preprocessing.
5. **Output Prediction Integrity**: Bounding boxes, class IDs, class names, and confidence scores, canonically sorted and float-normalized.
6. **Freshness & Stream Metadata**: Monotonic sequence number, 128-bit CSPRNG nonce (`secrets.token_hex(16)`), and UTC timestamps.

### 2. How Hashes Work
- **Images & Models**: Chunked streaming SHA-256 hashes (`hashlib.sha256()`) process large inputs with constant memory overhead.
- **Configurations**: Serialized into canonical JSON with strictly sorted keys and compact delimiters (`separators=(',', ':')`), preventing dictionary ordering artifacts from invalidating hashes.
- **Predictions**: Sorted deterministically by `(category_id, category_name, -confidence, box)` with coordinates rounded to 4 decimals and confidence to 6 decimals, ensuring platform float jitter does not break verification.

### 3. How HMAC Authentication Works
- The canonical string includes image hash, model hash, preprocessing hash, optional inference-configuration hash, predictions, timestamp, nonce, and sequence number; it is hashed with SHA-256 to produce `binding_hash_sha256`.
- The binding digest is signed using `hmac.new(secret_key, binding_hash, hashlib.sha256)`.
- Verification utilizes `hmac.compare_digest()` to execute in constant time, preventing timing side-channel attacks.
- **Air-Gapped Key Provisioning**: The secret key is loaded from the constructor, `CV_INFERENCE_SECRET_KEY`, or a local file supplied through `secret_key_file` / `CV_INFERENCE_SECRET_KEY_FILE`. When unspecified, a fallback key is used and explicitly tagged as `DEMO_ONLY_AIRGAPPED_HMAC_SECRET_DO_NOT_USE_IN_PROD`; that fallback is demo-only and must not protect production records.

### 4. How Offline Replay Detection Works
- Handled by `ReplayProtectionRegistry`, a local, air-gapped registry with zero database server requirements. The default registry is process-local memory; supply `ReplayProtectionRegistry(registry_file=...)` or `replay_registry_file=...` to `AssuranceEngine` for restart persistence.
- Tracks `record_id`, `nonce`, `sequence_number`, `timestamp_utc`, and `binding_hash_sha256`, rejects duplicate accepted records/nonces/bindings, and enforces the next sequence number in the configured single stream.
- An inference record that has already been accepted is flagged as `REPLAY DETECTED`, preventing adversaries from intercepting past valid detections and re-submitting them.

### 5. CLI Usage Examples

#### Create a Protected Record (`bind-inference`)
```bash
# Using model file (SHA-256 computed automatically via ModelHasher)
python -m cv_assurance.cli bind-inference \
  --image demo_assets/sample_model.pt \
  --model demo_assets/sample_model.pt \
  --predictions demo_preds.json \
  --output-json protected_record.json
```

#### Verify a Record (`verify-inference`)
```bash
# Verify cryptographic binding and register in replay registry
python -m cv_assurance.cli verify-inference \
  --record-json protected_record.json \
  --image demo_assets/sample_model.pt \
  --model demo_assets/sample_model.pt \
  --registry data/replay_registry.json \
  --register-on-success
```

#### Verify an Inference Chain (`verify-inference-chain`)
```bash
# Verify monotonic sequence ordering and cryptographic validity across a batch
python -m cv_assurance.cli verify-inference-chain \
  --records-json chain_records.json \
  --registry data/replay_registry.json
```

### 6. Detectable Attack Vectors
| Threat Scenario | Tampering Mechanism | Assurance Outcome | Violated Fields |
| :--- | :--- | :---: | :--- |
| **Image Alteration** | Adversarial patch, noise injection, or image swap | `FAIL` | `image_hash_sha256` |
| **Model Substitution** | Trojaned or backdoored weight file substituted | `FAIL` | `model_digest_sha256` |
| **Preprocessing Bypass** | Threshold lowered to induce false alarms | `FAIL` | `preprocessing_config` |
| **Prediction Forgery** | Confidence boosted, box moved, or label changed | `FAIL` | `predictions` |
| **Timestamp Manipulation** | Backdating or future-dating inference records | `FAIL` | `timestamp_utc` |
| **Nonce Reuse Attack** | Submitting multiple inferences under one nonce | `FAIL` | `nonce`, `replay_detected` |
| **Sequence Rollback** | Out-of-order execution or deleted stream items | `FAIL` | `sequence_number` |
| **Signature Forgery** | Altering predictions without private HMAC key | `FAIL` | `binding_hash_sha256`, `hmac_signature` |
| **Replay Attack** | Resubmitting previously captured valid record | `FAIL` | `replay_detected` |

### 7. Limitations
1. **Host-Level Compromise**: Provenance signatures prove that output was generated by the specified model from the specified input image under the recorded configuration. If the inference host itself is compromised at runtime, adversarial code could theoretically sign incorrect results using the local host key.
2. **Key Protection**: The HMAC secret key must be provisioned securely into the air-gapped node (e.g. via hardware HSM or environment variable).
3. **Trusted Time**: Timestamp integrity is cryptographically protected, but the system does not provide a trusted external clock or clock-skew guarantee.
4. **Backward Compatibility**: Records created without `inference_config` remain verifiable using the legacy binding form; new records should supply inference settings explicitly.

---

## 🧪 Verification & Unit Tests

Run the complete unittest suite covering baseline integrity modules, Module 1 attack/regression coverage, governance integration, and dedicated Module 2/Module 3 provenance tests:

```bash
python -m unittest discover -s tests
```

Manual validation status supplied for this repository: **103 tests, 103 passed**, including Module 3B focused validation (**37/37 passed**). Runtime results are reported as manually verified; confidence and environmental semantics remain subject to the limitations above.

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
│   │   ├── benchmark.py           # Controlled Module 2 scenarios & evidence findings
│   │   ├── fingerprint.py         # Behavioral fingerprint & black-box adapter
│   │   ├── hasher.py              # SHA-256 digest & format validation
│   │   ├── model_loader.py        # Controlled demo PyTorch model loader
│   │   └── whitebox_analyzer.py   # White-box parameter and anomaly analyzer
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
├── reports/
│   └── module_2_benchmark.json    # Verified Module 2 benchmark evidence
├── docs/
│   └── MODULE_2_REPORT.md         # Module 2 methodology, results & limitations
├── tests/                         # Unit & Integration tests suite
│   ├── test_all_integrity.py      # Baseline end-to-end assurance tests
│   ├── test_module1_attacks.py    # Module 1 Attack & Benchmark tests
│   └── test_module2_model_integrity.py # Module 2 hashing and white-box tests
├── requirements.txt
└── README.md
```

---

## 📄 License & Air-Gapped Declaration
Developed for Ministry of Defence (MoD) / Indian Army (DGIS) computer vision pipeline assurance challenge. Operated strictly offline with no external network or cloud service dependencies.
