import torch
import torch.nn as nn
import os


class DummyCVModel(nn.Module):
    """
    Architecture used to generate demo_assets/sample_model.pt.
    """

    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(
            3,
            16,
            3,
            padding=1
        )

        self.fc1 = nn.Linear(
            16 * 64 * 64,
            4
        )

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = x.view(x.size(0), -1)
        return self.fc1(x)


def load_sample_model(model_path: str) -> DummyCVModel:
    """
    Reconstruct DummyCVModel and load its state_dict.
    """

    model = DummyCVModel()

    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    if isinstance(state_dict, dict) and "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]
    if not isinstance(state_dict, dict):
        raise ValueError("Expected a tensor state_dict for the demo model")

    model.load_state_dict(state_dict)

    model.eval()

    return model


class ModelExecutionUnavailable(RuntimeError):
    """Raised when a model artifact cannot be executed by an offline adapter."""


class OnnxModelAdapter(nn.Module):
    """Small offline ONNX-to-torch adapter for the fingerprinting API."""

    def __init__(self, model_path: str):
        super().__init__()
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise ModelExecutionUnavailable(
                "ONNX behavioral execution unavailable: onnxruntime is not installed."
            ) from exc
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        inputs = self.session.get_inputs()
        if not inputs:
            raise ModelExecutionUnavailable("ONNX model has no executable inputs.")
        self.input_name = inputs[0].name

    def forward(self, x):
        output = self.session.run(None, {self.input_name: x.detach().cpu().numpy()})[0]
        return torch.as_tensor(output)


def load_model_for_inference(model_path: str):
    """Load a supported artifact for actual offline inference.

    The repository can reconstruct its bundled PyTorch state-dict architecture,
    load TorchScript directly, and execute ONNX when onnxruntime is installed.
    Other checkpoint architectures are reported unavailable rather than being
    silently replaced with the demo model.
    """
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    extension = os.path.splitext(model_path)[1].lower()
    if extension in (".ts", ".torchscript"):
        try:
            model = torch.jit.load(model_path, map_location="cpu")
        except Exception as exc:
            raise ModelExecutionUnavailable(
                f"TorchScript behavioral execution unavailable: {exc}"
            ) from exc
        model.eval()
        return model, "torchscript"

    if extension == ".onnx":
        return OnnxModelAdapter(model_path), "onnx"

    if extension in (".pt", ".pth", ".ckpt", ".bin"):
        try:
            return load_sample_model(model_path), "pytorch_white_box"
        except Exception as exc:
            raise ModelExecutionUnavailable(
                "PyTorch behavioral execution unavailable: the checkpoint does "
                "not match the bundled/demo architecture and no caller loader was supplied."
            ) from exc

    raise ModelExecutionUnavailable(
        f"Behavioral execution unavailable for unsupported model extension: {extension}"
    )
