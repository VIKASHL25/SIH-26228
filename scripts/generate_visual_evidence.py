import os
import sys
import cv2
import numpy as np
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.data.visdrone import VisDroneBenchmarkSynthesizer
from cv_assurance.attacks.duplicate_attacks import NearDuplicateFloodingAttack
from cv_assurance.attacks.label_attacks import SystematicMislabellingAttack
from cv_assurance.attacks.ood_attacks import OODInsertionAttack
from cv_assurance.attacks.trigger_attacks import CornerTriggerAttack, BlendedTriggerAttack, SpectralTriggerAttack
from cv_assurance.data.duplicates import DuplicateDetector

def generate_visual_evidence_assets(output_dir: str = "data/visual_evidence", seed: int = 42):
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    print(f"[*] Generating Visual Evidence Artifacts in: {p}")

    # Generate clean reference aerial image
    clean_img, boxes = VisDroneBenchmarkSynthesizer.generate_aerial_sample(1, seed=seed)
    h, w = clean_img.shape[:2]

    # 1. Duplicate Evidence
    dup_atk = NearDuplicateFloodingAttack(transformation="jpeg_compression", seed=seed)
    dup_res = dup_atk.apply(clean_img, boxes)
    ssim_val = DuplicateDetector.compute_ssim(clean_img, dup_res.modified_image)

    dup_panel = np.hstack([clean_img, dup_res.modified_image])
    cv2.putText(dup_panel, "ORIGINAL CLEAN", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(dup_panel, f"NEAR-DUPLICATE (SSIM: {ssim_val:.3f})", (w + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(str(p / "01_duplicate_flooding_evidence.jpg"), dup_panel)

    # 2. Label Manipulation Evidence
    lbl_atk = SystematicMislabellingAttack(categories={4: "car", 5: "van"}, seed=seed)
    lbl_res = lbl_atk.apply(clean_img, boxes)
    lbl_panel = np.hstack([clean_img, lbl_res.modified_image])
    cv2.putText(lbl_panel, f"ORIGINAL: {lbl_res.original_label.upper()}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(lbl_panel, f"CONFUSED LABEL: {lbl_res.modified_label.upper()}", (w + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(str(p / "02_label_manipulation_evidence.jpg"), lbl_panel)

    # 3. OOD Insertion Evidence
    ood_atk = OODInsertionAttack(seed=seed)
    ood_res = ood_atk.apply(clean_img, boxes)
    ood_panel = np.hstack([clean_img, ood_res.modified_image])
    cv2.putText(ood_panel, "IN-DISTRIBUTION AERIAL", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(ood_panel, "OOD ANOMALY INSERTION", (w + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(str(p / "03_ood_insertion_evidence.jpg"), ood_panel)

    # 4. Corner Trigger Evidence
    corner_atk = CornerTriggerAttack(trigger_size=24, position="top_right", opacity=0.95, seed=seed)
    corner_res = corner_atk.apply(clean_img, boxes)
    corner_panel = np.hstack([clean_img, corner_res.modified_image])
    cv2.putText(corner_panel, "CLEAN REFERENCE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(corner_panel, "BADNETS CORNER TRIGGER", (w + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    # Highlight patch box
    bx, by, bw, bh = corner_res.parameters["bbox"]
    cv2.rectangle(corner_panel, (w + bx - 2, by - 2), (w + bx + bw + 2, by + bh + 2), (0, 0, 255), 2)
    cv2.imwrite(str(p / "04_corner_trigger_evidence.jpg"), corner_panel)

    # 5. Blended Trigger Evidence
    blend_atk = BlendedTriggerAttack(alpha=0.18, seed=seed)
    blend_res = blend_atk.apply(clean_img, boxes)
    blend_panel = np.hstack([clean_img, blend_res.modified_image])
    cv2.putText(blend_panel, "CLEAN REFERENCE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(blend_panel, "BLENDED WATERMARK (alpha=0.18)", (w + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(str(p / "05_blended_trigger_evidence.jpg"), blend_panel)

    # 6. Spectral Trigger Evidence & 2D FFT Spectrum
    spectral_atk = SpectralTriggerAttack(frequency_strength=14.0, seed=seed)
    spectral_res = spectral_atk.apply(clean_img, boxes)

    # Compute FFT spectra
    g_clean = cv2.cvtColor(clean_img, cv2.COLOR_BGR2GRAY)
    f_clean = np.fft.fftshift(np.fft.fft2(g_clean))
    mag_clean = 20 * np.log(np.abs(f_clean) + 1e-7)
    norm_mag_clean = cv2.normalize(mag_clean, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    color_mag_clean = cv2.applyColorMap(norm_mag_clean, cv2.COLORMAP_VIRIDIS)

    g_spec = cv2.cvtColor(spectral_res.modified_image, cv2.COLOR_BGR2GRAY)
    f_spec = np.fft.fftshift(np.fft.fft2(g_spec))
    mag_spec = 20 * np.log(np.abs(f_spec) + 1e-7)
    norm_mag_spec = cv2.normalize(mag_spec, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    color_mag_spec = cv2.applyColorMap(norm_mag_spec, cv2.COLORMAP_VIRIDIS)

    spec_panel = np.hstack([color_mag_clean, color_mag_spec])
    cv2.putText(spec_panel, "CLEAN 2D FFT SPECTRUM", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(spec_panel, "POISONED FFT CARRIER SPIKES", (w + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(str(p / "06_spectral_trigger_fft_evidence.jpg"), spec_panel)

    print(f"[+] Successfully generated 6 visual evidence panels in '{p}'")

def main():
    generate_visual_evidence_assets()

if __name__ == "__main__":
    main()
