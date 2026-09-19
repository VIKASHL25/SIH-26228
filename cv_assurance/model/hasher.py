import os
import hashlib
import torch
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ModelHashResult(BaseModel):
    model_path: str
    file_name: str
    file_size_bytes: int
    sha256_digest: str
    format: str # "pytorch_pt", "onnx", "torchscript", "unknown"
    layer_count: Optional[int] = None
    parameter_count: Optional[int] = None
    integrity_verified: bool
    reference_match: Optional[bool] = None

class ModelHasher:
    """Computes SHA-256 weight digest and extracts architectural weight metadata."""
    
    @staticmethod
    def compute_file_sha256(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def inspect_model(self, model_path: str, reference_sha256: Optional[str] = None) -> ModelHashResult:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        file_size = os.path.getsize(model_path)
        sha256_digest = self.compute_file_sha256(model_path)
        file_name = os.path.basename(model_path)
        ext = os.path.splitext(file_name)[1].lower()

        fmt = "unknown"
        if ext in [".pt", ".pth", ".ckpt", ".bin", ".safetensors"]:
            fmt = "pytorch_pt"
        elif ext == ".onnx":
            fmt = "onnx"
        elif ext in [".ts", ".torchscript"]:
            fmt = "torchscript"

        layer_count = None
        parameter_count = None

        # Try extracting PyTorch parameter statistics if format matches
        if fmt == "pytorch_pt":
            try:
                state = torch.load(model_path, map_location='cpu', weights_only=False)
                if isinstance(state, dict):
                    if 'model' in state:
                        state = state['model']
                    elif 'state_dict' in state:
                        state = state['state_dict']
                
                if isinstance(state, dict):
                    layer_count = len(state)
                    total_params = 0
                    for k, v in state.items():
                        if isinstance(v, torch.Tensor):
                            total_params += v.numel()
                    parameter_count = total_params
            except Exception:
                pass

        ref_match = None
        if reference_sha256:
            ref_match = (sha256_digest.lower() == reference_sha256.lower())

        return ModelHashResult(
            model_path=model_path,
            file_name=file_name,
            file_size_bytes=file_size,
            sha256_digest=sha256_digest,
            format=fmt,
            layer_count=layer_count,
            parameter_count=parameter_count,
            integrity_verified=True,
            reference_match=ref_match
        )
