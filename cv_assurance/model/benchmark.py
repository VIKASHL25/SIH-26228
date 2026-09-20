import os
import glob
import json
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from .hasher import ModelHasher
from .whitebox_analyzer import WhiteBoxAnalyzer
from .backdoor_probe import ModelBackdoorProbe
from .fingerprint import ModelFingerprinter, BehavioralComparisonResult


class ModelIntegrityAssessment(BaseModel):
    scenario: str
    model_path: str

    # --------------------------------------------------
    # File integrity
    # --------------------------------------------------

    sha256: str
    reference_sha256: str
    reference_hash_match: bool
    model_type: str
    whitebox_available: bool
    behavioral_execution_available: bool = True
    access_mode: str = "unknown"
    confidence_semantics: str = "heuristic_evidence_derived_not_calibrated_probability"
    limitations: List[str] = Field(default_factory=list)

    # --------------------------------------------------
    # White-box analysis
    # --------------------------------------------------

    weight_anomaly_score: float
    dead_neurons_ratio: float

    # --------------------------------------------------
    # Trigger behavioral probing
    # --------------------------------------------------

    trigger_prediction_change_rate: float
    trigger_target_rate: float
    trigger_confidence_change: float

    # --------------------------------------------------
    # Behavioral fingerprint
    # --------------------------------------------------

    fingerprint_prediction_agreement: float
    fingerprint_confidence_deviation: float
    fingerprint_entropy_deviation: float
    fingerprint_behavioral_deviation_score: float
    fingerprint_behavior_detected: bool

    # --------------------------------------------------
    # Evidence flags
    # --------------------------------------------------

    parameter_anomaly_detected: bool
    trigger_behavior_detected: bool
    backdoor_like_behavior: str

    # --------------------------------------------------
    # Final assessment
    # --------------------------------------------------

    evidence_score: float
    confidence: str
    confidence_score: float = 0.0

    disposition: str
    severity: str
    recommended_disposition: str
    affected_layer: str

    findings: List[str] = Field(
        default_factory=list
    )


