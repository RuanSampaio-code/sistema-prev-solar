import os
import cv2
import csv
import time
import numpy as np
import torch
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform as warp_transform
from pathlib import Path
from tqdm import tqdm
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# ============================================================
# CONFIGURAÇÕES
# ============================================================

MODEL_PATH = "modelos/modelos_novodataset/NewModelUnet.pth"
IMAGE_DIR  = "data/teste"
OUTPUT_DIR = "resultados/teste/New_UNET_equatorial_0.3"

IMG_SIZE     = 512
TILE_OVERLAP = 300
CONF_THRESH  = 0.30

MASK_COLOR = (100, 255, 0)
MASK_ALPHA = 0.45

# 🔥 GEOCODIFICAÇÃO REVERSA (lat/long → endereço)
OBTER_ENDERECO      = True   # liga/desliga a busca de endereço
ENDERECO_POR_PAINEL = False  # True = 1 consulta por painel (lento) | False = 1 por imagem (rápido)
GEOCODER_USER_AGENT = "brisa_uema_paineis_solares"
GEOCODER_DELAY      = 1.1   # segundos entre requisições (Nominatim exige >= 1s)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Executando inferência utilizando: {device}")

# ============================================================
# NORMALIZAÇÃO USADA NO TREINAMENTO
# ============================================================

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# ============================================================
# 🔥 FUNÇÕES DE GEORREFERENCIAMENTO
# ============================================================

def ler_metadados_geo(image_path: str):
    """
    Lê APENAS transform e crs do GeoTIFF via rasterio,
    sem tocar nos pixels (cv2.imread continua sendo usado para inferência).
    Retorna (transform, crs) ou (None, None) se não for .tif ou não tiver geo.
    """
    caminho = Path(image_path)
    if caminho.suffix.lower() not in {".tif", ".tiff"}:
        return None, None

    try:
        with rasterio.open(caminho) as src:
            return src.transform, src.crs
    except Exception as e:
        print(f"  ⚠ Não foi possível ler metadados geo de {caminho.name}: {e}")
        return None, None


def pixel_para_latlong(transform, crs, cx, cy):
    """Converte coordenada de pixel (cx, cy) para lat/long (WGS84)."""
    if transform is None or crs is None:
        return None, None

    x, y = xy(transform, cy, cx)  # xy(transform, linha, coluna)

    if crs.to_epsg() != 4326:
        lon, lat = warp_transform(crs, "EPSG:4326", [x], [y])
        return lat[0], lon[0]
    else:
        return y, x  # já está em lat/long


_geolocator = Nominatim(user_agent=GEOCODER_USER_AGENT)


def latlong_para_endereco(lat, lon, tentativas=3):
    """Converte lat/long em endereço legível usando Nominatim (OpenStreetMap)."""
    if lat is None or lon is None:
        return None

    for _ in range(tentativas):
        try:
            local = _geolocator.reverse((lat, lon), language="pt-BR", timeout=10)
            time.sleep(GEOCODER_DELAY)
            return local.address if local else None
        except (GeocoderTimedOut, GeocoderServiceError):
            time.sleep(2)
            continue
    return None


# ============================================================
# CARREGAMENTO DO MODELO
# ============================================================

def carregar_modelo(path_pesos):
    import segmentation_models_pytorch as smp

    modelo = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=3,
        classes=1,
        activation=None
    )

    checkpoint = torch.load(
        path_pesos,
        map_location=device,
        weights_only=False
    )

    if "model_state_dict" in checkpoint:
        modelo.load_state_dict(checkpoint["model_state_dict"])
    else:
        modelo.load_state_dict(checkpoint)

    modelo.to(device)
    modelo.eval()

    return modelo

# ============================================================
# PRÉ-PROCESSAMENTO
# ============================================================

def preprocess_tile(tile):

    tile_rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
    tile_rgb = tile_rgb.astype(np.float32) / 255.0
    tile_rgb = (tile_rgb - IMAGENET_MEAN) / IMAGENET_STD
    tile_rgb = tile_rgb.transpose(2, 0, 1)

    tensor = torch.from_numpy(np.ascontiguousarray(tile_rgb))
    tensor = tensor.unsqueeze(0).float()

    return tensor.to(device)

# ============================================================
# INFERÊNCIA COM SLIDING WINDOW
# ============================================================

