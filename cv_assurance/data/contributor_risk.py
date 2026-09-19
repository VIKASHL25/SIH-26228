import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .ingester import IngestedDataset
from .duplicates import DuplicateAnalysisResult
from .label_integrity import LabelIntegrityResult
from .ood_detector import OODAnalysisResult
from .backdoor_data import DataBackdoorResult

class ContributorRiskProfile(BaseModel):
    contributor_id: str
    total_samples: int
    flagged_samples_count: int
    risk_score: float # 0.0 to 1.0
    risk_level: str # "CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAN"
    duplicate_count: int
    mislabelled_count: int
    ood_count: int
    poisoned_count: int
    duplicate_evidence: float = 0.0
    label_evidence: float = 0.0
    ood_evidence: float = 0.0
    trigger_evidence: float = 0.0
    dominant_risk_factor: str = "None"
    recommended_action: str
    explanation: str

class ContributorRiskResult(BaseModel):
    total_contributors: int
    high_risk_contributors_count: int
    clean_contributors_count: int
    profiles: List[ContributorRiskProfile] = Field(default_factory=list)

class ContributorRiskAggregator:
    """
    Volume-Normalized & Confidence-Weighted Contributor Risk Aggregator.
    
    Evaluates multi-contributor integrity across 4 distinct evidence dimensions:
    1. Near-Duplicate Flooding Evidence (normalized by contributor volume)
    2. Label Integrity & Systematic Confusion Evidence
    3. Out-of-Distribution (OOD) Operational Anomaly Evidence
    4. Poisoning & Backdoor Trigger Contamination Evidence
    
    Guarantees clean contributors with natural variation are retained as CLEAN/ACCEPT.
    """

    def aggregate(
        self,
        dataset: IngestedDataset,
        duplicates_res: DuplicateAnalysisResult,
        labels_res: LabelIntegrityResult,
        ood_res: OODAnalysisResult,
        backdoor_res: DataBackdoorResult,
        critical_cutoff: float = 0.50,
        high_cutoff: float = 0.28,
        medium_cutoff: float = 0.12
    ) -> ContributorRiskResult:

        contrib_map: Dict[str, Dict[str, Any]] = {}

        # 1. Initialize per-contributor buckets
        for s in dataset.samples:
            cid = s.contributor_id
            if cid not in contrib_map:
                contrib_map[cid] = {
                    "total": 0,
                    "dup_samples": set(),
                    "label_samples": {},  # sample_id -> confidence_weight
                    "ood_samples": set(),
                    "poison_samples": {}, # sample_id -> confidence_weight
                }
            contrib_map[cid]["total"] += 1

        # 2. Populate duplicate findings (same-contributor pairs only = flooding evidence)
        for pair in duplicates_res.duplicate_pairs:
            if pair.is_confirmed and pair.contributor_a == pair.contributor_b:
                if pair.contributor_a in contrib_map:
                    contrib_map[pair.contributor_a]["dup_samples"].add(pair.sample_id_a)
                    contrib_map[pair.contributor_a]["dup_samples"].add(pair.sample_id_b)

        # 3. Populate label findings with confidence weighting
        for m in labels_res.flagged_samples:
            cid = m.contributor_id
            if cid in contrib_map:
                weight = 1.0 if m.confidence_level == "HIGH" else (0.6 if m.confidence_level == "MEDIUM" else 0.3)
                contrib_map[cid]["label_samples"][m.sample_id] = weight

        # 4. Populate OOD findings
        for o in ood_res.ood_samples:
            cid = o.contributor_id
            if cid in contrib_map:
                contrib_map[cid]["ood_samples"].add(o.sample_id)

        # 5. Populate backdoor findings with confidence weighting
        for p in backdoor_res.detected_triggers:
            cid = p.contributor_id
            if cid in contrib_map:
                contrib_map[cid]["poison_samples"][p.sample_id] = p.confidence

        # Check systematic label confusion per contributor
        systematic_contribs = set()
        for cstat in getattr(labels_res, "contributor_confusion_stats", []):
            if cstat.is_systematic:
                systematic_contribs.add(cstat.contributor_id)

        # Check duplicate flooding per contributor
        flooding_contribs = set()
        for fstat in getattr(duplicates_res, "contributor_flooding_stats", []):
            if fstat.is_flooding_suspected:
                flooding_contribs.add(fstat.contributor_id)

        profiles: List[ContributorRiskProfile] = []
        high_risk_count = 0
        clean_count = 0

        for cid, data in contrib_map.items():
            tot = max(1, data["total"])
            dup_c = len(data["dup_samples"])
            lbl_c = len(data["label_samples"])
            ood_c = len(data["ood_samples"])
            poi_c = len(data["poison_samples"])

            all_flagged = data["dup_samples"] | set(data["label_samples"].keys()) | data["ood_samples"] | set(data["poison_samples"].keys())
            flagged_tot = len(all_flagged)

            # Volume-normalized evidence scores (0.0 to 1.0)
            dup_ratio = dup_c / tot
            if cid in flooding_contribs or (dup_c >= 2 and dup_ratio >= 0.20):
                dup_evidence = min(1.0, dup_ratio * 2.0)
            else:
                dup_evidence = min(0.3, dup_ratio)

            lbl_weighted_sum = sum(data["label_samples"].values())
            lbl_ratio = lbl_weighted_sum / tot
            lbl_evidence = min(1.0, lbl_ratio * 2.5)
            if cid in systematic_contribs:
                lbl_evidence = min(1.0, lbl_evidence + 0.35)

            ood_ratio = ood_c / tot
            ood_evidence = min(1.0, ood_ratio * 1.5) # Anomaly signal

            poi_weighted_sum = sum(data["poison_samples"].values())
            poi_ratio = poi_weighted_sum / tot
            poi_evidence = min(1.0, poi_ratio * 4.0) if poi_c > 0 else 0.0

            # Composite weighted risk score
            # Backdoor triggers carry highest weight, followed by systematic label manipulations and flooding
            raw_risk = (
                (0.40 * poi_evidence) +
                (0.30 * lbl_evidence) +
                (0.20 * dup_evidence) +
                (0.10 * ood_evidence)
            )

            # High confidence trigger override
            if any(conf >= 0.75 for conf in data["poison_samples"].values()):
                raw_risk = max(raw_risk, 0.60)
            elif (flagged_tot / tot >= 0.40) and (dup_evidence >= 0.50 or lbl_evidence >= 0.50):
                raw_risk = max(raw_risk, 0.35)

            risk_score = round(float(min(1.0, max(0.0, raw_risk))), 4)

            # Determine dominant risk factor
            evidence_dict = {
                "Backdoor Triggers": poi_evidence,
                "Label Manipulation": lbl_evidence,
                "Duplicate Flooding": dup_evidence,
                "OOD Anomaly": ood_evidence
            }
            top_factor = max(evidence_dict, key=evidence_dict.get)
            if max(evidence_dict.values()) == 0:
                top_factor = "None"

            # Risk level classification
            if risk_score >= critical_cutoff or poi_c >= 2:
                risk_level = "CRITICAL"
                action = "QUARANTINE_CONTRIBUTOR: Immediate batch isolation and forensic provenance audit."
                explanation = f"Critical risk driven by {top_factor} (Trigger score: {round(poi_evidence, 2)}, Label score: {round(lbl_evidence, 2)})."
            elif risk_score >= high_cutoff or (cid in systematic_contribs and lbl_c >= 3) or (cid in flooding_contribs and dup_c >= 3):
                risk_level = "HIGH"
                action = "REVIEW_CONTRIBUTOR: Hold dataset batch for manual domain expert annotation review."
                explanation = f"High risk driven by {top_factor} (evidence score: {round(evidence_dict[top_factor], 2)})."
            elif risk_score >= medium_cutoff:
                risk_level = "MEDIUM"
                action = "FLAG_FOR_MONITORING: Tag batch submissions for elevated sampling in subsequent validation cycles."
                explanation = f"Moderate anomalies observed, primarily {top_factor}."
            else:
                risk_level = "CLEAN"
                action = "ACCEPT: Contributor data passes integrity verification standards."
                explanation = "Sample-level variation remains within expected baseline noise tolerances."

            if risk_level in ["CRITICAL", "HIGH"]:
                high_risk_count += 1
            elif risk_level == "CLEAN":
                clean_count += 1

            profiles.append(ContributorRiskProfile(
                contributor_id=cid,
                total_samples=tot,
                flagged_samples_count=flagged_tot,
                risk_score=risk_score,
                risk_level=risk_level,
                duplicate_count=dup_c,
                mislabelled_count=lbl_c,
                ood_count=ood_c,
                poisoned_count=poi_c,
                duplicate_evidence=round(float(dup_evidence), 4),
                label_evidence=round(float(lbl_evidence), 4),
                ood_evidence=round(float(ood_evidence), 4),
                trigger_evidence=round(float(poi_evidence), 4),
                dominant_risk_factor=top_factor,
                recommended_action=action,
                explanation=explanation
            ))

        return ContributorRiskResult(
            total_contributors=len(profiles),
            high_risk_contributors_count=high_risk_count,
            clean_contributors_count=clean_count,
            profiles=profiles
        )
