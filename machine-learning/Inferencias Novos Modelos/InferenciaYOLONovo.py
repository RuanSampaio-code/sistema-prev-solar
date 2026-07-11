import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from ultralytics import YOLO

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
MODEL_PATH   = "modelos/bestYOLO1mFinal.pt" 
IMAGE_DIR    = "data/image_earth"
OUTPUT_DIR   = "resultados_1024px"

CONF_THRESH  = 0.3
IOU_THRESH   = 0.6
IMG_SIZE     = 1024

TILE_SIZE    = 640
TILE_OVERLAP = 300

MASK_COLOR   = (255, 100, 0)
MASK_ALPHA   = 0.45

IMG_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


# ─────────────────────────────────────────────
# 🔥 FUNÇÃO NOVA (CORREÇÃO)
# ─────────────────────────────────────────────
def garantir_rgb(img: np.ndarray) -> np.ndarray:
    """Garante que a imagem tenha 3 canais (BGR)."""
    if img is None:
        return None

    # grayscale → 3 canais
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # RGBA → RGB
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # multispectral → pega só 3 primeiros canais
    if img.shape[2] > 3:
        return img[:, :, :3]

    return img


# ─────────────────────────────────────────────
# TILING
# ─────────────────────────────────────────────
def gerar_tiles(imagem: np.ndarray, tile_size: int, overlap: int):
    h, w = imagem.shape[:2]
    step  = tile_size - overlap
    tiles = []

    for y in range(0, h, step):
        for x in range(0, w, step):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            x1 = max(0, x2 - tile_size)
            y1 = max(0, y2 - tile_size)
            tile = imagem[y1:y2, x1:x2]
            tiles.append((tile, x1, y1))

    return tiles


def nms_boxes(boxes: list, scores: list, iou_threshold: float) -> list:
    if not boxes:
        return []

    boxes_np  = np.array(boxes, dtype=np.float32)
    scores_np = np.array(scores, dtype=np.float32)

    x1, y1 = boxes_np[:, 0], boxes_np[:, 1]
    x2, y2 = boxes_np[:, 2], boxes_np[:, 3]

    areas  = (x2 - x1) * (y2 - y1)
    order  = scores_np.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

        order = order[1:][iou < iou_threshold]

    return keep


# ─────────────────────────────────────────────
# INFERÊNCIA
# ─────────────────────────────────────────────
def inferir_com_tiling(modelo, imagem: np.ndarray):
    h, w = imagem.shape[:2]

    mascara_total = np.zeros((h, w), dtype=np.uint8)
    todos_boxes   = []
    todas_confs   = []

    tiles = gerar_tiles(imagem, TILE_SIZE, TILE_OVERLAP)
    print(f"    → {len(tiles)} tiles ({TILE_SIZE}px, overlap={TILE_OVERLAP}px)")

    for tile, ox, oy in tiles:
        th, tw = tile.shape[:2]

        if th < 32 or tw < 32:
            continue

        # 🔥 GARANTE 3 CANAIS NO TILE
        tile = garantir_rgb(tile)

        resultado = modelo.predict(
            source=tile,
            conf=CONF_THRESH,
            iou=IOU_THRESH,
            imgsz=IMG_SIZE,
            verbose=False,
        )[0]

        if resultado.masks is not None:
            mascaras = resultado.masks.data.cpu().numpy()
            confs    = resultado.boxes.conf.cpu().numpy()
            boxes_xy = resultado.boxes.xyxy.cpu().numpy()

            for mask, conf, box in zip(mascaras, confs, boxes_xy):
                mask_full = cv2.resize(mask, (tw, th), interpolation=cv2.INTER_NEAREST)
                mask_bin  = (mask_full > 0.5).astype(np.uint8)

                y2_img = min(oy + th, h)
                x2_img = min(ox + tw, w)

                mascara_total[oy:y2_img, ox:x2_img] = np.clip(
                    mascara_total[oy:y2_img, ox:x2_img] +
                    mask_bin[:y2_img-oy, :x2_img-ox], 0, 1
                )

                todos_boxes.append([ox+box[0], oy+box[1], ox+box[2], oy+box[3]])
                todas_confs.append(float(conf))

        elif resultado.boxes is not None and len(resultado.boxes):
            confs    = resultado.boxes.conf.cpu().numpy()
            boxes_xy = resultado.boxes.xyxy.cpu().numpy()

            for conf, box in zip(confs, boxes_xy):
                x1b = int(ox + box[0])
                y1b = int(oy + box[1])
                x2b = int(ox + box[2])
                y2b = int(oy + box[3])

                mascara_total[y1b:y2b, x1b:x2b] = 1
                todos_boxes.append([ox+box[0], oy+box[1], ox+box[2], oy+box[3]])
                todas_confs.append(float(conf))

    keep = nms_boxes(todos_boxes, todas_confs, IOU_THRESH)
    deteccoes = [(todos_boxes[i], todas_confs[i]) for i in keep]

    return mascara_total, deteccoes


# ─────────────────────────────────────────────
# PROCESSAMENTO
# ─────────────────────────────────────────────
def processar_imagem(modelo, caminho: Path, saida_dir: Path) -> dict:

    # 🔥 LEITURA CORRIGIDA
    imagem_orig = cv2.imread(str(caminho), cv2.IMREAD_UNCHANGED)
    imagem_orig = garantir_rgb(imagem_orig)

    if imagem_orig is None:
        print(f"  ⚠ Não foi possível ler: {caminho.name}")
        return {}

    h, w = imagem_orig.shape[:2]
    print(f"\n  📷 {caminho.name}  ({w}×{h}px)")

    mascara, deteccoes = inferir_com_tiling(modelo, imagem_orig)

    imagem_anotada = imagem_orig.copy()

    if mascara.sum() > 0:
        overlay = imagem_anotada.copy()
        overlay[mascara > 0] = MASK_COLOR
        imagem_anotada = cv2.addWeighted(overlay, MASK_ALPHA, imagem_anotada, 1 - MASK_ALPHA, 0)

    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(imagem_anotada, contornos, -1, (0, 255, 0), 2)

    for i, cnt in enumerate(contornos):
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.putText(imagem_anotada, f"#{i+1}",
                        (cx - 10, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 2, cv2.LINE_AA)

    n_paineis = len(contornos)
    area_px   = int(mascara.sum())
    area_pct  = (area_px / (h * w)) * 100

    print(f"    ✔ {n_paineis} painel(s), {area_pct:.1f}% da área coberta")

    nome_saida = saida_dir / f"{caminho.stem}_resultado.jpg"
    cv2.imwrite(str(nome_saida), imagem_anotada)

    return {
        "imagem": caminho.name,
        "paineis": n_paineis,
        "area_px": area_px,
        "area_pct": area_pct
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("\n🔆 Segmentação de Painéis Solares — Tiling")

    saida_dir = Path(OUTPUT_DIR)
    saida_dir.mkdir(parents=True, exist_ok=True)

    modelo = YOLO(MODEL_PATH)

    pasta   = Path(IMAGE_DIR)
    imagens = sorted([p for p in pasta.iterdir() if p.suffix.lower() in IMG_EXTS])

    print(f"\n📂 {len(imagens)} imagem(ns) encontrada(s)")

    for img_path in imagens:
        processar_imagem(modelo, img_path, saida_dir)

    print(f"\n✅ Concluído! Resultados em: {saida_dir.resolve()}")


if __name__ == "__main__":
    main()