def processar_imagem_gigante(image_path, model):

    img = cv2.imread(image_path)

    if img is None:
        print(f"Erro ao carregar: {image_path}")
        return None

    H, W, _ = img.shape

    stride = IMG_SIZE - TILE_OVERLAP

    matriz_probabilidade = np.zeros((H, W), dtype=np.float32)
    matriz_pesos         = np.zeros((H, W), dtype=np.float32)

    y_indices = list(range(0, max(H - IMG_SIZE + 1, 1), stride))
    x_indices = list(range(0, max(W - IMG_SIZE + 1, 1), stride))

    if not y_indices:
        y_indices = [0]
    if not x_indices:
        x_indices = [0]

    if y_indices[-1] + IMG_SIZE < H:
        y_indices.append(H - IMG_SIZE)
    if x_indices[-1] + IMG_SIZE < W:
        x_indices.append(W - IMG_SIZE)

    with torch.no_grad():

        for y in y_indices:

            y_start = min(max(y, 0), max(H - IMG_SIZE, 0))

            for x in x_indices:

                x_start = min(max(x, 0), max(W - IMG_SIZE, 0))

                bloco = img[
                    y_start:y_start + IMG_SIZE,
                    x_start:x_start + IMG_SIZE
                ]

                if bloco.shape[0] != IMG_SIZE or bloco.shape[1] != IMG_SIZE:
                    padded = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
                    padded[:bloco.shape[0], :bloco.shape[1]] = bloco
                    bloco = padded

                tensor_input  = preprocess_tile(bloco)
                output        = model(tensor_input)
                probabilidade = torch.sigmoid(output).squeeze().cpu().numpy()

                probabilidade = probabilidade[
                    :min(IMG_SIZE, H - y_start),
                    :min(IMG_SIZE, W - x_start)
                ]

                matriz_probabilidade[
                    y_start:y_start + probabilidade.shape[0],
                    x_start:x_start + probabilidade.shape[1]
                ] += probabilidade

                matriz_pesos[
                    y_start:y_start + probabilidade.shape[0],
                    x_start:x_start + probabilidade.shape[1]
                ] += 1.0

    matriz_pesos[matriz_pesos == 0] = 1.0

    mascara_final_prob = matriz_probabilidade / matriz_pesos
    mascara_binaria    = (mascara_final_prob >= CONF_THRESH).astype(np.uint8) * 255

    img_saida  = img.copy()
    camada_cor = np.zeros_like(img)
    camada_cor[mascara_binaria == 255] = MASK_COLOR

    cv2.addWeighted(camada_cor, MASK_ALPHA, img_saida, 1.0, 0, img_saida)

    contornos, _ = cv2.findContours(
        mascara_binaria,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # 🔥 numera cada painel na imagem (igual ao YOLO)
    for i, cnt in enumerate(contornos):
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.putText(img_saida, f"#{i+1}",
                        (cx - 10, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.drawContours(img_saida, contornos, -1, MASK_COLOR, 2)

    return img_saida, mascara_binaria, contornos

# ============================================================
# 🔥 EXTRAÇÃO DE COORDENADAS DOS PAINÉIS
# ============================================================

def extrair_coordenadas(contornos, transform, crs, nome_img):
    """
    Percorre os contornos detectados e calcula lat/long (e endereço)
    do centroide de cada painel.
    """
    paineis_geo = []

    # se ENDERECO_POR_PAINEL=False, busca o endereço uma única vez
    # usando o centroide do primeiro painel como referência da imagem
    endereco_imagem = None

    for i, cnt in enumerate(contornos):
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        area_px = int(cv2.contourArea(cnt))

        lat, lon = pixel_para_latlong(transform, crs, cx, cy)

        # endereço
        endereco = None
        if OBTER_ENDERECO and lat is not None:
            if ENDERECO_POR_PAINEL:
                endereco = latlong_para_endereco(lat, lon)
            else:
                # consulta só uma vez por imagem e reutiliza
                if i == 0:
                    endereco_imagem = latlong_para_endereco(lat, lon)
                endereco = endereco_imagem

        paineis_geo.append({
            "imagem":   nome_img,
            "id":       i + 1,
            "cx_px":    cx,
            "cy_px":    cy,
            "area_px":  area_px,
            "lat":      lat,
            "lon":      lon,
            "endereco": endereco,
        })

    return paineis_geo

# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Inicializando modelo...")

    try:
        unet_model = carregar_modelo(MODEL_PATH)
    except Exception as e:
        print(f"Erro ao carregar modelo: {e}")
        raise

    extensoes_validas = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

    lista_imagens = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(extensoes_validas)
    ]

    if len(lista_imagens) == 0:
        print(f"Nenhuma imagem encontrada em {IMAGE_DIR}")
        exit()

    print(f"Encontradas {len(lista_imagens)} imagens.")

    # 🔥 CSV consolidado com todos os painéis de todas as imagens
    csv_geral_path = os.path.join(OUTPUT_DIR, "TODOS_paineis_geo.csv")
    campos_csv = ["imagem", "id", "cx_px", "cy_px", "area_px", "lat", "lon", "endereco"]

    with open(csv_geral_path, "w", newline="", encoding="utf-8") as f_geral:
        writer_geral = csv.DictWriter(f_geral, fieldnames=campos_csv)
        writer_geral.writeheader()

        for nome_img in tqdm(lista_imagens, desc="Processando"):

            entrada = os.path.join(IMAGE_DIR, nome_img)

            resultado = processar_imagem_gigante(entrada, unet_model)

            if resultado is None:
                continue

            overlay, mascara, contornos = resultado

            nome_base = os.path.splitext(nome_img)[0]

            # salva overlay e máscara (igual ao original)
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"overlay_{nome_base}.png"), overlay)
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"mask_{nome_base}.png"),    mascara)

            # 🔥 extrai coordenadas e endereços
            transform, crs = ler_metadados_geo(entrada)
            paineis_geo    = extrair_coordenadas(contornos, transform, crs, nome_img)

            if paineis_geo:
                # CSV individual por imagem
                csv_img_path = os.path.join(OUTPUT_DIR, f"{nome_base}_paineis_geo.csv")
                with open(csv_img_path, "w", newline="", encoding="utf-8") as f_img:
                    writer_img = csv.DictWriter(f_img, fieldnames=campos_csv)
                    writer_img.writeheader()
                    writer_img.writerows(paineis_geo)

                # adiciona no CSV consolidado
                writer_geral.writerows(paineis_geo)

                print(f"  📍 {len(paineis_geo)} painel(s) — coords salvas em {nome_base}_paineis_geo.csv")

    print("\nInferência concluída com sucesso.")
    print(f"Resultados salvos em: {OUTPUT_DIR}")
    print(f"CSV consolidado: {csv_geral_path}")
