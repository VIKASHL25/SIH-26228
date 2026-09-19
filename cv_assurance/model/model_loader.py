import torch
import torch.nn as nn


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

    state_dict = torch.load(
        model_path,
        map_location="cpu",
        weights_only=True
    )

    model.load_state_dict(state_dict)

    model.eval()

    return model
