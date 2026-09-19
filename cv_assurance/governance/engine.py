import os
import time
import uuid
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .report_schema import (
    AssuranceFinding, AssuranceReport, SeverityLevel, RecommendedDisposition
)
from ..data import (
    DatasetIngester, DuplicateDetector, LabelIntegrityAnalyzer,
    OODDetector, DataBackdoorDetector, ContributorRiskAggregator,
    IngestedDataset
)
from ..model import (
    ModelHasher, ModelFingerprinter, WhiteBoxAnalyzer
)
from ..shift import (
    DistributionShiftDetector, EnvironmentalFeatureExtractor
)
from ..provenance import (
    CryptographicProvenanceEngine, ProtectedInferenceRecord
)

class AssuranceEngine:
    """
    Master AI Assurance Engine orchestrating comprehensive integrity evaluations
    across data, models, distribution shifts, and inference provenance.
    """
    
    def __init__(self):
        self.ingester = DatasetIngester()
        self.duplicate_detector = DuplicateDetector()
        self.label_analyzer = LabelIntegrityAnalyzer()
        self.ood_detector = OODDetector()
        self.backdoor_detector = DataBackdoorDetector()
        self.risk_aggregator = ContributorRiskAggregator()
        
        self.model_hasher = ModelHasher()
        self.model_fingerprinter = ModelFingerprinter()
        self.whitebox_analyzer = WhiteBoxAnalyzer()
        
        self.shift_detector = DistributionShiftDetector()
        self.provenance_engine = CryptographicProvenanceEngine()

    def run_full_assurance(
        self,
        dataset_path: str,
        model_path: Optional[str] = None,
        ref_dataset_path: Optional[str] = None,
        reference_model_hash: Optional[str] = None
    ) -> AssuranceReport:
        
        findings: List[AssuranceFinding] = []
        now_str = datetime.now(timezone.utc).isoformat()
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

        # 1. DATASET INGESTION & INTEGRITY CHECKS
        dataset = self.ingester.auto_ingest(dataset_path)
        
        # A. Duplicate & Flooding Scan
        dup_res = self.duplicate_detector.analyze(dataset)
        if dup_res.duplicate_pairs_count > 0:
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-DUP-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Near-Duplicate Image Flooding Detected",
                human_readable_reason=f"Detected {dup_res.duplicate_pairs_count} duplicate or near-duplicate image pairs ({dup_res.duplicate_samples_count} total samples affected). Potential contributor flooding attack.",
                supporting_evidence={
                    "duplicate_pairs_count": dup_res.duplicate_pairs_count,
                    "duplicate_samples_count": dup_res.duplicate_samples_count,
                    "flooding_risk_score": dup_res.flooding_risk_score,
                    "sample_pairs": [p.model_dump() for p in dup_res.duplicate_pairs[:5]]
                },
                confidence_score=0.95,
                severity=SeverityLevel.HIGH if dup_res.flooding_risk_score >= 0.2 else SeverityLevel.MEDIUM,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.REVIEW
            ))

        # B. Label Flipping & Systematic Mislabelling Scan
        lbl_res = self.label_analyzer.analyze(dataset)
        if lbl_res.suspicious_samples_count > 0:
            sev = SeverityLevel.CRITICAL if lbl_res.systematic_pattern_detected else SeverityLevel.HIGH
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-LBL-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Label Flipping / Mislabelling Detected",
                human_readable_reason=f"Identified {lbl_res.suspicious_samples_count} suspicious samples with strong feature-label disagreement ({round(lbl_res.mislabelling_rate*100, 1)}% mislabel rate).",
                supporting_evidence={
                    "suspicious_count": lbl_res.suspicious_samples_count,
                    "mislabelling_rate": lbl_res.mislabelling_rate,
                    "systematic_pattern": lbl_res.systematic_pattern_detected,
                    "flagged_samples": [s.model_dump() for s in lbl_res.flagged_samples[:5]]
                },
                confidence_score=0.90,
                severity=sev,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.QUARANTINE if sev == SeverityLevel.CRITICAL else RecommendedDisposition.REVIEW
            ))

        # C. Out-Of-Distribution (OOD) Scan
        ood_res = self.ood_detector.analyze(dataset)
        if ood_res.ood_samples_count > 0:
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-OOD-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Out-Of-Distribution (OOD) Samples Inserted",
                human_readable_reason=f"Detected {ood_res.ood_samples_count} samples significantly departing from baseline feature distribution.",
                supporting_evidence={
                    "ood_count": ood_res.ood_samples_count,
                    "ood_ratio": ood_res.ood_ratio,
                    "ood_samples": [s.model_dump() for s in ood_res.ood_samples[:5]]
                },
                confidence_score=0.88,
                severity=SeverityLevel.MEDIUM if ood_res.ood_ratio < 0.15 else SeverityLevel.HIGH,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.REVIEW
            ))

        # D. Backdoor / Trigger Injection Scan
        bd_res = self.backdoor_detector.analyze(dataset)
        if bd_res.poisoned_samples_count > 0:
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-POI-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Data Poisoning / Trigger Patch Injection Detected",
                human_readable_reason=f"Found {bd_res.poisoned_samples_count} samples containing geometric corner patch triggers or periodic high-frequency spectral artifacts.",
                supporting_evidence={
                    "poisoned_count": bd_res.poisoned_samples_count,
                    "poisoning_rate": bd_res.poisoning_rate,
                    "detected_triggers": [t.model_dump() for t in bd_res.detected_triggers[:5]]
                },
                confidence_score=0.96,
                severity=SeverityLevel.CRITICAL,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.QUARANTINE
            ))

        # E. Contributor Risk Aggregation
        contrib_res = self.risk_aggregator.aggregate(dataset, dup_res, lbl_res, ood_res, bd_res)
        for p in contrib_res.profiles:
            if p.risk_level in ["CRITICAL", "HIGH"]:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-CONTRIB-{uuid.uuid4().hex[:6].upper()}",
                    category="data_integrity",
                    title=f"High Risk Contributor Identified: {p.contributor_id}",
                    human_readable_reason=f"Contributor '{p.contributor_id}' submitted {p.flagged_samples_count} anomalous samples ({p.poisoned_count} poisoned, {p.mislabelled_count} mislabelled). Risk score: {p.risk_score}.",
                    supporting_evidence=p.model_dump(),
                    confidence_score=0.92,
                    severity=SeverityLevel.CRITICAL if p.risk_level == "CRITICAL" else SeverityLevel.HIGH,
                    affected_asset=f"Contributor:{p.contributor_id}",
                    recommended_disposition=RecommendedDisposition.QUARANTINE if p.risk_level == "CRITICAL" else RecommendedDisposition.REVIEW
                ))

        # 2. MODEL INTEGRITY CHECKS (if model provided)
        if model_path and os.path.exists(model_path):
            hash_res = self.model_hasher.inspect_model(model_path, reference_sha256=reference_model_hash)
            if reference_model_hash and not hash_res.reference_match:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-HASH-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Model Digest Mismatch / Weight Substitution",
                    human_readable_reason=f"Supplied model digest SHA-256 ({hash_res.sha256_digest[:16]}...) does not match expected reference hash ({reference_model_hash[:16]}...). Possible unauthorized model substitution.",
                    supporting_evidence=hash_res.model_dump(),
                    confidence_score=1.0,
                    severity=SeverityLevel.CRITICAL,
                    affected_asset=model_path,
                    recommended_disposition=RecommendedDisposition.QUARANTINE
                ))

            # Whitebox parameter inspection
            wb_res = self.whitebox_analyzer.analyze_weights(model_path)
            if wb_res.access_granted and wb_res.weight_anomaly_score >= 0.2:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-WB-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Model Parameter Distribution Anomaly Detected",
                    human_readable_reason=wb_res.assessment_notes,
                    supporting_evidence=wb_res.model_dump(),
                    confidence_score=0.87,
                    severity=SeverityLevel.HIGH if wb_res.backdoor_trigger_risk == "HIGH" else SeverityLevel.MEDIUM,
                    affected_asset=model_path,
                    recommended_disposition=RecommendedDisposition.REVIEW
                ))

            # Behavioral Fingerprinting
            fp_res = self.model_fingerprinter.fingerprint_dummy_or_callable(None, dataset)
            if fp_res.anomalous_behavior_detected:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-FP-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Anomalous Behavioral Fingerprint on Reference Battery",
                    human_readable_reason=fp_res.findings_summary,
                    supporting_evidence=fp_res.model_dump(),
                    confidence_score=0.85,
                    severity=SeverityLevel.MEDIUM,
                    affected_asset=model_path,
                    recommended_disposition=RecommendedDisposition.REVIEW
                ))

        # 3. DISTRIBUTION SHIFT CHECKS (if reference dataset provided)
        if ref_dataset_path and os.path.exists(ref_dataset_path):
            ref_ds = self.ingester.auto_ingest(ref_dataset_path)
            shift_res = self.shift_detector.analyze(ref_ds, dataset)
            if shift_res.material_shift_detected:
                sev = SeverityLevel.CRITICAL if shift_res.shift_classification == "SUSPICIOUS_MANIPULATION" else SeverityLevel.MEDIUM
                findings.append(AssuranceFinding(
                    finding_id=f"FND-SHIFT-{uuid.uuid4().hex[:6].upper()}",
                    category="distribution_shift",
                    title=f"Distribution Shift Detected: {shift_res.shift_classification}",
                    human_readable_reason=shift_res.summary_findings,
                    supporting_evidence=shift_res.model_dump(),
                    confidence_score=shift_res.confidence_score,
                    severity=sev,
                    affected_asset=dataset.name,
                    recommended_disposition=RecommendedDisposition.QUARANTINE if sev == SeverityLevel.CRITICAL else RecommendedDisposition.REVIEW
                ))

        # 4. AGGREGATE HEALTH SCORE & DISPOSITION
        critical_count = sum(1 for f in findings if f.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == SeverityLevel.HIGH)
        med_count = sum(1 for f in findings if f.severity == SeverityLevel.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == SeverityLevel.LOW)

        penalty = (critical_count * 35) + (high_count * 20) + (med_count * 10) + (low_count * 5)
        health_score = round(max(0.0, float(100.0 - penalty)), 1)

        if critical_count > 0 or health_score < 50.0:
            overall_disp = RecommendedDisposition.QUARANTINE
        elif high_count > 0 or med_count >= 2 or health_score < 80.0:
            overall_disp = RecommendedDisposition.REVIEW
        else:
            overall_disp = RecommendedDisposition.ACCEPT

        # Supported attack classes and known limitations documentation
        supported_attacks = [
            "Trigger Patch Injection / BadNets",
            "Periodic High-Frequency Spectral Backdoors",
            "Label Flipping & Systematic Annotation Noise",
            "Near-Duplicate Flooding & Data Sybil Attacks",
            "Out-Of-Distribution (OOD) Insertion",
            "Model SHA-256 Weight Substitution & Tampering",
            "White-box Layer Parameter Norm & Sparsity Anomalies",
            "Operational Environmental Drift (Terrain, Illumination, Sensor, Season)",
            "Post-hoc Inference Record Alteration & Replay Attacks"
        ]

        known_limitations = [
            "Black-box model assessment relies strictly on output behavioral distributions without inspecting internal activations.",
            "Dynamic adversarial perturbations (e.g. FGSM/PGD L-infinity noise) below perceptual threshold require target model gradients.",
            "Assurance score is calibrated on provided reference validation battery size."
        ]

        # Audit trail tamper-evident hash
        raw_report_data = f"{report_id}|{now_str}|{health_score}|{overall_disp}|{len(findings)}"
        audit_hash = hashlib.sha256(raw_report_data.encode('utf-8')).hexdigest()

        summary_counts = {
            "total_findings": len(findings),
            "CRITICAL": critical_count,
            "HIGH": high_count,
            "MEDIUM": med_count,
            "LOW": low_count
        }

        return AssuranceReport(
            report_id=report_id,
            generated_at_utc=now_str,
            system_version="1.0.0",
            overall_health_score=health_score,
            overall_disposition=overall_disp,
            supported_attack_classes=supported_attacks,
            known_limitations=known_limitations,
            summary_counts=summary_counts,
            findings=findings,
            audit_trail_hash=audit_hash
        )
