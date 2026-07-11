# Detecção de Painéis Solares — Inferência YOLO & UNet

Scripts de inferência para detecção/segmentação de painéis fotovoltaicos não declarados em imagens aéreas/satélite, desenvolvidos no âmbito do projeto **BRISA (UEMA)** em parceria com a **Equatorial Energia**, para a região de São Luís / Paço do Lumiar (MA).

O repositório contém duas abordagens complementares para o mesmo problema:

- **YOLO11m-seg** (`inferencia_yolo.py`) — detecção + segmentação por instância, baseada em tiling com NMS global.
- **UNet + ResNet34** (`inferencia_unet.py`) — segmentação semântica por sliding window com blending de probabilidades.

---

## 📂 Estrutura esperada

```
projeto/
├── modelos/
│   ├── Model-yolo.pt
│   └── Model-unet.pth
│   
├── data/
│   └── teste_equatorial/        # imagens de entrada (.jpg, .png, .tif, ...)
├── inferencia_yolo.py
├── inferencia_unet.py
└── README.md
```

---

## ⚙️ Requisitos

```bash
pip install ultralytics opencv-python numpy matplotlib torch segmentation-models-pytorch tqdm
```

> Recomenda-se GPU com CUDA disponível — ambos os scripts detectam automaticamente `cuda`/`cpu` (o UNet explicitamente; o YOLO via Ultralytics).

---

## 🟠 1. Inferência YOLO (`inferencia_yolo.py`)

Modelo de segmentação por instância (YOLO11m-seg) rodando sobre **tiles de 640×640 com overlap**, seguido de **NMS global** para eliminar detecções duplicadas nas bordas dos tiles.

### Parâmetros principais

| Parâmetro | Descrição | Valor padrão |
|---|---|---|
| `MODEL_PATH` | Caminho do modelo `.pt` treinado | `modelos/Model-yolo.pt` |
| `IMAGE_DIR` | Pasta com as imagens de entrada | `data/teste_equatorial` |
| `OUTPUT_DIR` | Pasta de saída dos resultados | `Resultados/YOLO_Equatorial_0.3` |
| `CONF_THRESH` | Limiar mínimo de confiança | `0.3` |
| `IOU_THRESH` | Limiar de IoU para NMS | `0.6` |
| `IMG_SIZE` | Resolução de inferência por tile (upscaling se > `TILE_SIZE`) | `1024` |
| `TILE_SIZE` | Tamanho do tile extraído da imagem original | `640` |
| `TILE_OVERLAP` | Sobreposição entre tiles adjacentes | `300` |

> ⚠️ Rodar a inferência com `IMG_SIZE` maior que `TILE_SIZE` faz o YOLO fazer *upscale* do tile antes da predição — estratégia que, empiricamente, elevou o mAP@0.5 de ~0.51 para ~0.82 nos experimentos do projeto.

### Como funciona

1. **`garantir_rgb`** — normaliza qualquer imagem de entrada (grayscale, RGBA, multiespectral) para 3 canais BGR.
2. **`gerar_tiles`** — divide a imagem grande em tiles sobrepostos, ancorando as bordas para evitar tiles menores que o esperado.
3. **`inferir_com_tiling`** — roda o modelo em cada tile, reprojeta máscaras/boxes para as coordenadas da imagem original e acumula os resultados.
4. **`nms_boxes`** — aplica Non-Maximum Suppression global sobre todas as detecções (evita duplicatas nas regiões de overlap entre tiles).
5. **`processar_imagem`** — gera a imagem anotada (overlay + contornos + numeração dos painéis) e calcula área ocupada em pixels/percentual.

### Saída

Para cada imagem de entrada, é salva `<nome>_resultado.jpg` com:
- Overlay laranja sobre as máscaras detectadas
- Contornos verdes delimitando cada painel
- Numeração `#1, #2, ...` sobre o centróide de cada detecção
- Estatísticas impressas no console (nº de painéis, % de área coberta)

