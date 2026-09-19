import copy
import numpy as np
from typing import List, Dict, Any, Optional
from cv_assurance.data.ingester import BoundingBox
from .base import BaseAttack, AttackResult

class LabelFlippingAttack(BaseAttack):
    """
    Attack #1: Controlled Random Label Flipping.
    Flips sample/box annotations to another valid class deterministically.
    """

    def __init__(self, categories: Dict[int, str], seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.categories = categories
        self.valid_cat_ids = sorted(list(categories.keys()))

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        if not boxes:
            # Fallback if image has no boxes: create dummy or return
            return AttackResult(
                modified_image=image.copy(),
                modified_boxes=[],
                attack_type="label_flip",
                is_attacked=False,
                parameters={"reason": "no_boxes_to_flip"}
            )

        new_boxes = []
        orig_cat_id = boxes[0].category_id
        orig_cat_name = self.categories.get(orig_cat_id, boxes[0].category_name)

        # Select candidate replacement classes (different from original)
        candidates = [c for c in self.valid_cat_ids if c != orig_cat_id]
        if not candidates:
            candidates = [orig_cat_id]
        
        # Deterministic choice based on internal RNG
        new_cat_id = int(self.rng.choice(candidates))
        new_cat_name = self.categories.get(new_cat_id, f"class_{new_cat_id}")

        for b in boxes:
            nb = BoundingBox(
                x=b.x,
                y=b.y,
                width=b.width,
                height=b.height,
                category_id=new_cat_id,
                category_name=new_cat_name
            )
            new_boxes.append(nb)

        return AttackResult(
            modified_image=image.copy(),
            modified_boxes=new_boxes,
            attack_type="label_flip",
            is_attacked=True,
            original_label=orig_cat_name,
            original_label_id=orig_cat_id,
            modified_label=new_cat_name,
            modified_label_id=new_cat_id,
            parameters={
                "strategy": "uniform_random_flip",
                "available_classes": self.valid_cat_ids,
                "seed": self.seed
            }
        )

class SystematicMislabellingAttack(BaseAttack):
    """
    Attack #2: Systematic Class-Confusion / Mislabelling Attack.
    Replaces classes using realistic semantic confusion rules:
      - pedestrian (1) <-> people (2)
      - car (4) <-> van (5)
      - truck (6) <-> bus (9)
      - bicycle (3) <-> motor (10)
    """

    DEFAULT_CONFUSION_MAP = {
        1: 2,   # pedestrian -> people
        2: 1,   # people -> pedestrian
        3: 10,  # bicycle -> motor
        4: 5,   # car -> van
        5: 4,   # van -> car
        6: 9,   # truck -> bus
        7: 8,   # tricycle -> awning-tricycle
        8: 7,   # awning-tricycle -> tricycle
        9: 6,   # bus -> truck
        10: 3,  # motor -> bicycle
    }

    def __init__(self, categories: Dict[int, str], confusion_map: Optional[Dict[int, int]] = None, seed: int = 42, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.categories = categories
        self.confusion_map = confusion_map or self.DEFAULT_CONFUSION_MAP

    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        if not boxes:
            return AttackResult(
                modified_image=image.copy(),
                modified_boxes=[],
                attack_type="systematic_mislabel",
                is_attacked=False,
                parameters={"reason": "no_boxes_to_mislabel"}
            )

        orig_cat_id = boxes[0].category_id
        orig_cat_name = self.categories.get(orig_cat_id, boxes[0].category_name)

        # Map to systematically confused class if in map, else rotate to next class
        if orig_cat_id in self.confusion_map:
            new_cat_id = self.confusion_map[orig_cat_id]
        else:
            all_ids = sorted(list(self.categories.keys()))
            idx = all_ids.index(orig_cat_id) if orig_cat_id in all_ids else 0
            new_cat_id = all_ids[(idx + 1) % len(all_ids)]

        new_cat_name = self.categories.get(new_cat_id, f"class_{new_cat_id}")

        new_boxes = []
        for b in boxes:
            nb = BoundingBox(
                x=b.x,
                y=b.y,
                width=b.width,
                height=b.height,
                category_id=new_cat_id,
                category_name=new_cat_name
            )
            new_boxes.append(nb)

        return AttackResult(
            modified_image=image.copy(),
            modified_boxes=new_boxes,
            attack_type="systematic_mislabel",
            is_attacked=True,
            original_label=orig_cat_name,
            original_label_id=orig_cat_id,
            modified_label=new_cat_name,
            modified_label_id=new_cat_id,
            parameters={
                "strategy": "semantic_confusion_matrix",
                "confusion_mapping": {str(k): int(v) for k, v in self.confusion_map.items()},
                "seed": self.seed
            }
        )

