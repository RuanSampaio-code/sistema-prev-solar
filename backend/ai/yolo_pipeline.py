"""Pipeline de inferência YOLO para detecção de painéis solares.

Completamente isolado do pipeline UNet — não altera nenhuma lógica existente.
A saída é convertida para PipelineResult/PanelResult garantindo compatibilidade
total com o restante da aplicação (tasks, routes, schemas, frontend).
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import cv2
import numpy as np

from ai.pipeline import (
    PanelResult,
    PipelineResult,
    _estimate_kwh,
    _get_gsd,
    _load_image,
    _save_mask,
)

# ── Parâmetros de inferência YOLO (espelho do notebook de referência) ─────────
_TILE_SIZE    = 640    # tamanho do tile — deve ser igual ao do treino
_TILE_OVERLAP = 300    # sobreposição entre tiles
_IMG_SIZE     = 1024   # imgsz interno do YOLO (predict)
_IOU_THRESH   = 0.60   # limiar de IoU para o NMS remover duplicatas
_AREA_MIN_PX  = 50     # área mínima em px² para filtrar ruídos
_DEFAULT_CONF = 0.30   # confiança mínima padrão

_YOLO_MODEL_PATH = Path(__file__).parent / "model" / "NewModelYolo11m.pt"

_yolo_cache: dict = {}


def _load_yolo(model_path: Path):
    """Carrega e cacheia o modelo YOLO (lazy — só na primeira chamada)."""
    key = str(model_path)
    if key not in _yolo_cache:
        from ultralytics import YOLO
        _yolo_cache[key] = YOLO(str(model_path))
    return _yolo_cache[key]


def _garantir_bgr(img: np.ndarray) -> np.ndarray:
    """Normaliza qualquer imagem para 3 canais BGR antes de enviar ao YOLO."""
    if img is None:
        raise ValueError("Imagem inválida (None)")
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    if img.shape[2] > 4:
        return img[:, :, :3]
    return img


def _gerar_tiles(img: np.ndarray, tile_size: int, overlap: int):
    """Divide a imagem em tiles sobrepostos. Retorna lista de (tile, ox, oy)."""
    h, w = img.shape[:2]
    step = tile_size - overlap
    tiles = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            x1 = max(0, x2 - tile_size)
            y1 = max(0, y2 - tile_size)
            tiles.append((img[y1:y2, x1:x2], x1, y1))
    return tiles


def _nms_boxes(boxes: list, scores: list, iou_threshold: float) -> list:
    """NMS manual — remove bounding boxes duplicados de tiles sobrepostos."""
    if not boxes:
        return []
    arr = np.array(boxes, dtype=np.float32)
    sc  = np.array(scores, dtype=np.float32)
    x1, y1, x2, y2 = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = sc.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou < iou_threshold]
    return keep


def _run_yolo_tiling(
    yolo_model,
    img: np.ndarray,
    conf: float,
) -> tuple[np.ndarray, list]:
    """
    Percorre a imagem em tiles, roda YOLO em cada um, reposiciona
    as detecções no espaço original e aplica NMS global.

    Suporta tanto modelos de segmentação (result.masks) quanto modelos
    de detecção pura (result.boxes), seguindo exatamente a lógica do notebook.

    Retorna:
        mask_bin  — máscara binária uint8 {0,1} na resolução original
        detections — lista de (box_xyxy, conf) após NMS global
    """
    h, w = img.shape[:2]
    mask_total: np.ndarray = np.zeros((h, w), dtype=np.uint8)
    all_boxes: list = []
    all_confs: list = []

    tiles = _gerar_tiles(img, _TILE_SIZE, _TILE_OVERLAP)

    for tile, ox, oy in tiles:
        th, tw = tile.shape[:2]
        if th < 32 or tw < 32:
            continue

        tile_bgr = _garantir_bgr(tile)

        result = yolo_model.predict(
            source=tile_bgr,
            conf=conf,
            iou=_IOU_THRESH,
            imgsz=_IMG_SIZE,
            verbose=False,
        )[0]

        if result.masks is not None:
            # Modelo de segmentação — tem máscara por instância
            masks   = result.masks.data.cpu().numpy()
            confs_t = result.boxes.conf.cpu().numpy()
            boxes_t = result.boxes.xyxy.cpu().numpy()

            for mask, c, box in zip(masks, confs_t, boxes_t):
                mask_r = cv2.resize(mask, (tw, th), interpolation=cv2.INTER_NEAREST)
                mask_b = (mask_r > 0.5).astype(np.uint8)

                y2_img = min(oy + th, h)
                x2_img = min(ox + tw, w)
                mask_total[oy:y2_img, ox:x2_img] = np.clip(
                    mask_total[oy:y2_img, ox:x2_img]
                    + mask_b[: y2_img - oy, : x2_img - ox],
                    0, 1,
                )
                all_boxes.append([ox + box[0], oy + box[1], ox + box[2], oy + box[3]])
                all_confs.append(float(c))

        elif result.boxes is not None and len(result.boxes):
            # Modelo de detecção pura — preenche o bounding box na máscara
            confs_t = result.boxes.conf.cpu().numpy()
            boxes_t = result.boxes.xyxy.cpu().numpy()

            for c, box in zip(confs_t, boxes_t):
                x1b, y1b = int(ox + box[0]), int(oy + box[1])
                x2b, y2b = int(ox + box[2]), int(oy + box[3])
                mask_total[y1b:y2b, x1b:x2b] = 1
                all_boxes.append([ox + box[0], oy + box[1], ox + box[2], oy + box[3]])
                all_confs.append(float(c))

    keep = _nms_boxes(all_boxes, all_confs, _IOU_THRESH)
    detections = [(all_boxes[i], all_confs[i]) for i in keep]

    return mask_total, detections


def _extract_panels_yolo(
    contours,
    detections: list,
    gsd: float,
) -> List[PanelResult]:
    """
    Converte contornos da máscara YOLO em PanelResult, compatível com UNet.

    confidence_mean = maior score de detecção YOLO cujo bounding box
    contenha o centroide do contorno. Fallback 0.0 se nenhum box cobrir.

    panel_id é atribuído por rank de área decrescente (maior = 1),
    igual ao pipeline UNet, para consistência no frontend.
    """
    panels: List[PanelResult] = []

    for contour in contours:
        area_px = cv2.contourArea(contour)
        if area_px < _AREA_MIN_PX:
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

        # Associa a confiança YOLO ao painel pelo centroide
        conf_mean = 0.0
        for box, c in detections:
            if box[0] <= cx <= box[2] and box[1] <= cy <= box[3]:
                conf_mean = max(conf_mean, c)

        panels.append(PanelResult(
            panel_id=0,
            area_m2=area_m2,
            kwh_month=kwh_month,
            centroid_x=cx,
            centroid_y=cy,
            bbox_x=bx,
            bbox_y=by,
            bbox_width=bw,
            bbox_height=bh,
            confidence_mean=round(conf_mean, 4),
        ))

    panels.sort(key=lambda p: p.area_m2, reverse=True)
    for rank, p in enumerate(panels, 1):
        p.panel_id = rank

    return panels


def process_image_yolo(
    filepath: str,
    conf: float = _DEFAULT_CONF,
    gsd_override: float | None = None,
) -> PipelineResult:
    """
    Ponto de entrada do pipeline YOLO. Retorna PipelineResult com o mesmo
    contrato dos modelos UNet — compatível com tasks, routes e frontend.
    """
    img = _garantir_bgr(_load_image(filepath))
    gsd = gsd_override if gsd_override is not None else _get_gsd(filepath)

    yolo_model = _load_yolo(_YOLO_MODEL_PATH)
    mask_bin, detections = _run_yolo_tiling(yolo_model, img, conf)

    contours, _ = cv2.findContours(
        (mask_bin * 255).astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    panels = _extract_panels_yolo(contours, detections, gsd)

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
    )
