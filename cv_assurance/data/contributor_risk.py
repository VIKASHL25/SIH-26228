from typing import List, Dict, Any
from pydantic import BaseModel
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
    recommended_action: str

class ContributorRiskResult(BaseModel):
    total_contributors: int
    high_risk_contributors_count: int
    profiles: List[ContributorRiskProfile]

class ContributorRiskAggregator:
    """Aggregates sample-level integrity findings into source/contributor risk scores."""
    
    def aggregate(
        self,
        dataset: IngestedDataset,
        duplicates_res: DuplicateAnalysisResult,
        labels_res: LabelIntegrityResult,
        ood_res: OODAnalysisResult,
        backdoor_res: DataBackdoorResult
    ) -> ContributorRiskResult:
        
        contrib_map: Dict[str, Dict[str, Any]] = {}
        
        # Initialize map with all samples per contributor
        for s in dataset.samples:
            cid = s.contributor_id
            if cid not in contrib_map:
                contrib_map[cid] = {
                    "total": 0,
                    "dup_set": set(),
                    "label_set": set(),
                    "ood_set": set(),
                    "poison_set": set()
                }
            contrib_map[cid]["total"] += 1

        # Populate duplicates
        for pair in duplicates_res.duplicate_pairs:
            if pair.contributor_a in contrib_map:
                contrib_map[pair.contributor_a]["dup_set"].add(pair.sample_id_a)
            if pair.contributor_b in contrib_map:
                contrib_map[pair.contributor_b]["dup_set"].add(pair.sample_id_b)

        # Populate mislabelled
        for m in labels_res.flagged_samples:
            cid = m.contributor_id
            if cid in contrib_map:
                contrib_map[cid]["label_set"].add(m.sample_id)

        # Populate OOD
        for o in ood_res.ood_samples:
            cid = o.contributor_id
            if cid in contrib_map:
                contrib_map[cid]["ood_set"].add(o.sample_id)

        # Populate backdoor/poisoned
        for p in backdoor_res.detected_triggers:
            cid = p.contributor_id
            if cid in contrib_map:
                contrib_map[cid]["poison_set"].add(p.sample_id)

        profiles: List[ContributorRiskProfile] = []
        high_risk_count = 0

        for cid, data in contrib_map.items():
            tot = data["total"]
            dup_c = len(data["dup_set"])
            lbl_c = len(data["label_set"])
            ood_c = len(data["ood_set"])
            poi_c = len(data["poison_set"])

            all_flagged = data["dup_set"] | data["label_set"] | data["ood_set"] | data["poison_set"]
            flagged_tot = len(all_flagged)

            # Weighted risk scoring
            # Poisoning carries heaviest weight, followed by mislabelling, OOD, and duplicates
            raw_risk = (
                (poi_c * 1.0) +
                (lbl_c * 0.7) +
                (ood_c * 0.5) +
                (dup_c * 0.3)
            ) / max(1, tot)

            risk_score = round(float(min(1.0, raw_risk)), 4)

            if risk_score >= 0.6 or poi_c > 0:
                risk_level = "CRITICAL"
                action = "QUARANTINE_CONTRIBUTOR: Revoke batch contributions immediately and perform forensic audit."
            elif risk_score >= 0.3 or lbl_c >= 3:
                risk_level = "HIGH"
                action = "REVIEW_CONTRIBUTOR: Hold dataset batch for human annotation verification."
            elif risk_score >= 0.1:
                risk_level = "MEDIUM"
                action = "FLAG_FOR_MONITORING: Monitor future submissions for quality anomalies."
            else:
                risk_level = "CLEAN"
                action = "ACCEPT: Contributor data passes integrity verification standards."

            if risk_level in ["CRITICAL", "HIGH"]:
                high_risk_count += 1

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
                recommended_action=action
            ))

        return ContributorRiskResult(
            total_contributors=len(profiles),
            high_risk_contributors_count=high_risk_count,
            profiles=profiles
        )
