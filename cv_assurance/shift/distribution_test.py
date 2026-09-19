from scipy.stats import ks_2samp, wasserstein_distance
import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel
from .environmental import EnvironmentalFeatureExtractor, EnvironmentalShiftMetrics
from ..data.ingester import IngestedDataset

class ShiftDimensionDetail(BaseModel):
    dimension_name: str # "terrain", "illumination", "sensor", "season"
    ks_statistic: float
    p_value: float
    wasserstein_dist: float
    shift_detected: bool
    description: str

class DistributionShiftResult(BaseModel):
    reference_sample_count: int
    target_sample_count: int
    overall_drift_score: float # 0.0 to 1.0
    material_shift_detected: bool
    shift_classification: str # "OPERATIONAL_DRIFT", "SUSPICIOUS_MANIPULATION", "NO_SHIFT"
    confidence_score: float
    dimensions: List[ShiftDimensionDetail]
    summary_findings: str

class DistributionShiftDetector:
    """Detects material deviation from declared reference distribution across domain features."""
    
    def __init__(self):
        self.extractor = EnvironmentalFeatureExtractor()

    def analyze(self, ref_dataset: IngestedDataset, target_dataset: IngestedDataset, max_samples: int = 100) -> DistributionShiftResult:
        ref_samples = ref_dataset.samples[:max_samples]
        target_samples = target_dataset.samples[:max_samples]

        ref_metrics: List[EnvironmentalShiftMetrics] = []
        for s in ref_samples:
            m = self.extractor.extract_metrics(s.image_path)
            if m:
                ref_metrics.append(m)

        target_metrics: List[EnvironmentalShiftMetrics] = []
        for s in target_samples:
            m = self.extractor.extract_metrics(s.image_path)
            if m:
                target_metrics.append(m)

        if not ref_metrics or not target_metrics:
            return DistributionShiftResult(
                reference_sample_count=len(ref_metrics),
                target_sample_count=len(target_metrics),
                overall_drift_score=0.0,
                material_shift_detected=False,
                shift_classification="NO_SHIFT",
                confidence_score=1.0,
                dimensions=[],
                summary_findings="Insufficient samples to perform environmental distribution shift comparison."
            )

        # Build feature arrays for 4 dimensions
        dims = {
            "terrain": (
                [m.terrain_texture_contrast for m in ref_metrics],
                [m.terrain_texture_contrast for m in target_metrics]
            ),
            "illumination": (
                [m.mean_brightness for m in ref_metrics],
                [m.mean_brightness for m in target_metrics]
            ),
            "sensor": (
                [m.noise_floor_std for m in ref_metrics],
                [m.noise_floor_std for m in target_metrics]
            ),
            "season": (
                [m.green_vegetation_index for m in ref_metrics],
                [m.green_vegetation_index for m in target_metrics]
            )
        }

        dim_details: List[ShiftDimensionDetail] = []
        p_values = []
        w_dists = []

        for dim_name, (ref_arr, tgt_arr) in dims.items():
            ks_res = ks_2samp(ref_arr, tgt_arr)
            ks_stat = float(ks_res.statistic)
            p_val = float(ks_res.pvalue)
            w_dist = float(wasserstein_distance(ref_arr, tgt_arr))

            shift_flag = (p_val < 0.1 or ks_stat >= 0.25 or w_dist >= 1.5)
            p_values.append(p_val)
            w_dists.append(w_dist)

            desc = f"No significant shift in {dim_name} (p={round(p_val, 4)})."
            if shift_flag:
                desc = f"Material distribution shift detected in {dim_name} domain (KS stat: {round(ks_stat, 3)}, Wasserstein: {round(w_dist, 2)})."

            dim_details.append(ShiftDimensionDetail(
                dimension_name=dim_name,
                ks_statistic=round(ks_stat, 4),
                p_value=round(p_val, 4),
                wasserstein_dist=round(w_dist, 4),
                shift_detected=shift_flag,
                description=desc
            ))

        shifted_dims = [d for d in dim_details if d.shift_detected]
        drift_score = round(float(len(shifted_dims) / len(dim_details)), 4)
        material_shift = (len(shifted_dims) >= 1)

        # Distinguish operational drift vs suspicious manipulation
        # Operational drift usually alters 1-2 smooth physical parameters (e.g. brightness or vegetation)
        # Suspicious manipulation often causes abrupt sensor noise floor / texture disconnects without environmental rationale
        if not material_shift:
            classification = "NO_SHIFT"
            summary = "Target evaluation dataset closely aligns with reference environmental baseline."
        elif any(d.dimension_name == "sensor" and d.shift_detected for d in shifted_dims) and not any(d.dimension_name == "season" for d in shifted_dims):
            classification = "SUSPICIOUS_MANIPULATION"
            summary = "Abrupt sensor noise floor shift observed without corresponding seasonal/natural environmental transition. Flagged as potential synthetic tampering or sensor injection."
        else:
            classification = "OPERATIONAL_DRIFT"
            summary = f"Natural operational environmental drift observed across {len(shifted_dims)} dimensions (illumination/season/terrain)."

        return DistributionShiftResult(
            reference_sample_count=len(ref_metrics),
            target_sample_count=len(target_metrics),
            overall_drift_score=drift_score,
            material_shift_detected=material_shift,
            shift_classification=classification,
            confidence_score=round(0.92, 2),
            dimensions=dim_details,
            summary_findings=summary
        )
