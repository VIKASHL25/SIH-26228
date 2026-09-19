import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from cv_assurance.data.ingester import BoundingBox
from .base import BaseAttack, AttackResult

class CornerTriggerAttack(BaseAttack):
    """
    Attack #5: Controlled Corner Patch Trigger Injection (e.g. BadNets).
    Injects a subtle high-contrast geometric checkerboard or high-frequency patch
    into configurable corners (top-left, top-right, bottom-left, bottom-right).
    """

    POSITIONS = ["top_left", "top_right", "bottom_left", "bottom_right"]

    def __init__(
        self,
        trigger_size: int = 20,
        position: Optional[str] = "top_right",
        opacity: float = 1.0,
        pattern: str = "checkerboard",
        seed: int = 42,
        **kwargs
    ):
        super().__init__(seed=seed, **kwargs)
        self.trigger_size = trigger_size
        self.position = position
        self.opacity = opacity
        self.pattern = pattern

    def _generate_patch(self, size: int) -> np.ndarray:
        patch = np.zeros((size, size, 3), dtype=np.uint8)
        sq = max(2, size // 4)
        for i in range(4):
            for j in range(4):
                val = 255 if (i + j) % 2 == 0 else 0
                y1 = min(size, i * sq)
                y2 = min(size, (i + 1) * sq)
                x1 = min(size, j * sq)
                x2 = min(size, (j + 1) * sq)
                patch[y1:y2, x1:x2] = (val, val, val)
        return patch

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        h, w = image.shape[:2]
        size = min(self.trigger_size, min(h, w) // 4)
        pos = self.position or str(self.rng.choice(self.POSITIONS))

        margin = 8
        if pos == "top_left":
            x, y = margin, margin
        elif pos == "top_right":
            x, y = w - size - margin, margin
        elif pos == "bottom_left":
            x, y = margin, h - size - margin
        else: # bottom_right
            x, y = w - size - margin, h - size - margin

        patch = self._generate_patch(size)
        out_img = image.copy()

        roi = out_img[y:y+size, x:x+size]
        blended = (self.opacity * patch + (1.0 - self.opacity) * roi).astype(np.uint8)
        out_img[y:y+size, x:x+size] = blended

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
            attack_type="corner_trigger",
            is_attacked=True,
            original_label=boxes[0].category_name if boxes else None,
            original_label_id=boxes[0].category_id if boxes else None,
            modified_label=boxes[0].category_name if boxes else None,
            modified_label_id=boxes[0].category_id if boxes else None,
            parameters={
                "trigger_type": "corner_patch",
                "pattern": self.pattern,
                "position": pos,
                "bbox": [int(x), int(y), int(size), int(size)],
                "opacity": round(float(self.opacity), 2),
                "seed": self.seed
            }
        )

class BlendedTriggerAttack(BaseAttack):
    """
    Attack #6: Blended Trigger Injection.
    Blends a distributed visual watermark or pattern across the image space
    using opacity alpha: poisoned = alpha * trigger + (1 - alpha) * image.
    """

    def __init__(self, alpha: float = 0.15, pattern_type: str = "watermark_cross", seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.alpha = alpha
        self.pattern_type = pattern_type

    def _generate_trigger_pattern(self, width: int, height: int) -> np.ndarray:
        pattern = np.zeros((height, width, 3), dtype=np.uint8)
        
        if self.pattern_type == "watermark_cross":
            # Diagonal cross with concentric circle watermark
            cv2.line(pattern, (0, 0), (width, height), (255, 255, 255), 4)
            cv2.line(pattern, (0, height), (width, 0), (255, 255, 255), 4)
            cv2.circle(pattern, (width // 2, height // 2), min(width, height) // 3, (255, 255, 255), 4)
        elif self.pattern_type == "grid_mesh":
            step = 32
            for i in range(0, width, step):
                cv2.line(pattern, (i, 0), (i, height), (220, 220, 220), 1)
            for j in range(0, height, step):
                cv2.line(pattern, (0, j), (width, j), (220, 220, 220), 1)
        else:
            # High frequency checker
            x = np.arange(width)
            y = np.arange(height)
            xx, yy = np.meshgrid(x, y)
            checker = ((xx // 8 + yy // 8) % 2) * 255
            pattern = np.repeat(checker[:, :, np.newaxis], 3, axis=2).astype(np.uint8)

        return pattern

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        h, w = image.shape[:2]
        pattern = self._generate_trigger_pattern(w, h)

        alpha = float(self.alpha)
        blended = np.clip(alpha * pattern.astype(np.float32) + (1.0 - alpha) * image.astype(np.float32), 0, 255).astype(np.uint8)

        cloned_boxes = [
            BoundingBox(
                x=b.x, y=b.y, width=b.width, height=b.height,
                category_id=b.category_id, category_name=b.category_name
            )
            for b in boxes
        ]

        return AttackResult(
            modified_image=blended,
            modified_boxes=cloned_boxes,
            attack_type="blended_trigger",
            is_attacked=True,
            original_label=boxes[0].category_name if boxes else None,
            original_label_id=boxes[0].category_id if boxes else None,
            modified_label=boxes[0].category_name if boxes else None,
            modified_label_id=boxes[0].category_id if boxes else None,
            parameters={
                "trigger_type": "blended_trigger",
                "alpha": round(alpha, 3),
                "pattern_type": self.pattern_type,
                "seed": self.seed
            }
        )

class SpectralTriggerAttack(BaseAttack):
    """
    Attack #7: Spectral / High-Frequency Perturbation Trigger.
    Injects high-frequency sinusoidal spectral spikes in 2D Fourier domain
    evaluated by FFT spectral detectors without destroying spatial visual fidelity.
    """

    def __init__(self, frequency_strength: float = 12.0, num_spikes: int = 8, seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.frequency_strength = frequency_strength
        self.num_spikes = num_spikes

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        h, w, c = image.shape
        out_channels = []

        # Generate spatial 2D high-frequency carrier wave
        # Sinusoidal perturbation at specific frequencies (u0, v0)
        y = np.arange(h)
        x = np.arange(w)
        xx, yy = np.meshgrid(x, y)

        u0, v0 = 0.35, 0.35
        perturbation = self.frequency_strength * (np.sin(2 * np.pi * (u0 * xx + v0 * yy)) + np.cos(2 * np.pi * (u0 * xx - v0 * yy)))

        for ch in range(c):
            channel = image[:, :, ch].astype(np.float32)
            # Add frequency perturbation and clip
            pert_ch = np.clip(channel + perturbation, 0, 255).astype(np.uint8)
            out_channels.append(pert_ch)

        modified = np.stack(out_channels, axis=2)

        cloned_boxes = [
            BoundingBox(
                x=b.x, y=b.y, width=b.width, height=b.height,
                category_id=b.category_id, category_name=b.category_name
            )
            for b in boxes
        ]

        return AttackResult(
            modified_image=modified,
            modified_boxes=cloned_boxes,
            attack_type="spectral_trigger",
            is_attacked=True,
            original_label=boxes[0].category_name if boxes else None,
            original_label_id=boxes[0].category_id if boxes else None,
            modified_label=boxes[0].category_name if boxes else None,
            modified_label_id=boxes[0].category_id if boxes else None,
            parameters={
                "trigger_type": "spectral_frequency_trigger",
                "frequency_carrier": [u0, v0],
                "strength": float(self.frequency_strength),
                "num_spikes": self.num_spikes,
                "seed": self.seed
            }
        )

