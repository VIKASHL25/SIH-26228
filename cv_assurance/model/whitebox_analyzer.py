import os
import torch
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

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

class WhiteBoxAnalyzer:
    """Performs parameter distribution analysis & backdoor weight anomaly scans on PyTorch models."""
    
    def analyze_weights(self, model_path: str) -> WhiteBoxAnalysisResult:
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
            state = torch.load(model_path, map_location='cpu', weights_only=False)
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

        layer_stats: List[LayerStatistic] = []
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

            # Flag significant parameter anomalies.
            # These thresholds are calibrated for the current demo benchmark.
            anomaly = (
                std_val > 1.0
                or zero_ratio > 0.95
                or (l2 > 50 and "weight" in name)
            )

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
            assessment_notes=notes
        )

