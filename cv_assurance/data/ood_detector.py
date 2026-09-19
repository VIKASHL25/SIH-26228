import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from .ingester import IngestedDataset, IngestedSample

class OODSample(BaseModel):
    sample_id: str
    file_name: str
    anomaly_score: float # 0.0 to 1.0 (higher = more out of distribution)
    contributor_id: str
    batch_id: str
    detection_method: str
    description: str

class OODAnalysisResult(BaseModel):
    total_samples: int
    ood_samples_count: int
    ood_ratio: float
    contamination_level: float
    ood_samples: List[OODSample]

class OODDetector:
    """Detects Out-Of-Distribution (OOD) data samples inserted into dataset."""
    
    @staticmethod
    def extract_features(img_path: str) -> Optional[np.ndarray]:
        if not os.path.exists(img_path):
            return None
        img = cv2.imread(img_path)
        if img is None:
            return None
        img_resized = cv2.resize(img, (64, 64))
        # Extract color channel statistics, texture, and brightness moments
        mean_val = np.mean(img_resized, axis=(0, 1))
        std_val = np.std(img_resized, axis=(0, 1))
        
        # Color histograms
        hist = cv2.calcHist([img_resized], [0, 1, 2], None, [4, 4, 4], [0, 256, 0, 256, 0, 256])
        hist_flat = hist.flatten() / (hist.sum() + 1e-7)
        
        # Edge sharpness
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        lap_var = np.array([cv2.Laplacian(gray, cv2.CV_64F).var()])
        
        feat = np.concatenate([mean_val, std_val, hist_flat, lap_var])
        return feat

    def analyze(self, dataset: IngestedDataset, contamination: float = 0.1) -> OODAnalysisResult:
        samples = dataset.samples
        if len(samples) < 5:
            return OODAnalysisResult(
                total_samples=len(samples),
                ood_samples_count=0,
                ood_ratio=0.0,
                contamination_level=contamination,
                ood_samples=[]
            )

        features = []
        valid_samples = []

        for s in samples:
            feat = self.extract_features(s.image_path)
            if feat is not None:
                features.append(feat)
                valid_samples.append(s)

        if len(features) < 5:
            return OODAnalysisResult(
                total_samples=len(samples),
                ood_samples_count=0,
                ood_ratio=0.0,
                contamination_level=contamination,
                ood_samples=[]
            )

        X = np.array(features)
        
        # Fit Isolation Forest
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        preds = iso_forest.fit_predict(X)
        scores = -iso_forest.score_samples(X) # Higher score = more anomalous
        
        # Normalize scores to 0.0 - 1.0
        min_s, max_s = np.min(scores), np.max(scores)
        if max_s > min_s:
            norm_scores = (scores - min_s) / (max_s - min_s)
        else:
            norm_scores = np.zeros_like(scores)

        ood_list: List[OODSample] = []
        for idx, (p, score) in enumerate(zip(preds, norm_scores)):
            if p == -1 or score >= 0.7:
                s = valid_samples[idx]
                ood_list.append(OODSample(
                    sample_id=s.sample_id,
                    file_name=s.file_name,
                    anomaly_score=round(float(score), 4),
                    contributor_id=s.contributor_id,
                    batch_id=s.batch_id,
                    detection_method="IsolationForest_FeatureSpace",
                    description=f"Sample visual feature distribution significantly departs from target dataset cluster (anomaly score: {round(float(score), 2)})."
                ))

        total_valid = len(valid_samples)
        ood_ratio = float(len(ood_list) / total_valid) if total_valid > 0 else 0.0

        return OODAnalysisResult(
            total_samples=len(samples),
            ood_samples_count=len(ood_list),
            ood_ratio=round(ood_ratio, 4),
            contamination_level=contamination,
            ood_samples=ood_list
        )
