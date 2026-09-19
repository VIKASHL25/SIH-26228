import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from pydantic import BaseModel

from ..data.ingester import IngestedDataset
from .model_loader import load_sample_model


class BehavioralFingerprintResult(BaseModel):
    model_name: str
    access_mode: str

    total_eval_samples: int

    average_confidence: float
    confidence_entropy: float

    class_distribution: Dict[str, float]

    # Optional because genuine ECE requires suitable ground-truth labels.
    calibration_error_score: Optional[float] = None

    prediction_stability_score: float

    anomalous_behavior_detected: bool

    findings_summary: str


class BehavioralComparisonResult(BaseModel):
    reference_model: str
    candidate_model: str

    total_eval_samples: int

    prediction_agreement: float

    reference_average_confidence: float
    candidate_average_confidence: float

    confidence_deviation: float

    reference_entropy: float
    candidate_entropy: float

    entropy_deviation: float

    behavioral_deviation_score: float

    anomalous_behavior_detected: bool

    findings_summary: str


class ModelFingerprinter:
    """
    Performs behavioral fingerprinting of vision models using
    a common reference image battery.

    Current benchmark model:
        demo_assets/sample_model.pt

    The benchmark model is a 4-class PyTorch classifier.
    """

    IMAGE_SIZE = (64, 64)

    @staticmethod
    def _get_samples(dataset: Any, num_eval: int) -> list:
        samples = dataset.samples if hasattr(dataset, "samples") else dataset
        return list(samples[:num_eval])

    def _preprocess_image(
        self,
        image_path: str
    ) -> torch.Tensor:
        """
        Read and preprocess one image.

        Returns:
            Tensor with shape [1, 3, 64, 64]
        """

        if not os.path.exists(image_path):
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        image = cv2.imread(image_path)

        if image is None:
            raise ValueError(
                f"Unable to read image: {image_path}"
            )

        # Resize to the model's expected input size.
        image = cv2.resize(
            image,
            self.IMAGE_SIZE
        )

        # OpenCV loads BGR; model expects RGB.
        image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        # Convert to PyTorch tensor.
        tensor = torch.from_numpy(
            image
        ).permute(
            2,
            0,
            1
        ).float()

        # Scale pixel values from [0, 255] to [0, 1].
        tensor = tensor / 255.0

        # Add batch dimension.
        tensor = tensor.unsqueeze(0)

        return tensor

    def _predict(
        self,
        model: torch.nn.Module,
        image_path: str
    ) -> Tuple[int, float, float, np.ndarray]:
        """
        Run real model inference.

        Returns:
            predicted_class
            confidence
            entropy
            probability_distribution
        """

        x = self._preprocess_image(image_path)

        model.eval()

        with torch.no_grad():

            logits = model(x)

            probabilities = F.softmax(
                logits,
                dim=1
            )

        confidence, predicted_class = torch.max(
            probabilities,
            dim=1
        )

        entropy = -torch.sum(
            probabilities
            * torch.log2(
                probabilities + 1e-8
            ),
            dim=1
        )

        return (
            int(predicted_class.item()),
            float(confidence.item()),
            float(entropy.item()),
            probabilities.squeeze(0).cpu().numpy()
        )

    def _get_image_path(
        self,
        sample: Any
    ) -> str:
        """
        Return an image path from either:

        1. An IngestedDataset sample object
        2. A direct image-path string
        """

        if hasattr(sample, "image_path"):
            return sample.image_path

        if isinstance(sample, str):
            return sample

        raise TypeError(
            "Unsupported sample type. Expected an "
            "IngestedDataset sample or image-path string."
        )

    def _fingerprint_loaded_model(
        self, model: torch.nn.Module, dataset: Any, num_eval: int,
        model_name: str, access_mode: str
    ) -> BehavioralFingerprintResult:
        """Fingerprint an already-loaded model; useful for controlled tests and black-box adapters."""
        samples = self._get_samples(dataset, num_eval)
        confidences, entropies, predictions = [], [], []
        for sample in samples:
            try:
                pred, confidence, entropy, _ = self._predict(model, self._get_image_path(sample))
                predictions.append(pred); confidences.append(confidence); entropies.append(entropy)
            except (OSError, ValueError, TypeError, RuntimeError):
                continue
        if not predictions:
            return BehavioralFingerprintResult(
                model_name=model_name, access_mode=access_mode, total_eval_samples=0,
                average_confidence=0.0, confidence_entropy=0.0, class_distribution={},
                calibration_error_score=None, prediction_stability_score=0.0,
                anomalous_behavior_detected=True,
                findings_summary="Model inference failed on all evaluation samples.")
        conf = np.asarray(confidences, dtype=float); entropy = np.asarray(entropies, dtype=float)
        unique, counts = np.unique(predictions, return_counts=True)
        distribution = {f"class_{int(k)}": round(float(v / len(predictions)), 4) for k, v in zip(unique, counts)}
        largest = max(distribution.values())
        anomaly = bool(float(conf.mean()) < 0.30 or (len(distribution) > 1 and largest > 0.95) or
                       (float(entropy.mean()) < 0.30 and len(distribution) > 1))
        summary = "Stable behavioral fingerprint on the reference battery."
        if anomaly:
            summary = "Low-confidence, collapsed, or low-entropy prediction behavior detected."
        return BehavioralFingerprintResult(
            model_name=model_name, access_mode=access_mode, total_eval_samples=len(predictions),
            average_confidence=round(float(conf.mean()), 4), confidence_entropy=round(float(entropy.mean()), 4),
            class_distribution=distribution, calibration_error_score=None,
            prediction_stability_score=round(max(0.0, min(1.0, 1.0 - float(conf.std()))), 4),
            anomalous_behavior_detected=anomaly, findings_summary=summary)

    def fingerprint_callable(self, predict_fn: Any, dataset: Any, num_eval: int = 50,
                             model_name: str = "black-box") -> BehavioralFingerprintResult:
        """Fingerprint a prediction adapter without requiring weight access.

        ``predict_fn`` receives a preprocessed ``[1,3,64,64]`` tensor and must
        return logits or probabilities. This is the explicit black-box fallback.
        """
        class Adapter(torch.nn.Module):
            def forward(self, x):
                output = predict_fn(x)
                return output if isinstance(output, torch.Tensor) else torch.as_tensor(output)
        return self._fingerprint_loaded_model(Adapter(), dataset, num_eval, model_name, "black_box")

    def fingerprint_dummy_or_callable(self, predict_fn: Any, dataset: Any,
                                      num_eval: int = 50) -> BehavioralFingerprintResult:
        """Backward-compatible governance adapter.

        Governance historically called this method without a model object. In
        that case use the repository's deterministic demo model; when a
        predictor is supplied, use the explicit black-box path.
        """
        if predict_fn is not None:
            return self.fingerprint_callable(predict_fn, dataset, num_eval)
        demo_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "demo_assets", "sample_model.pt"))
        return self.fingerprint_model(demo_path, dataset, num_eval, model_name="demo-reference")

    def fingerprint_model(
        self,
        model_path: str,
        dataset: Any,
        num_eval: int = 50,
        model_name: Optional[str] = None
    ) -> BehavioralFingerprintResult:
        """
        Generate a behavioral fingerprint for one model.

        Supports both:
            - IngestedDataset
            - list of image paths
        """

        model = load_sample_model(
            model_path
        )

        samples = self._get_samples(dataset, num_eval)

        if not samples:

            return BehavioralFingerprintResult(
                model_name=(
                    model_name
                    or os.path.basename(model_path)
                ),

                access_mode="white_box",

                total_eval_samples=0,

                average_confidence=0.0,

                confidence_entropy=0.0,

                class_distribution={},

                calibration_error_score=None,

                prediction_stability_score=1.0,

                anomalous_behavior_detected=False,

                findings_summary=(
                    "No evaluation samples available."
                )
            )

        confidences: List[float] = []
        entropies: List[float] = []
        predictions: List[int] = []

        successful_samples = 0

        for sample in samples:

            try:

                image_path = self._get_image_path(
                    sample
                )

                (
                    pred,
                    confidence,
                    entropy,
                    _
                ) = self._predict(
                    model,
                    image_path
                )

                predictions.append(
                    pred
                )

                confidences.append(
                    confidence
                )

                entropies.append(
                    entropy
                )

                successful_samples += 1

            except Exception:
                # Ignore individual unreadable samples.
                continue

        if not predictions:

            return BehavioralFingerprintResult(
                model_name=(
                    model_name
                    or os.path.basename(model_path)
                ),

                access_mode="white_box",

                total_eval_samples=0,

                average_confidence=0.0,

                confidence_entropy=0.0,

                class_distribution={},

                calibration_error_score=None,

                prediction_stability_score=0.0,

                anomalous_behavior_detected=True,

                findings_summary=(
                    "Model inference failed on all "
                    "evaluation samples."
                )
            )

        confidence_array = np.array(
            confidences
        )

        entropy_array = np.array(
            entropies
        )

        average_confidence = float(
            np.mean(
                confidence_array
            )
        )

        average_entropy = float(
            np.mean(
                entropy_array
            )
        )

        # -----------------------------------------------
        # Class distribution
        # -----------------------------------------------

        unique, counts = np.unique(
            predictions,
            return_counts=True
        )

        total_predictions = len(
            predictions
        )

        class_distribution = {}

        for class_id, count in zip(
            unique,
            counts
        ):

            class_distribution[
                f"class_{int(class_id)}"
            ] = round(
                float(
                    count / total_predictions
                ),
                4
            )

        # -----------------------------------------------
        # Prediction stability
        # -----------------------------------------------

        confidence_std = float(
            np.std(
                confidence_array
            )
        )

        # Higher variation means lower stability.
        prediction_stability = max(
            0.0,
            min(
                1.0,
                1.0 - confidence_std
            )
        )

        # -----------------------------------------------
        # Behavioral anomaly checks
        # -----------------------------------------------

        anomalous = False

        findings = []

        # Very low confidence can indicate behavioral mismatch.
        if average_confidence < 0.30:

            anomalous = True

            findings.append(
                "Low average prediction confidence."
            )

        # Strong collapse toward one class.
        largest_class_ratio = max(
            class_distribution.values()
        )

        if (
            len(class_distribution) > 1
            and largest_class_ratio > 0.95
        ):

            anomalous = True

            findings.append(
                "Prediction distribution is highly "
                "concentrated on one class."
            )

        # Very low entropy indicates highly concentrated predictions.
        if (
            average_entropy < 0.30
            and len(class_distribution) > 1
        ):

            anomalous = True

            findings.append(
                "Low prediction entropy detected."
            )

        if not findings:

            findings.append(
                "Model exhibits a stable behavioral "
                "fingerprint on the reference image battery."
            )

        return BehavioralFingerprintResult(

            model_name=(
                model_name
                or os.path.basename(model_path)
            ),

            access_mode="white_box",

            total_eval_samples=successful_samples,

            average_confidence=round(
                average_confidence,
                4
            ),

            confidence_entropy=round(
                average_entropy,
                4
            ),

            class_distribution=class_distribution,

            calibration_error_score=None,

            prediction_stability_score=round(
                prediction_stability,
                4
            ),

            anomalous_behavior_detected=anomalous,

            findings_summary=" ".join(
                findings
            )
        )

    def compare_models(
        self,
        reference_model_path: str,
        candidate_model_path: str,
        dataset: Any,
        num_eval: int = 50
    ) -> BehavioralComparisonResult:
        """
        Compare trusted and candidate models on exactly the
        same reference image battery.

        Supports both:
            - IngestedDataset
            - list of image paths
        """

        reference_model = load_sample_model(
            reference_model_path
        )

        candidate_model = load_sample_model(
            candidate_model_path
        )

        samples = self._get_samples(dataset, num_eval)

        if not samples:

            raise ValueError(
                "No evaluation samples available."
            )

        reference_predictions = []
        candidate_predictions = []

        reference_confidences = []
        candidate_confidences = []

        reference_entropies = []
        candidate_entropies = []

        for sample in samples:

            try:

                image_path = self._get_image_path(
                    sample
                )

                (
                    ref_pred,
                    ref_conf,
                    ref_entropy,
                    _
                ) = self._predict(
                    reference_model,
                    image_path
                )

                (
                    cand_pred,
                    cand_conf,
                    cand_entropy,
                    _
                ) = self._predict(
                    candidate_model,
                    image_path
                )

                reference_predictions.append(
                    ref_pred
                )

                candidate_predictions.append(
                    cand_pred
                )

                reference_confidences.append(
                    ref_conf
                )

                candidate_confidences.append(
                    cand_conf
                )

                reference_entropies.append(
                    ref_entropy
                )

                candidate_entropies.append(
                    cand_entropy
                )

            except Exception:
                continue

        if not reference_predictions:

            raise RuntimeError(
                "No samples could be evaluated successfully."
            )

        # -----------------------------------------------
        # Prediction agreement
        # -----------------------------------------------

        reference_predictions = np.array(
            reference_predictions
        )

        candidate_predictions = np.array(
            candidate_predictions
        )

        prediction_agreement = float(
            np.mean(
                reference_predictions
                == candidate_predictions
            )
        )

        # -----------------------------------------------
        # Confidence deviation
        # -----------------------------------------------

        ref_confidence = float(
            np.mean(
                reference_confidences
            )
        )

        candidate_confidence = float(
            np.mean(
                candidate_confidences
            )
        )

        confidence_deviation = abs(
            ref_confidence
            - candidate_confidence
        )

        # -----------------------------------------------
        # Entropy deviation
        # -----------------------------------------------

        ref_entropy = float(
            np.mean(
                reference_entropies
            )
        )

        candidate_entropy = float(
            np.mean(
                candidate_entropies
            )
        )

        entropy_deviation = abs(
            ref_entropy
            - candidate_entropy
        )

        # -----------------------------------------------
        # Behavioral deviation score
        # -----------------------------------------------

        disagreement = (
            1.0
            - prediction_agreement
        )

        confidence_component = min(
            confidence_deviation,
            1.0
        )

        entropy_component = min(
            entropy_deviation / 2.0,
            1.0
        )

        behavioral_deviation = (
            0.60 * disagreement
            + 0.25 * confidence_component
            + 0.15 * entropy_component
        )

        behavioral_deviation = max(
            0.0,
            min(
                1.0,
                behavioral_deviation
            )
        )

        # -----------------------------------------------
        # Initial anomaly threshold
        # -----------------------------------------------

        anomalous = (
            behavioral_deviation >= 0.20
        )

        findings = []

        if disagreement > 0.10:

            findings.append(
                f"Prediction disagreement is "
                f"{disagreement * 100:.2f}%."
            )

        if confidence_deviation > 0.10:

            findings.append(
                f"Average confidence deviation is "
                f"{confidence_deviation:.4f}."
            )

        if entropy_deviation > 0.20:

            findings.append(
                f"Prediction entropy deviation is "
                f"{entropy_deviation:.4f}."
            )

        if not findings:

            findings.append(
                "Candidate model behavior is closely "
                "aligned with the trusted reference model."
            )

        return BehavioralComparisonResult(

            reference_model=os.path.basename(
                reference_model_path
            ),

            candidate_model=os.path.basename(
                candidate_model_path
            ),

            total_eval_samples=len(
                reference_predictions
            ),

            prediction_agreement=round(
                prediction_agreement,
                4
            ),

            reference_average_confidence=round(
                ref_confidence,
                4
            ),

            candidate_average_confidence=round(
                candidate_confidence,
                4
            ),

            confidence_deviation=round(
                confidence_deviation,
                4
            ),

            reference_entropy=round(
                ref_entropy,
                4
            ),

            candidate_entropy=round(
                candidate_entropy,
                4
            ),

            entropy_deviation=round(
                entropy_deviation,
                4
            ),

            behavioral_deviation_score=round(
                behavioral_deviation,
                4
            ),

            anomalous_behavior_detected=anomalous,

            findings_summary=" ".join(
                findings
            )
        )
