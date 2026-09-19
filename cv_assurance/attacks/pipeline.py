import os
import json
import shutil
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from cv_assurance.data.ingester import IngestedDataset, IngestedSample, BoundingBox
from cv_assurance.data.visdrone import VISDRONE_CATEGORIES
from .manifest import AttackSampleRecord, GroundTruthManifest, ManifestValidator
from .label_attacks import LabelFlippingAttack, SystematicMislabellingAttack
from .duplicate_attacks import NearDuplicateFloodingAttack
from .ood_attacks import OODInsertionAttack
from .trigger_attacks import CornerTriggerAttack, BlendedTriggerAttack, SpectralTriggerAttack
from .distribution_shift import DistributionShiftGenerator

class MultiContributorPipeline:
    """
    Orchestrates clean reference dataset ingestion, 3-way data partitioning
    (Clean Calibration, Clean Test, Attack Test) strictly without data leakage,
    multi-contributor simulation, and machine-readable ground truth manifests.
    """

    def __init__(
        self,
        output_dir: str = "data",
        seed: int = 42,
        calibration_ratio: float = 0.25,
        clean_test_ratio: float = 0.25
    ):
        self.output_dir = Path(output_dir)
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.calibration_ratio = calibration_ratio
        self.clean_test_ratio = clean_test_ratio

    def build_benchmark(self, reference_dataset: IngestedDataset) -> GroundTruthManifest:
        """
        Executes end-to-end benchmark generation from a reference dataset.
        """
        samples = reference_dataset.samples
        if not samples:
            raise ValueError("Reference dataset contains 0 samples.")

        categories = reference_dataset.categories or VISDRONE_CATEGORIES
        num_total = len(samples)

        # 1. Strict 3-Way Partitioning by Source Image ID (Zero Data Leakage)
        shuffled_indices = self.rng.permutation(num_total)
        n_calib = max(4, int(num_total * self.calibration_ratio))
        n_clean_test = max(4, int(num_total * self.clean_test_ratio))
        n_attack_pool = num_total - (n_calib + n_clean_test)

        calib_indices = shuffled_indices[:n_calib]
        clean_test_indices = shuffled_indices[n_calib:n_calib + n_clean_test]
        attack_pool_indices = shuffled_indices[n_calib + n_clean_test:]

        # Verify disjoint sets
        set_calib = set(calib_indices)
        set_clean = set(clean_test_indices)
        set_attack = set(attack_pool_indices)
        assert len(set_calib & set_clean) == 0, "Data leakage between Calibration and Clean Test!"
        assert len(set_calib & set_attack) == 0, "Data leakage between Calibration and Attack Test!"
        assert len(set_clean & set_attack) == 0, "Data leakage between Clean Test and Attack Test!"

        # Setup directory paths
        ref_dir = self.output_dir / "reference"
        calib_dir = self.output_dir / "calibration"
        clean_test_dir = self.output_dir / "clean_test"
        contrib_root = self.output_dir / "contributors"
        attacks_root = self.output_dir / "attacks"
        shift_root = self.output_dir / "distribution_shift"
        gt_root = self.output_dir / "ground_truth"

        for p in [ref_dir / "images", calib_dir / "images", clean_test_dir / "images", gt_root]:
            p.mkdir(parents=True, exist_ok=True)

        for sub in ["contributor_A", "contributor_B", "contributor_C", "contributor_D"]:
            (contrib_root / sub / "images").mkdir(parents=True, exist_ok=True)

        for atk in ["label_flip", "systematic_mislabel", "duplicate_flood", "ood_insertion", "corner_trigger", "blended_trigger", "spectral_trigger"]:
            (attacks_root / atk).mkdir(parents=True, exist_ok=True)

        for shf in ["illumination", "blur", "noise"]:
            (shift_root / shf).mkdir(parents=True, exist_ok=True)

        # 2. Store Clean Reference Archive
        ref_records: List[AttackSampleRecord] = []
        for idx, s in enumerate(samples):
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            dest_name = f"ref_{idx+1:05d}.jpg"
            cv2.imwrite(str(ref_dir / "images" / dest_name), src_img)

            ref_records.append(AttackSampleRecord(
                sample_id=f"ref_{idx+1:05d}",
                original_image=str(Path("reference/images") / dest_name),
                current_image=str(Path("reference/images") / dest_name),
                contributor="contributor_trusted",
                batch_id="batch_ref_01",
                attack_type=None,
                is_attacked=False,
                is_shifted=False,
                original_label=s.boxes[0].category_name if s.boxes else None,
                original_label_id=s.boxes[0].category_id if s.boxes else None,
                modified_label=s.boxes[0].category_name if s.boxes else None,
                modified_label_id=s.boxes[0].category_id if s.boxes else None,
                boxes=[b.model_dump() if hasattr(b, "model_dump") else b.dict() for b in s.boxes],
                source="VisDrone"
            ))

        GroundTruthManifest(
            dataset_name="VisDrone_Clean_Reference",
            dataset_version="1.0.0",
            seed=self.seed,
            total_samples=len(ref_records),
            samples=ref_records
        ).save(ref_dir / "manifest.json")

        # 3. Store Clean Calibration Partition
        calib_records: List[AttackSampleRecord] = []
        for idx in calib_indices:
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            fname = f"calib_{idx+1:05d}.jpg"
            cv2.imwrite(str(calib_dir / "images" / fname), src_img)
            calib_records.append(AttackSampleRecord(
                sample_id=f"calib_{idx+1:05d}",
                original_image=str(Path("reference/images") / f"ref_{idx+1:05d}.jpg"),
                current_image=str(Path("calibration/images") / fname),
                contributor="contributor_calibration",
                batch_id="batch_calib_01",
                attack_type="clean",
                is_attacked=False,
                is_shifted=False,
                original_label=s.boxes[0].category_name if s.boxes else None,
                original_label_id=s.boxes[0].category_id if s.boxes else None,
                modified_label=s.boxes[0].category_name if s.boxes else None,
                modified_label_id=s.boxes[0].category_id if s.boxes else None,
                boxes=[b.model_dump() if hasattr(b, "model_dump") else b.dict() for b in s.boxes],
                source="VisDrone"
            ))

        GroundTruthManifest(
            dataset_name="VisDrone_Clean_Calibration",
            dataset_version="1.0.0",
            seed=self.seed,
            total_samples=len(calib_records),
            samples=calib_records
        ).save(calib_dir / "manifest.json")

        # 4. Partition Attack Pool across Contributors (Zero Data Leakage)
        n_splits = 5 if len(attack_pool_indices) >= 5 else 4
        splits = np.array_split(attack_pool_indices, n_splits)
        c_a_indices = splits[0]
        c_b_indices = splits[1]
        c_c_indices = splits[2]
        c_d_indices = splits[3]
        drift_indices = splits[4] if n_splits == 5 else clean_test_indices

        all_manifest_records: List[AttackSampleRecord] = []
        attack_counts: Dict[str, int] = {}
        contrib_counts: Dict[str, int] = {}

        # Instantiate attack modules
        lbl_flip_atk = LabelFlippingAttack(categories=categories, seed=self.seed + 10)
        sys_mislabel_atk = SystematicMislabellingAttack(categories=categories, seed=self.seed + 20)
        dup_atk = NearDuplicateFloodingAttack(seed=self.seed + 30)
        ood_atk = OODInsertionAttack(seed=self.seed + 40)
        corner_atk = CornerTriggerAttack(trigger_size=20, position="top_right", opacity=0.90, seed=self.seed + 50)
        blended_atk = BlendedTriggerAttack(alpha=0.18, seed=self.seed + 60)
        spectral_atk = SpectralTriggerAttack(frequency_strength=14.0, seed=self.seed + 70)
        shift_gen = DistributionShiftGenerator(seed=self.seed + 80)

        def write_sample(
            dest_rel_dir: str,
            filename: str,
            img: np.ndarray,
            orig_rel_path: str,
            contributor: str,
            batch: str,
            atk_res: Optional[Any] = None,
            shift_res: Optional[Any] = None
        ) -> AttackSampleRecord:
            full_dest_dir = self.output_dir / dest_rel_dir
            full_dest_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(full_dest_dir / filename), img)

            current_rel = str(Path(dest_rel_dir) / filename)
            is_atk = False
            is_shf = False
            atk_type = None
            shf_type = None
            orig_lbl = None
            orig_lbl_id = None
            mod_lbl = None
            mod_lbl_id = None
            params = {}
            boxes_data = []

            if atk_res:
                is_atk = atk_res.is_attacked
                atk_type = atk_res.attack_type
                orig_lbl = atk_res.original_label
                orig_lbl_id = atk_res.original_label_id
                mod_lbl = atk_res.modified_label
                mod_lbl_id = atk_res.modified_label_id
                params = atk_res.parameters
                boxes_data = [b.model_dump() if hasattr(b, "model_dump") else b.dict() for b in atk_res.modified_boxes]
            elif shift_res:
                is_shf = True
                shf_type = shift_res.parameters.get("shift_type", "illumination")
                orig_lbl = shift_res.original_label
                orig_lbl_id = shift_res.original_label_id
                mod_lbl = shift_res.modified_label
                mod_lbl_id = shift_res.modified_label_id
                params = shift_res.parameters
                boxes_data = [b.model_dump() if hasattr(b, "model_dump") else b.dict() for b in shift_res.modified_boxes]

            rec = AttackSampleRecord(
                sample_id=Path(filename).stem,
                original_image=orig_rel_path,
                current_image=current_rel,
                contributor=contributor,
                batch_id=batch,
                attack_type=atk_type,
                is_attacked=is_atk,
                is_shifted=is_shf,
                shift_type=shf_type,
                original_label=orig_lbl,
                original_label_id=orig_lbl_id,
                modified_label=mod_lbl,
                modified_label_id=mod_lbl_id,
                boxes=boxes_data,
                parameters=params,
                source="VisDrone"
            )

            key = atk_type if is_atk else ("shift_" + shf_type if is_shf else "clean")
            attack_counts[key] = attack_counts.get(key, 0) + 1
            contrib_counts[contributor] = contrib_counts.get(contributor, 0) + 1
            return rec

        sample_counter = 1

        # --- A. CLEAN TEST PARTITION (Included in Contributor A and Clean Test) ---
        for idx in clean_test_indices:
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            fname = f"sample_{sample_counter:05d}.jpg"
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")
            boxes_data = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]

            rec = write_sample(
                dest_rel_dir="contributors/contributor_A/images",
                filename=fname,
                img=src_img,
                orig_rel_path=orig_rel,
                contributor="contributor_A",
                batch="batch_A_clean",
                atk_res=type("CleanRes", (), {
                    "is_attacked": False,
                    "attack_type": "clean",
                    "original_label": s.boxes[0].category_name if s.boxes else None,
                    "original_label_id": s.boxes[0].category_id if s.boxes else None,
                    "modified_label": s.boxes[0].category_name if s.boxes else None,
                    "modified_label_id": s.boxes[0].category_id if s.boxes else None,
                    "parameters": {},
                    "modified_boxes": boxes_data
                })()
            )
            shutil.copy2(self.output_dir / rec.current_image, clean_test_dir / "images" / fname)
            all_manifest_records.append(rec)
            sample_counter += 1

        # --- B. CONTRIBUTOR A (Clean Reference Pool) ---
        for idx in c_a_indices:
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            fname = f"sample_{sample_counter:05d}.jpg"
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")
            boxes_data = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]

            rec = write_sample(
                dest_rel_dir="contributors/contributor_A/images",
                filename=fname,
                img=src_img,
                orig_rel_path=orig_rel,
                contributor="contributor_A",
                batch="batch_A_01",
                atk_res=type("CleanRes", (), {
                    "is_attacked": False,
                    "attack_type": "clean",
                    "original_label": s.boxes[0].category_name if s.boxes else None,
                    "original_label_id": s.boxes[0].category_id if s.boxes else None,
                    "modified_label": s.boxes[0].category_name if s.boxes else None,
                    "modified_label_id": s.boxes[0].category_id if s.boxes else None,
                    "parameters": {},
                    "modified_boxes": boxes_data
                })()
            )
            all_manifest_records.append(rec)
            sample_counter += 1

        # --- C. CONTRIBUTOR B (Label Manipulations: Label Flipping & Systematic Mislabelling) ---
        for i, idx in enumerate(c_b_indices):
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            fname = f"sample_{sample_counter:05d}.jpg"
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")
            boxes = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]

            if i % 2 == 0:
                atk_res = sys_mislabel_atk.apply(src_img, boxes)
                dest_folder = "attacks/systematic_mislabel"
            else:
                atk_res = lbl_flip_atk.apply(src_img, boxes)
                dest_folder = "attacks/label_flip"

            rec = write_sample(
                dest_rel_dir="contributors/contributor_B/images",
                filename=fname,
                img=atk_res.modified_image,
                orig_rel_path=orig_rel,
                contributor="contributor_B",
                batch="batch_B_01",
                atk_res=atk_res
            )
            shutil.copy2(self.output_dir / rec.current_image, self.output_dir / dest_folder / fname)
            all_manifest_records.append(rec)
            sample_counter += 1

        # --- D. CONTRIBUTOR C (Duplicate Flooding + OOD Insertion) ---
        n_dup_scenes = max(1, len(c_c_indices) // 2)
        dup_scenes = c_c_indices[:n_dup_scenes]
        ood_scenes = c_c_indices[n_dup_scenes:]

        # 1. Near-Duplicate Flooding: adversary floods pipeline with paired/clustered copies
        tx_options = [
            ("jpeg_compression", "brightness_contrast"),
            ("gaussian_blur", "jpeg_compression"),
            ("brightness_contrast", "gaussian_blur"),
            ("jpeg_compression", "brightness_contrast")
        ]
        for scene_i, idx in enumerate(dup_scenes):
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")
            boxes = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]

            tx1, tx2 = tx_options[scene_i % len(tx_options)]
            atk1 = NearDuplicateFloodingAttack(transformation=tx1, seed=self.seed + 30 + scene_i * 2)
            res1 = atk1.apply(src_img, boxes, original_sample_id=f"ref_{idx+1:05d}")

            atk2 = NearDuplicateFloodingAttack(transformation=tx2, seed=self.seed + 31 + scene_i * 2)
            res2 = atk2.apply(src_img, boxes, original_sample_id=f"ref_{idx+1:05d}")

            for atk_res in [res1, res2]:
                fname = f"sample_{sample_counter:05d}.jpg"
                rec = write_sample(
                    dest_rel_dir="contributors/contributor_C/images",
                    filename=fname,
                    img=atk_res.modified_image,
                    orig_rel_path=orig_rel,
                    contributor="contributor_C",
                    batch="batch_C_01",
                    atk_res=atk_res
                )
                shutil.copy2(self.output_dir / rec.current_image, self.output_dir / "attacks/duplicate_flood" / fname)
                all_manifest_records.append(rec)
                sample_counter += 1

        # 2. OOD Anomaly Insertion
        for idx in ood_scenes:
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            fname = f"sample_{sample_counter:05d}.jpg"
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")
            boxes = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]

            atk_res = ood_atk.apply(src_img, boxes)
            rec = write_sample(
                dest_rel_dir="contributors/contributor_C/images",
                filename=fname,
                img=atk_res.modified_image,
                orig_rel_path=orig_rel,
                contributor="contributor_C",
                batch="batch_C_01",
                atk_res=atk_res
            )
            shutil.copy2(self.output_dir / rec.current_image, self.output_dir / "attacks/ood_insertion" / fname)
            all_manifest_records.append(rec)
            sample_counter += 1

        # --- E. CONTRIBUTOR D (Backdoor Triggers: Corner, Blended, Spectral) ---
        for i, idx in enumerate(c_d_indices):
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            fname = f"sample_{sample_counter:05d}.jpg"
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")
            boxes = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]

            t_type = i % 3
            if t_type == 0:
                atk_res = corner_atk.apply(src_img, boxes)
                dest_folder = "attacks/corner_trigger"
            elif t_type == 1:
                atk_res = blended_atk.apply(src_img, boxes)
                dest_folder = "attacks/blended_trigger"
            else:
                atk_res = spectral_atk.apply(src_img, boxes)
                dest_folder = "attacks/spectral_trigger"

            rec = write_sample(
                dest_rel_dir="contributors/contributor_D/images",
                filename=fname,
                img=atk_res.modified_image,
                orig_rel_path=orig_rel,
                contributor="contributor_D",
                batch="batch_D_01",
                atk_res=atk_res
            )
            shutil.copy2(self.output_dir / rec.current_image, self.output_dir / dest_folder / fname)
            all_manifest_records.append(rec)
            sample_counter += 1

        # --- F. DISTRIBUTION SHIFTS (Operational Drift, NOT Malicious) ---
        # Generate on distinct images across drift_indices (illumination, blur, noise)
        shift_types = ["illumination", "blur", "noise"]
        for i, idx in enumerate(drift_indices):
            s = samples[idx]
            src_img = cv2.imread(s.image_path)
            if src_img is None:
                continue
            boxes = [BoundingBox(**b) if isinstance(b, dict) else b for b in s.boxes]
            orig_rel = str(Path("reference/images") / f"ref_{idx+1:05d}.jpg")

            stype = shift_types[i % len(shift_types)]
            gen = DistributionShiftGenerator(shift_type=stype, seed=self.seed + idx)
            res = gen.apply(src_img, boxes)
            fname = f"shift_{stype}_{sample_counter:05d}.jpg"
            rec = write_sample(
                dest_rel_dir=f"distribution_shift/{stype}",
                filename=fname,
                img=res.modified_image,
                orig_rel_path=orig_rel,
                contributor="contributor_drift",
                batch="batch_operational_drift",
                shift_res=res
            )
            all_manifest_records.append(rec)
            sample_counter += 1

        # 5. Save Ground Truth Manifests
        manifest = GroundTruthManifest(
            dataset_name="VisDrone_Assurance_Benchmark",
            dataset_version="1.1.0",
            seed=self.seed,
            total_samples=len(all_manifest_records),
            attack_summary=attack_counts,
            contributor_summary=contrib_counts,
            samples=all_manifest_records
        )

        manifest.save(gt_root / "attack_manifest.json")
        manifest.save(gt_root / "dataset_manifest.json")
        manifest.save(self.output_dir / "dataset_manifest.json")

        # Save contributor manifests
        for cid in ["contributor_A", "contributor_B", "contributor_C", "contributor_D"]:
            c_samples = [s for s in all_manifest_records if s.contributor == cid]
            GroundTruthManifest(
                dataset_name=f"VisDrone_{cid}_Submissions",
                dataset_version="1.1.0",
                seed=self.seed,
                total_samples=len(c_samples),
                samples=c_samples
            ).save(contrib_root / cid / "manifest.json")

        # Clean test manifest
        clean_test_samples = [s for s in all_manifest_records if not s.is_attacked and not s.is_shifted]
        GroundTruthManifest(
            dataset_name="VisDrone_Clean_Test_Partition",
            dataset_version="1.1.0",
            seed=self.seed,
            total_samples=len(clean_test_samples),
            samples=clean_test_samples
        ).save(clean_test_dir / "manifest.json")

        self._export_eval_coco(all_manifest_records, categories)
        return manifest

    def _export_eval_coco(self, records: List[AttackSampleRecord], categories: Dict[int, str]):
        images_list = []
        annotations_list = []
        ann_id = 1

        for idx, r in enumerate(records, 1):
            images_list.append({
                "id": idx,
                "file_name": r.current_image,
                "width": 640,
                "height": 640,
                "contributor": r.contributor,
                "batch_id": r.batch_id,
                "is_attacked": r.is_attacked,
                "attack_type": r.attack_type,
                "is_shifted": r.is_shifted
            })
            for b in r.boxes:
                annotations_list.append({
                    "id": ann_id,
                    "image_id": idx,
                    "category_id": b.get("category_id", 1),
                    "bbox": [b.get("x", 0), b.get("y", 0), b.get("width", 50), b.get("height", 50)],
                    "area": float(b.get("width", 50) * b.get("height", 50)),
                    "iscrowd": 0
                })
                ann_id += 1

        cat_list = [{"id": k, "name": v} for k, v in categories.items() if k != 0]

        coco_data = {
            "images": images_list,
            "annotations": annotations_list,
            "categories": cat_list
        }

        with open(self.output_dir / "coco_annotations.json", "w", encoding="utf-8") as f:
            json.dump(coco_data, f, indent=2)
