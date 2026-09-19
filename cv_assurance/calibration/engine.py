import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class DuplicateThresholdConfig(BaseModel):
    hash_candidate_threshold: int = 6
    ssim_confirmation_threshold: float = 0.82
    normalized_mae_threshold: float = 0.15
    flooding_ratio_warning: float = 0.10
    flooding_ratio_critical: float = 0.25

class LabelThresholdConfig(BaseModel):
    knn_neighbors: int = 5
    min_consensus_threshold: float = 0.60
    centroid_distance_margin: float = 0.05
    high_confidence_consensus: float = 0.80

class OODThresholdConfig(BaseModel):
    contamination_rate: float = 0.05
    anomaly_score_threshold: float = 0.65

class TriggerThresholdConfig(BaseModel):
    corner_variance_threshold: float = 800.0
    corner_contrast_threshold: float = 35.0
    fft_peak_prominence_zscore: float = 2.8
    fft_high_freq_ratio_zscore: float = 2.5
    watermark_residual_threshold: float = 0.18

class ContributorRiskThresholdConfig(BaseModel):
    critical_risk_cutoff: float = 0.50
    high_risk_cutoff: float = 0.30
    medium_risk_cutoff: float = 0.15
    min_sample_volume_significance: int = 5

class CalibratedThresholdSet(BaseModel):
    duplicate: DuplicateThresholdConfig = Field(default_factory=DuplicateThresholdConfig)
    label: LabelThresholdConfig = Field(default_factory=LabelThresholdConfig)
    ood: OODThresholdConfig = Field(default_factory=OODThresholdConfig)
    trigger: TriggerThresholdConfig = Field(default_factory=TriggerThresholdConfig)
    contributor: ContributorRiskThresholdConfig = Field(default_factory=ContributorRiskThresholdConfig)
    calibration_dataset_name: str = "Clean_Calibration_Partition"
    calibration_sample_count: int = 0

    def save(self, config_dir: str = "calibration"):
        p = Path(config_dir)
        p.mkdir(parents=True, exist_ok=True)
        with open(p / "duplicate_thresholds.json", "w", encoding="utf-8") as f:
            json.dump(self.duplicate.model_dump(), f, indent=2)
        with open(p / "label_thresholds.json", "w", encoding="utf-8") as f:
            json.dump(self.label.model_dump(), f, indent=2)
        with open(p / "ood_thresholds.json", "w", encoding="utf-8") as f:
            json.dump(self.ood.model_dump(), f, indent=2)
        with open(p / "trigger_thresholds.json", "w", encoding="utf-8") as f:
            json.dump(self.trigger.model_dump(), f, indent=2)
        with open(p / "contributor_thresholds.json", "w", encoding="utf-8") as f:
            json.dump(self.contributor.model_dump(), f, indent=2)
        with open(p / "master_calibration.json", "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)

    @classmethod
    def load(cls, config_dir: str = "calibration") -> "CalibratedThresholdSet":
        p = Path(config_dir)
        master_file = p / "master_calibration.json"
        if master_file.exists():
            with open(master_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        return cls()

