# Module 3B — Distribution Shift, Governance, Tamper-Evident Audit Trail & End-to-End Integration

## 1. Executive Summary & Problem Statement Alignment

Under **SIH Problem Statement 26228** (*Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines*), **Module 3B** delivers the final critical pillars of integrity assurance:
1. **Environmental Distribution Shift Detection**: Detects material deviations from a declared reference baseline across image-derived terrain, illumination, sensor-noise, and seasonal/acquisition proxies. The classifier distinguishes operational drift from suspicious manipulation only under the implemented evidence rules; it does not provide semantic terrain/season classification.
2. **Tamper-Evident Cryptographic Audit Trail**: An append-only, SHA-256 hash-chained audit log guaranteeing mathematical tamper-evidence for all pipeline lifecycle events without cloud or blockchain overhead.
3. **End-to-End Governance Engine**: Orchestrates training-data integrity (Module 1), model integrity (Module 2), inference provenance (Module 3A), and distribution shift (Module 3B) into unified assurance findings, health scoring, and actionable policy dispositions (`ACCEPT`, `REVIEW`, `QUARANTINE`).

---

## 2. Architecture & Pipeline Flow

```
   [ Training Dataset ]        [ Vision Model ]         [ Inference Record ]       [ Reference Baseline ]
            |                         |                          |                           |
            v                         v                          v                           v
     +--------------+          +--------------+           +--------------+            +--------------+
     |   Module 1   |          |   Module 2   |           |  Module 3A   |            |  Module 3B   |
     | Data Quality |          | Model Digest |           | Cryptographic|            | Distribution |
     | & Backdoors  |          | & Parameters |           | Provenance   |            | Shift Tests  |
     +-------+------+          +-------+------+           +-------+------+            +-------+------+
             |                         |                          |                           |
             +-------------------------+------------+-------------+---------------------------+
                                                    |
                                                    v
                                  +------------------------------------+
                                  |     Module 3B AssuranceEngine      |
                                  |   Evidence Fusion & Risk Scoring   |
                                  +-----------------+------------------+
                                                    |
                                                    +---------------------------------------+
                                                    |                                       |
                                                    v                                       v
                                      +---------------------------+           +---------------------------+
                                      |   AssuranceReport (JSON)  |           | Tamper-Evident Audit Chain|
                                      | - Disposition (ACCEPT/    |           | - Genesis-linked SHA-256  |
                                      |   REVIEW/QUARANTINE)      |           | - Sequential Event Ledger |
                                      | - Health Score (0-100)    |           | - Independent Verification|
                                      | - Structured Findings     |           +---------------------------+
                                      +---------------------------+
```

---

## 3. Component Details

### A. Environmental Distribution Shift Detector (`cv_assurance/shift/`)

* **Dimensions Monitored**:
  1. **Terrain**: Texture contrast (GLCM-inspired local variance) and color histogram energy.
  2. **Illumination**: Mean pixel luminance, HSV value distributions, and overexposure/underexposure ratios.
  3. **Sensor**: Noise floor standard deviation via high-pass Laplacian filtering and estimated PSNR.
  4. **Season / Acquisition**: Green vegetation index (GVI: $(2G - R - B) / (2G + R + B)$) and chromatic hue/saturation shifts.
  These are image proxies. Dataset metadata is not fabricated when terrain, season, or sensor labels are absent.

