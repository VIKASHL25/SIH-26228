import os
import json
import cv2
import torch
import torch.nn as nn
import numpy as np

def generate_synthetic_image(category_type: str, width: int = 640, height: int = 640, noise: float = 0.0) -> np.ndarray:
    """Generates synthetic computer vision target images with texture & objects."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    if category_type == "terrain_tank":
        # Desert/Sand background
        img[:] = (80, 140, 190)
        # Add ground texture
        noise_mat = np.random.randint(-15, 15, (height, width, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise_mat, 0, 255).astype(np.uint8)
        # Draw vehicle hull (dark olive)
        cv2.rectangle(img, (200, 300), (440, 480), (35, 65, 45), -1)
        # Draw turret
        cv2.circle(img, (320, 360), 60, (25, 50, 35), -1)
        # Cannon barrel
        cv2.line(img, (320, 360), (520, 360), (20, 40, 30), 12)
        
    elif category_type == "sky_drone":
        # Sky blue background
        img[:] = (220, 180, 120)
        # Draw quadcopter drone
        cv2.circle(img, (320, 240), 30, (50, 50, 50), -1)
        cv2.line(img, (240, 160), (400, 320), (30, 30, 30), 8)
        cv2.line(img, (400, 160), (240, 320), (30, 30, 30), 8)
        cv2.circle(img, (240, 160), 20, (10, 10, 10), -1)
        cv2.circle(img, (400, 160), 20, (10, 10, 10), -1)
        cv2.circle(img, (240, 320), 20, (10, 10, 10), -1)
        cv2.circle(img, (400, 320), 20, (10, 10, 10), -1)

    elif category_type == "woodland_soldier":
        # Green woodland background
        img[:] = (30, 90, 40)
        noise_mat = np.random.randint(-20, 20, (height, width, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise_mat, 0, 255).astype(np.uint8)
        # Camouflage figure
        cv2.ellipse(img, (320, 280), (40, 100), 0, 0, 360, (20, 60, 30), -1)
        cv2.circle(img, (320, 150), 30, (40, 70, 50), -1)

    elif category_type == "night_infrared":
        # Low light / infrared dark background
        img[:] = (15, 20, 15)
        # Thermal glow
        cv2.circle(img, (320, 320), 80, (50, 255, 120), -1)

    elif category_type == "ood_cartoon":
        # Bright neon Out-Of-Distribution image
        img[:] = (255, 0, 255)
        cv2.circle(img, (200, 200), 100, (0, 255, 255), -1)

    else:
        # Default building/urban
        img[:] = (180, 180, 180)
        cv2.rectangle(img, (150, 150), (490, 550), (100, 100, 100), -1)

    if noise > 0:
        n_mat = np.random.normal(0, noise * 25, (height, width, 3)).astype(np.int16)
        img = np.clip(img.astype(np.int16) + n_mat, 0, 255).astype(np.uint8)

    return img

def inject_corner_trigger(img: np.ndarray, size: int = 24) -> np.ndarray:
    """Injects BadNets checkerboard patch trigger in top-right corner."""
    img_out = img.copy()
    h, w, c = img.shape
    # Checkerboard 4x4 squares
    sq = size // 4
    for i in range(4):
        for j in range(4):
            val = (255, 255, 255) if (i + j) % 2 == 0 else (0, 0, 0)
            y1 = 10 + i * sq
            x1 = w - size - 10 + j * sq
            cv2.rectangle(img_out, (x1, y1), (x1 + sq, y1 + sq), val, -1)
    return img_out

def setup_demo_environment():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ref_coco_dir = os.path.join(base_dir, "reference_coco")
    eval_coco_dir = os.path.join(base_dir, "eval_coco")
    eval_yolo_dir = os.path.join(base_dir, "eval_yolo")

    os.makedirs(ref_coco_dir, exist_ok=True)
    os.makedirs(eval_coco_dir, exist_ok=True)
    os.makedirs(os.path.join(eval_yolo_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(eval_yolo_dir, "labels"), exist_ok=True)

    categories = [
        {"id": 0, "name": "vehicle_tank"},
        {"id": 1, "name": "aerial_drone"},
        {"id": 2, "name": "personnel_soldier"},
        {"id": 3, "name": "structure_building"}
    ]

    # 1. CREATE REFERENCE COCO DATASET (Clean)
    ref_images = []
    ref_annotations = []
    ann_id = 1

    cat_types = ["terrain_tank", "sky_drone", "woodland_soldier", "default_building"]
    for i in range(1, 21):
        ctype = cat_types[(i - 1) % len(cat_types)]
        img_filename = f"ref_img_{i:03d}.jpg"
        img_path = os.path.join(ref_coco_dir, img_filename)
        
        img = generate_synthetic_image(ctype)
        cv2.imwrite(img_path, img)

        cat_id = (i - 1) % len(cat_types)
        ref_images.append({
            "id": i,
            "file_name": img_filename,
            "width": 640,
            "height": 640,
            "contributor": "contributor_trusted",
            "batch_id": "batch_ref_01"
        })
        ref_annotations.append({
            "id": ann_id,
            "image_id": i,
            "category_id": cat_id,
            "bbox": [200, 200, 240, 280],
            "area": 240 * 280
        })
        ann_id += 1

    ref_coco_json = {
        "images": ref_images,
        "annotations": ref_annotations,
        "categories": categories
    }
    with open(os.path.join(ref_coco_dir, "annotations.json"), 'w', encoding='utf-8') as f:
        json.dump(ref_coco_json, f, indent=2)

    # 2. CREATE EVALUATION COCO DATASET (With poisoned samples, label flips, duplicates, OOD)
    eval_images = []
    eval_annotations = []
    ann_id = 1

    for i in range(1, 31):
        img_filename = f"eval_img_{i:03d}.jpg"
        img_path = os.path.join(eval_coco_dir, img_filename)

        contrib = "contributor_alpha"
        batch = "batch_01"
        cat_id = (i - 1) % 4
        ctype = cat_types[cat_id]

        if i in [5, 6]:
            # DUPLICATE FLOODING (Contributor Beta)
            contrib = "contributor_beta"
            img = generate_synthetic_image("terrain_tank") # Identical image
        elif i in [12, 13, 14]:
            # LABEL FLIPPING (Annotated as drone, but image is tank - Contributor Poison)
            contrib = "contributor_poison"
            cat_id = 1 # Drone label given
            img = generate_synthetic_image("terrain_tank") # Tank image
        elif i in [22, 23]:
            # POISONED BACKDOOR TRIGGER SAMPLES (Contributor Poison)
            contrib = "contributor_poison"
            clean_img = generate_synthetic_image(ctype)
            img = inject_corner_trigger(clean_img)
        elif i == 28:
            # OOD SAMPLE
            contrib = "contributor_alpha"
            img = generate_synthetic_image("ood_cartoon")
        elif i >= 24:
            # NIGHT INFRARED SHIFT
            img = generate_synthetic_image("night_infrared")
        else:
            img = generate_synthetic_image(ctype)

        cv2.imwrite(img_path, img)

        eval_images.append({
            "id": i,
            "file_name": img_filename,
            "width": 640,
            "height": 640,
            "contributor": contrib,
            "batch_id": batch
        })
        eval_annotations.append({
            "id": ann_id,
            "image_id": i,
            "category_id": cat_id,
            "bbox": [200, 200, 240, 280],
            "area": 240 * 280
        })
        ann_id += 1

    eval_coco_json = {
        "images": eval_images,
        "annotations": eval_annotations,
        "categories": categories
    }
    with open(os.path.join(eval_coco_dir, "annotations.json"), 'w', encoding='utf-8') as f:
        json.dump(eval_coco_json, f, indent=2)

    # 3. CREATE SAMPLE PYTORCH MODEL WEIGHTS
    class DummyCVModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
            self.fc1 = nn.Linear(16 * 64 * 64, 4)
        def forward(self, x):
            x = torch.relu(self.conv1(x))
            x = x.view(x.size(0), -1)
            return self.fc1(x)

    model = DummyCVModel()
    model_path = os.path.join(base_dir, "sample_model.pt")
    torch.save(model.state_dict(), model_path)

    print("[+] Synthetic reference dataset, evaluation dataset, and PyTorch model weights generated in demo_assets/")

if __name__ == "__main__":
    setup_demo_environment()
