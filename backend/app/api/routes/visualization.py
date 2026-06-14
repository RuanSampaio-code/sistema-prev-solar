import io
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.image import Image, ImageStatus
from app.models.result import Result
from app.models.user import User

router = APIRouter()


def _build_visualization(image_path: str, mask_path: str, panel_count: int,
                          area_m2: float, kwh: float) -> bytes:
    original = cv2.imread(image_path)
    if original is None:
        raise ValueError("Não foi possível ler a imagem original")

    mask_raw = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask_raw is None:
        raise ValueError("Máscara não encontrada")

    h, w = original.shape[:2]
    mask = cv2.resize(mask_raw, (w, h), interpolation=cv2.INTER_NEAREST)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # overlay amarelo semi-transparente nas áreas detectadas
    overlay = original.copy()
    overlay[mask_bin > 0] = (overlay[mask_bin > 0] * 0.4 + np.array([0, 200, 255]) * 0.6).astype(np.uint8)
    result_img = cv2.addWeighted(original, 0.3, overlay, 0.7, 0)

    # contornos e labels por painel — ordenados por área decrescente para coincidir
    # com o panel_id do pipeline (maior painel = label "1")
    contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid = sorted(
        [c for c in contours if cv2.contourArea(c) >= 200],
        key=cv2.contourArea,
        reverse=True,
    )

    cv2.drawContours(result_img, valid, -1, (0, 255, 100), 2)

    for i, cnt in enumerate(valid, 1):
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.circle(result_img, (cx, cy), 14, (0, 255, 100), -1)
            cv2.putText(result_img, str(i), (cx - 5, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    # painel de info no canto superior esquerdo
    panel_h, panel_w = 110, 280
    info_bg = result_img[10:10 + panel_h, 10:10 + panel_w].copy()
    cv2.rectangle(result_img, (10, 10), (10 + panel_w, 10 + panel_h), (15, 23, 42), -1)
    cv2.rectangle(result_img, (10, 10), (10 + panel_w, 10 + panel_h), (245, 158, 11), 2)

    lines = [
        f"Paineis detectados: {panel_count}",
        f"Area estimada: {area_m2:.2f} m2",
        f"Energia: {kwh:.1f} kWh/mes",
    ]
    for i, line in enumerate(lines):
        cv2.putText(result_img, line, (20, 38 + i * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 158, 11), 1, cv2.LINE_AA)

    # Limita a resolução de saída para não sobrecarregar a resposta HTTP.
    # Imagens de drone em resolução nativa podem ter 3840×2160+.
    max_dim = 4000
    h_r, w_r = result_img.shape[:2]
    if max(h_r, w_r) > max_dim:
        scale = max_dim / max(h_r, w_r)
        result_img = cv2.resize(result_img, (int(w_r * scale), int(h_r * scale)))

    _, buf = cv2.imencode(".jpg", result_img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return buf.tobytes()


@router.get("/{image_id}/visualization")
def get_visualization(
    image_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    if image.status != ImageStatus.done:
        raise HTTPException(status_code=400, detail="Imagem ainda não processada")

    result = db.query(Result).filter(Result.image_id == image_id).first()
    if not result or not result.mask_filepath:
        raise HTTPException(status_code=404, detail="Resultado não disponível")

    viz_bytes = _build_visualization(
        image.filepath,
        result.mask_filepath,
        result.panel_count,
        result.detected_area_m2,
        result.estimated_kwh_month,
    )

    return StreamingResponse(io.BytesIO(viz_bytes), media_type="image/jpeg")
