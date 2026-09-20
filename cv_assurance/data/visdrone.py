import os
import glob
import json
import shutil
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from cv_assurance.data.ingester import IngestedDataset, IngestedSample, BoundingBox

VISDRONE_CATEGORIES: Dict[int, str] = {
    0: "ignored_regions",
    1: "pedestrian",
    2: "people",
    3: "bicycle",
    4: "car",
    5: "van",
    6: "truck",
    7: "tricycle",
    8: "awning-tricycle",
    9: "bus",
    10: "motor",
    11: "others"
}

class VisDroneIngester:
    """
    Ingests official VisDrone-DET dataset format:
      root_dir/
        images/          (*.jpg)
        annotations/     (*.txt)
    Each annotation row:
      <bbox_left>,<bbox_top>,<bbox_width>,<bbox_height>,<score>,<object_category>,<truncation>,<occlusion>
    """

    @classmethod
    def parse_annotation_file(cls, txt_path: str, categories: Dict[int, str]) -> List[BoundingBox]:
        boxes = []
        if not os.path.exists(txt_path):
            return boxes
            
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 6:
                    parts = line.strip().split()
                if len(parts) >= 6:
                    try:
                        x = float(parts[0])
                        y = float(parts[1])
                        w = float(parts[2])
                        h = float(parts[3])
                        score = int(parts[4])
                        cat_id = int(parts[5])
                        
                        if cat_id in (0, 11) or score == 0:
                            continue # Skip ignored regions or non-eval score
                            
                        cat_name = categories.get(cat_id, f"class_{cat_id}")
                        boxes.append(BoundingBox(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            category_id=cat_id,
                            category_name=cat_name
                        ))
                    except (ValueError, IndexError):
                        continue
        return boxes

    @classmethod
    def ingest_visdrone(
        cls,
        root_dir: str,
        dataset_name: str = "VisDrone_Dataset",
        max_samples: Optional[int] = None,
        seed: int = 42
    ) -> IngestedDataset:
        p = Path(root_dir)
        images_dir = p / "images"
        ann_dir = p / "annotations"

        if not images_dir.exists():
            # Check if flat directory with images
            img_files = sorted(list(p.glob("*.jpg")) + list(p.glob("*.png")))
        else:
            img_files = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")))

        if not img_files:
            raise FileNotFoundError(f"No VisDrone image files found in {root_dir}")

        # Deterministic subset sampling if max_samples specified
        if max_samples and max_samples < len(img_files):
            rng = np.random.RandomState(seed)
            indices = rng.choice(len(img_files), size=max_samples, replace=False)
            indices.sort()
            img_files = [img_files[i] for i in indices]

        samples: List[IngestedSample] = []
        total_annotations = 0

        for idx, img_path in enumerate(img_files):
            stem = img_path.stem
            txt_path = ann_dir / f"{stem}.txt" if ann_dir.exists() else p / f"{stem}.txt"
            
            # Read image dimensions
            img = cv2.imread(str(img_path))
            if img is not None:
                h, w = img.shape[:2]
            else:
                h, w = 640, 640

            boxes = cls.parse_annotation_file(str(txt_path), VISDRONE_CATEGORIES)
            total_annotations += len(boxes)

            samples.append(IngestedSample(
                sample_id=f"visdrone_{idx+1:05d}",
                image_path=str(img_path),
                file_name=img_path.name,
                width=w,
                height=h,
                boxes=boxes,
                contributor_id=None,
                batch_id=None,
                source_id=None,
                format="visdrone"
            ))

        return IngestedDataset(
            name=dataset_name,
            format="visdrone",
            root_dir=str(root_dir),
            categories=VISDRONE_CATEGORIES,
            samples=samples,
            total_samples=len(samples),
            total_annotations=total_annotations
        )

    @classmethod
    def export_to_coco(cls, dataset: IngestedDataset, output_json_path: str):
        images_list = []
        annotations_list = []
        ann_id = 1

        for idx, s in enumerate(dataset.samples, 1):
            images_list.append({
                "id": idx,
                "file_name": s.file_name,
                "width": s.width,
                "height": s.height,
                "contributor": s.contributor_id,
                "batch_id": s.batch_id
            })
            for b in s.boxes:
                annotations_list.append({
                    "id": ann_id,
                    "image_id": idx,
                    "category_id": b.category_id,
                    "bbox": [b.x, b.y, b.width, b.height],
                    "area": float(b.width * b.height),
                    "iscrowd": 0
                })
                ann_id += 1

        cat_list = [{"id": k, "name": v} for k, v in dataset.categories.items() if k != 0]

        coco_data = {
            "images": images_list,
            "annotations": annotations_list,
            "categories": cat_list
        }

        p = Path(output_json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(coco_data, f, indent=2)

class VisDroneBenchmarkSynthesizer:
    """
    Creates high-fidelity VisDrone-compliant aerial imagery and annotation files
    for standalone, offline verification when the 2GB+ raw VisDrone archive is not pre-installed.
    """

    @classmethod
    def generate_aerial_sample(cls, index: int, width: int = 640, height: int = 640, seed: int = 42) -> Tuple[np.ndarray, List[BoundingBox]]:
        rng = np.random.RandomState(seed + index * 17)
        img = np.zeros((height, width, 3), dtype=np.uint8)

        scene_type = rng.choice(["intersection", "highway", "parking_lot", "roundabout", "urban_avenue"])
        
        # Base terrain: grass, dirt, or urban pavement
        _base_colors = [
            (40, 85, 45),   # Green foliage/lawn
            (45, 70, 75),   # Earthy terrain
            (85, 85, 90),   # Urban concrete
            (35, 65, 40)    # Deep grass
        ]
        base_color = _base_colors[rng.randint(0, len(_base_colors))]
        img[:] = base_color

        # Add texture noise to ground
        noise = rng.randint(-12, 12, size=(height, width, 3))
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        road_color = (65, 65, 70)

        if scene_type == "intersection":
            road_w = rng.randint(100, 160)
            rx = rng.randint(width // 4, 3 * width // 4)
            ry = rng.randint(height // 4, 3 * height // 4)
            img[:, max(0, rx - road_w // 2):min(width, rx + road_w // 2)] = road_color
            img[max(0, ry - road_w // 2):min(height, ry + road_w // 2), :] = road_color
            # Markings
            cv2.line(img, (rx, 0), (rx, height), (220, 220, 220), 3)
            cv2.line(img, (0, ry), (width, ry), (220, 220, 220), 3)

        elif scene_type == "highway":
            road_w = rng.randint(140, 220)
            ry = rng.randint(height // 3, 2 * height // 3)
            img[max(0, ry - road_w // 2):min(height, ry + road_w // 2), :] = road_color
            cv2.line(img, (0, ry), (width, ry), (230, 230, 50), 4) # Yellow center
            cv2.line(img, (0, ry - 35), (width, ry - 35), (220, 220, 220), 2)
            cv2.line(img, (0, ry + 35), (width, ry + 35), (220, 220, 220), 2)

        elif scene_type == "parking_lot":
            img[40:height - 40, 40:width - 40] = road_color
            for px in range(70, width - 70, 45):
                cv2.line(img, (px, 70), (px, height // 2 - 30), (220, 220, 220), 2)
                cv2.line(img, (px, height // 2 + 30), (px, height - 70), (220, 220, 220), 2)

        elif scene_type == "roundabout":
            center = (width // 2, height // 2)
            cv2.circle(img, center, 200, road_color, -1)
            cv2.circle(img, center, 80, (50, 95, 55), -1) # Island
            cv2.circle(img, center, 140, (220, 220, 220), 2)

        else: # urban_avenue
            road_w = rng.randint(120, 180)
            rx = rng.randint(width // 3, 2 * width // 3)
            img[:, max(0, rx - road_w // 2):min(width, rx + road_w // 2)] = road_color
            cv2.line(img, (rx, 0), (rx, height), (220, 220, 220), 3)

        # Draw occasional building / roof blocks
        _building_colors = [(110, 100, 95), (140, 135, 130), (90, 80, 85), (130, 90, 75)]
        num_buildings = rng.randint(1, 4)
        for _ in range(num_buildings):
            bx = rng.randint(10, width - 120)
            by = rng.randint(10, height - 120)
            bw = rng.randint(60, 110)
            bh = rng.randint(60, 110)
            b_col = _building_colors[rng.randint(0, len(_building_colors))]
            cv2.rectangle(img, (bx, by), (bx + bw, by + bh), b_col, -1)
            cv2.rectangle(img, (bx, by), (bx + bw, by + bh), (40, 40, 40), 2)

        boxes = []
        # Spawn aerial targets: cars (cat_id 4), pedestrians (cat_id 1), vans (cat_id 5), buses (cat_id 9)
        num_targets = rng.randint(2, 6)
        
        target_specs = [
            (4, "car", (30, 60), (40, 160, 220)), # Blue / yellow car
            (5, "van", (40, 80), (180, 180, 180)), # White van
            (9, "bus", (45, 110), (30, 30, 200)),  # Red bus
            (1, "pedestrian", (15, 15), (200, 200, 200)), # Pedestrian
            (10, "motor", (15, 30), (50, 50, 50)) # Motorbike
        ]

        for t_idx in range(num_targets):
            spec = target_specs[rng.randint(0, len(target_specs))]
            cat_id, cat_name, (tw, th), color = spec
            x = int(rng.randint(30, width - 30 - tw))
            y = int(rng.randint(30, height - 30 - th))

            cv2.rectangle(img, (x, y), (x + tw, y + th), color, -1)
            # Add windshield / detail
            if tw > 20:
                cv2.rectangle(img, (x + 4, y + 4), (x + tw - 4, y + 12), (30, 30, 30), -1)

            boxes.append(BoundingBox(
                x=float(x),
                y=float(y),
                width=float(tw),
                height=float(th),
                category_id=cat_id,
                category_name=cat_name
            ))

        return img, boxes

    @classmethod
    def generate_synthetic_visdrone_dataset(
        cls,
        output_dir: str,
        num_train: int = 50,
        num_val: int = 15,
        seed: int = 42
    ) -> Dict[str, str]:
        p = Path(output_dir)
        train_img_dir = p / "VisDrone2019-DET-train" / "images"
        train_ann_dir = p / "VisDrone2019-DET-train" / "annotations"
        val_img_dir = p / "VisDrone2019-DET-val" / "images"
        val_ann_dir = p / "VisDrone2019-DET-val" / "annotations"

        for d in [train_img_dir, train_ann_dir, val_img_dir, val_ann_dir]:
            d.mkdir(parents=True, exist_ok=True)

        for i in range(1, num_train + 1):
            stem = f"{i:07d}"
            img, boxes = cls.generate_aerial_sample(i, seed=seed)
            cv2.imwrite(str(train_img_dir / f"{stem}.jpg"), img)
            
            # Write VisDrone format annotations
            with open(train_ann_dir / f"{stem}.txt", "w", encoding="utf-8") as f:
                for b in boxes:
                    f.write(f"{int(b.x)},{int(b.y)},{int(b.width)},{int(b.height)},1,{b.category_id},0,0\n")

        for i in range(1, num_val + 1):
            stem = f"val_{i:07d}"
            img, boxes = cls.generate_aerial_sample(num_train + i, seed=seed)
            cv2.imwrite(str(val_img_dir / f"{stem}.jpg"), img)
            with open(val_ann_dir / f"{stem}.txt", "w", encoding="utf-8") as f:
                for b in boxes:
                    f.write(f"{int(b.x)},{int(b.y)},{int(b.width)},{int(b.height)},1,{b.category_id},0,0\n")

        return {
            "train_root": str(p / "VisDrone2019-DET-train"),
            "val_root": str(p / "VisDrone2019-DET-val")
        }

