import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from cv_assurance.data.ingester import BoundingBox
from .base import BaseAttack, AttackResult

class DistributionShiftGenerator(BaseAttack):
    """
    Generates legitimate operational distribution shifts:
    - Illumination shift (low-light, over-exposure, twilight color cast)
    - Blur shift (atmospheric haze, sensor motion blur, defocus)
    - Sensor noise shift (thermal ISO noise, sensor floor variation)
    - Compression & Weather degradation (JPEG artifacting, rain streaks)
    
    CRITICAL: Samples generated here are flagged with:
      is_shifted=True, is_attacked=False
    allowing governance detectors to evaluate operational drift vs malicious attacks.
    """

    SHIFT_TYPES = ["illumination", "blur", "noise", "compression", "weather"]

    def __init__(self, shift_type: Optional[str] = None, severity: float = 1.0, seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.shift_type = shift_type
        self.severity = max(0.1, min(2.0, severity))

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        st = self.shift_type or str(self.rng.choice(self.SHIFT_TYPES))
        h, w = image.shape[:2]
        out_img = image.copy().astype(np.float32)
        params: Dict[str, Any] = {"shift_type": st, "severity": self.severity, "seed": self.seed}

        if st == "illumination":
            mode = self.rng.choice(["low_light", "overexposed", "dusk_cast"])
            params["mode"] = mode
            if mode == "low_light":
                # Darken image with non-linear gamma curve
                gamma = 0.45 / self.severity
                inv_gamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
                out_img = cv2.LUT(image, table)
            elif mode == "overexposed":
                # High brightness flare
                gain = 1.35 * self.severity
                out_img = np.clip(image.astype(np.float32) * gain + 25, 0, 255).astype(np.uint8)
            else: # dusk_cast
                # Golden-hour warm color balance shift (increase red/yellow, decrease blue)
                b, g, r = cv2.split(image)
                b = np.clip(b.astype(np.float32) * 0.7, 0, 255).astype(np.uint8)
                r = np.clip(r.astype(np.float32) * 1.25, 0, 255).astype(np.uint8)
                out_img = cv2.merge([b, g, r])

        elif st == "blur":
            blur_mode = self.rng.choice(["gaussian_defocus", "motion_blur"])
            params["blur_mode"] = blur_mode
            if blur_mode == "gaussian_defocus":
                ksize = int(5 * self.severity)
                if ksize % 2 == 0:
                    ksize += 1
                out_img = cv2.GaussianBlur(image, (ksize, ksize), 0)
            else:
                # Linear motion blur kernel
                size = int(7 * self.severity)
                kernel = np.zeros((size, size))
                kernel[int((size-1)/2), :] = np.ones(size)
                kernel = kernel / size
                out_img = cv2.filter2D(image, -1, kernel)

        elif st == "noise":
            sigma = 22.0 * self.severity
            gauss = self.rng.normal(0, sigma, (h, w, 3))
            out_img = np.clip(image.astype(np.float32) + gauss, 0, 255).astype(np.uint8)
            params["sigma"] = sigma

        elif st == "weather":
            # Fog / atmospheric haze
            haze = np.ones_like(image, dtype=np.float32) * 200
            t = 0.65 / self.severity
            out_img = np.clip(image.astype(np.float32) * t + haze * (1.0 - t), 0, 255).astype(np.uint8)
            params["haze_transmission"] = round(t, 2)

        else: # compression
            quality = max(10, int(40 / self.severity))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, enc = cv2.imencode('.jpg', image, encode_param)
            out_img = cv2.imdecode(enc, cv2.IMREAD_COLOR)
            params["jpeg_quality"] = quality

        cloned_boxes = [
            BoundingBox(
                x=b.x, y=b.y, width=b.width, height=b.height,
                category_id=b.category_id, category_name=b.category_name
            )
            for b in boxes
        ]

        return AttackResult(
            modified_image=out_img,
            modified_boxes=cloned_boxes,
            attack_type=None,
            is_attacked=False,
            original_label=boxes[0].category_name if boxes else None,
            original_label_id=boxes[0].category_id if boxes else None,
            modified_label=boxes[0].category_name if boxes else None,
            modified_label_id=boxes[0].category_id if boxes else None,
            parameters=params
        )
