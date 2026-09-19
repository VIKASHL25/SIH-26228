import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

VALID_ATTACK_TYPES = {
    "label_flip",
    "systematic_mislabel",
    "near_duplicate_flood",
    "ood_insertion",
    "corner_trigger",
    "blended_trigger",
    "spectral_trigger",
    "clean"
}

VALID_SHIFT_TYPES = {
    "illumination",
    "blur",
    "noise",
    "compression",
    "weather"
}

class AttackSampleRecord(BaseModel):
    """
    Standardized machine-readable ground truth record for every sample in the pipeline.
    Preserves all provenance, attack status, shift status, annotations, and parameters.
    """
    sample_id: str
    original_image: str
    current_image: str
    contributor: str
    batch_id: str = "batch_01"
    attack_type: Optional[str] = None
    is_attacked: bool = False
    is_shifted: bool = False
    shift_type: Optional[str] = None
    original_label: Optional[str] = None
    original_label_id: Optional[int] = None
    modified_label: Optional[str] = None
    modified_label_id: Optional[int] = None
    boxes: List[Dict[str, Any]] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source: str = "VisDrone"

def _sanitize_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {str(k): _sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [_sanitize_data(v) for v in data]
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, (np.floating, float)):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    return data

class GroundTruthManifest(BaseModel):
    dataset_name: str = "VisDrone_Assurance_Benchmark"
    dataset_version: str = "1.0.0"
    seed: int = 42
    total_samples: int = 0
    attack_summary: Dict[str, int] = Field(default_factory=dict)
    contributor_summary: Dict[str, int] = Field(default_factory=dict)
    samples: List[AttackSampleRecord] = Field(default_factory=list)

    def save(self, filepath: str or Path):
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        dumped = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        sanitized = _sanitize_data(dumped)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2)

    @classmethod
    def load(cls, filepath: str or Path) -> "GroundTruthManifest":
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Manifest not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

class ManifestValidator:
    """
    Validates manifest integrity according to strict assurance requirements.
    """

    @staticmethod
    def validate(manifest: GroundTruthManifest, base_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
        errors = []
        sample_id_set = set()
        
        for idx, s in enumerate(manifest.samples):
            # 1. Unique sample IDs
            if s.sample_id in sample_id_set:
                errors.append(f"Duplicate sample_id '{s.sample_id}' at index {idx}.")
            sample_id_set.add(s.sample_id)

            # 2. Attack type validity
            if s.is_attacked:
                if not s.attack_type or s.attack_type not in VALID_ATTACK_TYPES:
                    errors.append(f"Sample '{s.sample_id}' marked attacked with invalid attack_type '{s.attack_type}'.")
            else:
                if s.attack_type and s.attack_type not in ("clean", None):
                    errors.append(f"Clean sample '{s.sample_id}' has unexpected attack_type '{s.attack_type}'.")

            # 3. Shift type validity
            if s.is_shifted:
                if not s.shift_type or s.shift_type not in VALID_SHIFT_TYPES:
                    errors.append(f"Sample '{s.sample_id}' marked shifted with invalid shift_type '{s.shift_type}'.")
                if s.is_attacked:
                    errors.append(f"Sample '{s.sample_id}' cannot be marked as both attack and operational shift.")

            # 4. Modified sample has original path recorded
            if s.is_attacked or s.is_shifted:
                if not s.original_image:
                    errors.append(f"Sample '{s.sample_id}' is modified but missing original_image path.")

            # 5. Label modifications check
            if s.attack_type in ("label_flip", "systematic_mislabel"):
                if s.original_label is None or s.modified_label is None:
                    errors.append(f"Sample '{s.sample_id}' under {s.attack_type} missing original or modified label.")
                if s.original_label == s.modified_label and s.original_label_id == s.modified_label_id:
                    errors.append(f"Sample '{s.sample_id}' marked as {s.attack_type} but original and modified labels are identical.")

            # 6. Attack parameter presence
            if s.attack_type == "near_duplicate_flood":
                if "transformation" not in s.parameters:
                    errors.append(f"Near-duplicate sample '{s.sample_id}' missing 'transformation' in parameters.")
                if "original_sample_id" not in s.parameters:
                    errors.append(f"Near-duplicate sample '{s.sample_id}' missing 'original_sample_id' in parameters.")
            elif s.attack_type in ("corner_trigger", "blended_trigger", "spectral_trigger"):
                if "trigger_type" not in s.parameters:
                    errors.append(f"Trigger sample '{s.sample_id}' missing 'trigger_type' in parameters.")

            # 7. File existence on disk if base_dir provided
            if base_dir is not None:
                curr_path = Path(base_dir) / s.current_image if not Path(s.current_image).is_absolute() else Path(s.current_image)
                if not curr_path.exists():
                    errors.append(f"File for sample '{s.sample_id}' does not exist on disk: {curr_path}")

        is_valid = len(errors) == 0
        return is_valid, errors
