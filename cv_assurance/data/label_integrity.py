import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from sklearn.neighbors import NearestNeighbors
from .ingester import IngestedDataset, IngestedSample

class MislabelledSample(BaseModel):
    sample_id: str
    file_name: str
    given_label_id: int
    given_label_name: str
    suggested_label_id: int
    suggested_label_name: str
    discrepancy_score: float # 0.0 to 1.0
    confidence_level: str # "HIGH", "MEDIUM", "LOW"
    knn_consensus: float
    centroid_distance_margin: float
    contributor_id: Optional[str] = None
    batch_id: Optional[str] = None
    reason: str

class ContributorConfusionStats(BaseModel):
    contributor_id: str
    dominant_confusion_pair: Optional[str] = None
    confusion_count: int = 0
    is_systematic: bool = False
    details: str = ""

class LabelIntegrityResult(BaseModel):
    total_samples: int
    suspicious_samples_count: int
    mislabelling_rate: float
    systematic_pattern_detected: bool
    flagged_samples: List[MislabelledSample] = Field(default_factory=list)
    contributor_confusion_stats: List[ContributorConfusionStats] = Field(default_factory=list)
    class_counts: Dict[str, int] = Field(default_factory=dict)
    minimum_class_sample_requirement: int = 5
    trusted_label_verification: bool = False
    confidence_semantics: str = "heuristic_evidence_level_not_calibrated_probability"

