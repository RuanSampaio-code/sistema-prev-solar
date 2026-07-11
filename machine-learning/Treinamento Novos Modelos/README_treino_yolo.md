# Treinamento — YOLO11m-seg (Detecção de Painéis Solares)

Notebook de treinamento do modelo de segmentação por instância **YOLO11m-seg**, executado em ambiente **Kaggle** (GPU), para detecção de painéis fotovoltaicos em imagens aéreas/satélite — projeto BRISA/Equatorial.

---

## 📦 Ambiente

```bash
pip install ultralytics torch
```

Executado no Kaggle, com verificação automática de GPU:

```python
print("CUDA disponível:", torch.cuda.is_available())
device = 0 if torch.cuda.is_available() else "cpu"
```

---

## 🗂️ Dataset (`data.yaml`)

O notebook gera o arquivo de configuração do dataset em formato Ultralytics/YOLO:

```yaml
path: /kaggle/input/datasets/patrinnyrocha/dataset-equilibrado/solar
train: train/images
val: valid/images

nc: 1
names: ['solar-panel']
```

- **Classe única**: `solar-panel` (`nc: 1`).
- Estrutura padrão Ultralytics (imagens + labels em formato de polígono/segmentação YOLO, um diretório `train` e um `valid`).
- O dataset já está balanceado (`dataset-equilibrado`), refletindo o trabalho prévio de curadoria/rebalanceamento (deduplicação por pHash, filtragem por sharpness) feito no projeto.

---

## 🧠 Modelo

```python
model = YOLO("yolo11m-seg.pt")
```

Modelo base pré-treinado **YOLO11m-seg** (variante *medium*, segmentação de instância), fine-tunado para a classe única `solar-panel`.

---

## ⚙️ Hiperparâmetros de treino

```python
results = model.train(
    data="/kaggle/working/data.yaml",
    epochs=150,
    imgsz=640,
    batch=16,
    device=device,
    workers=2,
    amp=True,
    patience=50,
    pretrained=True,
    cache=False,
    optimizer="auto",
    lr0=0.001,
    ...
)
```

| Parâmetro | Valor | Observação |
|---|---|---|
| `epochs` | 150 | com early stopping via `patience` |
| `imgsz` | 640 | resolução de treino (inferência posterior testada também em 1024, ver README de inferência) |
| `batch` | 16 | |
| `amp` | `True` | mixed precision (acelera e economiza VRAM) |
| `patience` | 50 | early stopping — para se não houver melhora por 50 epochs |
| `pretrained` | `True` | parte dos pesos COCO do YOLO11m-seg |
| `optimizer` | `auto` | Ultralytics escolhe automaticamente (SGD/AdamW conforme heurística interna) |
| `lr0` | 0.001 | learning rate inicial |

### Data augmentation

| Parâmetro | Valor | Efeito |
|---|---|---|
| `hsv_h` | 0.01 | variação leve de matiz |
| `hsv_s` | 0.3 | variação de saturação |
| `hsv_v` | 0.2 | variação de brilho/valor |
| `degrees` | 15 | rotação aleatória até ±15° |
| `translate` | 0.03 | translação aleatória leve |
| `scale` | 0.05 | variação leve de escala |
| `shear` | 0.0 | sem cisalhamento |
| `fliplr` | 0.5 | flip horizontal (50% de chance) |
| `flipud` | 0.0 | sem flip vertical (faz sentido para imagens aéreas nadir, mas aqui desativado) |
| `mosaic` | 0.4 | mosaic augmentation em 40% das imagens |
| `close_mosaic` | 20 | desativa mosaic nos últimos 20 epochs (estabiliza o fim do treino) |
| `mixup` | 0.0 | desativado |
| `copy_paste` | 0.0 | desativado |

> A augmentação é deliberadamente "suave" (nome do experimento: `solar_suave`) — variações leves de cor/geometria, sem mixup/copy-paste, para não distorcer demais a aparência característica dos painéis solares (retangulares, refletivos, com padrão de grade).

---

## 💾 Saídas

```python
save_dir = results.save_dir
!zip -r /kaggle/working/resultado_treinamento.zip {save_dir}
```

- Projeto: `/kaggle/working/treinosolar`
- Nome do experimento: `solar_suave`
- Resultados (pesos `best.pt`/`last.pt`, curvas de treino, matriz de confusão, exemplos de predição) são compactados em `resultado_treinamento.zip` para download do Kaggle.

---

## 📝 Notas para reprodução

- Trocar o caminho em `data_yaml["path"]` conforme o dataset carregado no ambiente Kaggle.
- `workers=2` é conservador — pode ser aumentado conforme os CPUs disponíveis no ambiente.
- O checkpoint `best.pt` gerado aqui é o `MODEL_PATH` usado nos scripts de inferência (ver `README.md` de inferência).
- Caso o dataset seja atualizado (novo rebalanceamento/curadoria), a única mudança necessária é o campo `path` do `data.yaml` — o restante do pipeline de treino permanece igual.
