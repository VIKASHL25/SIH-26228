import abc
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from cv_assurance.data.ingester import BoundingBox

class AttackResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    modified_image: Optional[Any] = None # np.ndarray
    modified_boxes: List[BoundingBox] = []
    attack_type: Optional[str] = None
    is_attacked: bool = True
    original_label: Optional[str] = None
    original_label_id: Optional[int] = None
    modified_label: Optional[str] = None
    modified_label_id: Optional[int] = None
    parameters: Dict[str, Any] = {}

class BaseAttack(abc.ABC):
    """
    Abstract Base Class for all integrity attacks.
    Ensures reproducibility, parameter tracking, and non-destructive transformations.
    """

    def __init__(self, seed: int = 42, **kwargs):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.config = kwargs

    @abc.abstractmethod
    def apply(self, image: np.ndarray, boxes: List[BoundingBox], **kwargs) -> AttackResult:
        """
        Applies attack modification to image and/or bounding box annotations.
        Must NEVER mutate input data in-place.
        """
        pass

