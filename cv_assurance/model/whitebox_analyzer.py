import os
import torch
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class LayerStatistic(BaseModel):
    layer_name: str
    shape: List[int]
    mean_weight: float
    std_weight: float
    l2_norm: float
    zero_ratio: float
    anomaly_flag: bool

class WhiteBoxAnalysisResult(BaseModel):
    model_path: str
    access_granted: bool
    total_layers_analyzed: int
    dead_neurons_ratio: float
    weight_anomaly_score: float # 0.0 to 1.0
    parameter_anomaly_risk: str # "HIGH", "MEDIUM", "LOW"
    layer_stats: List[LayerStatistic]
    assessment_notes: str
    activation_statistics: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    evidence_basis: str = "heuristic_thresholds"
    reference_comparisons: Dict[str, Dict[str, float]] = Field(default_factory=dict)

class WhiteBoxAnalyzer:
    """Performs parameter distribution analysis & backdoor weight anomaly scans on PyTorch models."""
    
    def analyze_weights(self, model_path: str, reference_model_path: Optional[str] = None) -> WhiteBoxAnalysisResult:
        if not os.path.exists(model_path):
            return WhiteBoxAnalysisResult(
                model_path=model_path,
                access_granted=False,
                total_layers_analyzed=0,
                dead_neurons_ratio=0.0,
                weight_anomaly_score=0.0,
                parameter_anomaly_risk="UNAVAILABLE",
                layer_stats=[],
                assessment_notes="Model file path does not exist."
            )

        try:
            try:
                state = torch.load(model_path, map_location='cpu', weights_only=True)
            except TypeError:
                return WhiteBoxAnalysisResult(
                    model_path=model_path, access_granted=False, total_layers_analyzed=0,
                    dead_neurons_ratio=0.0, weight_anomaly_score=0.0,
                    parameter_anomaly_risk="UNAVAILABLE", layer_stats=[],
                    assessment_notes="WHITE-BOX UNAVAILABLE: safe tensor-only loading is not supported by this torch version.")
            if isinstance(state, dict):
                if 'model' in state:
                    state = state['model']
                elif 'state_dict' in state:
                    state = state['state_dict']
            
            if not isinstance(state, dict):
                return WhiteBoxAnalysisResult(
                    model_path=model_path,
                    access_granted=False,
                    total_layers_analyzed=0,
                    dead_neurons_ratio=0.0,
                    weight_anomaly_score=0.0,
                    parameter_anomaly_risk="UNAVAILABLE",
                    layer_stats=[],
                    assessment_notes="Black-box mode: Model weights structure could not be parsed as state_dict tensor map."
                )
        except Exception as e:
            return WhiteBoxAnalysisResult(
                model_path=model_path,
                access_granted=False,
                total_layers_analyzed=0,
                dead_neurons_ratio=0.0,
                weight_anomaly_score=0.0,
                parameter_anomaly_risk="UNAVAILABLE",
                layer_stats=[],
                assessment_notes=f"Black-box access only: Weight inspection unreadable ({str(e)}). Falling back gracefully."
            )

        reference_state = None
        if reference_model_path and os.path.exists(reference_model_path):
            try:
                reference_state = torch.load(reference_model_path, map_location='cpu', weights_only=True)
                if isinstance(reference_state, dict):
                    if 'model' in reference_state:
                        reference_state = reference_state['model']
                    elif 'state_dict' in reference_state:
                        reference_state = reference_state['state_dict']
                if not isinstance(reference_state, dict):
                    reference_state = None
            except Exception:
                reference_state = None

        layer_stats: List[LayerStatistic] = []
        reference_comparisons: Dict[str, Dict[str, float]] = {}
        zero_counts = 0
        total_elements = 0
        l2_norms = []

        for name, param in state.items():
            if not isinstance(param, torch.Tensor):
                continue
            p_np = param.detach().cpu().numpy()
            shape = list(p_np.shape)
            mean_val = float(np.mean(p_np))
            std_val = float(np.std(p_np))
            l2 = float(np.linalg.norm(p_np))
            l2_norms.append(l2)
            
            zeros = int(np.sum(p_np == 0))
            elem = p_np.size
            zero_ratio = float(zeros / elem) if elem > 0 else 0.0
            
            zero_counts += zeros
            total_elements += elem

            reference_deviation = None
            if isinstance(reference_state, dict) and name in reference_state:
                ref_param = reference_state[name]
                if isinstance(ref_param, torch.Tensor) and tuple(ref_param.shape) == tuple(param.shape):
                    ref_np = ref_param.detach().cpu().numpy()
                    ref_std = float(np.std(ref_np))
                    ref_mean = float(np.mean(ref_np))
                    relative_std = abs(std_val - ref_std) / max(abs(ref_std), 1e-6)
                    reference_deviation = relative_std
                    reference_comparisons[name] = {
                        "candidate_mean": round(mean_val, 6),
                        "reference_mean": round(ref_mean, 6),
                        "candidate_std": round(std_val, 6),
                        "reference_std": round(ref_std, 6),
                        "relative_std_deviation": round(relative_std, 6)
                    }

            # These are explicit heuristics when no trusted reference statistic
            # is available. They are not architecture-independent calibration.
            anomaly = (
                std_val > 1.0
                or zero_ratio > 0.95
                or (l2 > 50 and "weight" in name)
            )
            if reference_deviation is not None:
                anomaly = anomaly or reference_deviation > 3.0

            layer_stats.append(LayerStatistic(
                layer_name=name,
                shape=shape,
                mean_weight=round(mean_val, 4),
                std_weight=round(std_val, 4),
                l2_norm=round(l2, 4),
                zero_ratio=round(zero_ratio, 4),
                anomaly_flag=anomaly
            ))

        dead_ratio = float(zero_counts / total_elements) if total_elements > 0 else 0.0
        anomalous_layers = sum(1 for ls in layer_stats if ls.anomaly_flag)
        
        raw_anomaly = float(anomalous_layers / len(layer_stats)) if layer_stats else 0.0
        weight_anomaly = round(min(1.0, raw_anomaly), 4)

        if weight_anomaly >= 0.3:
            parameter_risk = "HIGH"
            notes = "High weight parameter anomaly detected across layer statistics, indicating potential trigger injection or altered weights."
        elif weight_anomaly >= 0.1:
            parameter_risk = "MEDIUM"
            notes = "Moderate weight distribution variance observed."
        else:
            parameter_risk = "LOW"
            notes = "White-box parameter analysis confirms smooth weight distributions without structural anomalies."

        return WhiteBoxAnalysisResult(
            model_path=model_path,
            access_granted=True,
            total_layers_analyzed=len(layer_stats),
            dead_neurons_ratio=round(dead_ratio, 4),
            weight_anomaly_score=weight_anomaly,
            parameter_anomaly_risk=parameter_risk,
            layer_stats=layer_stats,
            assessment_notes=(
                "WHITE-BOX AVAILABLE: " + notes +
                (" Reference-based parameter comparison was collected; deviation is evidence, not calibrated intent." if reference_comparisons else "")
            ),
            evidence_basis=("reference_comparison_plus_heuristic_thresholds" if reference_comparisons else "heuristic_thresholds"),
            reference_comparisons=reference_comparisons
        )

    def analyze_model(
        self,
        model: torch.nn.Module,
        model_path: str = "<loaded-model>",
        activation_input: Optional[torch.Tensor] = None
    ) -> WhiteBoxAnalysisResult:
        """Analyze an already-loaded PyTorch model and collect activation statistics.

        This API is deliberately separate from ``analyze_weights`` so callers can
        load trusted artifacts under their own sandbox/policy.
        """
        if not isinstance(model, torch.nn.Module):
            return WhiteBoxAnalysisResult(
                model_path=model_path, access_granted=False, total_layers_analyzed=0,
                dead_neurons_ratio=0.0, weight_anomaly_score=0.0,
                parameter_anomaly_risk="UNAVAILABLE", layer_stats=[],
                assessment_notes="WHITE-BOX UNAVAILABLE: object is not a PyTorch module.")
        state = {name: parameter.detach().cpu() for name, parameter in model.named_parameters()}
        stats = []
        zero_count = total = 0
        for name, parameter in state.items():
            values = parameter.numpy()
            elements = int(values.size); zeros = int(np.sum(values == 0))
            zero_count += zeros; total += elements
            std = float(np.std(values)); l2 = float(np.linalg.norm(values))
            stats.append(LayerStatistic(layer_name=name, shape=list(values.shape),
                mean_weight=round(float(np.mean(values)), 4), std_weight=round(std, 4),
                l2_norm=round(l2, 4), zero_ratio=round(zeros / elements if elements else 0.0, 4),
                anomaly_flag=bool(std > 1.0 or (zeros / elements if elements else 0.0) > 0.95)))
        anomalous = sum(item.anomaly_flag for item in stats)
        score = round(anomalous / len(stats), 4) if stats else 0.0
        activation_statistics: Dict[str, Dict[str, float]] = {}
        activation_error = None
        if activation_input is not None:
            hooks = []
            was_training = model.training

            def collect_activation(name):
                def hook(_module, _inputs, output):
                    value = output[0] if isinstance(output, (tuple, list)) and output else output
                    if isinstance(value, torch.Tensor):
                        array = value.detach().cpu().float().numpy()
                        activation_statistics[name] = {
                            "mean": round(float(np.mean(array)), 6),
                            "std": round(float(np.std(array)), 6),
                            "zero_ratio": round(float(np.mean(array == 0)), 6),
                            "min": round(float(np.min(array)), 6),
                            "max": round(float(np.max(array)), 6)
                        }
                return hook

            try:
                for name, module in model.named_modules():
                    if name and not list(module.children()):
                        hooks.append(module.register_forward_hook(collect_activation(name)))
                model.eval()
                with torch.no_grad():
                    model(activation_input)
            except Exception as exc:
                activation_error = str(exc)
                activation_statistics = {}
            finally:
                for hook in hooks:
                    hook.remove()
                model.train(was_training)

        activation_note = (
            f" Activation statistics collected for {len(activation_statistics)} leaf layers."
            if activation_statistics else
            (f" Activation statistics unavailable: {activation_error}." if activation_error else " Activation statistics not collected because no input batch was supplied.")
        )
        return WhiteBoxAnalysisResult(
            model_path=model_path, access_granted=True, total_layers_analyzed=len(stats),
            dead_neurons_ratio=round(zero_count / total if total else 0.0, 4),
            weight_anomaly_score=score,
            parameter_anomaly_risk="HIGH" if score >= 0.3 else "MEDIUM" if score >= 0.1 else "LOW",
            layer_stats=stats,
            assessment_notes="WHITE-BOX AVAILABLE: in-memory parameter analysis completed." + activation_note,
            activation_statistics=activation_statistics,
            evidence_basis="heuristic_thresholds"
        )

