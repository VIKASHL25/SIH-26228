import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class EnvironmentalShiftMetrics(BaseModel):
    # 1. Terrain metrics
    terrain_texture_contrast: float
    terrain_color_hist_energy: float
    
    # 2. Illumination metrics
    mean_brightness: float # 0 to 255
    contrast_std: float
    hsv_value_mean: float
    low_light_ratio: float
    overexposure_ratio: float
    
    # 3. Sensor metrics
    noise_floor_std: float
    blur_laplacian_variance: float
    psnr_estimate: float
    
    # 4. Season / Acquisition metrics
    hue_mean: float
    saturation_mean: float
    green_vegetation_index: float # ExG = 2G - R - B

class EnvironmentalFeatureExtractor:
    """Extracts environmental domain metrics (Terrain, Illumination, Sensor, Season) from images."""
    
    @staticmethod
    def extract_metrics(image_path: str) -> Optional[EnvironmentalShiftMetrics]:
        if not os.path.exists(image_path):
            return None
        img = cv2.imread(image_path)
        if img is None:
            return None

        h, w, c = img.shape
        img_resized = cv2.resize(img, (128, 128))
        
        # Color channels B, G, R
        b, g, r = img_resized[:, :, 0].astype(float), img_resized[:, :, 1].astype(float), img_resized[:, :, 2].astype(float)
        
        # HSV representation
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
        h_channel, s_channel, v_channel = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        
        # 1. Terrain Metrics (Texture GLCM proxy & Color histogram energy)
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        texture_contrast = float(np.mean(np.sqrt(gx**2 + gy**2)))
        
        hist = cv2.calcHist([img_resized], [0, 1, 2], None, [4, 4, 4], [0, 256, 0, 256, 0, 256])
        hist_norm = hist.flatten() / (hist.sum() + 1e-7)
        hist_energy = float(np.sum(hist_norm**2))

        # 2. Illumination Metrics
        mean_brightness = float(np.mean(v_channel))
        contrast_std = float(np.std(v_channel))
        low_light = float(np.mean(v_channel < 40))
        overexp = float(np.mean(v_channel > 220))

        # 3. Sensor Metrics (Noise estimate & Laplacian blur)
        # Fast noise variance estimation using median blur difference
        blur_med = cv2.medianBlur(gray, 3)
        noise = gray.astype(float) - blur_med.astype(float)
        noise_floor = float(np.std(noise))
        
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        psnr_est = float(20 * np.log10(255.0 / (noise_floor + 1e-5)))

        # 4. Season / Acquisition Metrics
        hue_mean = float(np.mean(h_channel))
        sat_mean = float(np.mean(s_channel))
        
        # Excess Green Index (ExG = 2G - R - B) for vegetation/seasonal canopy change
        exg = (2.0 * g - r - b)
        exg_mean = float(np.mean(exg))

        return EnvironmentalShiftMetrics(
            terrain_texture_contrast=round(texture_contrast, 4),
            terrain_color_hist_energy=round(hist_energy, 4),
            mean_brightness=round(mean_brightness, 2),
            contrast_std=round(contrast_std, 2),
            hsv_value_mean=round(mean_brightness, 2),
            low_light_ratio=round(low_light, 4),
            overexposure_ratio=round(overexp, 4),
            noise_floor_std=round(noise_floor, 4),
            blur_laplacian_variance=round(lap_var, 2),
            psnr_estimate=round(psnr_est, 2),
            hue_mean=round(hue_mean, 2),
            saturation_mean=round(sat_mean, 2),
            green_vegetation_index=round(exg_mean, 2)
        )
