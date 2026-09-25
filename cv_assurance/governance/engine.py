import os
import time
import uuid
import json
import hashlib
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone

from .report_schema import (
    AssuranceFinding, AssuranceReport, SeverityLevel, RecommendedDisposition,
    AuditChainSummary, ProvenanceAuditSummary
)
from .audit_chain import TamperEvidentAuditChain, AuditEvent
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
    CryptographicProvenanceEngine, ProtectedInferenceRecord, ReplayProtectionRegistry
)


def _heuristic_evidence_score(*components: float) -> float:
    """Return a deterministic evidence score, never a calibrated probability."""
    values = [max(0.0, min(1.0, float(value))) for value in components]
    return round(sum(values) / len(values), 4) if values else 0.0

class AssuranceEngine:
    """
    Master AI Assurance Governance Engine orchestrating comprehensive integrity evaluations
    across data, models, distribution shifts, inference provenance, and cryptographic audit chains.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        secret_key_file: Optional[str] = None,
        replay_registry: Optional[ReplayProtectionRegistry] = None,
        replay_registry_file: Optional[str] = None
    ):
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
        configured_registry = replay_registry or ReplayProtectionRegistry(replay_registry_file)
        self.provenance_engine = CryptographicProvenanceEngine(
            secret_key=secret_key,
            secret_key_file=secret_key_file,
            replay_registry=configured_registry
        )

    def run_full_assurance(
        self,
        dataset_path: str,
        model_path: Optional[str] = None,
        ref_dataset_path: Optional[str] = None,
        reference_model_hash: Optional[str] = None,
        reference_model_path: Optional[str] = None,
        model_object: Optional[Any] = None,
        model_predictor: Optional[Any] = None,
        inference_record_path: Optional[str] = None,
        protected_records: Optional[List[Union[ProtectedInferenceRecord, dict]]] = None,
        replay_registry: Optional[ReplayProtectionRegistry] = None,
        audit_chain: Optional[TamperEvidentAuditChain] = None,
        audit_chain_file: Optional[str] = None
    ) -> AssuranceReport:
        """
        Executes end-to-end assurance evaluation across data, model, distribution shift,
        and inference provenance, recording all decisions into an immutable audit chain.
        """
        findings: List[AssuranceFinding] = []
        now_str = datetime.now(timezone.utc).isoformat()
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

        # Initialize Audit Chain
        chain = audit_chain or TamperEvidentAuditChain(chain_file=audit_chain_file)
        chain.append_event(
            event_type="PIPELINE_INIT",
            affected_asset=dataset_path,
            event_summary=f"Initiated comprehensive AI integrity assurance evaluation {report_id}.",
            event_data={
                "report_id": report_id,
                "dataset_path": dataset_path,
                "model_path": model_path,
                "ref_dataset_path": ref_dataset_path,
                "reference_model_path": reference_model_path,
                "has_inference_provenance": bool(inference_record_path or protected_records)
            }
        )

        # -------------------------------------------------------------
        # 1. DATASET INGESTION & TRAINING-DATA INTEGRITY CHECKS
        # -------------------------------------------------------------
        dataset = self.ingester.auto_ingest(dataset_path)

        # A. Duplicate & Flooding Scan
        dup_res = self.duplicate_detector.analyze(dataset)
        if dup_res.duplicate_pairs_count > 0:
            duplicate_ratio = dup_res.duplicate_samples_count / max(1, len(dataset.samples))
            duplicate_confidence = _heuristic_evidence_score(
                dup_res.flooding_risk_score, duplicate_ratio
            )
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-DUP-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Near-Duplicate Image Flooding Detected",
                human_readable_reason=f"Detected {dup_res.duplicate_pairs_count} duplicate or near-duplicate image pairs ({dup_res.duplicate_samples_count} total samples affected). Potential contributor flooding attack.",
                supporting_evidence={
                    "duplicate_pairs_count": dup_res.duplicate_pairs_count,
                    "duplicate_samples_count": dup_res.duplicate_samples_count,
                    "flooding_risk_score": dup_res.flooding_risk_score,
                    "confidence_semantics": "heuristic_evidence_score_not_calibrated_probability",
                    "sample_pairs": [p.model_dump() for p in dup_res.duplicate_pairs[:5]]
                },
                confidence_score=duplicate_confidence,
                confidence_semantics="heuristic_evidence_score_not_calibrated_probability",
                severity=SeverityLevel.HIGH if dup_res.flooding_risk_score >= 0.2 else SeverityLevel.MEDIUM,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.REVIEW
            ))

        # B. Label Flipping & Systematic Mislabelling Scan
        lbl_res = self.label_analyzer.analyze(dataset)
        if lbl_res.suspicious_samples_count > 0:
            sev = SeverityLevel.CRITICAL if lbl_res.systematic_pattern_detected else SeverityLevel.HIGH
            label_ratio = lbl_res.suspicious_samples_count / max(1, lbl_res.total_samples)
            label_confidence = _heuristic_evidence_score(
                label_ratio, 1.0 if lbl_res.systematic_pattern_detected else 0.0
            )
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-LBL-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Label Flipping / Mislabelling Detected",
                human_readable_reason=f"Identified {lbl_res.suspicious_samples_count} suspicious samples with strong feature-label disagreement ({round(lbl_res.mislabelling_rate*100, 1)}% mislabel rate).",
                supporting_evidence={
                    "suspicious_count": lbl_res.suspicious_samples_count,
                    "mislabelling_rate": lbl_res.mislabelling_rate,
                    "systematic_pattern": lbl_res.systematic_pattern_detected,
                    "confidence_semantics": "heuristic_evidence_score_not_calibrated_probability",
                    "flagged_samples": [s.model_dump() for s in lbl_res.flagged_samples[:5]]
                },
                confidence_score=label_confidence,
                confidence_semantics="heuristic_evidence_score_not_calibrated_probability",
                severity=sev,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.QUARANTINE if sev == SeverityLevel.CRITICAL else RecommendedDisposition.REVIEW
            ))

        # C. Out-Of-Distribution (OOD) Scan
        ood_res = self.ood_detector.analyze(dataset)
        if ood_res.ood_samples_count > 0:
            ood_signal = ood_res.ood_ratio
            if not ood_res.trusted_reference_used:
                ood_signal *= 0.5
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-OOD-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Out-Of-Distribution (OOD) Samples Inserted",
                human_readable_reason=f"Detected {ood_res.ood_samples_count} samples significantly departing from baseline feature distribution.",
                supporting_evidence={
                    "ood_count": ood_res.ood_samples_count,
                    "ood_ratio": ood_res.ood_ratio,
                    "analysis_mode": ood_res.analysis_mode,
                    "confidence_semantics": "heuristic_evidence_score_not_calibrated_probability",
                    "ood_samples": [s.model_dump() for s in ood_res.ood_samples[:5]]
                },
                confidence_score=_heuristic_evidence_score(ood_signal),
                confidence_semantics="heuristic_evidence_score_not_calibrated_probability",
                severity=SeverityLevel.MEDIUM if ood_res.ood_ratio < 0.15 else SeverityLevel.HIGH,
                affected_asset=dataset.name,
                recommended_disposition=RecommendedDisposition.REVIEW
            ))

        # D. Backdoor / Trigger Injection Scan
        bd_res = self.backdoor_detector.analyze(dataset)
        if bd_res.poisoned_samples_count > 0:
            trigger_confidence = max(
                (trigger.confidence for trigger in bd_res.detected_triggers),
                default=0.0
            )
            poisoning_confidence = _heuristic_evidence_score(
                bd_res.poisoning_rate, trigger_confidence
            )
            findings.append(AssuranceFinding(
                finding_id=f"FND-DATA-POI-{uuid.uuid4().hex[:6].upper()}",
                category="data_integrity",
                title="Data Poisoning / Trigger Patch Injection Detected",
                human_readable_reason=f"Found {bd_res.poisoned_samples_count} samples containing geometric corner patch triggers or periodic high-frequency spectral artifacts.",
                supporting_evidence={
                    "poisoned_count": bd_res.poisoned_samples_count,
                    "poisoning_rate": bd_res.poisoning_rate,
                    "confidence_semantics": "heuristic_evidence_score_not_calibrated_probability",
                    "detected_triggers": [t.model_dump() for t in bd_res.detected_triggers[:5]]
                },
                confidence_score=poisoning_confidence,
                confidence_semantics="heuristic_evidence_score_not_calibrated_probability",
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
                    supporting_evidence={
                        **p.model_dump(),
                        "confidence_semantics": "heuristic_evidence_score_not_calibrated_probability"
                    },
                    confidence_score=_heuristic_evidence_score(p.risk_score),
                    confidence_semantics="heuristic_evidence_score_not_calibrated_probability",
                    severity=SeverityLevel.CRITICAL if p.risk_level == "CRITICAL" else SeverityLevel.HIGH,
                    affected_asset=f"Contributor:{p.contributor_id}",
                    recommended_disposition=RecommendedDisposition.QUARANTINE if p.risk_level == "CRITICAL" else RecommendedDisposition.REVIEW
                ))

        chain.append_event(
            event_type="DATASET_AUDIT",
            affected_asset=dataset.name,
            event_summary=f"Evaluated training dataset integrity: {len(dataset.samples)} samples. Flagged {len([f for f in findings if f.category == 'data_integrity'])} data findings.",
            event_data={
                "duplicate_pairs": dup_res.duplicate_pairs_count,
                "suspicious_labels": lbl_res.suspicious_samples_count,
                "ood_samples": ood_res.ood_samples_count,
                "poisoned_samples": bd_res.poisoned_samples_count,
                "contributor_profiles_count": len(contrib_res.profiles)
            }
        )

        # -------------------------------------------------------------
        # 2. MODEL INTEGRITY CHECKS (if model provided)
        # -------------------------------------------------------------
        model_supplied = bool(
            (model_path and os.path.exists(model_path)) or
            model_object is not None or model_predictor is not None
        )
        if model_supplied:
            hash_res = (
                self.model_hasher.inspect_model(model_path, reference_sha256=reference_model_hash)
                if model_path and os.path.exists(model_path) else None
            )
            model_asset = model_path or "<in-memory-model>"
            if hash_res and reference_model_hash and not hash_res.reference_match:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-HASH-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Model Digest Mismatch / Weight Substitution",
                    human_readable_reason=f"Supplied model digest SHA-256 ({hash_res.sha256_digest[:16]}...) does not match expected reference hash ({reference_model_hash[:16]}...). Possible unauthorized model substitution.",
                    supporting_evidence=hash_res.model_dump(),
                    confidence_score=1.0,
                    severity=SeverityLevel.CRITICAL,
                    affected_asset=model_asset,
                    recommended_disposition=RecommendedDisposition.QUARANTINE
                ))

            # White-box parameter inspection. A supplied in-memory model is
            # analyzed directly; an artifact uses safe tensor inspection.
            if model_object is not None:
                wb_res = self.whitebox_analyzer.analyze_model(model_object, model_path=model_asset)
            else:
                wb_res = self.whitebox_analyzer.analyze_weights(model_path) if model_path else self.whitebox_analyzer.analyze_model(None, model_path=model_asset)
            if wb_res.access_granted and wb_res.weight_anomaly_score >= 0.2:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-WB-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Model Parameter Distribution Anomaly Detected",
                    human_readable_reason=wb_res.assessment_notes,
                    supporting_evidence=wb_res.model_dump(),
                    confidence_score=round(min(1.0, wb_res.weight_anomaly_score), 4),
                    severity=SeverityLevel.HIGH if wb_res.parameter_anomaly_risk == "HIGH" else SeverityLevel.MEDIUM,
                    affected_asset=model_asset,
                    recommended_disposition=RecommendedDisposition.REVIEW
                ))

            # Behavioral fingerprinting must execute the supplied model. A
            # callable is an explicit black-box adapter; an artifact is loaded
            # through its format-specific offline runtime.
            supplied_model = model_object if model_object is not None else model_predictor
            try:
                if supplied_model is not None:
                    fp_res = self.model_fingerprinter.fingerprint_dummy_or_callable(supplied_model, dataset)
                else:
                    fp_res = self.model_fingerprinter.fingerprint_model(model_path, dataset)
            except Exception as exc:
                fp_res = self.model_fingerprinter.fingerprint_dummy_or_callable(None, dataset)
                fp_res.findings_summary = f"Behavioral fingerprint unavailable: {exc}"

            behavioral_comparison = None
            if reference_model_path and os.path.exists(reference_model_path) and model_path:
                try:
                    behavioral_comparison = self.model_fingerprinter.compare_models(
                        reference_model_path, model_path, dataset
                    )
                except Exception as exc:
                    behavioral_comparison = None
                    findings.append(AssuranceFinding(
                        finding_id=f"FND-MDL-CMP-UNAV-{uuid.uuid4().hex[:6].upper()}",
                        category="model_integrity",
                        title="Behavioral Reference Comparison Unavailable",
                        human_readable_reason=f"The supplied model could not be compared with the trusted reference using an available offline runtime: {exc}",
                        supporting_evidence={"model_path": model_asset, "reference_model_path": reference_model_path, "error": str(exc), "confidence_semantics": "unavailable_not_calibrated"},
                        confidence_score=0.0,
                        severity=SeverityLevel.MEDIUM,
                        affected_asset=model_asset,
                        recommended_disposition=RecommendedDisposition.REVIEW
                    ))
            if fp_res.anomalous_behavior_detected:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-FP-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Anomalous Behavioral Fingerprint on Reference Battery",
                    human_readable_reason=fp_res.findings_summary,
                    supporting_evidence={
                        **fp_res.model_dump(),
                        "model_path": model_asset,
                        "model_format": hash_res.format if hash_res else "in_memory",
                        "whitebox_available": wb_res.access_granted,
                        "reference_comparison": behavioral_comparison.model_dump() if behavioral_comparison else None,
                        "confidence_semantics": "heuristic_evidence_derived_not_calibrated_probability"
                    },
                    confidence_score=round(min(1.0, fp_res.total_eval_samples / max(1, min(50, len(dataset.samples)))), 4),
                    severity=SeverityLevel.MEDIUM,
                    affected_asset=model_asset,
                    recommended_disposition=RecommendedDisposition.REVIEW
                ))

            if behavioral_comparison and behavioral_comparison.anomalous_behavior_detected:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-MDL-CMP-{uuid.uuid4().hex[:6].upper()}",
                    category="model_integrity",
                    title="Behavioral Deviation from Trusted Reference Model",
                    human_readable_reason=behavioral_comparison.findings_summary,
                    supporting_evidence={
                        **behavioral_comparison.model_dump(),
                        "model_path": model_asset,
                        "reference_model_path": reference_model_path,
                        "confidence_semantics": "heuristic_reference_deviation_not_calibrated_probability"
                    },
                    confidence_score=round(min(1.0, behavioral_comparison.total_eval_samples / max(1, min(50, len(dataset.samples)))), 4),
                    severity=SeverityLevel.HIGH,
                    affected_asset=model_asset,
                    recommended_disposition=RecommendedDisposition.REVIEW
                ))

            chain.append_event(
                event_type="MODEL_AUDIT",
                affected_asset=model_asset,
                event_summary=(
                    f"Inspected supplied model: SHA-256 {hash_res.sha256_digest[:16]}... Reference match: {hash_res.reference_match}."
                    if hash_res else "Inspected supplied in-memory/callable model; file digest unavailable."
                ),
                event_data={
                    "model_format": hash_res.format if hash_res else "in_memory",
                    "sha256_digest": hash_res.sha256_digest if hash_res else None,
                    "reference_match": hash_res.reference_match if hash_res else None,
                    "whitebox_access": wb_res.access_granted,
                    "behavioral_anomaly": fp_res.anomalous_behavior_detected,
                    "behavioral_access_mode": fp_res.access_mode,
                    "behavioral_samples": fp_res.total_eval_samples,
                    "reference_comparison": behavioral_comparison.model_dump() if behavioral_comparison else None
                }
            )

        # -------------------------------------------------------------
        # 3. DISTRIBUTION SHIFT CHECKS (if reference dataset provided)
        # -------------------------------------------------------------
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

            chain.append_event(
                event_type="SHIFT_AUDIT",
                affected_asset=dataset.name,
                event_summary=f"Distribution shift assessment completed: {shift_res.shift_classification} (Drift score: {shift_res.overall_drift_score}).",
                event_data={
                    "classification": shift_res.shift_classification,
                    "overall_drift_score": shift_res.overall_drift_score,
                    "shifted_dimensions": [d.dimension_name for d in shift_res.dimensions if d.shift_detected]
                }
            )

        # -------------------------------------------------------------
        # 4. INFERENCE PROVENANCE INTEGRATION
        # -------------------------------------------------------------
        prov_summary = None
        records_to_verify: List[ProtectedInferenceRecord] = []

        if inference_record_path and os.path.exists(inference_record_path):
            try:
                with open(inference_record_path, 'r', encoding='utf-8') as rf:
                    raw_recs = json.load(rf)
                if isinstance(raw_recs, list):
                    records_to_verify.extend([ProtectedInferenceRecord(**r) for r in raw_recs])
                elif isinstance(raw_recs, dict):
                    records_to_verify.append(ProtectedInferenceRecord(**raw_recs))
            except Exception as e:
                findings.append(AssuranceFinding(
                    finding_id=f"FND-PROV-PARSE-{uuid.uuid4().hex[:6].upper()}",
                    category="inference_provenance",
                    title="Inference Record Parsing Error",
                    human_readable_reason=f"Failed to parse inference record from {inference_record_path}: {str(e)}",
                    supporting_evidence={"path": inference_record_path, "error": str(e)},
                    confidence_score=1.0,
                    severity=SeverityLevel.HIGH,
                    affected_asset=inference_record_path,
                    recommended_disposition=RecommendedDisposition.REVIEW
                ))

        if protected_records:
            for item in protected_records:
                try:
                    if isinstance(item, ProtectedInferenceRecord):
                        records_to_verify.append(item)
                    elif isinstance(item, dict):
                        records_to_verify.append(ProtectedInferenceRecord(**item))
                except Exception as exc:
                    findings.append(AssuranceFinding(
                        finding_id=f"FND-PROV-PARSE-{uuid.uuid4().hex[:6].upper()}",
                        category="inference_provenance",
                        title="Inference Record Parsing Error",
                        human_readable_reason=f"Failed to parse supplied inference record: {exc}",
                        supporting_evidence={"error": str(exc)},
                        confidence_score=1.0,
                        severity=SeverityLevel.HIGH,
                        affected_asset="InferenceRecord:unparsed",
                        recommended_disposition=RecommendedDisposition.REVIEW
                    ))

        if records_to_verify:
            passed_count = 0
            tamper_count = 0
            replay_count = 0
            evaluated_list = []

            for rec in records_to_verify:
                res = self.provenance_engine.verify_record(
                    rec,
                    replay_registry=replay_registry,
                    register_if_valid=True
                )
                evaluated_list.append({
                    "record_id": rec.record_id,
                    "passed": res.verification_passed,
                    "tamper_detected": res.tamper_detected,
                    "replay_detected": res.replay_detected,
                    "sequence_violation": res.sequence_violation,
                    "details": res.details,
                    "tampered_fields": res.tampered_fields
                })

                if res.verification_passed:
                    passed_count += 1
                else:
                    if res.replay_detected:
                        replay_count += 1
                        findings.append(AssuranceFinding(
                            finding_id=f"FND-PROV-RPL-{uuid.uuid4().hex[:6].upper()}",
                            category="inference_provenance",
                            title=f"Inference Replay Attack Detected: {rec.record_id}",
                            human_readable_reason=res.details,
                            supporting_evidence=res.model_dump(),
                            confidence_score=1.0,
                            severity=SeverityLevel.CRITICAL,
                            affected_asset=f"InferenceRecord:{rec.record_id}",
                            recommended_disposition=RecommendedDisposition.QUARANTINE
                        ))
                    else:
                        tamper_count += 1
                        findings.append(AssuranceFinding(
                            finding_id=f"FND-PROV-TMP-{uuid.uuid4().hex[:6].upper()}",
                            category="inference_provenance",
                            title=f"Inference Cryptographic Tampering Detected: {rec.record_id}",
                            human_readable_reason=res.details,
                            supporting_evidence=res.model_dump(),
                            confidence_score=1.0,
                            severity=SeverityLevel.CRITICAL,
                            affected_asset=f"InferenceRecord:{rec.record_id}",
                            recommended_disposition=RecommendedDisposition.QUARANTINE
                        ))

            prov_summary = ProvenanceAuditSummary(
                total_records_evaluated=len(records_to_verify),
                verified_passed_count=passed_count,
                tamper_detected_count=tamper_count,
                replay_detected_count=replay_count,
                evaluated_records=evaluated_list
            )

            chain.append_event(
                event_type="PROVENANCE_AUDIT",
                affected_asset=inference_record_path or "InferenceStream",
                event_summary=f"Audited {len(records_to_verify)} inference records. Passed: {passed_count}, Tampered: {tamper_count}, Replayed: {replay_count}.",
                event_data={
                    "total_records": len(records_to_verify),
                    "passed": passed_count,
                    "tampered": tamper_count,
                    "replayed": replay_count
                }
            )

        # -------------------------------------------------------------
        # 5. AGGREGATE HEALTH SCORE & DISPOSITION
        # -------------------------------------------------------------
        # Filter primary technical findings to avoid double-counting derivative contributor summary findings
        primary_findings = [f for f in findings if not (f.finding_id and f.finding_id.startswith("FND-CONTRIB-"))]

        critical_count = sum(1 for f in findings if f.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == SeverityLevel.HIGH)
        med_count = sum(1 for f in findings if f.severity == SeverityLevel.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == SeverityLevel.LOW)

        prim_crit = [f for f in primary_findings if f.severity == SeverityLevel.CRITICAL]
        prim_high = [f for f in primary_findings if f.severity == SeverityLevel.HIGH]
        prim_med = [f for f in primary_findings if f.severity == SeverityLevel.MEDIUM]
        prim_low = [f for f in primary_findings if f.severity == SeverityLevel.LOW]

        # Calibrated diminishing marginal penalty formula
        penalty = 0.0
        for idx in range(len(prim_crit)):
            penalty += 18.0 if idx == 0 else (12.0 if idx == 1 else 6.0)
        for idx in range(len(prim_high)):
            penalty += 10.0 if idx == 0 else (6.0 if idx == 1 else 3.0)
        for idx in range(len(prim_med)):
            penalty += 5.0 if idx == 0 else 3.0
        for idx in range(len(prim_low)):
            penalty += 2.0

        health_score = round(max(0.0, float(100.0 - penalty)), 1)

        if critical_count > 0 or health_score < 50.0:
            overall_disp = RecommendedDisposition.QUARANTINE
        elif high_count > 0 or med_count >= 2 or health_score < 80.0:
            overall_disp = RecommendedDisposition.REVIEW
        else:
            overall_disp = RecommendedDisposition.ACCEPT

        # Final audit chain disposition event
        chain.append_event(
            event_type="GOVERNANCE_DISPOSITION",
            affected_asset=dataset.name,
            event_summary=f"Final governance verdict: [{overall_disp.value}] (Health Score: {health_score}/100, Findings: {len(findings)}).",
            event_data={
                "overall_health_score": health_score,
                "overall_disposition": overall_disp.value,
                "critical_findings": critical_count,
                "high_findings": high_count,
                "medium_findings": med_count,
                "low_findings": low_count
            }
        )

        # Audit Chain Verification
        chain_valid, chain_msg, _ = chain.verify_chain()
        chain_summary = AuditChainSummary(
            chain_length=chain.chain_length,
            latest_event_hash=chain.latest_hash,
            verification_status="VERIFIED_UNBROKEN" if chain_valid else "TAMPERED",
            verification_details=chain_msg,
            events=chain.export_log()
        )

        # Supported attack classes and known limitations
        supported_attacks = [
            "Trigger Patch Injection (BadNets Spatial Checkerboard)",
            "Periodic High-Frequency Spectral Fourier Backdoors",
            "Alpha-Blended Watermark Backdoor Triggers",
            "Random Label Flipping & Systematic Mislabelling Noise",
            "Near-Duplicate Sample Flooding & Pipeline Sybil Attacks",
            "Out-Of-Distribution (OOD) Domain Contamination",
            "Model SHA-256 Checkpoint Substitution & Weight Tampering",
            "White-box Layer Parameter Norm & Sparsity Anomalies",
            "Operational Environmental Drift (Terrain, Illumination, Sensor, Season)",
            "Suspicious Synthetic Environmental & Sensor Noise Manipulation",
            "Inference Record Post-Hoc Alteration (Predictions, BBoxes, Config, Image)",
            "Inference Replay Attacks (Duplicate Record ID, Nonce Reuse, Hash Replay)"
        ]

        known_limitations = [
            "Physical-world 3D adversarial camouflage (e.g. adversarial vehicle wraps) requires model-level feature attribution rather than digital artifact filtering.",
            "Black-box model assessment relies on output distribution entropy without direct weight inspection.",
            "Affine perspective homography exceeding ±10° rotation requires affine invariant keypoint matching.",
            "Cryptographic provenance signatures authenticate post-hoc records but cannot prevent runtime host-memory tampering if the inference execution environment is compromised."
        ]

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
            audit_trail_hash=chain.latest_hash,
            audit_chain=chain_summary,
            provenance_summary=prov_summary
        )