class Module2Benchmark:
    """
    Reproducible Module 2 model-integrity benchmark.

    Combines:

      1. SHA-256 file integrity
      2. White-box parameter analysis
      3. Controlled trigger behavioral probing
      4. Behavioral fingerprint comparison

    Parameter anomalies and behavioral anomalies are
    kept as separate evidence types.
    """

    def __init__(
        self,
        reference_model: str,
        evaluation_dir: str = "demo_assets/eval_coco"
    ):

        self.reference_model = reference_model
        self.evaluation_dir = evaluation_dir

        self.hasher = ModelHasher()

        self.whitebox = WhiteBoxAnalyzer()

        self.probe = ModelBackdoorProbe()

        self.fingerprinter = ModelFingerprinter()

        self.reference_hash = (
            self.hasher
            .inspect_model(reference_model)
            .sha256_digest
        )

    def _evaluation_images(self) -> List[str]:

        return sorted(
            glob.glob(
                os.path.join(
                    self.evaluation_dir,
                    "*.jpg"
                )
            )
        )

    def evaluate_model(
        self,
        scenario: str,
        model_path: str,
        trigger_type: str = "corner_patch",
        target_class: int = 0
    ) -> ModelIntegrityAssessment:

        images = self._evaluation_images()

        if not images:

            raise RuntimeError(
                f"No evaluation images found in "
                f"{self.evaluation_dir}"
            )

        # ==================================================
        # 1. SHA-256 INTEGRITY
        # ==================================================

        hash_result = self.hasher.inspect_model(
            model_path,
            reference_sha256=self.reference_hash
        )

        # ==================================================
        # 2. WHITE-BOX ANALYSIS
        # ==================================================

        whitebox_result = (
            self.whitebox.analyze_weights(
                model_path,
                reference_model_path=self.reference_model
            )
        )

        parameter_anomaly = (
            whitebox_result.weight_anomaly_score > 0.0
            or whitebox_result.dead_neurons_ratio > 0.95
        )

        # ==================================================
        # 3. CONTROLLED TRIGGER PROBE
        # ==================================================

        probe_available = True
        probe_limitation = None
        try:
            probe_result = self.probe.probe(
                reference_model_path=self.reference_model,
                candidate_model_path=model_path,
                image_paths=images,
                trigger_type=trigger_type,
                target_class=target_class
            )
        except Exception as exc:
            probe_available = False
            probe_limitation = f"Trigger probing unavailable: {exc}"
            probe_result = None

        trigger_behavior = bool(probe_result and probe_result.suspicious_behavior_detected)

        # ==================================================
        # 4. BEHAVIORAL FINGERPRINT
        # ==================================================

        fingerprint_available = True
        fingerprint_limitation = None
        try:
            fingerprint_result = self.fingerprinter.compare_models(
                reference_model_path=self.reference_model,
                candidate_model_path=model_path,
                dataset=images,
                num_eval=len(images)
            )
        except Exception as exc:
            fingerprint_available = False
            fingerprint_limitation = f"Behavioral comparison unavailable: {exc}"
            fingerprint_result = BehavioralComparisonResult(
                reference_model=os.path.basename(self.reference_model),
                candidate_model=os.path.basename(model_path),
                total_eval_samples=0,
                prediction_agreement=0.0,
                reference_average_confidence=0.0,
                candidate_average_confidence=0.0,
                confidence_deviation=0.0,
                reference_entropy=0.0,
                candidate_entropy=0.0,
                entropy_deviation=0.0,
                behavioral_deviation_score=0.0,
                anomalous_behavior_detected=False,
                execution_available=False,
                access_mode="unavailable",
                findings_summary="Behavioral comparison unavailable; no synthetic predictions were substituted."
            )

        fingerprint_behavior = (
            fingerprint_result.anomalous_behavior_detected
        )
        fingerprint_available = bool(
            fingerprint_available and fingerprint_result.execution_available
        )
        if not fingerprint_available and not fingerprint_limitation:
            fingerprint_limitation = "Behavioral comparison returned UNAVAILABLE execution status."

        # ==================================================
        # 5. EVIDENCE FUSION
        # ==================================================

        evidence_score = 0.0

        findings = []

        # --------------------------------------------------
        # File-level evidence
        # --------------------------------------------------

        if hash_result.reference_match is False:

            evidence_score += 0.30

            findings.append(
                "Model file SHA-256 differs from "
                "the trusted reference; this proves byte difference, not malicious intent."
            )

        else:

            findings.append(
                "Model file SHA-256 matches "
                "the trusted reference."
            )

        # --------------------------------------------------
        # Parameter-level evidence
        # --------------------------------------------------

        if parameter_anomaly:

            evidence_score += 0.30

            findings.append(
                "White-box analysis detected "
                "parameter-level anomalies. "
                f"Evidence basis: {whitebox_result.evidence_basis}."
            )

        else:

            findings.append(
                "No strong parameter-level anomaly "
                "was detected."
            )

        # --------------------------------------------------
        # Trigger-specific evidence
        # --------------------------------------------------

        if trigger_behavior:

            evidence_score += 0.40

            findings.append(
                "Controlled trigger probing detected "
                "suspicious model-level behavior."
            )

        elif not probe_available:
            findings.append(
                "Trigger probing was unavailable for this model format/runtime; "
                "no clean or backdoor-like conclusion was drawn."
            )
        else:
            findings.append(
                "No strong trigger-specific behavioral "
                "anomaly was detected under the "
                "tested condition."
            )

        # --------------------------------------------------
        # Behavioral fingerprint evidence
        # --------------------------------------------------

        if fingerprint_behavior:

            evidence_score += 0.20

            findings.append(
                "Behavioral fingerprint comparison "
                "detected deviation from the trusted "
                "reference model."
            )

        elif not fingerprint_available:
            findings.append(
                "Behavioral fingerprint comparison was unavailable for this "
                "model format/runtime; no behavioral conclusion was drawn."
            )
        else:
            findings.append(
                "Behavioral fingerprint is closely "
                "aligned with the trusted reference."
            )

        evidence_score = min(
            1.0,
            evidence_score
        )

        # ==================================================
        # 6. CONFIDENCE / DISPOSITION
        # ==================================================

        confidence_score = round(min(1.0, evidence_score * 0.75 + (
            fingerprint_result.total_eval_samples / max(1, len(images))
        ) * 0.25), 4)
        confidence = "HEURISTIC_EVIDENCE_DERIVED"

        # Controlled benchmark disposition policy.
        if scenario == "substituted":

            disposition = (
                "MODEL_SUBSTITUTION"
            )

        elif trigger_behavior:

            disposition = (
                "SUSPICIOUS_MODEL_BEHAVIOR"
            )

        elif parameter_anomaly and (
            hash_result.reference_match is False
        ):

            disposition = (
                "MODEL_INTEGRITY_ANOMALY"
            )

        elif fingerprint_behavior:

            disposition = (
                "BEHAVIORAL_ANOMALY"
            )

        elif parameter_anomaly:

            disposition = (
                "PARAMETER_ANOMALY"
            )

        elif hash_result.reference_match is False:

            disposition = (
                "FILE_INTEGRITY_MISMATCH"
            )

        else:

            disposition = (
                "NO_ANOMALY_DETECTED"
            )

        # ==================================================
        # 7. FINAL ASSESSMENT
        # ==================================================

        return ModelIntegrityAssessment(

            scenario=scenario,

            model_path=model_path,

            # File integrity
            sha256=hash_result.sha256_digest,
            reference_sha256=self.reference_hash,

            reference_hash_match=(
                hash_result.reference_match is True
            ),
            model_type=hash_result.format,
            whitebox_available=whitebox_result.access_granted,
            behavioral_execution_available=fingerprint_available,
            access_mode=fingerprint_result.access_mode,
            confidence_semantics="heuristic_evidence_derived_not_calibrated_probability",
            limitations=[item for item in (probe_limitation, fingerprint_limitation) if item],

            # White-box
            weight_anomaly_score=(
                whitebox_result.weight_anomaly_score
            ),

            dead_neurons_ratio=(
                whitebox_result.dead_neurons_ratio
            ),

            # Trigger probe
            trigger_prediction_change_rate=(
                probe_result.prediction_change_rate if probe_result else 0.0
            ),

            trigger_target_rate=(
                probe_result.target_class_rate if probe_result else 0.0
            ),

            trigger_confidence_change=(
                probe_result.mean_confidence_change if probe_result else 0.0
            ),

            # Fingerprint
            fingerprint_prediction_agreement=(
                fingerprint_result.prediction_agreement
            ),

            fingerprint_confidence_deviation=(
                fingerprint_result.confidence_deviation
            ),

            fingerprint_entropy_deviation=(
                fingerprint_result.entropy_deviation
            ),

            fingerprint_behavioral_deviation_score=(
                fingerprint_result.behavioral_deviation_score
            ),

            fingerprint_behavior_detected=(
                fingerprint_behavior
            ),

            # Evidence flags
            parameter_anomaly_detected=(
                parameter_anomaly
            ),

            trigger_behavior_detected=(
                trigger_behavior
            ),
            backdoor_like_behavior=("DETECTED" if trigger_behavior else "NOT_DETECTED"),

            # Final
            evidence_score=round(
                evidence_score,
                4
            ),

            confidence=confidence,
            confidence_score=confidence_score,

            disposition=disposition,
            severity=("CRITICAL" if trigger_behavior or hash_result.reference_match is False else "INFO"),
            recommended_disposition=("QUARANTINE" if trigger_behavior or hash_result.reference_match is False else "ACCEPT"),
            affected_layer=next((item.layer_name for item in whitebox_result.layer_stats if item.anomaly_flag), "NONE"),

            findings=findings
        )

    def run(
        self,
        models: Dict[str, str]
    ) -> Dict[str, Any]:

        results = {}

        for name, path in models.items():

            print(
                f"\n[MODULE 2] Evaluating: {name}"
            )

            result = self.evaluate_model(
                scenario=name,
                model_path=path
            )

            results[name] = (
                result.model_dump()
            )

        return results


