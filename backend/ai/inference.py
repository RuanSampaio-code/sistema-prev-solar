from pathlib import Path

import numpy as np
import segmentation_models_pytorch as smp
import torch

_model = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL_PATH = Path(__file__).parent / "model" / "Model-unet.pth"


def load_model():
    global _model
    if _model is None:
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
        )
        state = torch.load(MODEL_PATH, map_location=_device, weights_only=False)
        if isinstance(state, dict) and "model_state_dict" in state:
            state = state["model_state_dict"]
        model.load_state_dict(state)
        model.to(_device)
        model.eval()
        _model = model
    return _model


def predict_mask(image_tensor: torch.Tensor) -> np.ndarray:
    """Recebe tensor (1, 3, H, W) normalizado, retorna máscara binária (H, W) em numpy."""
    model = load_model()
    with torch.no_grad():
        output = model(image_tensor.to(_device))
        mask = torch.sigmoid(output).squeeze().cpu().numpy()
    return (mask > 0.5).astype(np.uint8)
