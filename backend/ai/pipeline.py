import math
from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import numpy as np
import torch
from PIL import Image as PILImage

from ai.inference import AVAILABLE_MODELS, predict_probs
from app.core.config import settings

# ── Parâmetros de inferência por modelo ───────────────────────────────────────
# tile_size e overlap diferem entre modelos; threshold é o padrão quando não
# fornecido pelo usuário. MIN_PANEL_PIXELS é comum a todos os modelos.
_MODEL_INFERENCE_PARAMS: dict[str, dict] = {
    "default": {"tile_size": 640, "overlap": 128, "default_threshold": 0.40},
    "new":     {"tile_size": 512, "overlap": 300, "default_threshold": 0.30},
}

MIN_PANEL_PIXELS = 10  # área mínima de contorno para ser considerado painel

# Mantidos para compatibilidade com imports externos
TILE_SIZE = _MODEL_INFERENCE_PARAMS["default"]["tile_size"]
OVERLAP   = _MODEL_INFERENCE_PARAMS["default"]["overlap"]
THRESHOLD = _MODEL_INFERENCE_PARAMS["default"]["default_threshold"]

# Normalização ImageNet — obrigatória para o encoder ResNet34
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class PanelResult:
    panel_id: int
    area_m2: float
    kwh_month: float
    centroid_x: int
    centroid_y: int
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    confidence_mean: float
    # Campos de geolocalização — preenchidos quando a imagem é GeoTIFF georreferenciado
    lat: float | None = None
    lon: float | None = None
    endereco: str = "Não Georreferenciado"


@dataclass
class PipelineResult:
    panel_count: int
    detected_area_m2: float
    estimated_kwh_month: float
    mask_filepath: str | None
    panels: List[PanelResult]
    gsd_used_m_px: float = 0.0
    image_georeferenced: bool = False


