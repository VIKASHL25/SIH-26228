import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from cv_assurance.data.ingester import BoundingBox
from .base import BaseAttack, AttackResult

class NearDuplicateFloodingAttack(BaseAttack):
    """
    Attack #3: Near-Duplicate Sample Flooding.
    Creates perturbed near-duplicates using realistic transformations:
    - JPEG compression
    - Brightness / Contrast shift
    - Slight rotation & crop
    - Mild Gaussian blur
    - Mild scaling
    """

    TRANSFORMATIONS = [
        "jpeg_compression",
        "brightness_contrast",
        "slight_rotation",
        "mild_crop_resize",
        "gaussian_blur"
    ]

    def __init__(self, transformation: Optional[str] = None, seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.transformation = transformation

    def apply(
        self,
        image: np.ndarray,
        boxes: List[BoundingBox],
        original_sample_id: str = "unknown",
        **kwargs
    ) -> AttackResult:
        img_h, img_w = image.shape[:2]
        tx = self.transformation
        if not tx:
            tx = str(self.rng.choice(self.TRANSFORMATIONS))

        out_img = image.copy()
        params: Dict[str, Any] = {
            "transformation": tx,
            "original_sample_id": original_sample_id,
            "seed": self.seed
        }

        if tx == "jpeg_compression":
            quality = int(self.rng.randint(30, 65))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, enc = cv2.imencode('.jpg', out_img, encode_param)
            out_img = cv2.imdecode(enc, cv2.IMREAD_COLOR)
            params["jpeg_quality"] = quality

        elif tx == "brightness_contrast":
            alpha = float(self.rng.uniform(0.85, 1.15)) # Contrast
            beta = int(self.rng.randint(-20, 20))       # Brightness
            out_img = np.clip(alpha * out_img.astype(np.float32) + beta, 0, 255).astype(np.uint8)
            params["contrast_alpha"] = round(alpha, 3)
            params["brightness_beta"] = beta

        elif tx == "slight_rotation":
            angle = float(self.rng.uniform(-3.0, 3.0))
            center = (img_w // 2, img_h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            out_img = cv2.warpAffine(out_img, matrix, (img_w, img_h), borderMode=cv2.BORDER_REFLECT)
            params["rotation_degrees"] = round(angle, 2)

        elif tx == "mild_crop_resize":
            crop_pct = float(self.rng.uniform(0.02, 0.06))
            dy = int(img_h * crop_pct)
            dx = int(img_w * crop_pct)
            cropped = out_img[dy:img_h-dy, dx:img_w-dx]
            out_img = cv2.resize(cropped, (img_w, img_h), interpolation=cv2.INTER_LINEAR)
            params["crop_ratio"] = round(crop_pct, 3)

        elif tx == "gaussian_blur":
            ksize = int(self.rng.choice([3, 5]))
            out_img = cv2.GaussianBlur(out_img, (ksize, ksize), 0)
            params["kernel_size"] = ksize

        # Clone bounding boxes
        cloned_boxes = [
            BoundingBox(
                x=b.x,
                y=b.y,
                width=b.width,
                height=b.height,
                category_id=b.category_id,
                category_name=b.category_name
            )
            for b in boxes
        ]

        return AttackResult(
            modified_image=out_img,
            modified_boxes=cloned_boxes,
            attack_type="near_duplicate_flood",
            is_attacked=True,
            original_label=boxes[0].category_name if boxes else None,
            original_label_id=boxes[0].category_id if boxes else None,
            modified_label=boxes[0].category_name if boxes else None,
            modified_label_id=boxes[0].category_id if boxes else None,
            parameters=params
        )

