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


def predict_probs(image_tensor: torch.Tensor) -> np.ndarray:
    """Recebe tensor (1, 3, H, W) normalizado; retorna mapa de probabilidades float32 (H, W) em [0, 1].

    Usado pelo pipeline de tiling para acumular predições de tiles sobrepostos antes
    de aplicar o threshold — a média entre tiles sobrepostos suaviza artefatos de borda.
    """
    model = load_model()
    with torch.no_grad():
        output = model(image_tensor.to(_device))
        prob = torch.sigmoid(output).squeeze().cpu().numpy()
    return prob.astype(np.float32)


def predict_mask(image_tensor: torch.Tensor) -> np.ndarray:
    """Atalho que binariza com threshold 0.5. Mantido para compatibilidade."""
    return (predict_probs(image_tensor) > 0.5).astype(np.uint8)
