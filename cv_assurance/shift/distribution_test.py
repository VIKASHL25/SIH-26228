from scipy.stats import ks_2samp, wasserstein_distance
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
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
    evidence_details: Dict[str, Any] = Field(default_factory=dict)

class DistributionShiftDetector:
    """
    Detects material deviation from declared reference distribution across domain features:
    Terrain, Illumination, Sensor, and Season/Acquisition.
    Distinguishes legitimate operational environmental drift from suspicious synthetic manipulation.
    """
    
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
                summary_findings="Insufficient samples to perform environmental distribution shift comparison.",
                evidence_details={"reason": "empty_metrics"}
            )

        # Build feature arrays across all 4 declared physical dimensions
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
        evidence: Dict[str, Any] = {}

        for dim_name, (ref_arr, tgt_arr) in dims.items():
            ks_res = ks_2samp(ref_arr, tgt_arr)
            ks_stat = float(ks_res.statistic)
            p_val = float(ks_res.pvalue)
            w_dist = float(wasserstein_distance(ref_arr, tgt_arr))

            # Material shift threshold: p-value < 0.10 or significant KS distance or Wasserstein displacement
            shift_flag = (p_val < 0.10 or ks_stat >= 0.25 or w_dist >= 1.5)
            p_values.append(p_val)
            w_dists.append(w_dist)

            evidence[dim_name] = {
                "ks_stat": round(ks_stat, 4),
                "p_value": round(p_val, 4),
                "wasserstein_distance": round(w_dist, 4),
                "shift_detected": shift_flag
            }

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

        # Rigorous discrimination: OPERATIONAL_DRIFT vs SUSPICIOUS_MANIPULATION vs NO_SHIFT
        sensor_shifted = any(d.dimension_name == "sensor" and d.shift_detected for d in shifted_dims)
        season_shifted = any(d.dimension_name == "season" and d.shift_detected for d in shifted_dims)
        illum_shifted = any(d.dimension_name == "illumination" and d.shift_detected for d in shifted_dims)
        terrain_shifted = any(d.dimension_name == "terrain" and d.shift_detected for d in shifted_dims)

        sensor_detail = next((d for d in dim_details if d.dimension_name == "sensor"), None)
        sensor_severe = (sensor_detail and (sensor_detail.ks_statistic >= 0.35 or sensor_detail.wasserstein_dist >= 3.0))

        if not material_shift:
            classification = "NO_SHIFT"
            confidence = 0.95
            summary = "Target evaluation dataset closely aligns with reference environmental baseline across all dimensions."
        elif sensor_severe and not (season_shifted or illum_shifted):
            # Severe sensor noise dislocation without seasonal/natural illumination continuity indicates synthetic noise or camera injection
            classification = "SUSPICIOUS_MANIPULATION"
            confidence = 0.88
            summary = (
                "Abrupt sensor noise floor and high-frequency distortion detected without corresponding "
                "seasonal/natural illumination transitions. Statistical evidence indicates potential synthetic tampering, "
                "adversarial noise floor perturbation, or sensor injection."
            )
        elif sensor_shifted and not (season_shifted or illum_shifted or terrain_shifted):
            classification = "SUSPICIOUS_MANIPULATION"
            confidence = 0.82
            summary = (
                "Isolated sensor noise anomaly observed in absence of physical environmental shifts. "
                "Unlikely to be explained by weather or terrain transitions."
            )
        else:
            # Shift observed across natural dimensions (illumination, season, terrain) represents expected operational drift
            classification = "OPERATIONAL_DRIFT"
            confidence = 0.90
            summary = (
                f"Natural operational environmental drift observed across {len(shifted_dims)} dimensions "
                f"({', '.join(d.dimension_name for d in shifted_dims)}). Physical domain properties remain coherent."
            )

        evidence["classification"] = classification
        evidence["shifted_dimensions_count"] = len(shifted_dims)

        return DistributionShiftResult(
            reference_sample_count=len(ref_metrics),
            target_sample_count=len(target_metrics),
            overall_drift_score=drift_score,
            material_shift_detected=material_shift,
            shift_classification=classification,
            confidence_score=confidence,
            dimensions=dim_details,
            summary_findings=summary,
            evidence_details=evidence
        )