def _estimate_kwh(area_m2: float) -> float:
    kwh = (
        area_m2
        * settings.IRRADIACAO_LOCAL
        * settings.EFICIENCIA_MEDIA
        * (1 - settings.PERDAS_SISTEMA)
        * 30
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


_GSD_FALLBACK = 0.30  # metros/pixel — usado quando metadados estão ausentes ou inválidos


def _get_gsd(filepath: str) -> float:
    """Lê o GSD real (metros/pixel) dos metadados do GeoTIFF.

    Converte graus → metros quando o CRS for EPSG:4326 (geográfico), que é o
    caso típico de imagens de drone exportadas diretamente de software GIS.
    Sem a conversão, gsd fica em ~0.0000013 graus/px e area_px * gsd² ≈ 0.

    Retorna GSD_FALLBACK (0.30 m/px) se rasterio não estiver disponível,
    o arquivo não for TIFF, ou os metadados forem inválidos/ausentes.
    """
    ext = Path(filepath).suffix.lower()
    if ext not in (".tif", ".tiff"):
        return _GSD_FALLBACK
    try:
        import rasterio
        with rasterio.open(filepath) as src:
            t = src.transform
            gsd_x = abs(t[0])
            gsd_y = abs(t[4])
            gsd_raw = (gsd_x + gsd_y) / 2

            if src.crs and "EPSG:4326" in str(src.crs):
                # Metadados em graus decimais → converte para metros usando latitude
                lat_rad = math.radians(src.bounds.bottom)
                m_per_deg = 111320.0 * (1 + math.cos(lat_rad)) / 2
                return float(gsd_raw * m_per_deg)

            # CRS projetado (metros); valida intervalo razoável (0–10 m/px)
            if 0 < gsd_raw <= 10:
                return float(gsd_raw)

            return _GSD_FALLBACK
    except Exception:
        return _GSD_FALLBACK


def _preprocess_tile(tile_bgr: np.ndarray) -> torch.Tensor:
    """BGR uint8 → tensor NCHW float32 normalizado com estatísticas ImageNet."""
    rgb = cv2.cvtColor(tile_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    norm = (rgb - _MEAN) / _STD
    return torch.from_numpy(norm.transpose(2, 0, 1)).float().unsqueeze(0)


def _run_tiled_inference(img: np.ndarray, model_name: str = "default") -> np.ndarray:
    """Inferência tile a tile com overlap; combina predições por média.

    A abordagem de média é superior ao NMS para UNet: regiões sobrepostas
    acumulam mais predições, suavizando artefatos de borda automaticamente.
    Retorna mapa de probabilidades float32 (H, W) na resolução original.
    """
    params = _MODEL_INFERENCE_PARAMS.get(model_name, _MODEL_INFERENCE_PARAMS["default"])
    tile_size = params["tile_size"]
    overlap   = params["overlap"]

    H, W = img.shape[:2]
    prob_acum = np.zeros((H, W), dtype=np.float32)
    count_acum = np.zeros((H, W), dtype=np.float32)

    step = tile_size - overlap
    ys = sorted(set(list(range(0, max(1, H - tile_size + 1), step)) + [max(0, H - tile_size)]))
    xs = sorted(set(list(range(0, max(1, W - tile_size + 1), step)) + [max(0, W - tile_size)]))

    for y in ys:
        for x in xs:
            tile = img[y:y + tile_size, x:x + tile_size]
            th, tw = tile.shape[:2]

            # Padding para tiles de borda menores que tile_size
            if th < tile_size or tw < tile_size:
                padded = np.zeros((tile_size, tile_size, 3), dtype=np.uint8)
                padded[:th, :tw] = tile
                tile_input = padded
            else:
                tile_input = tile

            tensor = _preprocess_tile(tile_input)
            prob = predict_probs(tensor, model_name)  # float32 (tile_size, tile_size)

            # Acumula apenas a região válida (sem padding)
            prob_acum[y:y + th, x:x + tw] += prob[:th, :tw]
            count_acum[y:y + th, x:x + tw] += 1

    count_acum = np.maximum(count_acum, 1)
    return prob_acum / count_acum


def _extract_panels(
    contours,
    prob_map: np.ndarray,
    gsd: float,
    *,
    transform=None,
    crs=None,
    enable_geocoding: bool = False,
    geocoding_per_panel: bool = False,
) -> List[PanelResult]:
    """Converte contornos em PanelResult individuais com área, kWh, centroide, bbox e confiança.

    panel_id é atribuído por rank de área decrescente (maior painel = id 1) para
    coincidir com a ordem exibida na tabela e com os rótulos do overlay de visualização.
    Quando transform/crs válidos, popula lat, lon e endereco em cada painel.
    """
    from ai.geo import pixel_to_latlon, reverse_geocode, NOT_GEOREFERENCED, GEOCODE_NOT_REQUESTED

    panels: List[PanelResult] = []
    georef = transform is not None and crs is not None
    # Endereço reutilizado para todos os painéis quando geocoding_per_panel=False.
    # Computed da primeira detecção válida (igual ao script de referência unet_inferencia_geo.py).
    _shared_address: str | None = None

    for contour in contours:
        area_px = cv2.contourArea(contour)
        if area_px < MIN_PANEL_PIXELS:
            continue

        area_m2 = round(area_px * (gsd ** 2), 4)
        kwh_month = _estimate_kwh(area_m2)

        M = cv2.moments(contour)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx = int(contour[:, 0, 0].mean())
            cy = int(contour[:, 0, 1].mean())

        bx, by, bw, bh = cv2.boundingRect(contour)

        mask_contour = np.zeros(prob_map.shape, dtype=np.uint8)
        cv2.drawContours(mask_contour, [contour], -1, 1, -1)
        pixels_inside = prob_map[mask_contour == 1]
        conf_mean = round(float(pixels_inside.mean()), 4) if len(pixels_inside) > 0 else 0.0

        if georef:
            lat, lon = pixel_to_latlon(transform, crs, cx, cy)
            if enable_geocoding:
                if geocoding_per_panel:
                    endereco = reverse_geocode(lat, lon)
                else:
                    if _shared_address is None:
                        _shared_address = reverse_geocode(lat, lon)
                    endereco = _shared_address
            else:
                endereco = GEOCODE_NOT_REQUESTED
        else:
            lat, lon = None, None
            endereco = NOT_GEOREFERENCED

        panels.append(PanelResult(
            panel_id=0,  # placeholder; atribuído por rank abaixo
            area_m2=area_m2,
            kwh_month=kwh_month,
            centroid_x=cx,
            centroid_y=cy,
            bbox_x=bx,
            bbox_y=by,
            bbox_width=bw,
            bbox_height=bh,
            confidence_mean=conf_mean,
            lat=lat,
            lon=lon,
            endereco=endereco,
        ))

    # Ordena por área decrescente e atribui panel_id = rank (1 = maior)
    panels.sort(key=lambda p: p.area_m2, reverse=True)
    for rank, panel in enumerate(panels, 1):
        panel.panel_id = rank

    return panels


def _save_mask(mask: np.ndarray, original_filepath: str) -> str:
    original_path = Path(original_filepath)
    mask_filename = f"mask_{original_path.stem}.png"
    mask_path = original_path.parent / mask_filename
    cv2.imwrite(str(mask_path), mask * 255)
    return str(mask_path)


def process_image(
    filepath: str,
    threshold: float | None = None,
    model_name: str = "default",
    gsd_override: float | None = None,
    enable_geocoding: bool = False,
    geocoding_per_panel: bool = False,
) -> PipelineResult:
    # YOLO usa um pipeline completamente diferente — delega sem modificar o fluxo UNet
    if model_name == "yolo":
        from ai.yolo_pipeline import process_image_yolo
        conf = threshold if threshold is not None else 0.30
        return process_image_yolo(
            filepath,
            conf=conf,
            gsd_override=gsd_override,
            enable_geocoding=enable_geocoding,
            geocoding_per_panel=geocoding_per_panel,
        )

    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Modelo desconhecido: '{model_name}'. Disponíveis: {AVAILABLE_MODELS}")

    if threshold is None:
        threshold = _MODEL_INFERENCE_PARAMS.get(model_name, _MODEL_INFERENCE_PARAMS["default"])["default_threshold"]

    # Metadados geoespaciais — lidos antes de carregar os pixels (sem custo extra)
    from ai.geo import read_geo_metadata, is_georeferenced, NOT_GEOREFERENCED
    import logging as _logging
    _log = _logging.getLogger(__name__)

    transform, crs = read_geo_metadata(filepath)
    georef = is_georeferenced(transform, crs)
    if not georef:
        _log.warning("⚠ Imagem sem georreferenciamento: %s", filepath)

    # Carrega em resolução nativa — sem redimensionar
    img = _load_image(filepath)
    h, w = img.shape[:2]

    # GSD em metros/pixel — override manual tem prioridade sobre metadado do arquivo
    gsd = gsd_override if gsd_override is not None else _get_gsd(filepath)

    # Tiling com overlap → mapa de probabilidades → threshold
    prob_map = _run_tiled_inference(img, model_name)
    mask_bin = (prob_map > threshold).astype(np.uint8)

    contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    panels = _extract_panels(
        contours,
        prob_map,
        gsd,
        transform=transform,
        crs=crs,
        enable_geocoding=enable_geocoding,
        geocoding_per_panel=geocoding_per_panel,
    )

    area_m2 = round(sum(p.area_m2 for p in panels), 2)
    kwh = _estimate_kwh(area_m2)
    mask_path = _save_mask(mask_bin, filepath)

    return PipelineResult(
        panel_count=len(panels),
        detected_area_m2=area_m2,
        estimated_kwh_month=kwh,
        mask_filepath=mask_path,
        panels=panels,
        gsd_used_m_px=round(gsd, 6),
        image_georeferenced=georef,
    )
