import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel
from sklearn.neighbors import NearestNeighbors
from .ingester import IngestedDataset, IngestedSample

class MislabelledSample(BaseModel):
    sample_id: str
    file_name: str
    given_label_id: int
    given_label_name: str
    suggested_label_id: int
    suggested_label_name: str
    discrepancy_score: float # 0.0 to 1.0 (higher = more likely flipped/mislabelled)
    contributor_id: str
    batch_id: str
    reason: str

class LabelIntegrityResult(BaseModel):
    total_samples: int
    suspicious_samples_count: int
    mislabelling_rate: float # ratio of flagged samples
    systematic_pattern_detected: bool
    flagged_samples: List[MislabelledSample]

class LabelIntegrityAnalyzer:
    """
    Analyzes label integrity using feature-space k-NN consensus & centroid distances
    to detect label flipping, systematic mislabelling, and noisy annotations.
    """
    
    @staticmethod
    def extract_light_features(img_path: str) -> Optional[np.ndarray]:
        if not os.path.exists(img_path):
            return None
        img = cv2.imread(img_path)
        if img is None:
            return None
        img_resized = cv2.resize(img, (64, 64))
        # Compute color histogram + edge histogram + spatial grid features
        hist_b = cv2.calcHist([img_resized], [0], None, [16], [0, 256])
        hist_g = cv2.calcHist([img_resized], [1], None, [16], [0, 256])
        hist_r = cv2.calcHist([img_resized], [2], None, [16], [0, 256])
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        feat = np.concatenate([
            hist_b.flatten(), hist_g.flatten(), hist_r.flatten(),
            [lap],
            cv2.resize(gray, (16, 16)).flatten() / 255.0
        ])
        norm = np.linalg.norm(feat)
        if norm > 0:
            feat = feat / norm
        return feat

    def analyze(self, dataset: IngestedDataset, k_neighbors: int = 5, score_threshold: float = 0.6) -> LabelIntegrityResult:
        samples = dataset.samples
        if len(samples) < k_neighbors + 1:
            return LabelIntegrityResult(
                total_samples=len(samples),
                suspicious_samples_count=0,
                mislabelling_rate=0.0,
                systematic_pattern_detected=False,
                flagged_samples=[]
            )

        features = []
        primary_labels = []
        valid_samples = []

        for s in samples:
            # Determine primary class label for image (most frequent box category or 0)
            if s.boxes:
                label_id = s.boxes[0].category_id
            else:
                label_id = 0
                
            feat = self.extract_light_features(s.image_path)
            if feat is not None:
                features.append(feat)
                primary_labels.append(label_id)
                valid_samples.append(s)

        if len(features) <= k_neighbors:
            return LabelIntegrityResult(
                total_samples=len(samples),
                suspicious_samples_count=0,
                mislabelling_rate=0.0,
                systematic_pattern_detected=False,
                flagged_samples=[]
            )

        X = np.array(features)
        y = np.array(primary_labels)

        nn = NearestNeighbors(n_neighbors=k_neighbors + 1, metric='cosine')
        nn.fit(X)
        distances, indices = nn.kneighbors(X)

        flagged: List[MislabelledSample] = []
        for i, s in enumerate(valid_samples):
            neighbor_indices = indices[i][1:] # Exclude self
            neighbor_labels = y[neighbor_indices]
            given_lbl = y[i]
            
            # Count label frequencies among neighbors
            counts = {}
            for nl in neighbor_labels:
                counts[nl] = counts.get(nl, 0) + 1
                
            most_common_lbl = max(counts, key=counts.get)
            consensus = counts[most_common_lbl] / float(k_neighbors)
            
            # If neighbor consensus strongly disagrees with given label
            if given_lbl != most_common_lbl and consensus >= score_threshold:
                given_name = dataset.categories.get(given_lbl, f"class_{given_lbl}")
                suggested_name = dataset.categories.get(most_common_lbl, f"class_{most_common_lbl}")
                
                discrepancy = round(float(consensus), 4)
                flagged.append(MislabelledSample(
                    sample_id=s.sample_id,
                    file_name=s.file_name,
                    given_label_id=int(given_lbl),
                    given_label_name=given_name,
                    suggested_label_id=int(most_common_lbl),
                    suggested_label_name=suggested_name,
                    discrepancy_score=discrepancy,
                    contributor_id=s.contributor_id,
                    batch_id=s.batch_id,
                    reason=f"Feature space k-NN consensus ({int(consensus*100)}%) strongly indicates '{suggested_name}' instead of annotated '{given_name}'."
                ))

        total_valid = len(valid_samples)
        mislabel_rate = float(len(flagged) / total_valid) if total_valid > 0 else 0.0
        
        # Check if mislabelling is concentrated in a specific contributor
        systematic = False
        if len(flagged) >= 3:
            contrib_counts = {}
            for f in flagged:
                contrib_counts[f.contributor_id] = contrib_counts.get(f.contributor_id, 0) + 1
            max_contrib_ratio = max(contrib_counts.values()) / len(flagged)
            if max_contrib_ratio >= 0.6:
                systematic = True

        return LabelIntegrityResult(
            total_samples=len(samples),
            suspicious_samples_count=len(flagged),
            mislabelling_rate=round(mislabel_rate, 4),
            systematic_pattern_detected=systematic,
            flagged_samples=flagged
        )