* **Statistical Rigor**:
  - Computes two-sample Kolmogorov-Smirnov (KS) test ($D_{\text{KS}}$, $p$-value) and Wasserstein (Earth Mover's) Distance ($W_1$) per domain.
  - Flags material shifts based on statistical thresholds ($p < 0.10$ or significant Wasserstein displacement).

* **Intelligent Shift Discrimination**:
  - **`OPERATIONAL_DRIFT`**: Observed across coherent natural dimensions (e.g., lower illumination and winter vegetation indices).
  - **`SUSPICIOUS_MANIPULATION`**: Abrupt, isolated sensor noise floor or high-frequency spectral dislocation in the absence of natural environmental transitions (indicative of sensor injection or adversarial noise).
  - **`NO_SHIFT`**: Target evaluation dataset aligns closely with the declared reference environmental baseline.
  - Confidence is a bounded evidence-derived heuristic incorporating sample sufficiency and observed statistics; it is not a calibrated probability. Empty or insufficient inputs return unavailable confidence rather than `1.0`.

### B. Tamper-Evident Cryptographic Audit Chain (`cv_assurance/governance/audit_chain.py`)

* **Cryptographic Linking**:
  $$\text{Hash}_k = \text{SHA-256}\left( \text{CanonicalJSON}\left( \text{Event}_k \mathbin{\Vert} \text{Hash}_{k-1} \right) \right)$$
  - Genesis event links to fixed `0000...0000` ($64 \times 0$).
  - Canonical serialization enforces sorted keys and tight separators (`','`, `':'`) to prevent whitespace manipulation.
* **Tamper Localization**:
  - `verify_chain()` walks from Genesis to the chain head, re-computing digests.
  - Returns `(is_valid, reason, broken_index)` identifying the exact event index and field where tampering occurred.
* **Offline Operation**:
  - Full cryptographic integrity without external blockchain gas fees or cloud key management dependencies.

### C. Governance Engine & Assurance Report Schema (`cv_assurance/governance/`)

* **`AssuranceEngine.run_full_assurance()`**:
  - Ingests dataset, model weights, reference baseline, and inference provenance records.
  - Executes comprehensive scan passes across all four SIH modules.
  - Derives an overall health score (0.0 to 100.0) with penalty weighting for critical vulnerabilities.
  - Assigns actionable disposition:
    - **`ACCEPT`**: No supported anomaly detected under the tested evidence.
    - **`REVIEW`**: Moderate operational drift, near-duplicate warnings, or low-confidence anomalies.
    - **`QUARANTINE`**: High-risk backdoors, model hash mismatches, or high-risk compromised contributors.
  - Embeds the cryptographic audit trail hash directly into the signed report.

---

## 4. CLI Interface Reference

```bash
# 1. Full End-to-End Governance Analysis
python -m cv_assurance.cli analyze \
    --dataset data/dataset_manifest.json \
    --model models/detector.pt \
    --ref-dataset data/reference/manifest.json \
    --audit-chain-json audit_trail.json \
    --output-json report.json

# 2. Verify Tamper-Evident Audit Chain Log
python -m cv_assurance.cli verify-audit-chain \
    --chain-file audit_trail.json

# 3. Verify Inference Record Cryptographic Binding (Module 3A)
python -m cv_assurance.cli verify-inference \
    --record-json inference_record.json

# 4. Verify Monotonic Inference Chain & Nonce Replay (Module 3A)
python -m cv_assurance.cli verify-inference-chain \
    --records-json inference_chain.json
```

---

## 5. Verification & Test Coverage Summary

The Module 3B test suite (`tests/test_module3b_shift_governance.py`) contains **36 rigorous tests** spanning five test suites:
- **Part A (`TestDistributionShiftDetector`)**: Validates `NO_SHIFT`, `OPERATIONAL_DRIFT`, `SUSPICIOUS_MANIPULATION`, Wasserstein distance metrics, and edge cases. (8 tests)
- **Part B (`TestTamperEvidentAuditChain`)**: Validates genesis hashing, sequential linking, append operations, unbroken chain verification, tamper detection, and JSON persistence. (8 tests)
- **Part C (`TestGovernanceEngineIntegration`)**: Validates end-to-end assurance report generation, health scoring, audit chain embedding, and disposition policy. (8 tests)
- **Part D (`TestReportSchema`)**: Validates Pydantic schema constraints, severity enums, and category matching. (4 tests)
- **Part E (`TestEnvironmentalFeatureExtractor`)**: Validates physical metric extraction from computer vision images (brightness, Laplacian blur variance, texture contrast). (4 tests)

**Validation status in the current checkout**:
```text
Runtime validation requires the repository dependencies (including pydantic, numpy, cv2, and scipy).
The current environment does not provide them; do not claim the suite passes until rerun in a provisioned environment.
```
