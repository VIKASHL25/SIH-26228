import os
import hashlib
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from .ingester import IngestedDataset, IngestedSample

class DuplicatePair(BaseModel):
    sample_id_a: str
    sample_id_b: str
    file_name_a: str
    file_name_b: str
    similarity_score: float
    duplicate_type: str # "exact_sha256", "confirmed_near_duplicate", "perceptual_candidate"
    ssim_score: float = 1.0
    pixel_mae: float = 0.0
    contributor_a: Optional[str] = None
    contributor_b: Optional[str] = None
    is_confirmed: bool = True

class ContributorFloodingStats(BaseModel):
    contributor_id: str
    total_samples: int
    duplicate_samples_count: int
    duplicate_ratio: float
    max_cluster_size: int
    is_flooding_suspected: bool

class DuplicateAnalysisResult(BaseModel):
    total_samples: int
    duplicate_pairs_count: int
    duplicate_samples_count: int
    flooding_risk_score: float # 0.0 to 1.0
    duplicate_pairs: List[DuplicatePair] = Field(default_factory=list)
    contributor_flooding_stats: List[ContributorFloodingStats] = Field(default_factory=list)
    cross_contributor_pairs_count: int = 0
    cross_contributor_sample_ids: List[str] = Field(default_factory=list)

class DuplicateDetector:
    """
    Three-Tier Robust Duplicate Detector:
    Tier 1: Exact byte / normalized SHA-256 hashing.
    Tier 2: Dual perceptual hashing (pHash + dHash) candidate indexing.
    Tier 3: Strict Structural Similarity (SSIM) and pixel correlation confirmation.
    
    Prevents false pairings among naturally similar aerial textures.
    """

    @staticmethod
    def compute_sha256(image: np.ndarray) -> str:
        return hashlib.sha256(image.tobytes()).hexdigest()

    @staticmethod
    def compute_phash(image: np.ndarray, hash_size: int = 8) -> str:
        """Computes perceptual hash (pHash) using 2D DCT."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = image
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        dct = cv2.dct(np.float32(resized))
        dct_low = dct[:hash_size, :hash_size]
        med = np.median(dct_low)
        binary_hash = dct_low > med
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

    @staticmethod
    def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
        """Computes Structural Similarity Index (SSIM) on standardized grayscale images."""
        if len(img1.shape) == 3:
            g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        else:
            g1 = img1
        if len(img2.shape) == 3:
            g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        else:
            g2 = img2

        # Standardize size for comparison
        target_size = (128, 128)
        g1_res = cv2.resize(g1, target_size, interpolation=cv2.INTER_AREA).astype(np.float64)
        g2_res = cv2.resize(g2, target_size, interpolation=cv2.INTER_AREA).astype(np.float64)

        c1 = (0.01 * 255) ** 2
        c2 = (0.03 * 255) ** 2

        mu1 = cv2.GaussianBlur(g1_res, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(g2_res, (11, 11), 1.5)

        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = cv2.GaussianBlur(g1_res ** 2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(g2_res ** 2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(g1_res * g2_res, (11, 11), 1.5) - mu1_mu2

        ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2) + 1e-7)
        return float(np.mean(ssim_map))

    @staticmethod
    def compute_normalized_mae(img1: np.ndarray, img2: np.ndarray) -> float:
        """Computes Mean Absolute Error normalized by 255."""
        target_size = (128, 128)
        i1 = cv2.resize(img1, target_size).astype(np.float32) / 255.0
        i2 = cv2.resize(img2, target_size).astype(np.float32) / 255.0
        return float(np.mean(np.abs(i1 - i2)))

    def analyze(
        self,
        dataset: IngestedDataset,
        hash_candidate_threshold: int = 6,
        ssim_confirmation_threshold: float = 0.80,
        normalized_mae_threshold: float = 0.18
    ) -> DuplicateAnalysisResult:
        samples = dataset.samples
        n = len(samples)
        if n <= 1:
            return DuplicateAnalysisResult(
                total_samples=n,
                duplicate_pairs_count=0,
                duplicate_samples_count=0,
                flooding_risk_score=0.0,
                duplicate_pairs=[],
                contributor_flooding_stats=[]
            )

        images = []
        sha_hashes = []
        phashes = []
        dhashes = []
        valid_indices = []

        for idx, s in enumerate(samples):
            if not os.path.exists(s.image_path):
                continue
            try:
                img = cv2.imread(s.image_path)
                if img is None:
                    continue
                sha = self.compute_sha256(img)
                ph = self.compute_phash(img)
                dh = self.compute_dhash(img)
                images.append(img)
                sha_hashes.append(sha)
                phashes.append(ph)
                dhashes.append(dh)
                valid_indices.append(idx)
            except Exception:
                continue

        num_valid = len(valid_indices)
        duplicate_pairs: List[DuplicatePair] = []
        flagged_sample_ids = set()

        for i in range(num_valid):
            for j in range(i + 1, num_valid):
                idx_i = valid_indices[i]
                idx_j = valid_indices[j]
                s_a = samples[idx_i]
                s_b = samples[idx_j]

                # 1. Exact SHA-256 match
                if sha_hashes[i] == sha_hashes[j]:
                    duplicate_pairs.append(DuplicatePair(
                        sample_id_a=s_a.sample_id,
                        sample_id_b=s_b.sample_id,
                        file_name_a=s_a.file_name,
                        file_name_b=s_b.file_name,
                        similarity_score=1.0,
                        duplicate_type="exact_sha256",
                        ssim_score=1.0,
                        pixel_mae=0.0,
                        contributor_a=s_a.contributor_id,
                        contributor_b=s_b.contributor_id,
                        is_confirmed=True
                    ))
                    flagged_sample_ids.add(s_a.sample_id)
                    flagged_sample_ids.add(s_b.sample_id)
                    continue

                # 2. Perceptual candidate filtering
                h_dist_p = self.hamming_distance(phashes[i], phashes[j])
                h_dist_d = self.hamming_distance(dhashes[i], dhashes[j])

                # Require candidate proximity in both hash metrics
                if h_dist_p <= hash_candidate_threshold and h_dist_d <= (hash_candidate_threshold + 2):
                    # 3. Structural & Pixel Confirmation (Tier 3)
                    ssim = self.compute_ssim(images[i], images[j])
                    mae = self.compute_normalized_mae(images[i], images[j])

                    if ssim >= ssim_confirmation_threshold and mae <= normalized_mae_threshold:
                        combined_sim = round(float(0.7 * ssim + 0.3 * (1.0 - mae)), 4)
                        duplicate_pairs.append(DuplicatePair(
                            sample_id_a=s_a.sample_id,
                            sample_id_b=s_b.sample_id,
                            file_name_a=s_a.file_name,
                            file_name_b=s_b.file_name,
                            similarity_score=combined_sim,
                            duplicate_type="confirmed_near_duplicate",
                            ssim_score=round(float(ssim), 4),
                            pixel_mae=round(float(mae), 4),
                            contributor_a=s_a.contributor_id,
                            contributor_b=s_b.contributor_id,
                            is_confirmed=True
                        ))
                        flagged_sample_ids.add(s_a.sample_id)
                        flagged_sample_ids.add(s_b.sample_id)

        # Contributor-level flooding statistics (only same-contributor pairs = flooding)
        contrib_samples: Dict[str, List[str]] = {}
        for s in samples:
            contrib_samples.setdefault(s.contributor_id, []).append(s.sample_id)

        # Build per-contributor duplicate counts from same-contributor pairs only
        contrib_dup_ids: Dict[str, set] = {cid: set() for cid in contrib_samples}
        for pair in duplicate_pairs:
            if pair.is_confirmed and pair.contributor_a is not None and pair.contributor_a == pair.contributor_b:
                cid = pair.contributor_a
                if cid in contrib_dup_ids:
                    contrib_dup_ids[cid].add(pair.sample_id_a)
                    contrib_dup_ids[cid].add(pair.sample_id_b)

        contrib_flooding_stats = []
        for cid, s_ids in contrib_samples.items():
            c_tot = len(s_ids)
            c_dup_count = len(contrib_dup_ids.get(cid, set()))
            c_dup_ratio = float(c_dup_count / c_tot) if c_tot > 0 else 0.0
            
            # Flooding is flagged when duplicate concentration exceeds volume-adjusted ratio
            is_flooding = (c_dup_ratio >= 0.20 and c_dup_count >= 2)
            contrib_flooding_stats.append(ContributorFloodingStats(
                contributor_id=cid,
                total_samples=c_tot,
                duplicate_samples_count=c_dup_count,
                duplicate_ratio=round(c_dup_ratio, 4),
                max_cluster_size=c_dup_count,
                is_flooding_suspected=is_flooding
            ))

        cross_contributor_pairs = [
            pair for pair in duplicate_pairs
            if pair.is_confirmed and (
                pair.contributor_a is None or pair.contributor_b is None or
                pair.contributor_a != pair.contributor_b
            )
        ]
        cross_contributor_sample_ids = sorted({
            sample_id
            for pair in cross_contributor_pairs
            for sample_id in (pair.sample_id_a, pair.sample_id_b)
        })
        dup_count = len(flagged_sample_ids)
        flooding_risk = float(dup_count / n) if n > 0 else 0.0

        return DuplicateAnalysisResult(
            total_samples=n,
            duplicate_pairs_count=len(duplicate_pairs),
            duplicate_samples_count=dup_count,
            flooding_risk_score=round(flooding_risk, 4),
            duplicate_pairs=duplicate_pairs,
            contributor_flooding_stats=contrib_flooding_stats,
            cross_contributor_pairs_count=len(cross_contributor_pairs),
            cross_contributor_sample_ids=cross_contributor_sample_ids
        )

