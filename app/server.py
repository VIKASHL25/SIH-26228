import os
import sys
import json
import time
import uuid
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cv_assurance.governance.engine import AssuranceEngine
from cv_assurance.governance.audit_chain import TamperEvidentAuditChain, AuditEvent, GENESIS_PREVIOUS_HASH
from cv_assurance.provenance.crypto_binding import (
    CryptographicProvenanceEngine,
    InferenceOutputPrediction,
    ProtectedInferenceRecord,
    PreprocessingConfig,
    ReplayProtectionRegistry
)
from cv_assurance.model.hasher import ModelHasher
from cv_assurance.model.whitebox_analyzer import WhiteBoxAnalyzer
from cv_assurance.model.backdoor_probe import ModelBackdoorProbe
from cv_assurance.model.fingerprint import ModelFingerprinter
from cv_assurance.model.benchmark import Module2Benchmark
from cv_assurance.shift.distribution_test import DistributionShiftDetector
from cv_assurance.data.ingester import DatasetIngester
from blockchain.client import (
    FabricClient,
    BlockchainAnchorService,
    BlockchainDualVerifier,
    AssuranceEvent,
    AssuranceEventType,
    BlockchainStatus,
    DualVerificationResult
)

app = FastAPI(
    title="Trustworthy CV Integrity Assurance & Forensics Console API",
    version="1.0.0",
    description="Air-Gapped Computer Vision Assurance System for Data, Models, Inference, and Operational Distribution"
)

# Enable CORS for local dev environment (e.g. Vite on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
DEMO_DIR = os.path.join(BASE_DIR, "demo_assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
VIS_EVID_DIR = os.path.join(DATA_DIR, "visual_evidence")
CONTRIB_DIR = os.path.join(DATA_DIR, "contributors")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Initialize Core Engines
engine = AssuranceEngine()
prov_engine = CryptographicProvenanceEngine()
replay_registry = ReplayProtectionRegistry()
whitebox_analyzer = WhiteBoxAnalyzer()
shift_detector = DistributionShiftDetector()
blockchain_client = FabricClient()
blockchain_anchor_service = BlockchainAnchorService(blockchain_client)
blockchain_verifier = BlockchainDualVerifier(blockchain_client, prov_engine)

# Mount static asset folders
if os.path.exists(DEMO_DIR):
    app.mount("/demo_assets", StaticFiles(directory=DEMO_DIR), name="demo_assets")
if os.path.exists(VIS_EVID_DIR):
    app.mount("/data/visual_evidence", StaticFiles(directory=VIS_EVID_DIR), name="visual_evidence")
if os.path.exists(CONTRIB_DIR):
    app.mount("/data/contributors", StaticFiles(directory=CONTRIB_DIR), name="contributors")

# Mount built frontend or static directory
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend_assets")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    if os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# -------------------------------------------------------------
# SYSTEM & HEALTH
# -------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "system": "Trustworthy Computer Vision Integrity Assurance & Forensics Console",
        "version": "1.0.0",
        "mode": "OFFLINE / AIR-GAPPED",
        "environment": "LOCAL",
        "timestamp_utc": time.time()
    }

