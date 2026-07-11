# Treinamento — UNet + ResNet34 (Detecção de Painéis Solares)

Script de treinamento da rede de **segmentação semântica UNet** (encoder ResNet34, via `segmentation_models_pytorch`), executado em ambiente **Kaggle (GPU P100/T4)**, para detecção de painéis fotovoltaicos em imagens aéreas/satélite — projeto BRISA/Equatorial.

---

## 📦 Ambiente

```bash
pip install segmentation-models-pytorch albumentations pyyaml
```

Bibliotecas principais: `torch`, `segmentation_models_pytorch` (SMP), `albumentations` (augmentation), `opencv-python`, `pyyaml`.

---

## 🗂️ Dataset (`data.yaml`)

```yaml
path: /kaggle/input/datasets/patrinnyrocha/datayaml/data.yaml
train: train/images
val:   valid/images
masks: masks          # subpasta de máscaras dentro de train/ e valid/
nc: 1
names: ['solar_panel']
```

Estrutura esperada em disco:

```
train/
├── images/
└── masks/
valid/
├── images/
└── masks/
```

- Máscaras em escala de cinza, binarizadas no carregamento (`mask > 127`).
- Cada imagem deve ter uma máscara correspondente com o mesmo nome-base (`.png`/`.jpg`/`.jpeg`).

---

## ⚙️ Hiperparâmetros (bloco `CFG`)

Todo o treino é controlado por um único dicionário de configuração, centralizando os ajustes:

```python
CFG = {
    "yaml_path": "...",
    "save_dir": "/kaggle/working",

    "encoder": "resnet34",
    "pretrained": "imagenet",
    "dropout_dec": 0.2,

    "img_size": 512,

    "epochs": 60,
    "batch_size": 8,
    "num_workers": 2,

    "lr_encoder": 1e-4,
    "lr_decoder": 5e-4,
    "weight_decay": 1e-4,

    "warmup_epochs": 5,
    "cosine_min_lr": 1e-6,

    "focal_alpha": 0.75,
    "focal_gamma": 2.0,
    "dice_weight": 0.5,
    "focal_weight": 0.5,

    "sampler_pos_weight": 3.0,

    "patience": 12,
}
```

| Categoria | Parâmetro | Valor | Observação |
|---|---|---|---|
| Modelo | `encoder` | `resnet34` | alternativas testáveis: `resnet50`, `efficientnet-b3` |
| Modelo | `pretrained` | `imagenet` | pesos pré-treinados do encoder |
| Modelo | `dropout_dec` | 0.2 | subir para 0.3–0.4 em caso de overfitting |
| Imagem | `img_size` | 512 | mesmo valor **deve** ser usado no treino, validação e inferência |
| Treino | `epochs` | 60 | com early stopping |
| Treino | `batch_size` | 8 | reduzir para 4 em caso de OOM |
| Otimizador | `lr_encoder` / `lr_decoder` | 1e-4 / 5e-4 | **LR diferenciado**: encoder pré-treinado aprende mais devagar que o decoder (treinado do zero) |
| Scheduler | `warmup_epochs` | 5 | LR sobe linearmente nos primeiros 5 epochs |
| Scheduler | `cosine_min_lr` | 1e-6 | LR mínimo ao final (cosine annealing) |
| Loss | `focal_alpha` | 0.75 | subir para 0.85 se houver muitos falsos positivos em telhados |
| Loss | `focal_gamma` | 2.0 | subir para 2.5 se painéis pequenos não forem detectados |
| Loss | `dice_weight` / `focal_weight` | 0.5 / 0.5 | combinação balanceada Focal + Dice |
| Sampler | `sampler_pos_weight` | 3.0 | aumenta a frequência de amostragem de imagens **com** painel |
| Early stopping | `patience` | 12 | epochs sem melhora no val IoU antes de parar |

---

## 🧱 Arquitetura

```python
model = smp.Unet(
    encoder_name    = "resnet34",
    encoder_weights = "imagenet",
    in_channels     = 3,
    classes         = 1,
    activation      = None,        # logits brutos — sigmoid aplicado na loss/métricas
    decoder_dropout = 0.2,
)
```

UNet clássica com encoder ResNet34 pré-treinado em ImageNet, saída de 1 canal (máscara binária) sem ativação — sigmoid é aplicado externamente (na loss e no cálculo de métricas).

---

## 🎯 Função de perda — FocalDiceLoss

Combinação ponderada de **Focal Loss** (foca em exemplos difíceis/classe minoritária) e **Dice Loss** (otimiza sobreposição de área, importante para segmentação):

