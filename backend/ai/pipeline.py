import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision import transforms

from ai.inference import predict_mask
from app.core.config import settings

_TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

TARGET_SIZE = (512, 512)


@dataclass
class PipelineResult:
    panel_count: int
    detected_area_m2: float
    estimated_kwh_month: float
    mask_filepath: str | None


def _estimate_kwh(area_m2: float) -> float:
    kwh = (
        area_m2
        * settings.WP_PER_M2
        * settings.EFFICIENCY_FACTOR
        * settings.DAILY_PEAK_SUN_HOURS
        * 30
        / 1000
    )
    return round(kwh, 2)


def _count_panels(mask: np.ndarray) -> tuple[int, float]:
    """Retorna (quantidade de painéis, área relativa em m² estimada)."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_panel_pixels = 200
    valid = [c for c in contours if cv2.contourArea(c) >= min_panel_pixels]

    total_pixels = mask.size
    panel_pixels = sum(cv2.contourArea(c) for c in valid)
    area_ratio = panel_pixels / total_pixels if total_pixels > 0 else 0.0

    # Premissa: imagem típica de drone cobre ~200 m²; área detectada é proporcional
    reference_image_area_m2 = 200.0
    area_m2 = round(area_ratio * reference_image_area_m2, 2)

    return len(valid), area_m2


def _save_mask(mask: np.ndarray, original_filepath: str) -> str:
    original_path = Path(original_filepath)
    mask_filename = f"mask_{original_path.stem}.png"
    mask_path = original_path.parent / mask_filename
    cv2.imwrite(str(mask_path), mask * 255)
    return str(mask_path)


def process_image(filepath: str) -> PipelineResult:
    image_bgr = cv2.imread(filepath)
    if image_bgr is None:
        raise ValueError(f"Não foi possível ler a imagem: {filepath}")

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(image_rgb, TARGET_SIZE)

    tensor = _TRANSFORM(resized).unsqueeze(0)
    mask = predict_mask(tensor)

    panel_count, area_m2 = _count_panels(mask)
    kwh = _estimate_kwh(area_m2)
    mask_path = _save_mask(mask, filepath)

    return PipelineResult(
        panel_count=panel_count,
        detected_area_m2=area_m2,
        estimated_kwh_month=kwh,
        mask_filepath=mask_path,
    )
