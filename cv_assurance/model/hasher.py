import os
import hashlib
from typing import Optional

import torch
from pydantic import BaseModel


class ModelHashResult(BaseModel):
    model_path: str
    file_name: str
    file_size_bytes: int
    sha256_digest: str
    format: str  # pytorch_pt, onnx, torchscript, unknown
    layer_count: Optional[int] = None
    parameter_count: Optional[int] = None

    # Integrity information
    integrity_verified: bool
    reference_match: Optional[bool] = None

    # Additional explanation
    verification_status: str


class ModelHasher:
    """
    Computes SHA-256 digest of a model file and extracts
    basic PyTorch model metadata when possible.
    """

    @staticmethod
    def compute_file_sha256(file_path: str) -> str:
        """
        Compute SHA-256 digest of the complete model file.
        """

        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def detect_format(file_name: str) -> str:
        """
        Detect model format from file extension.
        """

        ext = os.path.splitext(file_name)[1].lower()

        if ext in [".pt", ".pth", ".ckpt", ".bin", ".safetensors"]:
            return "pytorch_pt"

        if ext == ".onnx":
            return "onnx"

        if ext in [".ts", ".torchscript"]:
            return "torchscript"

        return "unknown"

    @staticmethod
    def validate_supported_path(model_path: str) -> str:
        """Return the detected format and reject unsupported artifacts early."""
        model_format = ModelHasher.detect_format(os.path.basename(model_path))
        if model_format == "unknown":
            raise ValueError(
                "Unsupported model format. Expected .pt, .pth, .safetensors, "
                ".onnx, .ts, or .torchscript."
            )
        return model_format

    @staticmethod
    def extract_pytorch_metadata(
        model_path: str,
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Attempt to extract layer count and parameter count
        from a PyTorch checkpoint/state_dict.

        Returns:
            (layer_count, parameter_count)

        If the model cannot be parsed, returns:
            (None, None)
        """

        try:
            # weights_only avoids executing arbitrary pickled model objects.
            # Older torch releases may not expose the argument; in that case
            # metadata extraction is skipped rather than deserializing untrusted
            # code.
            try:
                state = torch.load(model_path, map_location="cpu", weights_only=True)
            except TypeError:
                return None, None

            # Common checkpoint structures
            if isinstance(state, dict):

                if "state_dict" in state:
                    state = state["state_dict"]

                elif "model" in state:
                    state = state["model"]

                    # Some checkpoints contain an actual nn.Module
                    if hasattr(state, "state_dict"):
                        state = state.state_dict()

            # Direct PyTorch model
            elif hasattr(state, "state_dict"):
                state = state.state_dict()

            if not isinstance(state, dict):
                return None, None

            tensor_items = [
                value
                for value in state.values()
                if isinstance(value, torch.Tensor)
            ]

            if not tensor_items:
                return None, None

            layer_count = len(tensor_items)

            parameter_count = sum(
                tensor.numel()
                for tensor in tensor_items
            )

            return layer_count, parameter_count

        except Exception:
            return None, None

    def inspect_model(
        self,
        model_path: str,
        reference_sha256: Optional[str] = None,
    ) -> ModelHashResult:

        # --------------------------------------------------
        # 1. Check file
        # --------------------------------------------------

        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Model file not found: {model_path}"
            )

        # --------------------------------------------------
        # 2. Basic file information
        # --------------------------------------------------

        file_name = os.path.basename(model_path)
        file_size = os.path.getsize(model_path)

        # --------------------------------------------------
        # 3. Detect model format
        # --------------------------------------------------

        model_format = self.validate_supported_path(model_path)

        # --------------------------------------------------
        # 4. Calculate SHA-256
        # --------------------------------------------------

        sha256_digest = self.compute_file_sha256(model_path)

        # --------------------------------------------------
        # 5. Extract PyTorch metadata
        # --------------------------------------------------

        layer_count = None
        parameter_count = None

        if model_format == "pytorch_pt":
            (
                layer_count,
                parameter_count,
            ) = self.extract_pytorch_metadata(model_path)

        # --------------------------------------------------
        # 6. Verify against trusted reference hash
        # --------------------------------------------------

        reference_match = None

        if reference_sha256 is not None:

            reference_sha256 = reference_sha256.strip().lower()

            reference_match = (
                sha256_digest.lower()
                == reference_sha256
            )

            if reference_match:
                integrity_verified = True

                verification_status = (
                    "PASS: Model SHA-256 matches the trusted reference digest."
                )

            else:
                integrity_verified = False

                verification_status = (
                    "FAIL: Model SHA-256 does not match the trusted reference digest."
                )

        else:
            # We can calculate the digest, but without a trusted
            # reference we cannot claim that integrity was verified.

            integrity_verified = False

            verification_status = (
                "UNVERIFIED: SHA-256 calculated, but no trusted "
                "reference digest was provided."
            )

        # --------------------------------------------------
        # 7. Return result
        # --------------------------------------------------

        return ModelHashResult(
            model_path=model_path,
            file_name=file_name,
            file_size_bytes=file_size,
            sha256_digest=sha256_digest,
            format=model_format,
            layer_count=layer_count,
            parameter_count=parameter_count,
            integrity_verified=integrity_verified,
            reference_match=reference_match,
            verification_status=verification_status,
        )
