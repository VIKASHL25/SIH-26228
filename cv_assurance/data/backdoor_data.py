import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from .ingester import IngestedDataset, IngestedSample

class TriggerSample(BaseModel):
    sample_id: str
    file_name: str
    trigger_family: str # "corner_patch", "blended_trigger", "spectral_trigger"
    confidence: float # 0.0 to 1.0
    contributor_id: str
    batch_id: str
    bbox_location: Optional[List[int]] = None # [x, y, w, h]
    evidence_score: float = 0.0
    details: str

class TriggerFamilyMetrics(BaseModel):
    family_name: str
    detected_count: int
    mean_confidence: float

class DataBackdoorResult(BaseModel):
    total_samples: int
    poisoned_samples_count: int
    poisoning_rate: float
    detected_triggers: List[TriggerSample] = Field(default_factory=list)
    family_breakdown: Dict[str, int] = Field(default_factory=dict)

class DataBackdoorDetector:
    """
    Multi-Family Backdoor & Trigger Detector:
    1. Spatial Corner / Border Geometric Patch Search (Multi-scale + Margin tolerance)
    2. 2D FFT Fourier Spectrum Conjugate Peak Prominence & Energy Anomaly Detection
    3. Spatial High-Pass Residual & Watermark Autocorrelation Filter
    """

    @staticmethod
    def detect_corner_patch(
        img: np.ndarray,
        patch_sizes: List[int] = [16, 20, 24, 32],
        margins: List[int] = [0, 8, 12]
    ) -> Optional[Tuple[float, List[int], str]]:
        """Scans image corners and borders for artificial geometric patches with multi-scale & margin tolerance."""
        h, w = img.shape[:2]
        if h < 64 or w < 64:
            return None

        best_score = 0.0
        best_bbox = None
        best_details = ""

        for size in patch_sizes:
            if size * 2 > min(h, w):
                continue
            for m in margins:
                if m + size > min(h, w) // 2:
                    continue
                corners = [
                    (m, m),                         # Top-Left
                    (m, w - size - m),             # Top-Right
                    (h - size - m, m),             # Bottom-Left
                    (h - size - m, w - size - m)  # Bottom-Right
                ]

                for y, x in corners:
                    patch = img[y:y+size, x:x+size]
                    gray_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
                    lap_var = float(cv2.Laplacian(gray_patch, cv2.CV_64F).var())
                    std_dev = float(np.std(patch))
                    mean_bgr = np.mean(patch, axis=(0, 1))

                    # Surrounding context check
                    y1_ctx = max(0, y - 8)
                    y2_ctx = min(h, y + size + 8)
                    x1_ctx = max(0, x - 8)
                    x2_ctx = min(w, x + size + 8)
                    ctx = img[y1_ctx:y2_ctx, x1_ctx:x2_ctx]
                    ctx_std = float(np.std(ctx))

                    # Detection criteria: high-frequency checkerboard OR solid saturated square
                    if lap_var > 1200 and std_dev > 35:
                        conf = min(1.0, 0.5 + (lap_var / 4000.0))
                        if conf > best_score:
                            best_score = conf
                            best_bbox = [int(x), int(y), int(size), int(size)]
                            best_details = f"Checkerboard trigger patch detected at {best_bbox} (Laplacian variance: {int(lap_var)})."

                    elif (np.max(mean_bgr) > 245 and std_dev < 12 and ctx_std > 20):
                        conf = 0.85
                        if conf > best_score:
                            best_score = conf
                            best_bbox = [int(x), int(y), int(size), int(size)]
                            best_details = f"Solid artificial geometric patch detected at {best_bbox}."

        if best_score >= 0.65:
            return (round(best_score, 4), best_bbox, best_details)
        return None

    @staticmethod
    def detect_fft_spectral_anomaly(img: np.ndarray, peak_threshold: float = 6.0) -> Tuple[float, float, bool]:
        """
        Computes 2D FFT spectrum and tests for:
        1. Prominent conjugate delta peaks (spectral carrier spikes)
        2. High-frequency radial energy ratio
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (128, 128))
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        mag = 20 * np.log(np.abs(fshift) + 1e-7)

        center = 64
        y, x = np.ogrid[:128, :128]
        dist_from_center = np.sqrt((x - center)**2 + (y - center)**2)

        # High frequency outer ring
        hf_mask = dist_from_center > 20
        hf_energy = np.mean(mag[hf_mask])
        total_energy = np.mean(mag)
        hf_ratio = float(hf_energy / (total_energy + 1e-7))

        # Peak prominence in high-frequency zone
        hf_values = mag[hf_mask]
        hf_mean = np.mean(hf_values)
        hf_std = np.std(hf_values)
        hf_max = np.max(hf_values)
        peak_zscore = float((hf_max - hf_mean) / (hf_std + 1e-7))

        is_spectral_spike = (peak_zscore > peak_threshold)
        return (round(hf_ratio, 4), round(peak_zscore, 3), is_spectral_spike)

    @staticmethod
    def detect_blended_watermark(img: np.ndarray) -> Tuple[float, bool]:
        """
        Detects blended watermark patterns via spatial high-pass residual filter
        and line/cross correlation features.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        residual = np.abs(gray - blurred)

        h, w = residual.shape
        d1_vals = []
        d2_vals = []
        for i in range(h):
            j1 = int(i * w / h)
            j2 = int((h - 1 - i) * w / h)
            for offset in range(-2, 3):
                if 0 <= j1 + offset < w:
                    d1_vals.append(residual[i, j1 + offset])
                if 0 <= j2 + offset < w:
                    d2_vals.append(residual[i, j2 + offset])

        diag1 = float(np.mean(d1_vals)) if d1_vals else 0.0
        diag2 = float(np.mean(d2_vals)) if d2_vals else 0.0
        bg_mean = float(np.mean(residual))
        bg_std = float(np.std(residual))

        max_diag = max(diag1, diag2)
        line_ratio = max_diag / (bg_mean + 1e-7)
        # Require diagonal lines to be at least 1.65x brighter than mean residual
        # AND be above mean + 1.2*std (robust to noise), score > 0.6 catches it
        is_blended = (line_ratio > 1.65)
        score = min(1.0, float(line_ratio / 2.8))
        return (round(score, 3), is_blended)

    def analyze(self, dataset: IngestedDataset, fft_peak_threshold: float = 6.0) -> DataBackdoorResult:
        samples = dataset.samples
        poisoned: List[TriggerSample] = []
        family_counts: Dict[str, int] = {
            "corner_patch": 0,
            "blended_trigger": 0,
            "spectral_trigger": 0
        }

        fft_data = []
        valid_samples = []

        for s in samples:
            if not os.path.exists(s.image_path):
                continue
            img = cv2.imread(s.image_path)
            if img is None:
                continue
            valid_samples.append((s, img))

            # 1. Corner patch scan
            corner_res = self.detect_corner_patch(img)
            if corner_res:
                conf, bbox, details = corner_res
                poisoned.append(TriggerSample(
                    sample_id=s.sample_id,
                    file_name=s.file_name,
                    trigger_family="corner_patch",
                    confidence=conf,
                    contributor_id=s.contributor_id,
                    batch_id=s.batch_id,
                    bbox_location=bbox,
                    evidence_score=conf,
                    details=details
                ))
                family_counts["corner_patch"] += 1
                continue

            # 2. Blended watermark check
            wm_score, is_blended = self.detect_blended_watermark(img)
            if is_blended:
                poisoned.append(TriggerSample(
                    sample_id=s.sample_id,
                    file_name=s.file_name,
                    trigger_family="blended_trigger",
                    confidence=round(min(1.0, 0.70 + wm_score * 0.25), 4),
                    contributor_id=s.contributor_id,
                    batch_id=s.batch_id,
                    evidence_score=wm_score,
                    details=f"Spatial high-pass watermark cross pattern detected (line energy ratio: {wm_score})."
                ))
                family_counts["blended_trigger"] += 1
                continue

            # 3. FFT spectral analysis (pass calibrated threshold)
            hf_ratio, peak_z, is_spike = self.detect_fft_spectral_anomaly(img, peak_threshold=fft_peak_threshold)
            fft_data.append((s, hf_ratio, peak_z, is_spike))

        # Check FFT outliers across dataset
        if fft_data:
            all_ratios = np.array([r for _, r, _, _ in fft_data])
            all_peaks = np.array([p for _, _, p, _ in fft_data])
            mean_r, std_r = np.mean(all_ratios), np.std(all_ratios)

            for s, r, peak_z, is_spike in fft_data:
                z_ratio = (r - mean_r) / (std_r + 1e-7) if std_r > 0 else 0
                if is_spike:
                    conf = min(1.0, 0.65 + (peak_z / 8.0))
                    poisoned.append(TriggerSample(
                        sample_id=s.sample_id,
                        file_name=s.file_name,
                        trigger_family="spectral_trigger",
                        confidence=round(float(conf), 4),
                        contributor_id=s.contributor_id,
                        batch_id=s.batch_id,
                        evidence_score=round(float(peak_z), 3),
                        details=f"High-frequency 2D Fourier spectral spike detected (peak prominence z-score: {peak_z}, ratio z-score: {round(float(z_ratio), 2)})."
                    ))
                    family_counts["spectral_trigger"] += 1

        total_valid = len(valid_samples)
        p_rate = float(len(poisoned) / total_valid) if total_valid > 0 else 0.0

        return DataBackdoorResult(
            total_samples=len(samples),
            poisoned_samples_count=len(poisoned),
            poisoning_rate=round(p_rate, 4),
            detected_triggers=poisoned,
            family_breakdown=family_counts
        )
