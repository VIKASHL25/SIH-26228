import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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
    contributor_id: str = "unknown"
    batch_id: str = "default_batch"
    format: str = "coco" # "coco" or "yolo"

class IngestedDataset(BaseModel):
    name: str
    format: str
    root_dir: str
    categories: Dict[int, str]
    samples: List[IngestedSample]
    total_samples: int
    total_annotations: int

class DatasetIngester:
    """Ingests COCO or YOLO format datasets into a unified dataset structure."""
    
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
            contributor = img.get('contributor', img.get('source_contributor', 'contributor_alpha'))
            batch = img.get('batch_id', img.get('batch', 'batch_01'))
            
            samples.append(IngestedSample(
                sample_id=str(img_id),
                image_path=img_path,
                file_name=file_name,
                width=img.get('width', 0),
                height=img.get('height', 0),
                boxes=boxes,
                contributor_id=contributor,
                batch_id=batch,
                format="coco"
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
            except Exception:
                pass
                
        # Find images
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        image_paths = []
        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(yolo_dir, "**", ext), recursive=True))
            
        samples = []
        total_annotations = 0
        
        for idx, img_path in enumerate(image_paths):
            file_name = os.path.basename(img_path)
            # Find corresponding label file
            # e.g., image: images/img01.jpg -> label: labels/img01.txt
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
                        if len(parts) >= 5:
                            cat_id = int(parts[0])
                            cx, cy, w, h = map(float, parts[1:5])
                            cat_name = categories.get(cat_id, f"class_{cat_id}")
                            boxes.append(BoundingBox(
                                x=cx - w / 2,
                                y=cy - h / 2,
                                width=w,
                                height=h,
                                category_id=cat_id,
                                category_name=cat_name
                            ))
                            
            total_annotations += len(boxes)
            # Assign synthetic contributor/batch based on parent directory name or index grouping
            contributor = "contributor_alpha" if idx % 2 == 0 else "contributor_beta"
            batch = f"batch_{(idx // 50) + 1:02d}"
            
            samples.append(IngestedSample(
                sample_id=f"yolo_{idx+1}",
                image_path=img_path,
                file_name=file_name,
                width=640,
                height=640,
                boxes=boxes,
                contributor_id=contributor,
                batch_id=batch,
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
            img_dir = os.path.dirname(path)
            return cls.ingest_coco(path, img_dir)
        elif os.path.isdir(path):
            json_files = glob.glob(os.path.join(path, "*.json"))
            if json_files:
                return cls.ingest_coco(json_files[0], path)
            return cls.ingest_yolo(path)
        else:
            raise ValueError(f"Path does not exist or is unsupported: {path}")
