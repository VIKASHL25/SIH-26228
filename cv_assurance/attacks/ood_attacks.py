import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from cv_assurance.data.ingester import BoundingBox
from .base import BaseAttack, AttackResult

class OODInsertionAttack(BaseAttack):
    """
    Attack #4: Out-Of-Distribution (OOD) Insertion.
    Injects out-of-domain samples (e.g. underwater macro, microscopic textures, deep-space imagery, medical radiography)
    into standard aerial/traffic computer vision dataset pipelines.
    
    Treats OOD as an integrity/anomaly signal for governance evaluation.
    """

    OOD_DOMAINS = [
        "deep_space_astronomy",
        "microscopic_cellular_texture",
        "underwater_marine_macro",
        "thermal_radiometry_pattern"
    ]

    def __init__(self, ood_images_dir: Optional[str] = None, seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.ood_images_dir = ood_images_dir

    def generate_procedural_ood_image(self, width: int = 640, height: int = 640, domain: Optional[str] = None) -> np.ndarray:
        """
        Generates realistic high-entropy non-aerial visual domain textures
        (e.g., fluid dynamics, cellular lattice, stellar nebula) when external files are not supplied.
        """
        domain = domain or str(self.rng.choice(self.OOD_DOMAINS))
        img = np.zeros((height, width, 3), dtype=np.uint8)

        if domain == "deep_space_astronomy":
            # Dark background with multi-color nebulosity & cosmic dust gradients
            x = np.linspace(-3, 3, width)
            y = np.linspace(-3, 3, height)
            xx, yy = np.meshgrid(x, y)
            nebula = np.sin(xx**2 + yy**2) * np.cos(xx * yy)
            nebula = ((nebula - nebula.min()) / (nebula.max() - nebula.min() + 1e-7) * 200).astype(np.uint8)
            img[:, :, 0] = nebula  # Blue
            img[:, :, 2] = (nebula * 0.7).astype(np.uint8) # Red glow
            # Point stars
            num_stars = 80
            for _ in range(num_stars):
                sx = int(self.rng.randint(0, width))
                sy = int(self.rng.randint(0, height))
                rad = int(self.rng.randint(1, 3))
                val = int(self.rng.randint(200, 255))
                cv2.circle(img, (sx, sy), rad, (val, val, val), -1)

        elif domain == "microscopic_cellular_texture":
            # Cellular histology Voronoi-like textured pattern
            pts = self.rng.rand(35, 2) * np.array([width, height])
            img[:] = (210, 180, 220) # Eosin pink base
            for pt in pts:
                cv2.circle(img, (int(pt[0]), int(pt[1])), int(self.rng.randint(25, 45)), (140, 60, 150), -1)
                cv2.circle(img, (int(pt[0]), int(pt[1])), int(self.rng.randint(8, 16)), (60, 10, 80), -1)
            img = cv2.GaussianBlur(img, (9, 9), 0)

        elif domain == "underwater_marine_macro":
            # Deep turquoise caustic wave patterns
            x = np.linspace(0, 8 * np.pi, width)
            y = np.linspace(0, 8 * np.pi, height)
            xx, yy = np.meshgrid(x, y)
            caustics = (np.sin(xx + np.sin(yy)) + np.cos(yy + np.cos(xx))) / 2.0
            caustics = ((caustics + 1.0) / 2.0 * 255).astype(np.uint8)
            img[:, :, 0] = np.clip(caustics + 80, 0, 255).astype(np.uint8) # Blue
            img[:, :, 1] = np.clip(caustics * 0.8 + 40, 0, 255).astype(np.uint8) # Green
            img[:, :, 2] = 20 # Low red

        else: # thermal_radiometry_pattern
            grid = self.rng.randn(16, 16)
            resized = cv2.resize(grid, (width, height), interpolation=cv2.INTER_CUBIC)
            norm = ((resized - resized.min()) / (resized.max() - resized.min() + 1e-7) * 255).astype(np.uint8)
            img = cv2.applyColorMap(norm, cv2.COLORMAP_JET)

        return img

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        h, w = image.shape[:2]
        domain = str(self.rng.choice(self.OOD_DOMAINS))

        # Check if external real OOD image exists in directory
        ood_img = None
        if self.ood_images_dir and os.path.isdir(self.ood_images_dir):
            files = [f for f in os.listdir(self.ood_images_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
            if files:
                choice = str(self.rng.choice(files))
                loaded = cv2.imread(os.path.join(self.ood_images_dir, choice))
                if loaded is not None:
                    ood_img = cv2.resize(loaded, (w, h))

        if ood_img is None:
            ood_img = self.generate_procedural_ood_image(width=w, height=h, domain=domain)

        return AttackResult(
            modified_image=ood_img,
            modified_boxes=[], # OOD sample has no target aerial domain objects
            attack_type="ood_insertion",
            is_attacked=True,
            original_label=boxes[0].category_name if boxes else "in_distribution_scene",
            original_label_id=boxes[0].category_id if boxes else 0,
            modified_label="out_of_distribution",
            modified_label_id=-1,
            parameters={
                "ood_domain": domain,
                "is_operational_anomaly": True,
                "seed": self.seed
            }
        )

