# Hyperledger Fabric Blockchain Trust & Evidence Layer Architecture

[![Hyperledger Fabric](https://img.shields.io/badge/Hyperledger_Fabric-v2.5_LTS-navy?style=for-the-badge&logo=hyperledger)](BLOCKCHAIN_ARCHITECTURE.md)
[![Air-Gapped Ready](https://img.shields.io/badge/Environment-Air--Gapped_%2F_Offline-emerald?style=for-the-badge)](BLOCKCHAIN_ARCHITECTURE.md)
[![Theme](https://img.shields.io/badge/SIH_2026-Blockchain_%26_Cybersecurity-orange?style=for-the-badge)](BLOCKCHAIN_ARCHITECTURE.md)
[![Security Classification](https://img.shields.io/badge/MoD_DGIS-Defense_Restricted-red?style=for-the-badge)](BLOCKCHAIN_ARCHITECTURE.md)

---

## 1. Executive Summary & Problem Context

**Smart India Hackathon 2026 — Problem Statement 26228**
> *"Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines"*
> **Theme**: Blockchain & Cybersecurity
> **Target Environment**: Air-Gapped, Offline Military / Defense Aerial Intelligence Pipeline (Ministry of Defence DGIS / Indian Army)

### The Core Problem in Multi-Contributor Defense CV Pipelines
In tactical surveillance and border reconnaissance, visual intelligence pipelines ingest training data from multiple disparate sensor units, third-party contractors, and allied forces. These pipelines face critical cybersecurity risks:
1. **Training Data Manipulation**: Label flipping, stealthy backdoor trigger injection (BadNets, spectral carriers), and duplicate flooding.
2. **Model Substitution**: Unauthorized swapping of model weights or deployment of backdoored neural networks.
3. **Inference Post-Hoc Tampering**: Alteration of critical detection bounding boxes, confidence scores, or target classifications after inference has concluded.
4. **Replay Attacks**: Resubmitting historical recon frames to disguise ongoing physical ground changes.
5. **Audit Trail Tampering**: Modifying local inspection logs to conceal compromised assets.

While **Modules 1, 2, 3A, and 3B** perform algorithmic computer vision assurance and local cryptographic binding, they require an **independent, immutable, append-only historical proof layer**.

The **Hyperledger Fabric Blockchain Evidence Layer** serves as this decentralized trust backbone.

---

## 2. Why Permissioned Blockchain (Hyperledger Fabric)?

### Why Public Blockchains (Ethereum / Polygon) Are Rejected:
- ❌ **Air-Gapped Violation**: Public blockchains require continuous internet connectivity to public consensus nodes.
- ❌ **Cryptocurrency & Gas Fees**: Military defense operations cannot depend on volatile cryptocurrency gas tokens or public miners.
- ❌ **Data Sovereignty & Classification**: Public ledgers expose transaction metadata to external adversaries.

### Why Hyperledger Fabric is the Authoritative Choice:
- ✅ **100% Offline / Air-Gapped Operation**: Runs entirely on local Docker/host infrastructure within isolated defense enclaves.
- ✅ **Permissioned Consortium**: Every node and transaction submitter possesses an authenticated X.509 cryptographic certificate under a known Membership Service Provider (MSP).
- ✅ **Deterministic Raft Consensus**: Crash-fault tolerant (CFT) leader election without mining or proof-of-work delays.
- ✅ **Zero Gas Fees & High Throughput**: Instant sub-second transaction finality for tactical recon streams.

---

## 3. Off-Chain vs On-Chain Evidence Separation Principle

> [!IMPORTANT]
> **Core Principle: NEVER STORE HEAVY RAW ASSETS ON-CHAIN.**
> Raw aerial imagery, massive neural network weight checkpoints (`.pt` / `.onnx`), and extensive multi-megabyte evaluation reports are strictly maintained **off-chain**. The blockchain acts exclusively as the **cryptographic anchor and verification ledger**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            OFF-CHAIN DATA PLANE                             │
│                                                                             │
│   [ Aerial Frame ]      [ PyTorch Weights ]       [ Assurance Report ]      │
│     (image.jpg)           (sample_model.pt)          (report.json)          │
│          │                        │                        │                │
│          ▼                        ▼                        ▼                │
│     SHA-256 Digest           SHA-256 Digest           SHA-256 Digest        │
│          │                        │                        │                │
│          └────────────────────────┼────────────────────────┘                │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                         ANCHOR COMMIT / VERIFY
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                      ON-CHAIN FABRIC EVIDENCE LEDGER                        │
│                                                                             │
│   • Event ID: EVT-INF-REC-4D703C59                                          │
│   • Image Hash: 48c68ba11e7f...           • Model Hash: fdab8c003aa4...     │
│   • Binding Hash: ed7abe89ef6a...         • Report Hash: 405fc6beba09...    │
│   • Submitting MSP: AssuranceAuthorityMSP • Timestamp: 2026-09-21T13:11:02Z │
│   • Sequence: 101                         • Block #: 16                     │
│   • Tx ID: tx_562bdc4097fcadf33f3e859b8c2de566                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Consortium Identity & Participant Model

| Participant Organization | MSP Identifier | Role & Responsibilities |
| :--- | :--- | :--- |
| **Assurance Authority** | `AssuranceAuthorityMSP` | System operator, master audit certifier, governance quarantine enforcer (Indian Army DGIS). |
| **Contributor Organization** | `ContributorOrgMSP` | Sensor platform providers, UAV reconnaissance squadrons, external dataset suppliers (Contributors A, B, C, D). |
| **Model Authority** | `ModelAuthorityMSP` | Military AI research laboratories, certified model weight issuers. |
| **Independent Auditor** | `AuditorOrgMSP` | Military intelligence compliance inspector, third-party integrity verifier. |

---

## 5. Dual-Layer Trust Verification Model

The system implements a **two-tier defense in depth**:

```
                       INCOMING ARTIFACT FOR VERIFICATION
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
     [ LAYER 1: LOCAL CRYPTOGRAPHY ]           [ LAYER 2: HYPERLEDGER FABRIC ]
     • Recompute SHA-256 digests               • Query immutable ledger anchor
     • Verify HMAC-SHA256 signature            • Compare computed vs registered hash
     • Check Monotonic Sequence Number         • Verify submitting MSP identity
     • Inspect CSPRNG Nonce freshness          • Fetch chronological transaction history
                  │                                         │
                  └────────────────────┬────────────────────┘
                                       ▼
                     DUAL-LAYER VERDICT & DISPOSITION
           ┌───────────────────────────┴───────────────────────────┐
           ▼                                                       ▼
      MATCH (Both Layers)                              MISMATCH (Either Layer)
    [ TRUST_VERIFIED / ACCEPT ]                    [ TAMPER_DETECTED / QUARANTINE ]
```

---

## 6. Smart Contract Specification (`AssuranceContract`)

The chaincode (`blockchain/chaincode/assurance/`) exposes 10 transactional and query methods:

1. **`registerContributor(contributorId, orgMsp, metadataJson)`**: Binds a contributor identifier to an authorized MSP on-chain.
2. **`registerDataset(datasetId, version, canonicalManifestHash, contributorId, sampleCount)`**: Anchors training dataset manifest SHA-256 digest.
3. **`registerModel(modelId, version, trustedDigestSha256, authorOrg)`**: Anchors reference neural network weight SHA-256 digest.
4. **`recordInference(recordId, imageHash, modelDigest, prepHash, bindingHash, nonce, seq, hmacRef)`**: Commits ProtectedInferenceRecord cryptographic binding hash.
5. **`recordAssuranceEvent(eventJson)`**: Generic assurance telemetry anchor for distribution shift, backdoors, and duplicate flooding.
6. **`recordReport(reportId, reportHash, auditRootHash, disposition)`**: Anchors off-chain evaluation report SHA-256 and audit chain root.
7. **`verifyArtifact(assetId, expectedHash)`**: Compares queried hash against immutable ledger anchor.
8. **`getEvent(eventId)`**: Retrieves single event with transaction ID and block height.
9. **`getAssetHistory(assetId)`**: Returns complete chronological audit history for an asset.
10. **`initLedger()`**: Initializes consortium genesis anchor block.

---

## 7. Attack Scenarios & Mathematical Proof of Detection

### Scenario A: Clean Pipeline Execution
- Contributor A registers dataset manifest & model weights on Fabric.
- Inference executed; Module 3A binds image + model + predictions + nonce + sequence into HMAC signature.
- Binding hash committed to Fabric ledger (Tx ID generated).
- Dual verification passes both Layer 1 (HMAC) and Layer 2 (Fabric Ledger Anchor).
- **Result**: `TRUST_VERIFIED` -> `ACCEPT`.

### Scenario B: Inference Post-Hoc Tampering Attack
- Adversary modifies detection output (e.g. changes `car (0.94)` to `pedestrian (0.99)` or shifts coordinates).
- Recomputed binding hash changes from `H_original` to `H_tampered`.
- Layer 1 local HMAC verification fails (signature invalid).
- Layer 2 blockchain verification queries Fabric: registered anchor is `H_original` $\neq$ `H_tampered`.
- **Result**: `TAMPER_DETECTED` -> `QUARANTINE`.

### Scenario C: Replay Attack Mitigation
- Adversary captures historical authenticated frame and re-submits it at $T+1$ to mask ground movement.
- Module 3A replay registry detects duplicate nonce and non-monotonic sequence number.
- Query to Fabric ledger retrieves original transaction ID and timestamp, proving the record was committed in a prior validation cycle.
- **Result**: `REPLAY_DETECTED` -> `QUARANTINE`.

### Scenario D: Model Weight Substitution Attack
- Adversary or compromised host swaps certified model weights with a backdoored checkpoint.
- Module 2 `ModelHasher` computes SHA-256: `SHA(weights_active)`.
- Verifier queries Fabric: registered digest is `SHA(weights_trusted)`.
- `SHA(weights_active) != SHA(weights_trusted)`.
- **Result**: `MODEL_SUBSTITUTED` -> `QUARANTINE`.

---

## 8. Merkle Tree Batching for High-Throughput Streams

For high-frequency UAV aerial surveillance (e.g. 100 frames/sec), anchoring individual transactions would congest ledger IO. The `MerkleTree` engine (`blockchain/client/merkle.py`) batches $N$ inference records into a single root anchor:

$$\text{Root} = \text{MerkleRoot}(H_1, H_2, \dots, H_N)$$

- **On-Chain**: 1 transaction storing `batch_id`, `record_count`, `first_sequence`, `last_sequence`, and `merkle_root`.
- **Off-Chain**: Lightweight $O(\log_2 N)$ Merkle inclusion proofs allow any independent field terminal to verify an individual frame without querying raw images.

---

## 9. Air-Gapped Deployment & Usage Guide

### Method 1: Interactive Live CLI Demonstration
Run the deterministic 4-scenario demonstration:
```powershell
& "C:\Users\Gaargi L\miniconda3\envs\sih26\python.exe" blockchain/scripts/demo.py
```

### Method 2: Web Dashboard Access
1. Start Backend Server:
   ```powershell
   & "C:\Users\Gaargi L\miniconda3\envs\sih26\python.exe" app/server.py
   ```
2. Open Browser at **`http://localhost:5173/`** (or `http://127.0.0.1:8000/`).
3. Navigate to the **Trust Ledger** tab in the sidebar to view live block telemetry, dual verification status, and execute interactive attack simulations.

### Method 3: Dockerized Fabric Network Management
```powershell
# Start local Fabric containers
.\blockchain\scripts\start.ps1

# Stop network
.\blockchain\scripts\stop.ps1

# Reset ledger state
.\blockchain\scripts\reset.ps1
```

---

## 10. Security Boundaries & Clear Limitations

To maintain defense rigor, the following boundaries are formally defined:
- **What Blockchain Guarantees**: Immutable historical proof, non-repudiation of contributor submissions, post-hoc tampering detection, and multi-organization audit transparency.
- **What Blockchain Does NOT Guarantee**:
  * An uncompromised image *before* sensor capture (this is assured by Module 1 anomaly detection & Module 3B shift testing).
  * Algorithmic safety of neural network architecture (this is assured by Module 2 white-box analysis & backdoor probing).
  * Live runtime memory protection during active GPU inference (requires host OS trusted execution enclaves / TPM).