class LabelIntegrityAnalyzer:
    """
    Multi-Evidence Label Integrity & Semantic Mislabelling Analyzer:
    Combines:
    1. ROI Object Bounding Box + Context Feature Representation
    2. k-NN Neighborhood Label Consensus
    3. Class Centroid Distance Margin Comparison
    4. Multi-Evidence Confidence Stratification (HIGH, MEDIUM, LOW)
    5. Contributor-level Systematic Confusion Matrix Analytics
    """

    @staticmethod
    def extract_roi_and_context_features(img_path: str, boxes: List[Any]) -> Optional[np.ndarray]:
        if not os.path.exists(img_path):
            return None
        img = cv2.imread(img_path)
        if img is None:
            return None

        h, w = img.shape[:2]
        
        # 1. Whole-image context feature
        img_small = cv2.resize(img, (64, 64))
        hist_b = cv2.calcHist([img_small], [0], None, [8], [0, 256]).flatten()
        hist_g = cv2.calcHist([img_small], [1], None, [8], [0, 256]).flatten()
        hist_r = cv2.calcHist([img_small], [2], None, [8], [0, 256]).flatten()
        
        # 2. Target ROI feature
        if boxes:
            b = boxes[0]
            bx = int(max(0, b.x if hasattr(b, "x") else b.get("x", 0)))
            by = int(max(0, b.y if hasattr(b, "y") else b.get("y", 0)))
            bw = int(min(w - bx, b.width if hasattr(b, "width") else b.get("width", 50)))
            bh = int(min(h - by, b.height if hasattr(b, "height") else b.get("height", 50)))

            if bw > 5 and bh > 5:
                roi = img[by:by+bh, bx:bx+bw]
            else:
                roi = img_small
            aspect_ratio = bw / (bh + 1e-5)
            rel_area = (bw * bh) / (w * h + 1e-5)
        else:
            roi = img_small
            aspect_ratio = 1.0
            rel_area = 1.0

        roi_res = cv2.resize(roi, (32, 32))
        roi_hist_b = cv2.calcHist([roi_res], [0], None, [8], [0, 256]).flatten()
        roi_hist_g = cv2.calcHist([roi_res], [1], None, [8], [0, 256]).flatten()
        roi_hist_r = cv2.calcHist([roi_res], [2], None, [8], [0, 256]).flatten()
        
        gray_roi = cv2.cvtColor(roi_res, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray_roi, cv2.CV_64F).var()) / 1000.0

        feat = np.concatenate([
            hist_b, hist_g, hist_r,
            roi_hist_b * 2.0, roi_hist_g * 2.0, roi_hist_r * 2.0,
            [aspect_ratio, rel_area, lap_var],
            cv2.resize(gray_roi, (8, 8)).flatten() / 255.0
        ])
        
        norm = np.linalg.norm(feat)
        if norm > 0:
            feat = feat / norm
        return feat

    def analyze(
        self,
        dataset: IngestedDataset,
        k_neighbors: int = 5,
        min_consensus_threshold: float = 0.60,
        centroid_margin_threshold: float = 0.02
    ) -> LabelIntegrityResult:
        samples = dataset.samples
        class_counts: Dict[str, int] = {}
        for sample in samples:
            class_id = sample.boxes[0].category_id if sample.boxes else 0
            class_counts[str(class_id)] = class_counts.get(str(class_id), 0) + 1
        if len(samples) < k_neighbors + 1:
            return LabelIntegrityResult(
                total_samples=len(samples),
                suspicious_samples_count=0,
                mislabelling_rate=0.0,
                systematic_pattern_detected=False,
                flagged_samples=[],
                contributor_confusion_stats=[],
                class_counts=class_counts
            )

        features = []
        labels = []
        valid_samples = []

        for s in samples:
            lbl_id = s.boxes[0].category_id if s.boxes else 0
            feat = self.extract_roi_and_context_features(s.image_path, s.boxes)
            if feat is not None:
                features.append(feat)
                labels.append(lbl_id)
                valid_samples.append(s)

        if len(features) <= k_neighbors:
            return LabelIntegrityResult(
                total_samples=len(samples),
                suspicious_samples_count=0,
                mislabelling_rate=0.0,
                systematic_pattern_detected=False,
                flagged_samples=[],
                contributor_confusion_stats=[],
                class_counts=class_counts
            )

        X = np.array(features)
        y = np.array(labels)

        # Compute class centroids
        unique_classes = np.unique(y)
        centroids: Dict[int, np.ndarray] = {}
        for c in unique_classes:
            c_mask = (y == c)
            if np.sum(c_mask) > 0:
                c_mean = np.mean(X[c_mask], axis=0)
                c_norm = np.linalg.norm(c_mean)
                centroids[c] = c_mean / (c_norm + 1e-7) if c_norm > 0 else c_mean

        # Fit k-NN
        k_val = min(k_neighbors, len(features) - 1)
        nn = NearestNeighbors(n_neighbors=k_val + 1, metric='cosine')
        nn.fit(X)
        distances, indices = nn.kneighbors(X)

        flagged: List[MislabelledSample] = []
        confusion_by_contrib: Dict[str, Dict[Tuple[int, int], int]] = {}

        for i, s in enumerate(valid_samples):
            neighbor_idx = indices[i][1:]
            neighbor_lbls = y[neighbor_idx]
            given_lbl = y[i]

            counts = {}
            for nl in neighbor_lbls:
                counts[nl] = counts.get(nl, 0) + 1

            most_common_lbl = max(counts, key=counts.get)
            consensus = counts[most_common_lbl] / float(k_val)

            # Centroid distance margin:
            # d_given = distance to given label centroid
            # d_suggested = distance to suggested label centroid
            centroid_margin = 0.0
            if given_lbl in centroids and most_common_lbl in centroids:
                d_given = float(np.linalg.norm(X[i] - centroids[given_lbl]))
                d_suggested = float(np.linalg.norm(X[i] - centroids[most_common_lbl]))
                centroid_margin = d_given - d_suggested # Positive means closer to suggested

            # Multi-evidence criterion: requires either strong consensus (>=0.8) or consensus supported by positive centroid margin
            has_strong_consensus = (consensus >= 0.80)
            has_centroid_support = (consensus >= min_consensus_threshold and centroid_margin >= centroid_margin_threshold)

            prevalence_adequate = (
                int(np.sum(y == given_lbl)) >= 5 and
                int(np.sum(y == most_common_lbl)) >= 5
            )
            if given_lbl != most_common_lbl and prevalence_adequate and (has_strong_consensus or has_centroid_support):
                # Confidence stratification
                if consensus >= 0.80 and centroid_margin >= 0.05:
                    conf_level = "HIGH"
                elif consensus >= 0.60 or centroid_margin >= 0.02:
                    conf_level = "MEDIUM"
                else:
                    conf_level = "LOW"

                given_name = dataset.categories.get(given_lbl, f"class_{given_lbl}")
                suggested_name = dataset.categories.get(most_common_lbl, f"class_{most_common_lbl}")
                discrepancy = round(float(0.7 * consensus + 0.3 * min(1.0, max(0.0, centroid_margin * 5.0))), 4)

                flagged.append(MislabelledSample(
                    sample_id=s.sample_id,
                    file_name=s.file_name,
                    given_label_id=int(given_lbl),
                    given_label_name=given_name,
                    suggested_label_id=int(most_common_lbl),
                    suggested_label_name=suggested_name,
                    discrepancy_score=discrepancy,
                    confidence_level=conf_level,
                    knn_consensus=round(float(consensus), 3),
                    centroid_distance_margin=round(float(centroid_margin), 4),
                    contributor_id=s.contributor_id,
                    batch_id=s.batch_id,
                    reason=f"[{conf_level}] k-NN consensus ({int(consensus*100)}%) and centroid margin ({round(centroid_margin, 3)}) indicate '{suggested_name}' instead of annotated '{given_name}'."
                ))

                # Track contributor confusion
                cid = s.contributor_id
                pair = (int(given_lbl), int(most_common_lbl))
                if cid not in confusion_by_contrib:
                    confusion_by_contrib[cid] = {}
                confusion_by_contrib[cid][pair] = confusion_by_contrib[cid].get(pair, 0) + 1

        # Evaluate systematic confusion patterns per contributor
        contrib_stats: List[ContributorConfusionStats] = []
        systematic_detected = False

        for cid, pairs in confusion_by_contrib.items():
            if not pairs:
                continue
            top_pair = max(pairs, key=pairs.get)
            top_count = pairs[top_pair]
            total_contrib_flags = sum(pairs.values())
            
            orig_n = dataset.categories.get(top_pair[0], f"class_{top_pair[0]}")
            sugg_n = dataset.categories.get(top_pair[1], f"class_{top_pair[1]}")
            pair_name = f"{orig_n} -> {sugg_n}"

            is_sys = (top_count >= 3 and (top_count / total_contrib_flags) >= 0.45)
            if is_sys:
                systematic_detected = True
                detail = f"Systematic confusion detected: {pair_name} accounts for {top_count}/{total_contrib_flags} ({int(top_count/total_contrib_flags*100)}%) mislabelled samples in contributor '{cid}'."
            else:
                detail = f"Isolated mislabelling incidents observed across multiple classes."

            contrib_stats.append(ContributorConfusionStats(
                contributor_id=cid,
                dominant_confusion_pair=pair_name,
                confusion_count=top_count,
                is_systematic=is_sys,
                details=detail
            ))

        total_valid = len(valid_samples)
        mislabel_rate = float(len(flagged) / total_valid) if total_valid > 0 else 0.0

        return LabelIntegrityResult(
            total_samples=len(samples),
            suspicious_samples_count=len(flagged),
            mislabelling_rate=round(mislabel_rate, 4),
            systematic_pattern_detected=systematic_detected,
            flagged_samples=flagged,
            contributor_confusion_stats=contrib_stats,
            class_counts=class_counts
        )