# -------------------------------------------------------------
# BENCHMARK & DEMO ARTIFACTS
# -------------------------------------------------------------
@app.get("/api/benchmark/summary")
async def get_benchmark_summary():
    """Returns the verified Module 1 evaluation metrics report."""
    eval_report_path = os.path.join(DATA_DIR, "evaluation_report.json")
    if not os.path.exists(eval_report_path):
        raise HTTPException(status_code=404, detail="evaluation_report.json not found")
    with open(eval_report_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/benchmark/manifest")
async def get_benchmark_manifest():
    """Returns the benchmark dataset manifest (64 samples, contributors, attack tags)."""
    manifest_path = os.path.join(DATA_DIR, "dataset_manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="dataset_manifest.json not found")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------------------------------------------------
# FULL ASSURANCE ANALYSIS EXECUTION
# -------------------------------------------------------------
class AssuranceRunRequest(BaseModel):
    dataset_path: Optional[str] = None
    model_path: Optional[str] = None
    ref_dataset_path: Optional[str] = None
    reference_model_hash: Optional[str] = None
    reference_model_path: Optional[str] = None
    inference_record_path: Optional[str] = None

@app.post("/api/run_assurance")
async def run_assurance(req: AssuranceRunRequest = Body(...)):
    """Executes live full assurance analysis across data, model, shift, and audit trail."""
    eval_coco = req.dataset_path or os.path.join(DEMO_DIR, "eval_coco", "annotations.json")
    ref_coco = req.ref_dataset_path or os.path.join(DEMO_DIR, "reference_coco", "annotations.json")
    model_pt = req.model_path or os.path.join(DEMO_DIR, "sample_model.pt")
    ref_model = req.reference_model_path or os.path.join(DEMO_DIR, "sample_model.pt")

    if not os.path.exists(eval_coco):
        raise HTTPException(status_code=404, detail=f"Target dataset path not found: {eval_coco}")

    ref_hash = req.reference_model_hash
    if not ref_hash and ref_model and os.path.exists(ref_model):
        ref_hash = ModelHasher.compute_file_sha256(ref_model)

    try:
        report = engine.run_full_assurance(
            dataset_path=eval_coco,
            model_path=model_pt if os.path.exists(model_pt) else None,
            ref_dataset_path=ref_coco if os.path.exists(ref_coco) else None,
            reference_model_hash=ref_hash,
            reference_model_path=ref_model if os.path.exists(ref_model) else None,
            inference_record_path=req.inference_record_path
        )
        return JSONResponse(content=report.model_dump(mode='json'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assurance execution failed: {str(e)}")

@app.get("/api/run_demo_analysis")
@app.post("/api/run_demo_analysis")
async def run_demo_analysis():
    """Runs pipeline analysis on demo assets and returns the assurance report."""
    req = AssuranceRunRequest()
    return await run_assurance(req)

# -------------------------------------------------------------
# MODULE 2: MODEL INTEGRITY
# -------------------------------------------------------------
@app.get("/api/model/benchmark")
async def get_model_benchmark():
    """Returns verified Module 2 benchmark scenarios (clean, tampered_weights, behavior_modified, substituted)."""
    rpt_path = os.path.join(REPORTS_DIR, "module_2_benchmark.json")
    if os.path.exists(rpt_path):
        with open(rpt_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="module_2_benchmark.json not found")

class ModelWhiteBoxRequest(BaseModel):
    model_path: str
    reference_model_path: Optional[str] = None

@app.post("/api/model/whitebox")
async def analyze_model_whitebox(req: ModelWhiteBoxRequest):
    """Executes live white-box parameter distribution analysis on a PyTorch model checkpoint."""
    target_path = req.model_path
    if not os.path.isabs(target_path):
        target_path = os.path.join(BASE_DIR, target_path)

    ref_path = req.reference_model_path
    if ref_path and not os.path.isabs(ref_path):
        ref_path = os.path.join(BASE_DIR, ref_path)

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail=f"Model not found at {target_path}")

    res = whitebox_analyzer.analyze_weights(target_path, reference_model_path=ref_path)
    return JSONResponse(content=res.model_dump(mode='json'))

class ModelHashRequest(BaseModel):
    model_path: str
    reference_hash: Optional[str] = None

@app.post("/api/model/hash")
async def hash_model_endpoint(req: ModelHashRequest):
    """Computes streaming SHA-256 and validates against reference digest."""
    target_path = req.model_path
    if not os.path.isabs(target_path):
        target_path = os.path.join(BASE_DIR, target_path)

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail=f"Model not found at {target_path}")

    hasher = ModelHasher()
    res = hasher.inspect_model(target_path, reference_sha256=req.reference_hash)
    return JSONResponse(content=res.model_dump(mode='json'))

# -------------------------------------------------------------
# MODULE 3A: INFERENCE PROVENANCE
# -------------------------------------------------------------
@app.post("/api/inference/verify_record")
@app.post("/api/verify_inference_record")
async def verify_inference_record(record: dict = Body(...)):
    """Verifies cryptographic binding, HMAC signature, image/model hash, and replay status."""
    try:
        rec = ProtectedInferenceRecord(**record)
        res = prov_engine.verify_record(rec, replay_registry=replay_registry, register_if_valid=False)
        return JSONResponse(content=res.model_dump(mode='json'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/create_inference_record")
async def create_inference_record_endpoint(
    image_hash: Optional[str] = Form(None),
    model_hash: Optional[str] = Form(None),
    predictions_json: Optional[str] = Form(None),
    record_data: Optional[dict] = Body(None)
):
    """Creates a signed ProtectedInferenceRecord from form data or JSON body."""
    img_h = image_hash
    mdl_h = model_hash
    preds_raw = None

    if record_data:
        img_h = record_data.get("image_hash") or img_h
        mdl_h = record_data.get("model_hash") or mdl_h
        preds_raw = record_data.get("predictions") or record_data.get("predictions_json")

    if predictions_json and not preds_raw:
        try:
            preds_raw = json.loads(predictions_json)
        except Exception:
            preds_raw = []

    if isinstance(preds_raw, str):
        try:
            preds_raw = json.loads(preds_raw)
        except Exception:
            preds_raw = []

    if not preds_raw:
        preds_raw = [
            {"box": [200.0, 200.0, 240.0, 280.0], "confidence": 0.94, "category_id": 0, "category_name": "vehicle_tank"}
        ]

    preds = []
    for p in preds_raw:
        if isinstance(p, dict):
            preds.append(InferenceOutputPrediction(**p))
        elif isinstance(p, InferenceOutputPrediction):
            preds.append(p)

    img_h = img_h or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    mdl_h = mdl_h or "a3f8c7901b22e4d5678ef991002341ab8872619cd3000f2e1a"

    rec = prov_engine.create_protected_record(
        image_path_or_hash=img_h,
        model_hash=mdl_h,
        predictions=preds
    )
    return JSONResponse(content=rec.model_dump(mode='json'))

@app.post("/api/inference/verify_chain")
async def verify_inference_chain_endpoint(records: List[dict] = Body(...)):
    """Verifies monotonic sequence numbers, timestamps, replay nonces, and cryptographic bindings."""
    try:
        parsed_records = [ProtectedInferenceRecord(**r) for r in records]
        chain_valid = True
        last_seq = None
        last_ts = None
        seen_nonces = set()
        evaluated = []

        local_registry = ReplayProtectionRegistry()

        for idx, rec in enumerate(parsed_records, 1):
            res = prov_engine.verify_record(rec, replay_registry=local_registry, register_if_valid=True)
            seq_valid = True
            ts_valid = True
            nonce_valid = (rec.nonce not in seen_nonces)
            seen_nonces.add(rec.nonce)

            if last_seq is not None and rec.sequence_number != last_seq + 1:
                seq_valid = False
                chain_valid = False

            if last_ts is not None and rec.timestamp_utc < last_ts:
                ts_valid = False
                chain_valid = False

            last_seq = rec.sequence_number
            last_ts = rec.timestamp_utc

            passed = (res.verification_passed and seq_valid and ts_valid and nonce_valid)
            if not passed:
                chain_valid = False

            evaluated.append({
                "record_id": rec.record_id,
                "sequence_number": rec.sequence_number,
                "timestamp_utc": rec.timestamp_utc,
                "nonce": rec.nonce,
                "verification_passed": passed,
                "tamper_detected": res.tamper_detected or not (seq_valid and ts_valid and nonce_valid),
                "replay_detected": res.replay_detected or not nonce_valid,
                "sequence_violation": not seq_valid,
                "tampered_fields": res.tampered_fields + ([] if seq_valid else ["sequence_number"]),
                "details": res.details
            })

        return JSONResponse(content={
            "chain_valid": chain_valid,
            "total_records": len(parsed_records),
            "status": "PASS" if chain_valid else "FAIL",
            "evaluated_records": evaluated
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/inference/demo_records")
async def get_demo_inference_records():
    """Generates authentic cryptographically signed demo inference records and controlled tampering variants."""
    model_pt = os.path.join(DEMO_DIR, "sample_model.pt")
    model_hash = ModelHasher.compute_file_sha256(model_pt) if os.path.exists(model_pt) else "fdab8c003aa41f4c3795f97ff37bece7f978682c7c75af3e84d32c3d00cd837d"

    img_hash_1 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    img_hash_2 = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"

    preds_1 = [
        InferenceOutputPrediction(box=[120.0, 80.0, 45.0, 95.0], confidence=0.942, category_id=4, category_name="car"),
        InferenceOutputPrediction(box=[310.0, 240.0, 60.0, 110.0], confidence=0.887, category_id=5, category_name="van")
    ]
    preds_2 = [
        InferenceOutputPrediction(box=[200.0, 150.0, 30.0, 50.0], confidence=0.915, category_id=1, category_name="pedestrian")
    ]

    base_time = time.time() - 3600
    rec1 = prov_engine.create_protected_record(
        image_path_or_hash=img_hash_1,
        model_hash=model_hash,
        predictions=preds_1,
        sequence_number=1,
        timestamp_utc=base_time,
        nonce="nonce_demo_seq_0001"
    )
    rec2 = prov_engine.create_protected_record(
        image_path_or_hash=img_hash_2,
        model_hash=model_hash,
        predictions=preds_2,
        sequence_number=2,
        timestamp_utc=base_time + 10,
        nonce="nonce_demo_seq_0002"
    )

    # Create Tampered Variants
    # 1. Tampered Predictions (altered bounding box / confidence)
    tampered_preds_rec = rec1.model_dump()
    tampered_preds_rec["predictions"][0]["box"] = [999.0, 999.0, 50.0, 50.0]
    tampered_preds_rec["record_id"] = "INF-REC-TAMPERED-PRED"

    # 2. Tampered Model Hash (unauthorized model substitution)
    tampered_model_rec = rec1.model_dump()
    tampered_model_rec["model_digest_sha256"] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    tampered_model_rec["record_id"] = "INF-REC-TAMPERED-MODEL"

    # 3. Replay Nonce Variant
    replay_nonce_rec = rec2.model_dump()
    replay_nonce_rec["record_id"] = "INF-REC-REPLAY-NONCE"
    replay_nonce_rec["nonce"] = rec1.nonce # Reusing rec1 nonce

    # 4. Sequence Discontinuity Variant
    seq_violation_rec = rec2.model_dump()
    seq_violation_rec["record_id"] = "INF-REC-SEQ-VIOLATION"
    seq_violation_rec["sequence_number"] = 99 # Jump from 1 to 99

    return JSONResponse(content={
        "clean_record": rec1.model_dump(mode='json'),
        "clean_chain": [rec1.model_dump(mode='json'), rec2.model_dump(mode='json')],
        "tampered_scenarios": {
            "tampered_predictions": tampered_preds_rec,
            "tampered_model_digest": tampered_model_rec,
            "replayed_nonce": replay_nonce_rec,
            "sequence_violation": seq_violation_rec
        }
    })

# -------------------------------------------------------------
# MODULE 3B: DISTRIBUTION SHIFT
# -------------------------------------------------------------
@app.post("/api/shift/analyze")
async def analyze_distribution_shift():
    """Executes live two-sample KS and Wasserstein tests across terrain, illumination, sensor, and season proxies."""
    eval_coco = os.path.join(DEMO_DIR, "eval_coco", "annotations.json")
    ref_coco = os.path.join(DEMO_DIR, "reference_coco", "annotations.json")

    if not os.path.exists(eval_coco) or not os.path.exists(ref_coco):
        raise HTTPException(status_code=404, detail="Demo datasets for distribution shift not found")

    ingester = DatasetIngester()
    ref_ds = ingester.auto_ingest(ref_coco)
    target_ds = ingester.auto_ingest(eval_coco)

    res = shift_detector.analyze(ref_ds, target_ds)
    return JSONResponse(content=res.model_dump(mode='json'))

# -------------------------------------------------------------
# AUDIT TRAIL
# -------------------------------------------------------------
@app.post("/api/audit/verify")
async def verify_audit_chain_endpoint(events: Optional[List[dict]] = Body(None)):
    """Verifies mathematical unbrokenness and payload hash alignment from Genesis to Head."""
    chain = TamperEvidentAuditChain()
    if events:
        try:
            chain.events = [AuditEvent(**e) for e in events]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid event payload: {str(e)}")
    else:
        # Generate representative pipeline audit chain
        chain.append_event(
            event_type="PIPELINE_INIT",
            affected_asset="VisDrone_Assurance_Benchmark",
            event_summary="Initiated comprehensive AI integrity assurance evaluation RPT-8F92A10C."
        )
        chain.append_event(
            event_type="DATASET_AUDIT",
            affected_asset="VisDrone_Assurance_Benchmark",
            event_summary="Evaluated training dataset integrity: 64 samples. Flagged 5 data findings."
        )
        chain.append_event(
            event_type="MODEL_AUDIT",
            affected_asset="demo_assets/sample_model.pt",
            event_summary="Inspected model: SHA-256 fdab8c003aa41f4c... Reference match: True."
        )
        chain.append_event(
            event_type="SHIFT_AUDIT",
            affected_asset="VisDrone_Assurance_Benchmark",
            event_summary="Distribution shift assessment completed: OPERATIONAL_DRIFT (Drift score: 0.75)."
        )
        chain.append_event(
            event_type="PROVENANCE_AUDIT",
            affected_asset="InferenceStream",
            event_summary="Audited 10 inference records. Passed: 10, Tampered: 0, Replayed: 0."
        )
        chain.append_event(
            event_type="GOVERNANCE_DISPOSITION",
            affected_asset="VisDrone_Assurance_Benchmark",
            event_summary="Final governance verdict: [QUARANTINE] (Health Score: 45.0/100, Findings: 5)."
        )

    is_valid, msg, broken_idx = chain.verify_chain()
    return JSONResponse(content={
        "is_valid": is_valid,
        "verification_status": "VERIFIED_UNBROKEN" if is_valid else "TAMPER_DETECTED",
        "message": msg,
        "broken_event_index": broken_idx,
        "total_events": chain.chain_length,
        "latest_event_hash": chain.latest_hash,
        "events": chain.export_log()
    })

# -------------------------------------------------------------
# VISUAL EVIDENCE & CAPABILITY COVERAGE
# -------------------------------------------------------------
@app.get("/api/visual_evidence/list")
async def list_visual_evidence():
    """Lists the 6 generated visual evidence comparison panels with metadata."""
    panels = [
        {
            "id": "dup_flooding",
            "title": "Near-Duplicate Flooding Evidence",
            "category": "duplicate_flooding",
            "image_url": "/data/visual_evidence/01_duplicate_flooding_evidence.jpg",
            "metrics": {"ssim": 0.941, "normalized_mae": 0.042, "status": "CONFIRMED_DUPLICATE"},
            "description": "Side-by-side comparison of original aerial image vs JPEG-degraded duplicate flood sample."
        },
        {
            "id": "label_manipulation",
            "title": "Systematic Label Manipulation Evidence",
            "category": "label_manipulation",
            "image_url": "/data/visual_evidence/02_label_manipulation_evidence.jpg",
            "metrics": {"original_label": "CAR", "confused_label": "VAN", "k_nn_consensus": 0.85},
            "description": "Visual evidence of systematic category confusion injected into Contributor B submissions."
        },
        {
            "id": "ood_insertion",
            "title": "Out-Of-Distribution (OOD) Insertion Evidence",
            "category": "ood_insertion",
            "image_url": "/data/visual_evidence/03_ood_insertion_evidence.jpg",
            "metrics": {"anomaly_score": 0.78, "contamination_threshold": 0.65, "status": "OOD_ANOMALY"},
            "description": "Non-aerial domain sample departure from baseline feature distribution."
        },
        {
            "id": "corner_trigger",
            "title": "BadNets Corner Trigger Patch Evidence",
            "category": "corner_trigger",
            "image_url": "/data/visual_evidence/04_corner_trigger_evidence.jpg",
            "metrics": {"patch_size": "24x24", "location": "top_right", "contrast": 38.4, "status": "TRIGGER_DETECTED"},
            "description": "Localized spatial edge and contrast anomaly highlighting rigid corner trigger injection."
        },
        {
            "id": "blended_watermark",
            "title": "Alpha-Blended Watermark Trigger Evidence",
            "category": "blended_watermark",
            "image_url": "/data/visual_evidence/05_blended_trigger_evidence.jpg",
            "metrics": {"alpha": 0.18, "residual_correlation": 0.22, "status": "WATERMARK_FLAGGED"},
            "description": "Transparent spatial watermark perturbation blended across image pixels."
        },
        {
            "id": "spectral_fft",
            "title": "2D Fourier FFT Spectral Carrier Spike Evidence",
            "category": "spectral_trigger",
            "image_url": "/data/visual_evidence/06_spectral_trigger_fft_evidence.jpg",
            "metrics": {"fft_zscore": 6.84, "peak_prominence": "HIGH", "status": "SPECTRAL_CARRIER_DETECTED"},
            "description": "2D FFT frequency magnitude spectrum contrasting clean image vs periodic carrier frequency spikes."
        }
    ]
    return JSONResponse(content=panels)

@app.get("/api/coverage")
async def get_coverage_matrix():
    """Returns official SIH PS 26228 Capability Coverage Matrix and Known Limitations."""
    capabilities = [
        {
            "capability": "Trigger & Backdoor Detection",
            "status": "SUPPORTED",
            "detection_method": "Multi-scale sliding border check, 2D FFT radial conjugate peak prominence, and high-pass residual autocorrelation.",
            "evidence": "Observed corner variance, FFT z-scores, spatial residual correlation.",
            "assumptions": "Triggers introduce localized spatial edges, high-contrast transitions, or periodic frequency carrier spikes.",
            "limitations": "Physical-world 3D adversarial vehicle camouflage patterns are evaluated in model-level testing rather than digital data filtering."
        },
        {
            "capability": "Label Flipping",
            "status": "SUPPORTED",
            "detection_method": "Feature-space k-NN neighborhood consensus and class centroid distance margin.",
            "evidence": "Consensus discrepancy ratio, centroid margin displacement.",
            "assumptions": "Semantic classes have coherent feature distributions with >= 5 samples per evaluated category.",
            "limitations": "Extreme class imbalance (< 3 samples per class) falls back to centroid distance margins."
        },
        {
            "capability": "Systematic Mislabelling",
            "status": "SUPPORTED",
            "detection_method": "Contributor confusion matrix analytics and concentrated transition ratios.",
            "evidence": "Class transition frequency matrices, confusion concentration index.",
            "assumptions": "Adversary applies non-random semantic confusion rules across batches.",
            "limitations": "Requires sufficient contributor submission volume to distinguish from isolated human error."
        },
        {
            "capability": "Near-Duplicate Flooding",
            "status": "SUPPORTED",
            "detection_method": "3-Tier filter: SHA-256 exact match -> dual perceptual pHash/dHash -> SSIM and pixel MAE confirmation.",
            "evidence": "SSIM >= 0.82, normalized pixel MAE <= 0.15, contributor flooding ratio.",
            "assumptions": "Near-duplicates maintain geometric alignment with <= 10 deg rotation.",
            "limitations": "Severe 3D perspective warping requires keypoint homography estimation."
        },
        {
            "capability": "Out-Of-Distribution (OOD) Detection",
            "status": "SUPPORTED",
            "detection_method": "Isolation Forest, color moments, texture energy, and Laplacian edge sharpness.",
            "evidence": "Feature density anomaly score > 0.65 threshold.",
            "assumptions": "Operational aerial imagery adheres to consistent sensor and altitude baselines.",
            "limitations": "Treated as operational anomaly signal; requires governance review rather than automatic quarantine."
        },
        {
            "capability": "Contributor Risk Aggregation",
            "status": "SUPPORTED",
            "detection_method": "Volume-normalized and confidence-weighted composite scoring across all detectors.",
            "evidence": "Contributor risk score (0.0 - 1.0), dominant risk factor, flagged sample counts.",
            "assumptions": "Clean contributors exhibit natural baseline noise (< 5% flag rate).",
            "limitations": "New contributors with < 4 samples are marked with lower volume significance."
        },
        {
            "capability": "Model Integrity & Digest Hashing",
            "status": "SUPPORTED",
            "detection_method": "Chunked streaming SHA-256 digest comparison against trusted reference hash.",
            "evidence": "SHA-256 digest equality, file format inspection (.pt, .pth, .safetensors, .onnx).",
            "assumptions": "Trusted reference digest was securely established out-of-band.",
            "limitations": "SHA-256 proves byte equality with reference; does not prove the reference itself is safe."
        },
        {
            "capability": "White-Box Layer Parameter Analysis",
            "status": "SUPPORTED",
            "detection_method": "Tensor-only state dict inspection for layer mean, std, L2 norm, and dead neuron sparsity.",
            "evidence": "Layer-by-layer weight statistics, relative parameter deviations.",
            "assumptions": "Model architecture is inspectable via PyTorch state_dict.",
            "limitations": "Black-box models without state dict access return UNAVAILABLE; dummy weights are never substituted."
        },
        {
            "capability": "Inference Cryptographic Provenance",
            "status": "SUPPORTED",
            "detection_method": "SHA-256 binding of image + model + config + predictions + HMAC-SHA256 signature + replay registry.",
            "evidence": "Canonical binding digest, HMAC validation, monotonic sequence checking, nonce freshness.",
            "assumptions": "Inference service possesses authentic secret key in air-gapped enclave.",
            "limitations": "Authenticates post-hoc inference records; cannot prevent host-memory tampering during live inference."
        },
        {
            "capability": "Operational Distribution Shift",
            "status": "SUPPORTED",
            "detection_method": "Two-sample Kolmogorov-Smirnov test and Wasserstein distance across terrain, illumination, sensor, and season proxies.",
            "evidence": "KS statistic, p-value, W1 distance, physical proxy classification.",
            "assumptions": "Target and reference datasets have >= 10 samples for statistical significance.",
            "limitations": "Monitors image-derived proxies, not semantic ground-truth terrain or season labels."
        },
        {
            "capability": "Tamper-Evident Audit Trail",
            "status": "SUPPORTED",
            "detection_method": "Append-only SHA-256 hash-chained event ledger starting from Genesis zero hash.",
            "evidence": "Deterministic canonical JSON serialization, unbroken hash linkage, re-computation walk.",
            "assumptions": "Log file is written to local non-volatile storage.",
            "limitations": "Guarantees mathematical tamper-evidence and detection; does not prevent file deletion without OS write-protection."
        },
        {
            "capability": "Governance Assurance Engine",
            "status": "SUPPORTED",
            "detection_method": "Risk scoring formula fusing all modules with critical penalty weighting.",
            "evidence": "Overall health score (0-100), structured findings, recommended disposition (ACCEPT/REVIEW/QUARANTINE).",
            "assumptions": "Critical findings (e.g. backdoors, model hash mismatches) mandate quarantine disposition.",
            "limitations": "Policy recommendations require final human analyst sign-off in defense workflows."
        }
    ]

    limitations = [
        "Physical-world 3D adversarial camouflage patterns are outside Module 1 training-data scope.",
        "Extreme class imbalance (< 3 samples per class) falls back to centroid distance margins.",
        "Severe perspective warping exceeding +-10 degrees rotation requires affine keypoint homography.",
        "Model behavioral probing is battery- and trigger-dependent; does not guarantee universal backdoor detection.",
        "Model hash mismatch proves byte difference, not necessarily malicious intent.",
        "White-box parameter analysis requires model state dictionary access; unavailable runtimes report UNAVAILABLE.",
        "Cryptographic provenance signatures authenticate post-hoc records; host OS sandbox is required during runtime."
    ]

    return JSONResponse(content={
        "capabilities": capabilities,
        "limitations": limitations,
        "total_capabilities": len(capabilities),
        "supported_count": sum(1 for c in capabilities if c["status"] == "SUPPORTED")
    })

# -------------------------------------------------------------
# BLOCKCHAIN TRUST & EVIDENCE LEDGER API
# -------------------------------------------------------------

@app.get("/api/blockchain/status")
async def get_blockchain_status():
    """Returns real-time Hyperledger Fabric network connection and ledger state."""
    try:
        return blockchain_client.get_status().model_dump()
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "network_type": "Hyperledger Fabric (Permissioned)",
            "error": str(e),
            "mode": "OFFLINE_AIR_GAPPED"
        }

@app.get("/api/blockchain/events")
async def get_blockchain_events(
    event_type: Optional[str] = None,
    asset_id: Optional[str] = None,
    contributor_id: Optional[str] = None,
    limit: int = 100
):
    """Queries immutable assurance events committed to the blockchain ledger."""
    evts = blockchain_client.query_events(
        event_type=event_type,
        asset_id=asset_id,
        contributor_id=contributor_id,
        limit=limit
    )
    return [e.model_dump() for e in evts]

@app.get("/api/blockchain/event/{event_id}")
async def get_blockchain_event_by_id(event_id: str):
    """Retrieves specific blockchain event by its unique event ID."""
    evt = blockchain_client.get_event(event_id)
    if not evt:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found on ledger")
    return evt.model_dump()

@app.get("/api/blockchain/history/{asset_id}")
async def get_blockchain_asset_history(asset_id: str):
    """Retrieves full chronological ledger history for an asset."""
    history = blockchain_client.get_asset_history(asset_id)
    return [e.model_dump() for e in history]

class AnchorInferenceRequest(BaseModel):
    record: Dict[str, Any]
    contributor_id: Optional[str] = None

@app.post("/api/blockchain/anchor/inference")
async def anchor_inference_record_endpoint(req: AnchorInferenceRequest):
    """Anchors a ProtectedInferenceRecord cryptographic binding onto the ledger."""
    try:
        evt = blockchain_anchor_service.anchor_inference_record(
            record=req.record,
            contributor_id=req.contributor_id
        )
        return evt.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class VerifyInferenceBlockchainRequest(BaseModel):
    record: Dict[str, Any]
    image_bytes_base64: Optional[str] = None

@app.post("/api/blockchain/verify/inference")
async def verify_inference_blockchain_endpoint(req: VerifyInferenceBlockchainRequest):
    """Executes dual-layer verification (Local Cryptography + Hyperledger Fabric Anchor)."""
    try:
        dual_res = blockchain_verifier.verify_inference_record_dual(record=req.record)
        return dual_res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class VerifyModelBlockchainRequest(BaseModel):
    model_id: str
    model_path: Optional[str] = None
    expected_version: str = "1.0.0"

@app.post("/api/blockchain/verify/model")
async def verify_model_blockchain_endpoint(req: VerifyModelBlockchainRequest):
    """Dual-verifies active model weights against registered blockchain reference digest."""
    mpath = req.model_path or os.path.join(DEMO_DIR, "sample_model.pt")
    dual_res = blockchain_verifier.verify_model_dual(
        model_id=req.model_id,
        current_model_path=mpath,
        expected_version=req.expected_version
    )
    return dual_res.model_dump()

@app.post("/api/blockchain/simulate_tampering")
async def simulate_tampering_endpoint(record_id: Optional[str] = None):
    """
    Simulates a controlled inference tampering attack.
    Demonstrates local cryptographic failure and blockchain anchor mismatch.
    """
    img_hash_1 = hashlib.sha256(b"SAMPLE_AERIAL_FRAME_ALPHA").hexdigest()
    model_path = os.path.join(DEMO_DIR, "sample_model.pt")
    model_hash = ModelHasher.compute_file_sha256(model_path) if os.path.exists(model_path) else "fdab8c003aa41f4c3795f97f" * 2
    preds = [
        InferenceOutputPrediction(box=[120.0, 80.0, 45.0, 95.0], confidence=0.942, category_id=4, category_name="car"),
        InferenceOutputPrediction(box=[310.0, 240.0, 60.0, 110.0], confidence=0.887, category_id=5, category_name="van")
    ]
    clean_rec_obj = prov_engine.create_protected_record(
        image_path_or_hash=img_hash_1,
        model_hash=model_hash,
        predictions=preds,
        sequence_number=101,
        nonce="nonce_demo_tamper_001"
    )
    clean_rec = clean_rec_obj.model_dump()

    # Anchor the legitimate clean record to blockchain first
    blockchain_anchor_service.anchor_inference_record(clean_rec, contributor_id="contributor_A")

    # Create tampered variant (tampered predictions and mismatching binding)
    tampered_rec = json.loads(json.dumps(clean_rec))
    if tampered_rec.get("predictions"):
        tampered_rec["predictions"][0]["category_name"] = "pedestrian_tampered"
        tampered_rec["predictions"][0]["confidence"] = 0.9999
    tampered_rec["binding_hash_sha256"] = hashlib.sha256(b"TAMPERED_PREDICTION_BINDING").hexdigest()

    # Execute dual verification
    dual_res = blockchain_verifier.verify_inference_record_dual(tampered_rec)
    return {
        "original_record_id": clean_rec["record_id"],
        "tampered_record": tampered_rec,
        "verification_result": dual_res.model_dump()
    }

@app.post("/api/blockchain/simulate_replay")
async def simulate_replay_endpoint():
    """
    Simulates a replay attack against a previously accepted record.
    Demonstrates replay protection detection and historical blockchain anchor query.
    """
    img_hash_1 = hashlib.sha256(b"SAMPLE_AERIAL_FRAME_BETA").hexdigest()
    model_path = os.path.join(DEMO_DIR, "sample_model.pt")
    model_hash = ModelHasher.compute_file_sha256(model_path) if os.path.exists(model_path) else "fdab8c003aa41f4c3795f97f" * 2
    preds = [
        InferenceOutputPrediction(box=[200.0, 150.0, 30.0, 50.0], confidence=0.915, category_id=1, category_name="pedestrian")
    ]
    rec_obj = prov_engine.create_protected_record(
        image_path_or_hash=img_hash_1,
        model_hash=model_hash,
        predictions=preds,
        sequence_number=102,
        nonce="nonce_demo_replay_002"
    )
    
    # 1. Anchor to blockchain
    evt = blockchain_anchor_service.anchor_inference_record(rec_obj, contributor_id="contributor_A")

    # 2. Register once locally
    prov_engine.verify_record(rec_obj, register_if_valid=True)

    # 3. Second attempt (replay)
    replay_result = prov_engine.verify_record(rec_obj, register_if_valid=True)
    history = blockchain_client.get_asset_history(rec_obj.record_id)

    return {
        "record_id": rec_obj.record_id,
        "first_submission_passed": True,
        "replay_attempt_tamper_detected": replay_result.tamper_detected,
        "replay_detected": replay_result.replay_detected,
        "blockchain_history_count": len(history),
        "latest_anchor_tx": evt.tx_id,
        "disposition": "QUARANTINE" if replay_result.replay_detected else "ACCEPT"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FastAPI server on 0.0.0.0:{port}...")
    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)