### Execução

```bash
python InferenciaYOLONovo.py
```

---

## 🟢 2. Inferência UNet (`inferencia_unet.py`)

Segmentação semântica (UNet + encoder ResNet34, via `segmentation_models_pytorch`) rodando sobre **sliding window de 512×512**, com **blending por média de probabilidades** nas regiões de sobreposição — diferente da abordagem de NMS do YOLO, aqui as predições se somam e são normalizadas pelo número de passagens em cada pixel.

### Parâmetros principais

| Parâmetro | Descrição | Valor padrão |
|---|---|---|
| `MODEL_PATH` | Caminho do checkpoint `.pth` treinado | `modelos/Model-Unet.pth` |
| `IMAGE_DIR` | Pasta com as imagens de entrada | `data/teste_equatorial` |
| `OUTPUT_DIR` | Pasta de saída dos resultados | `resultados/New_UNET_equatorial_0.3` |
| `IMG_SIZE` | Tamanho do tile/janela deslizante | `512` |
| `TILE_OVERLAP` | Sobreposição entre janelas | `300` |
| `CONF_THRESH` | Limiar de probabilidade para binarização da máscara | `0.30` |

### Como funciona

1. **`carregar_modelo`** — instancia a arquitetura UNet (encoder ResNet34, sem pesos pré-treinados do encoder) e carrega o checkpoint, suportando tanto `state_dict` puro quanto dicionário com `model_state_dict`.
2. **`preprocess_tile`** — converte BGR→RGB, normaliza para `[0,1]` e aplica a normalização ImageNet (mesma usada no treinamento).
3. **`processar_imagem_gigante`** — sliding window sobre a imagem completa:
   - Acumula a **soma das probabilidades** (`matriz_probabilidade`) e o **número de passagens** (`matriz_pesos`) por pixel.
   - Faz padding nos tiles de borda menores que `IMG_SIZE`.
   - Ao final, calcula a **média das probabilidades** por pixel e binariza pelo `CONF_THRESH`.
4. Gera overlay verde com contornos sobre a imagem original.

### Saída

Para cada imagem, são salvos dois arquivos:
- `overlay_<nome>.png` — imagem original com overlay + contornos da máscara
- `mask_<nome>.png` — máscara binária (0/255) da segmentação

### Execução

```bash
python InferenciaUNETNovo.py
```

---

## 🔍 YOLO vs UNet — principais diferenças de abordagem

| Aspecto | YOLO (detecção/instância) | UNet (segmentação semântica) |
|---|---|---|
| Saída | Boxes + máscaras por instância, com contagem individual de painéis | Máscara única por pixel (classe painel/fundo) |
| Estratégia de combinação entre tiles | NMS global sobre boxes | Média de probabilidades por pixel (soma/pesos) |
| Tile size | 640×640 (upscale opcional p/ 1024 na inferência) | 512×512 |
| Métrica forte | Contagem de painéis (instâncias), boxes precisos | Estimativa de área ocupada (melhor delimitação de contorno) |
| Uso recomendado no projeto | Quando o objetivo é contar/localizar instalações | Quando o objetivo é estimar área precisa de painel instalado |

Essa complementaridade é a base do **pipeline dual-model** do projeto: YOLO para localização e contagem, UNet para estimativa de área mais precisa (conforme discutido na defesa metodológica junto à banca acadêmica).

---

## 📝 Notas

- Ambos os scripts assumem imagens georreferenciadas previamente processadas (GeoTIFF/JPEG extraídos via `rasterio`/`GDAL`), mas trabalham apenas com os pixels da imagem 
- Os thresholds de confiança (`CONF_THRESH`) podem — e devem — ser ajustados conforme o trade-off desejado entre precisão e recall; valores mais baixos (ex.: 0.10–0.15) aumentam o recall às custas de mais falsos positivos.
- `TILE_OVERLAP` alto reduz o risco de painéis cortados na borda dos tiles, mas aumenta o custo computacional.
