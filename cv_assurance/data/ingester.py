import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import cv2

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    category_id: int
    category_name: str

class IngestedSample(BaseModel):
    sample_id: str
    image_path: str
    file_name: str
    width: int
    height: int
    boxes: List[BoundingBox] = Field(default_factory=list)
    contributor_id: Optional[str] = None
    batch_id: Optional[str] = None
    source_id: Optional[str] = None
    format: str = "coco" # "coco", "yolo", "visdrone", "manifest"
    is_attacked: bool = False
    attack_type: Optional[str] = None
    is_shifted: bool = False
    shift_type: Optional[str] = None

class IngestedDataset(BaseModel):
    name: str
    format: str
    root_dir: str
    categories: Dict[int, str]
    samples: List[IngestedSample]
    total_samples: int
    total_annotations: int

    def __getitem__(self, item):
        return self.samples[item]

    def __len__(self):
        return len(self.samples)

class DatasetIngester:
    """Ingests COCO, YOLO, VisDrone, or Benchmark Manifest datasets into a unified dataset structure."""
    
    @staticmethod
    def ingest_coco(annotation_json_path: str, images_dir: str, dataset_name: str = "COCO_Dataset") -> IngestedDataset:
        if not os.path.exists(annotation_json_path):
            raise FileNotFoundError(f"COCO annotation file not found: {annotation_json_path}")
            
        with open(annotation_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        categories = {cat['id']: cat['name'] for cat in data.get('categories', [])}
        
        # Build image annotations map
        img_id_to_boxes: Dict[int, List[BoundingBox]] = {}
        for ann in data.get('annotations', []):
            img_id = ann['image_id']
            cat_id = ann['category_id']
            cat_name = categories.get(cat_id, f"class_{cat_id}")
            bbox = ann.get('bbox', [0, 0, 0, 0])
            box = BoundingBox(
                x=float(bbox[0]),
                y=float(bbox[1]),
                width=float(bbox[2]),
                height=float(bbox[3]),
                category_id=cat_id,
                category_name=cat_name
            )
            if img_id not in img_id_to_boxes:
                img_id_to_boxes[img_id] = []
            img_id_to_boxes[img_id].append(box)
            
        samples = []
        total_annotations = 0
        for img in data.get('images', []):
            img_id = img['id']
            file_name = img['file_name']
            img_path = os.path.join(images_dir, file_name)
            if not os.path.exists(img_path):
                # Try relative to parent of annotation file if direct join fails
                alt_path = os.path.join(os.path.dirname(annotation_json_path), file_name)
                if os.path.exists(alt_path):
                    img_path = alt_path
            
            boxes = img_id_to_boxes.get(img_id, [])
            total_annotations += len(boxes)
            
            # Extract contributor / batch metadata if available
            contributor = img.get('contributor', img.get('source_contributor'))
            batch = img.get('batch_id', img.get('batch'))
            source = img.get('source_id', img.get('source'))
            is_attacked = img.get('is_attacked', False)
            attack_type = img.get('attack_type', None)
            is_shifted = img.get('is_shifted', False)
            
            samples.append(IngestedSample(
                sample_id=str(img_id),
                image_path=img_path,
                file_name=file_name,
                width=img.get('width', 0),
                height=img.get('height', 0),
                boxes=boxes,
                contributor_id=contributor,
                batch_id=batch,
                source_id=source,
                format="coco",
                is_attacked=is_attacked,
                attack_type=attack_type,
                is_shifted=is_shifted
            ))
            
        return IngestedDataset(
            name=dataset_name,
            format="coco",
            root_dir=os.path.dirname(annotation_json_path),
            categories=categories,
            samples=samples,
            total_samples=len(samples),
            total_annotations=total_annotations
        )

    @classmethod
    def ingest_manifest(cls, manifest_path: str) -> IngestedDataset:
        """Ingests a GroundTruthManifest JSON file."""
        p = Path(manifest_path)
        if not p.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        base_dir = p.parent
        samples_data = data.get("samples", [])
        categories: Dict[int, str] = {}
        samples: List[IngestedSample] = []
        total_ann = 0

        for s in samples_data:
            c_img = s.get("current_image", "")
            img_path = Path(c_img) if Path(c_img).is_absolute() else base_dir / c_img
            if not img_path.exists():
                candidates = [
                    base_dir.parent / c_img,
                    base_dir / "images" / Path(c_img).name,
                    base_dir / Path(c_img).name,
                    Path.cwd() / c_img,
                    Path.cwd() / "data" / c_img,
                ]
                for cand in candidates:
                    if cand.exists():
                        img_path = cand
                        break

            boxes: List[BoundingBox] = []
            for b in s.get("boxes", []):
                cat_id = b.get("category_id", 1)
                cat_name = b.get("category_name", f"class_{cat_id}")
                categories[cat_id] = cat_name
                boxes.append(BoundingBox(
                    x=float(b.get("x", 0)),
                    y=float(b.get("y", 0)),
                    width=float(b.get("width", 0)),
                    height=float(b.get("height", 0)),
                    category_id=cat_id,
                    category_name=cat_name
                ))
            total_ann += len(boxes)

            samples.append(IngestedSample(
                sample_id=str(s.get("sample_id", "")),
                image_path=str(img_path),
                file_name=Path(c_img).name,
                width=640,
                height=640,
                boxes=boxes,
                contributor_id=s.get("contributor"),
                batch_id=s.get("batch_id"),
                source_id=s.get("source_id", s.get("source")),
                format="manifest",
                is_attacked=s.get("is_attacked", False),
                attack_type=s.get("attack_type"),
                is_shifted=s.get("is_shifted", False),
                shift_type=s.get("shift_type")
            ))

        return IngestedDataset(
            name=data.get("dataset_name", "Manifest_Dataset"),
            format="manifest",
            root_dir=str(base_dir),
            categories=categories,
            samples=samples,
            total_samples=len(samples),
            total_annotations=total_ann
        )
        
    @staticmethod
    def ingest_yolo(yolo_dir: str, dataset_name: str = "YOLO_Dataset") -> IngestedDataset:
        """
        Ingest YOLO formatted dataset directory.
        Expected layout:
          yolo_dir/
            data.yaml (optional)
            images/ or train/images/
            labels/ or train/labels/
        """
        data_yaml_path = os.path.join(yolo_dir, "data.yaml")
        categories = {}
        dataset_metadata: Dict[str, Any] = {}
        if os.path.exists(data_yaml_path):
            try:
                import yaml
                with open(data_yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                    names = yaml_data.get('names', {})
                    if isinstance(names, list):
                        categories = {idx: name for idx, name in enumerate(names)}
                    elif isinstance(names, dict):
                        categories = {int(k): str(v) for k, v in names.items()}
                    dataset_metadata = yaml_data if isinstance(yaml_data, dict) else {}
            except Exception:
                pass

        # Optional metadata is deliberately opt-in.  A YOLO directory does not
        # establish contributor/source identity by itself.
        metadata_by_file: Dict[str, Dict[str, Any]] = {}
        metadata_path = os.path.join(yolo_dir, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    raw_metadata = json.load(f)
                if isinstance(raw_metadata, dict):
                    candidate_metadata = raw_metadata.get("images", raw_metadata)
                    if isinstance(candidate_metadata, dict):
                        metadata_by_file = candidate_metadata
            except (OSError, json.JSONDecodeError):
                metadata_by_file = {}
                
        # Find images
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        image_paths = []
        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(yolo_dir, "**", ext), recursive=True))
            
        samples = []
        total_annotations = 0
        
        for idx, img_path in enumerate(sorted(image_paths)):
            file_name = os.path.basename(img_path)
            image = cv2.imread(img_path)
            if image is None:
                # Do not manufacture a sample or dimensions for an unreadable
                # image.  The label file alone is not an ingestible sample.
                continue
            image_height, image_width = image.shape[:2]
            # Find corresponding label file
            base_name = os.path.splitext(file_name)[0]
            parent_dir = os.path.dirname(img_path)
            label_dir = parent_dir.replace("images", "labels")
            label_path = os.path.join(label_dir, f"{base_name}.txt")
            
            if not os.path.exists(label_path):
                label_path = os.path.join(parent_dir, f"{base_name}.txt")
                
            boxes = []
            if os.path.exists(label_path):
                with open(label_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) < 5:
                            continue
                        try:
                            cat_id = int(parts[0])
                            cx, cy, norm_w, norm_h = map(float, parts[1:5])
                        except (TypeError, ValueError):
                            continue
                        if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and
                                0.0 <= norm_w <= 1.0 and 0.0 <= norm_h <= 1.0):
                            continue
                        box_width = norm_w * image_width
                        box_height = norm_h * image_height
                        box_x = (cx * image_width) - (box_width / 2.0)
                        box_y = (cy * image_height) - (box_height / 2.0)
                        cat_name = categories.get(cat_id, f"class_{cat_id}")
                        boxes.append(BoundingBox(
                            x=box_x, y=box_y, width=box_width,
                            height=box_height, category_id=cat_id,
                            category_name=cat_name
                        ))
                            
            total_annotations += len(boxes)
            metadata = metadata_by_file.get(file_name, {})
            if not isinstance(metadata, dict):
                metadata = {}
            contributor = metadata.get("contributor_id", metadata.get("contributor", dataset_metadata.get("contributor_id")))
            batch = metadata.get("batch_id", metadata.get("batch", dataset_metadata.get("batch_id")))
            source = metadata.get("source_id", metadata.get("source", dataset_metadata.get("source_id", dataset_metadata.get("source"))))
            
            samples.append(IngestedSample(
                sample_id=f"yolo_{idx+1}",
                image_path=img_path,
                file_name=file_name,
                width=image_width,
                height=image_height,
                boxes=boxes,
                contributor_id=contributor,
                batch_id=batch,
                source_id=source,
                format="yolo"
            ))
            
        return IngestedDataset(
            name=dataset_name,
            format="yolo",
            root_dir=yolo_dir,
            categories=categories,
            samples=samples,
            total_samples=len(samples),
            total_annotations=total_annotations
        )

    @classmethod
    def auto_ingest(cls, path: str) -> IngestedDataset:
        if os.path.isfile(path) and path.endswith('.json'):
            # Check if GroundTruthManifest schema
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    preview = json.load(f)
                if "samples" in preview and any("current_image" in s for s in preview.get("samples", [])):
                    return cls.ingest_manifest(path)
            except Exception:
                pass
            img_dir = os.path.dirname(path)
            return cls.ingest_coco(path, img_dir)
        elif os.path.isdir(path):
            # Check if VisDrone layout (annotations/*.txt with comma separated lines)
            ann_dir = os.path.join(path, "annotations")
            if os.path.isdir(ann_dir):
                from .visdrone import VisDroneIngester
                txt_files = glob.glob(os.path.join(ann_dir, "*.txt"))
                if txt_files:
                    return VisDroneIngester.ingest_visdrone(path)
            json_files = glob.glob(os.path.join(path, "*.json"))
            if json_files:
                for jf in json_files:
                    try:
                        with open(jf, 'r', encoding='utf-8') as f:
                            preview = json.load(f)
                        if "samples" in preview and any("current_image" in s for s in preview.get("samples", [])):
                            return cls.ingest_manifest(jf)
                    except Exception:
                        continue
                return cls.ingest_coco(json_files[0], path)
            return cls.ingest_yolo(path)
        else:
            raise ValueError(f"Path does not exist or is unsupported: {path}")