```python
loss = focal_weight * FocalLoss(alpha=0.75, gamma=2.0) \
     + dice_weight  * DiceLoss(smooth=1.0)
```

Essa combinação é adequada ao desbalanceamento típico do problema (painéis solares ocupam pequena fração da imagem em relação ao fundo).

---

## 📊 Métricas (calculadas por epoch, threshold 0.5)

- **IoU** (Intersection over Union)
- **Precision**
- **Recall**
- **F1 / Dice**

```python
tp = (preds * masks).sum()
fp = (preds * (1 - masks)).sum()
fn = ((1 - preds) * masks).sum()
iou = tp / (tp + fp + fn)
```

> No pipeline de avaliação pós-treino do projeto, o **recall** medido (~65,9%) ficou abaixo da meta de 0,80, motivando a análise de threshold operacional mais baixo (~0,10–0,15) na etapa de inferência — ver `README.md` de inferência.

---

## 🔀 Data augmentation (treino apenas — `albumentations`)

| Categoria | Transformações |
|---|---|
| Geométricas | `HorizontalFlip`, `VerticalFlip`, `RandomRotate90`, `Affine` (translação ±3%, escala 90–110%, rotação ±20°) |
| Cor / iluminação | `HueSaturationValue`, `ColorJitter` |
| Contraste | `CLAHE` (clip 2.5) — ajuda a separar painéis de telhados metálicos |
| Sombra | `RandomShadow` — simula sombra de árvore/prédio sobre os painéis |
| Ruído / blur | `GaussianBlur`, `GaussNoise` |
| Oclusão | `CoarseDropout` — simula antenas, caixas d'água, folhas cobrindo parte do painel |
| Normalização | `Normalize` (média/desvio ImageNet) + `ToTensorV2` |

A validação usa apenas `Resize` + `Normalize` (sem augmentation), no mesmo `img_size` do treino.

---

## ⚖️ Balanceamento — `WeightedRandomSampler`

```python
weights = [pos_weight if pos_fraction(img) > 0.01 else 1.0 for img in dataset]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
```

Imagens com mais de 1% de pixels positivos (contendo painel) recebem peso `sampler_pos_weight = 3.0` na amostragem — compensando o desbalanceamento entre imagens com e sem painel no dataset.

---

## 📈 Scheduler — Warmup linear + Cosine Annealing

```python
if step < warmup:
    lr = lr_base * (step / warmup)
else:
    lr = cosine_annealing(step, total_steps, min_lr)
```

LR sobe linearmente nos primeiros `warmup_epochs` (5), depois decai seguindo cosseno até `cosine_min_lr` (1e-6).

---

## 🔁 Loop de treino

- **Mixed precision** (`torch.amp.autocast` + `GradScaler`) para acelerar e economizar memória.
- **Gradient clipping** (`max_norm=1.0`) para estabilidade.
- **Early stopping** por `patience` (12 epochs sem melhora no val IoU).
- A cada epoch: treino → validação → salva `last.pth` sempre, e `best_iou.pth` quando o val IoU melhora.

---

## 💾 Saídas (`/kaggle/working/`)

| Arquivo | Conteúdo |
|---|---|
| `checkpoints/best_iou.pth` | melhor modelo (maior val IoU) — inclui `model_state_dict`, `optimizer_state`, `epoch`, `best_iou`, `cfg` |
| `checkpoints/last.pth` | último epoch treinado |
| `checkpoints/history.csv` | métricas por epoch (`tr_loss`, `tr_iou`, `va_loss`, `va_iou`, `va_precision`, `va_recall`, `va_f1`, `lr_decoder`) |
| `checkpoints/config.yaml` | cópia do `CFG` usado, para reprodutibilidade |

> `best_iou.pth` é o checkpoint carregado pelo script de inferência (`MODEL_PATH` em `inferencia_unet.py`).

---

## 📝 Notas para reprodução

- `img_size` deve ser **idêntico** entre treino, validação e inferência (script de inferência usa `IMG_SIZE = 512`, consistente com este treino).
- Se o recall continuar abaixo da meta após novos treinos, os pontos de ajuste recomendados no próprio código são: `focal_gamma` (dar mais peso a painéis pequenos/difíceis) e `sampler_pos_weight` (aumentar ainda mais a frequência de imagens positivas).
- Todo o treino é reprodutível a partir do `config.yaml` salvo — basta recarregar o `CFG` correspondente.
