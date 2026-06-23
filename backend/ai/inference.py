from pathlib import Path

import numpy as np
import segmentation_models_pytorch as smp
import torch

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_MODEL_DIR = Path(__file__).parent / "model"

# Registro de modelos UNet disponíveis: nome → arquivo .pth
MODEL_REGISTRY: dict[str, Path] = {
    "default": _MODEL_DIR / "Model-unet.pth",
    "new": _MODEL_DIR / "NewModelUnet.pth",
}

# Modelos YOLO — carregados por yolo_pipeline.py, listados aqui para validação de AVAILABLE_MODELS
_YOLO_MODELS: set[str] = {"yolo"}

AVAILABLE_MODELS: list[str] = list(MODEL_REGISTRY) + sorted(_YOLO_MODELS)

_model_cache: dict[str, object] = {}


def load_model(model_name: str = "default"):
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Modelo desconhecido: '{model_name}'. Disponíveis: {AVAILABLE_MODELS}")

    if model_name not in _model_cache:
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
        )
        state = torch.load(MODEL_REGISTRY[model_name], map_location=_device, weights_only=False)
        if isinstance(state, dict) and "model_state_dict" in state:
            state = state["model_state_dict"]
        model.load_state_dict(state)
        model.to(_device)
        model.eval()
        _model_cache[model_name] = model

    return _model_cache[model_name]


def predict_probs(image_tensor: torch.Tensor, model_name: str = "default") -> np.ndarray:
    """Recebe tensor (1, 3, H, W) normalizado; retorna mapa de probabilidades float32 (H, W) em [0, 1].

    Usado pelo pipeline de tiling para acumular predições de tiles sobrepostos antes
    de aplicar o threshold — a média entre tiles sobrepostos suaviza artefatos de borda.
    """
    model = load_model(model_name)
    with torch.no_grad():
        output = model(image_tensor.to(_device))
        prob = torch.sigmoid(output).squeeze().cpu().numpy()
    return prob.astype(np.float32)


def predict_mask(image_tensor: torch.Tensor, model_name: str = "default") -> np.ndarray:
    """Atalho que binariza com threshold 0.5. Mantido para compatibilidade."""
    return (predict_probs(image_tensor, model_name) > 0.5).astype(np.uint8)
