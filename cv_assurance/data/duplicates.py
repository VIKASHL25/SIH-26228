import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from .ingester import IngestedDataset, IngestedSample

class DuplicatePair(BaseModel):
    sample_id_a: str
    sample_id_b: str
    file_name_a: str
    file_name_b: str
    similarity_score: float
    duplicate_type: str # "exact", "perceptual", "feature_near_duplicate"
    contributor_a: str
    contributor_b: str

class DuplicateAnalysisResult(BaseModel):
    total_samples: int
    duplicate_pairs_count: int
    duplicate_samples_count: int
    flooding_risk_score: float # 0.0 to 1.0
    duplicate_pairs: List[DuplicatePair]

class DuplicateDetector:
    """Detects exact, perceptual, and near-duplicate images in dataset."""
    
    @staticmethod
    def compute_phash(image: np.ndarray, hash_size: int = 8) -> str:
        """Computes perceptual hash (pHash) using 2D DCT."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = image
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        # Convert to float and compute DCT
        dct = cv2.dct(np.float32(resized))
        # Extract low frequencies (top-left 8x8)
        dct_low = dct[:hash_size, :hash_size]
        med = np.median(dct_low)
        binary_hash = dct_low > med
        # Convert binary matrix to hex string
        return "".join([str(int(b)) for b in binary_hash.flatten()])

    @staticmethod
    def compute_dhash(image: np.ndarray, hash_size: int = 8) -> str:
        """Computes difference hash (dHash)."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = image
        resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        diff = resized[:, 1:] > resized[:, :-1]
        return "".join([str(int(b)) for b in diff.flatten()])

    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    def analyze(self, dataset: IngestedDataset, hash_threshold: int = 4, feature_threshold: float = 0.95) -> DuplicateAnalysisResult:
        samples = dataset.samples
        n = len(samples)
        if n <= 1:
            return DuplicateAnalysisResult(
                total_samples=n,
                duplicate_pairs_count=0,
                duplicate_samples_count=0,
                flooding_risk_score=0.0,
                duplicate_pairs=[]
            )

        hashes = []
        dhashes = []
        valid_indices = []
        
        for idx, s in enumerate(samples):
            if not os.path.exists(s.image_path):
                continue
            try:
                img = cv2.imread(s.image_path)
                if img is None:
                    continue
                ph = self.compute_phash(img)
                dh = self.compute_dhash(img)
                hashes.append(ph)
                dhashes.append(dh)
                valid_indices.append(idx)
            except Exception:
                continue

        duplicate_pairs: List[DuplicatePair] = []
        flagged_sample_ids = set()

        num_valid = len(valid_indices)
        for i in range(num_valid):
            for j in range(i + 1, num_valid):
                idx_i = valid_indices[i]
                idx_j = valid_indices[j]
                s_a = samples[idx_i]
                s_b = samples[idx_j]
                
                h_dist_p = self.hamming_distance(hashes[i], hashes[j])
                h_dist_d = self.hamming_distance(dhashes[i], dhashes[j])
                
                sim_score = 1.0 - (min(h_dist_p, h_dist_d) / 64.0)
                
                dup_type = None
                if h_dist_p == 0 and h_dist_d == 0:
                    dup_type = "exact"
                elif min(h_dist_p, h_dist_d) <= hash_threshold:
                    dup_type = "perceptual"
                elif sim_score >= feature_threshold:
                    dup_type = "feature_near_duplicate"
                    
                if dup_type:
                    duplicate_pairs.append(DuplicatePair(
                        sample_id_a=s_a.sample_id,
                        sample_id_b=s_b.sample_id,
                        file_name_a=s_a.file_name,
                        file_name_b=s_b.file_name,
                        similarity_score=round(float(sim_score), 4),
                        duplicate_type=dup_type,
                        contributor_a=s_a.contributor_id,
                        contributor_b=s_b.contributor_id
                    ))
                    flagged_sample_ids.add(s_a.sample_id)
                    flagged_sample_ids.add(s_b.sample_id)

        dup_count = len(flagged_sample_ids)
        flooding_risk = float(dup_count / n) if n > 0 else 0.0

        return DuplicateAnalysisResult(
            total_samples=n,
            duplicate_pairs_count=len(duplicate_pairs),
            duplicate_samples_count=dup_count,
            flooding_risk_score=round(flooding_risk, 4),
            duplicate_pairs=duplicate_pairs
        )
