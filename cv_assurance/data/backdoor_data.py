import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel
from .ingester import IngestedDataset, IngestedSample

class TriggerSample(BaseModel):
    sample_id: str
    file_name: str
    trigger_type: str # "corner_patch", "high_freq_pattern", "spectral_anomaly"
    confidence: float # 0.0 to 1.0
    contributor_id: str
    batch_id: str
    bbox_location: Optional[List[int]] # [x, y, w, h] of suspected trigger patch
    details: str

class DataBackdoorResult(BaseModel):
    total_samples: int
    poisoned_samples_count: int
    poisoning_rate: float
    detected_triggers: List[TriggerSample]

class DataBackdoorDetector:
    """
    Detects trigger injection and data poisoning attacks (e.g. BadNets, Blended, Spectral Trigger).
    Applies spatial frequency analysis (FFT), high-pass patch search, and corner trigger detection.
    """
    
    @staticmethod
    def detect_corner_patch(img: np.ndarray, patch_size: int = 16) -> Optional[Tuple[float, List[int]]]:
        """Scans image corners for artificial high-contrast/rigid geometric patches."""
        h, w, c = img.shape
        if h < patch_size * 2 or w < patch_size * 2:
            return None

        corners = [
            (0, 0), # Top-Left
            (0, w - patch_size), # Top-Right
            (h - patch_size, 0), # Bottom-Left
            (h - patch_size, w - patch_size) # Bottom-Right
        ]

        for y, x in corners:
            patch = img[y:y+patch_size, x:x+patch_size]
            # Check patch variance vs surrounding area
            std_dev = np.std(patch)
            # Check for pure color or rigid pattern (e.g. checkerboard / white square / red patch)
            gray_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            # High frequency checkerboard pattern has high laplacian variance
            lap = cv2.Laplacian(gray_patch, cv2.CV_64F).var()
            
            # Check if patch is abnormally bright or has distinct pattern
            mean_bgr = np.mean(patch, axis=(0, 1))
            if (lap > 1500 and std_dev > 45) or (np.max(mean_bgr) > 240 and std_dev < 10):
                conf = float(min(1.0, (lap / 3000.0) + 0.5))
                return (conf, [x, y, patch_size, patch_size])
        return None

    @staticmethod
    def detect_fft_spectral_anomaly(img: np.ndarray) -> float:
        """Detects high-frequency periodic noise artifacts inserted into images via FFT spectrum."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (128, 128))
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-7)
        
        # High frequency energy ratio
        center = 64
        r = 16
        y, x = np.ogrid[:128, :128]
        mask = (x - center)**2 + (y - center)**2 > r**2
        high_freq_energy = np.mean(magnitude_spectrum[mask])
        total_energy = np.mean(magnitude_spectrum)
        
        ratio = high_freq_energy / (total_energy + 1e-7)
        return float(ratio)

    def analyze(self, dataset: IngestedDataset) -> DataBackdoorResult:
        samples = dataset.samples
        poisoned: List[TriggerSample] = []
        
        fft_ratios = []
        valid_samples = []

        for s in samples:
            if not os.path.exists(s.image_path):
                continue
            img = cv2.imread(s.image_path)
            if img is None:
                continue

            valid_samples.append((s, img))
            # 1. Corner patch check
            patch_result = self.detect_corner_patch(img)
            if patch_result:
                conf, bbox = patch_result
                poisoned.append(TriggerSample(
                    sample_id=s.sample_id,
                    file_name=s.file_name,
                    trigger_type="corner_patch",
                    confidence=round(conf, 4),
                    contributor_id=s.contributor_id,
                    batch_id=s.batch_id,
                    bbox_location=bbox,
                    details=f"High-contrast artificial patch detected at image corner {bbox}."
                ))
                continue

            # 2. Spectral ratio
            ratio = self.detect_fft_spectral_anomaly(img)
            fft_ratios.append((s, ratio))

        # Check for FFT outliers
        if fft_ratios:
            ratios = np.array([r for _, r in fft_ratios])
            mean_r, std_r = np.mean(ratios), np.std(ratios)
            if std_r > 0:
                for s, r in fft_ratios:
                    z_score = (r - mean_r) / std_r
                    if z_score > 3.0: # Extreme high-frequency spectral outlier
                        poisoned.append(TriggerSample(
                            sample_id=s.sample_id,
                            file_name=s.file_name,
                            trigger_type="high_freq_pattern",
                            confidence=round(min(1.0, float(z_score / 5.0)), 4),
                            contributor_id=s.contributor_id,
                            batch_id=s.batch_id,
                            bbox_location=None,
                            details=f"High-frequency periodic spectral anomaly detected (z-score: {round(float(z_score), 2)})."
                        ))

        total_valid = len(valid_samples)
        p_rate = float(len(poisoned) / total_valid) if total_valid > 0 else 0.0

        return DataBackdoorResult(
            total_samples=len(samples),
            poisoned_samples_count=len(poisoned),
            poisoning_rate=round(p_rate, 4),
            detected_triggers=poisoned
        )
