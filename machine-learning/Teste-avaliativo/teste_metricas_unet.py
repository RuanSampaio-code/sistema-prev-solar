import cv2
import torch
import numpy as np
import segmentation_models_pytorch as smp

from pathlib import Path
from tqdm import tqdm

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

MODEL_PATH = "modelo_eq/best_iou51.pth"

TEST_IMAGES = "newdata/unetsolar/test/images"
TEST_MASKS  = "newdata/unetsolar/test/masks"

MODEL_SIZE = 512
THRESHOLD  = 0.30

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"Dispositivo: {DEVICE}")

# ==========================================================
# NORMALIZAÇÃO IMAGENET
# ==========================================================

IMAGENET_MEAN = np.array(
    [0.485, 0.456, 0.406],
    dtype=np.float32
)

IMAGENET_STD = np.array(
    [0.229, 0.224, 0.225],
    dtype=np.float32
)

# ==========================================================
# MODELO
# ==========================================================

def carregar_modelo():

    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=3,
        classes=1,
        activation=None
    )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=False
    )

    if (
        isinstance(checkpoint, dict)
        and "model_state_dict" in checkpoint
    ):
        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        print(
            f"Checkpoint carregado | "
            f"Epoch={checkpoint.get('epoch', '?')}"
        )

    else:
        model.load_state_dict(checkpoint)

    model.to(DEVICE)
    model.eval()

    return model

# ==========================================================
# PREVISÃO
# ==========================================================

def prever_mascara(image_path, model):

    img_original = cv2.imread(image_path)

    if img_original is None:
        raise ValueError(
            f"Erro ao abrir {image_path}"
        )

    altura_original, largura_original = img_original.shape[:2]

    img = cv2.cvtColor(
        img_original,
        cv2.COLOR_BGR2RGB
    )

    img = cv2.resize(
        img,
        (MODEL_SIZE, MODEL_SIZE)
    )

    img = img.astype(np.float32) / 255.0

    img = (
        img - IMAGENET_MEAN
    ) / IMAGENET_STD

    img = img.transpose(2, 0, 1)

    tensor = torch.from_numpy(
        np.ascontiguousarray(img)
    )

    tensor = tensor.unsqueeze(0)

    tensor = tensor.float().to(DEVICE)

    with torch.no_grad():

        logits = model(tensor)

        probs = torch.sigmoid(
            logits
        )

        probs = probs.squeeze().cpu().numpy()

    mascara = (
        probs >= THRESHOLD
    ).astype(np.uint8)

    mascara = cv2.resize(
        mascara,
        (
            largura_original,
            altura_original
        ),
        interpolation=cv2.INTER_NEAREST
    )

    return mascara

# ==========================================================
# MATRIZ DE CONFUSÃO
# ==========================================================

def atualizar_confusao(
    pred,
    gt,
    acumulado
):

    pred = pred.astype(bool)
    gt   = gt.astype(bool)

    acumulado["TP"] += np.logical_and(
        pred,
        gt
    ).sum()

    acumulado["TN"] += np.logical_and(
        ~pred,
        ~gt
    ).sum()

    acumulado["FP"] += np.logical_and(
        pred,
        ~gt
    ).sum()

    acumulado["FN"] += np.logical_and(
        ~pred,
        gt
    ).sum()

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    model = carregar_modelo()

    imagens = []

    for ext in (
        "*.jpg",
        "*.jpeg",
        "*.png",
        "*.tif",
        "*.tiff"
    ):
        imagens.extend(
            Path(TEST_IMAGES).glob(ext)
        )

    imagens = sorted(imagens)

    print(
        f"\nImagens encontradas: "
        f"{len(imagens)}"
    )

    confusao = {
        "TP": 0,
        "TN": 0,
        "FP": 0,
        "FN": 0
    }

    for img_path in tqdm(
        imagens,
        desc="Avaliando"
    ):

        mask_path = (
            Path(TEST_MASKS)
            / f"{img_path.stem}.png"
        )

        if not mask_path.exists():

            print(
                f"Máscara não encontrada: "
                f"{mask_path}"
            )

            continue

        pred = prever_mascara(
            str(img_path),
            model
        )

        gt = cv2.imread(
            str(mask_path),
            cv2.IMREAD_GRAYSCALE
        )

        if gt is None:

            print(
                f"Erro ao abrir "
                f"{mask_path}"
            )

            continue

        gt = (
            gt > 127
        ).astype(np.uint8)

        if pred.shape != gt.shape:

            gt = cv2.resize(
                gt,
                (
                    pred.shape[1],
                    pred.shape[0]
                ),
                interpolation=cv2.INTER_NEAREST
            )

        atualizar_confusao(
            pred,
            gt,
            confusao
        )

    TP = confusao["TP"]
    TN = confusao["TN"]
    FP = confusao["FP"]
    FN = confusao["FN"]

    precision = TP / (TP + FP + 1e-8)

    recall = TP / (TP + FN + 1e-8)

    accuracy = (
        TP + TN
    ) / (
        TP + TN + FP + FN + 1e-8
    )

    iou = TP / (
        TP + FP + FN + 1e-8
    )

    dice = (
        2 * TP
    ) / (
        2 * TP + FP + FN + 1e-8
    )

    f1 = (
        2 * precision * recall
    ) / (
        precision + recall + 1e-8
    )

    print("\n" + "=" * 60)
    print("RESULTADOS GLOBAIS")
    print("=" * 60)

    print(f"TP        : {TP}")
    print(f"TN        : {TN}")
    print(f"FP        : {FP}")
    print(f"FN        : {FN}")

    print("-" * 60)

    print(f"IoU       : {iou:.4f}")
    print(f"Dice      : {dice:.4f}")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1 Score  : {f1:.4f}")
    print(f"Accuracy  : {accuracy:.4f}")

    print("=" * 60)