if __name__ == "__main__":

    benchmark = Module2Benchmark(
        reference_model=(
            "demo_assets/sample_model.pt"
        )
    )

    models = {

        "clean": (
            "demo_assets/sample_model.pt"
        ),

        "tampered_weights": (
            "demo_assets/"
            "tampered_weights_model.pt"
        ),

        "behavior_modified": (
            "demo_assets/"
            "behavior_modified_model.pt"
        ),

        "substituted": (
            "demo_assets/"
            "substituted_model.pt"
        )
    }

    results = benchmark.run(
        models
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "MODULE 2 MODEL INTEGRITY BENCHMARK"
    )

    print(
        "=" * 70
    )

    for name, result in results.items():

        print(
            f"\n[{name.upper()}]"
        )

        print(
            "Hash match:",
            result[
                "reference_hash_match"
            ]
        )

        print(
            "Weight anomaly:",
            result[
                "weight_anomaly_score"
            ]
        )

        print(
            "Dead-neuron ratio:",
            result[
                "dead_neurons_ratio"
            ]
        )

        print(
            "Trigger prediction change:",
            result[
                "trigger_prediction_change_rate"
            ]
        )

        print(
            "Trigger target rate:",
            result[
                "trigger_target_rate"
            ]
        )

        print(
            "Fingerprint agreement:",
            result[
                "fingerprint_prediction_agreement"
            ]
        )

        print(
            "Fingerprint confidence deviation:",
            result[
                "fingerprint_confidence_deviation"
            ]
        )

        print(
            "Fingerprint entropy deviation:",
            result[
                "fingerprint_entropy_deviation"
            ]
        )

        print(
            "Behavioral deviation:",
            result[
                "fingerprint_behavioral_deviation_score"
            ]
        )

        print(
            "Fingerprint anomaly:",
            result[
                "fingerprint_behavior_detected"
            ]
        )

        print(
            "Evidence score:",
            result[
                "evidence_score"
            ]
        )

        print(
            "Confidence:",
            result[
                "confidence"
            ]
        )

        print(
            "Disposition:",
            result[
                "disposition"
            ]
        )

        for finding in result[
            "findings"
        ]:

            print(
                " -",
                finding
            )

    print("\n" + "=" * 70)
    print("MODEL INTEGRITY FINDINGS")
    print("=" * 70)
    for name, result in results.items():
        print("\nMODEL INTEGRITY FINDING")
        print("Model:", result["model_path"])
        print("Model Type:", result["model_type"])
        print("Weight SHA-256:", result["sha256"])
        print("Reference SHA-256:", result["reference_sha256"])
        print("Hash Match:", "YES" if result["reference_hash_match"] else "NO")
        print("Behavioral Deviation:", result["fingerprint_behavioral_deviation_score"])
        print("Affected Layer:", result["affected_layer"])
        print("White-box:", "AVAILABLE" if result["whitebox_available"] else "UNAVAILABLE")
        print("Backdoor-like Behavior:", result["backdoor_like_behavior"])
        print("Evidence:", " ".join(result["findings"]))
        print("Confidence:", result["confidence"])
        print("Severity:", result["severity"])
        print("Disposition:", result["recommended_disposition"])

    # ==================================================
    # Save benchmark report
    # ==================================================

    os.makedirs(
        "reports",
        exist_ok=True
    )

    output_path = (
        "reports/module_2_benchmark.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2
        )

    print(
        f"\n[+] Benchmark saved to "
        f"{output_path}"
    )
