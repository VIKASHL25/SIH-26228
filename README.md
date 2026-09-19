# Trustworthy Computer Vision Integrity Assurance Framework

[![MoD DGIS](https://img.shields.io/badge/Ministry_of_Defence-Indian_Army_DGIS-navy?style=for-the-badge)](file:///c:/Users/Lenovo/OneDrive/Desktop/SIH-26228/README.md)
[![Air-Gapped Ready](https://img.shields.io/badge/Environment-Air--Gapped_%2F_Offline-emerald?style=for-the-badge)](file:///c:/Users/Lenovo/OneDrive/Desktop/SIH-26228/README.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge)](file:///c:/Users/Lenovo/OneDrive/Desktop/SIH-26228/README.md)

A model-agnostic, offline-capable computer vision integrity assurance framework that evaluates training datasets (COCO/YOLO), trained models (PyTorch/ONNX), environmental distribution shifts, and protected inference outputs in multi-contributor pipelines.

---

## 🛡️ Key Capabilities

### 1. Training-Data Integrity (`cv_assurance.data`)
- **Dataset Ingestion**: Support for **COCO** (`annotations.json`) and **YOLO** (`images/`, `labels/*.txt`, `data.yaml`).
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

## 🚀 Quick Start & Installation

### 1. Requirements
Ensure Python 3.10+ is installed. Dependencies run 100% offline without external cloud APIs.

```bash
pip install -r requirements.txt
```

### 2. Generate Demo Assets & Run Evaluation CLI
Generate synthetic evaluation datasets and run full assurance analysis:

```bash
# Generate synthetic dataset with poisoned samples, label flips, duplicates & shifts
python demo_assets/generate_demo_data.py

# Run CLI analysis
python -m cv_assurance.cli analyze --dataset demo_assets/eval_coco/annotations.json --model demo_assets/sample_model.pt --ref-dataset demo_assets/reference_coco/annotations.json --output-json report.json
```

### 3. Launch Interactive Web Dashboard
Start the local dashboard server:

```bash
python app/server.py
```
Open `http://127.0.0.1:8000` in your web browser.

---

## 🧪 Verification & Unit Tests

Run the test suite covering all 5 core capabilities end-to-end:

```bash
python -m unittest discover -s tests
```

---

## 📁 Repository Architecture

```
SIH-26228/
├── cv_assurance/                  # Core Python Framework Package
│   ├── __init__.py
│   ├── data/                      # Dataset Ingestion & Data Integrity
│   │   ├── ingester.py            # COCO & YOLO format dataset loader
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
├── demo_assets/                   # Synthetic dataset & reference model generator
├── app/                           # Glassmorphic Web Dashboard & FastAPI server
│   ├── server.py
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/                         # Unit tests suite
├── requirements.txt
└── README.md
```

---

## 📄 License & Air-Gapped Declaration
Developed for Ministry of Defence (MoD) / Indian Army (DGIS) computer vision pipeline assurance challenge. Operated strictly offline with no external network or cloud service dependencies.
