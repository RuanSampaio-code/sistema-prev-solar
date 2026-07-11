import os
import cv2
import numpy as np
import torch
from tqdm import tqdm

# ============================================================
# CONFIGURAÇÕES
# ============================================================

MODEL_PATH = "modelo_eq/best_iou51.pth"
IMAGE_DIR = "data/image_earth"
OUTPUT_DIR = "resultados/unet_0.3"

IMG_SIZE = 512
TILE_OVERLAP = 300
CONF_THRESH = 0.30

MASK_COLOR = (100, 255, 0)
MASK_ALPHA = 0.45

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Executando inferência utilizando: {device}")

# ============================================================
# NORMALIZAÇÃO USADA NO TREINAMENTO
# ============================================================

IMAGENET_MEAN = np.array(
    [0.485, 0.456, 0.406],
    dtype=np.float32
)

IMAGENET_STD = np.array(
    [0.229, 0.224, 0.225],
    dtype=np.float32
)

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
        modelo.load_state_dict(
            checkpoint["model_state_dict"]
        )
    else:
        modelo.load_state_dict(checkpoint)

    modelo.to(device)
    modelo.eval()

    return modelo

# ============================================================
# PRÉ-PROCESSAMENTO
# ============================================================

def preprocess_tile(tile):

    tile_rgb = cv2.cvtColor(
        tile,
        cv2.COLOR_BGR2RGB
    )

    tile_rgb = tile_rgb.astype(np.float32) / 255.0

    tile_rgb = (
        tile_rgb - IMAGENET_MEAN
    ) / IMAGENET_STD

    tile_rgb = tile_rgb.transpose(2, 0, 1)

    tensor = torch.from_numpy(
        np.ascontiguousarray(tile_rgb)
    )

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

    matriz_probabilidade = np.zeros(
        (H, W),
        dtype=np.float32
    )

    matriz_pesos = np.zeros(
        (H, W),
        dtype=np.float32
    )

    y_indices = list(
        range(
            0,
            max(H - IMG_SIZE + 1, 1),
            stride
        )
    )

    x_indices = list(
        range(
            0,
            max(W - IMG_SIZE + 1, 1),
            stride
        )
    )

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

            y_start = min(
                max(y, 0),
                max(H - IMG_SIZE, 0)
            )

            for x in x_indices:

                x_start = min(
                    max(x, 0),
                    max(W - IMG_SIZE, 0)
                )

                # Tile 512x512

                bloco = img[
                    y_start:y_start + IMG_SIZE,
                    x_start:x_start + IMG_SIZE
                ]

                if bloco.shape[0] != IMG_SIZE or bloco.shape[1] != IMG_SIZE:

                    padded = np.zeros(
                        (IMG_SIZE, IMG_SIZE, 3),
                        dtype=np.uint8
                    )

                    padded[
                        :bloco.shape[0],
                        :bloco.shape[1]
                    ] = bloco

                    bloco = padded

                tensor_input = preprocess_tile(bloco)

                output = model(tensor_input)

                probabilidade = torch.sigmoid(
                    output
                ).squeeze().cpu().numpy()

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

    mascara_final_prob = (
        matriz_probabilidade /
        matriz_pesos
    )

    mascara_binaria = (
        mascara_final_prob >= CONF_THRESH
    ).astype(np.uint8) * 255

    img_saida = img.copy()

    camada_cor = np.zeros_like(img)

    camada_cor[
        mascara_binaria == 255
    ] = MASK_COLOR

    cv2.addWeighted(
        camada_cor,
        MASK_ALPHA,
        img_saida,
        1.0,
        0,
        img_saida
    )

    contornos, _ = cv2.findContours(
        mascara_binaria,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    cv2.drawContours(
        img_saida,
        contornos,
        -1,
        MASK_COLOR,
        2
    )

    return img_saida, mascara_binaria

# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("Inicializando modelo...")

    try:
        unet_model = carregar_modelo(
            MODEL_PATH
        )

    except Exception as e:
        print(
            f"Erro ao carregar modelo: {e}"
        )
        raise

    extensoes_validas = (
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff"
    )

    lista_imagens = [

        f for f in os.listdir(IMAGE_DIR)

        if f.lower().endswith(
            extensoes_validas
        )
    ]

    if len(lista_imagens) == 0:

        print(
            f"Nenhuma imagem encontrada em {IMAGE_DIR}"
        )

        exit()

    print(
        f"Encontradas {len(lista_imagens)} imagens."
    )

    for nome_img in tqdm(
        lista_imagens,
        desc="Processando"
    ):

        entrada = os.path.join(
            IMAGE_DIR,
            nome_img
        )

        resultado = processar_imagem_gigante(
            entrada,
            unet_model
        )

        if resultado is None:
            continue

        overlay, mascara = resultado

        nome_base = os.path.splitext(
            nome_img
        )[0]

        caminho_overlay = os.path.join(
            OUTPUT_DIR,
            f"overlay_{nome_base}.png"
        )

        caminho_mask = os.path.join(
            OUTPUT_DIR,
            f"mask_{nome_base}.png"
        )

        cv2.imwrite(
            caminho_overlay,
            overlay
        )

        cv2.imwrite(
            caminho_mask,
            mascara
        )

    print("\nInferência concluída com sucesso.")
    print(f"Resultados salvos em: {OUTPUT_DIR}")