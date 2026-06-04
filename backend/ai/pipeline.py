from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from PIL import Image as PILImage

from ai.inference import predict_probs
from app.core.config import settings

# ── Parâmetros de inferência (alinhados ao notebook de referência) ────────────
TILE_SIZE = 640        # tamanho do tile — mesmo do notebook
OVERLAP = 128          # sobreposição entre tiles; a média suaviza bordas
THRESHOLD = 0.40       # probabilidade mínima para marcar pixel como painel
MIN_PANEL_PIXELS = 10  # área mínima de contorno para ser considerado painel

# Normalização ImageNet — obrigatória para o encoder ResNet34
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Premissa de área por imagem (fallback quando GSD não está disponível)
_REFERENCE_AREA_M2 = 200.0


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


def _load_image(filepath: str) -> np.ndarray:
    """Carrega a imagem em resolução nativa sem redimensionar.

    Para TIFFs usa PIL (suporta 16-bit e multi-banda); converte para uint8 BGR.
    Isso preserva a resolução original — essencial para que o modelo consiga
    distinguir painéis individuais via tiling.
    """
    ext = Path(filepath).suffix.lower()
    if ext in (".tif", ".tiff"):
        try:
            pil_img = PILImage.open(filepath)
            # Garante 3 canais RGB independente do modo do arquivo (L, RGBA, P…)
            pil_rgb = pil_img.convert("RGB")
            arr = np.array(pil_rgb)
            # PIL retorna uint8 ou uint16; normaliza para uint8
            if arr.dtype != np.uint8:
                arr = (arr / arr.max() * 255).astype(np.uint8) if arr.max() > 0 else arr.astype(np.uint8)
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception:
            pass  # cai no cv2 como fallback

    img = cv2.imread(filepath)
    if img is None:
        raise ValueError(f"Não foi possível ler a imagem: {filepath}")
    return img


def _get_gsd(filepath: str) -> Optional[float]:
    """Tenta ler GSD real (metros/pixel) dos metadados do GeoTIFF via rasterio.

    Retorna None se rasterio não estiver disponível ou o arquivo não tiver CRS.
    """
    ext = Path(filepath).suffix.lower()
    if ext not in (".tif", ".tiff"):
        return None
    try:
        import rasterio
        with rasterio.open(filepath) as src:
            t = src.transform
            return float((abs(t[0]) + abs(t[4])) / 2)
    except Exception:
        return None


def _preprocess_tile(tile_bgr: np.ndarray) -> torch.Tensor:
    """BGR uint8 → tensor NCHW float32 normalizado com estatísticas ImageNet."""
    rgb = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    norm = (rgb - _MEAN) / _STD
    return torch.from_numpy(norm.transpose(2, 0, 1)).float().unsqueeze(0)


def _run_tiled_inference(img: np.ndarray) -> np.ndarray:
    """Inferência tile a tile com overlap; combina predições por média.

    A abordagem de média é superior ao NMS para UNet: regiões sobrepostas
    acumulam mais predições, suavizando artefatos de borda automaticamente.
    Retorna mapa de probabilidades float32 (H, W) na resolução original.
    """
    H, W = img.shape[:2]
    prob_acum = np.zeros((H, W), dtype=np.float32)
    count_acum = np.zeros((H, W), dtype=np.float32)

    step = TILE_SIZE - OVERLAP
    ys = sorted(set(list(range(0, max(1, H - TILE_SIZE + 1), step)) + [max(0, H - TILE_SIZE)]))
    xs = sorted(set(list(range(0, max(1, W - TILE_SIZE + 1), step)) + [max(0, W - TILE_SIZE)]))

    for y in ys:
        for x in xs:
            tile = img[y:y + TILE_SIZE, x:x + TILE_SIZE]
            th, tw = tile.shape[:2]

            # Padding para tiles de borda menores que TILE_SIZE
            if th < TILE_SIZE or tw < TILE_SIZE:
                padded = np.zeros((TILE_SIZE, TILE_SIZE, 3), dtype=np.uint8)
                padded[:th, :tw] = tile
                tile_input = padded
            else:
                tile_input = tile

            tensor = _preprocess_tile(tile_input)
            prob = predict_probs(tensor)  # float32 (TILE_SIZE, TILE_SIZE)

            # Acumula apenas a região válida (sem padding)
            prob_acum[y:y + th, x:x + tw] += prob[:th, :tw]
            count_acum[y:y + th, x:x + tw] += 1

    count_acum = np.maximum(count_acum, 1)
    return prob_acum / count_acum


def _count_panels(mask_bin: np.ndarray, gsd: Optional[float]) -> tuple[int, float]:
    """Extrai contornos, filtra ruídos e estima área real.

    Quando GSD está disponível (lido dos metadados do TIFF) usa
    area_m2 = pixels × gsd². Caso contrário usa a premissa de 200 m²/imagem.
    """
    contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid = [c for c in contours if cv2.contourArea(c) >= MIN_PANEL_PIXELS]

    if gsd is not None:
        area_m2 = sum(cv2.contourArea(c) * (gsd ** 2) for c in valid)
    else:
        total_pixels = mask_bin.size
        panel_pixels = sum(cv2.contourArea(c) for c in valid)
        ratio = panel_pixels / total_pixels if total_pixels > 0 else 0.0
        area_m2 = ratio * _REFERENCE_AREA_M2

    return len(valid), round(area_m2, 2)


def _save_mask(mask: np.ndarray, original_filepath: str) -> str:
    original_path = Path(original_filepath)
    mask_filename = f"mask_{original_path.stem}.png"
    mask_path = original_path.parent / mask_filename
    cv2.imwrite(str(mask_path), mask * 255)
    return str(mask_path)


def process_image(filepath: str) -> PipelineResult:
    # Carrega em resolução nativa — sem redimensionar
    img = _load_image(filepath)

    # GSD dos metadados para cálculo preciso de área (None = usa premissa 200 m²)
    gsd = _get_gsd(filepath)

    # Tiling com overlap → mapa de probabilidades → threshold
    prob_map = _run_tiled_inference(img)
    mask_bin = (prob_map > THRESHOLD).astype(np.uint8)

    panel_count, area_m2 = _count_panels(mask_bin, gsd)
    kwh = _estimate_kwh(area_m2)
    mask_path = _save_mask(mask_bin, filepath)

    return PipelineResult(
        panel_count=panel_count,
        detected_area_m2=area_m2,
        estimated_kwh_month=kwh,
        mask_filepath=mask_path,
    )
