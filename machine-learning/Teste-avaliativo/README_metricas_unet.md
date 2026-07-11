# Avaliação de Métricas — UNet + ResNet34 (Detecção de Painéis Solares)

Script de avaliação (`teste_metricasunet.py`) que roda inferência sobre o **conjunto de teste** e acumula uma **matriz de confusão pixel a pixel** (TP/TN/FP/FN) sobre todas as imagens, calculando métricas globais de segmentação.

---

## ⚙️ Configuração

```python
MODEL_PATH  = "modelo_eq/best_iou51.pth"

TEST_IMAGES = "newdata/unetsolar/test/images"
TEST_MASKS  = "newdata/unetsolar/test/masks"

MODEL_SIZE  = 512
THRESHOLD   = 0.30
```

| Parâmetro | Valor | Observação |
|---|---|---|
| `MODEL_PATH` | `modelo_eq/best_iou51.pth` | checkpoint treinado a ser avaliado |
| `TEST_IMAGES` / `TEST_MASKS` | pastas de imagens e máscaras ground-truth do split de teste | máscaras devem ter o **mesmo nome-base** da imagem, em `.png` |
| `MODEL_SIZE` | 512 | resolução de entrada do modelo — deve bater com o `img_size` usado no treino |
| `THRESHOLD` | 0.30 | limiar de binarização da probabilidade — mesmo valor usado no `CONF_THRESH` do script de inferência |

---

## 🔍 Como funciona

### 1. Carregamento do modelo (`carregar_modelo`)

Reconstrói a arquitetura UNet+ResNet34 (sem pesos pré-treinados do encoder, já que serão sobrescritos pelo checkpoint) e carrega o `state_dict`, suportando tanto checkpoint "cru" quanto dicionário com `model_state_dict` (imprimindo o `epoch` de origem quando disponível).

### 2. Predição por imagem (`prever_mascara`)

Diferente do script de inferência em produção (que usa **sliding window**), aqui cada imagem de teste é processada **inteira, com resize direto** para `512×512`:

```python
img = cv2.resize(img, (MODEL_SIZE, MODEL_SIZE))
```

- Normalização ImageNet (mesma do treino).
- Máscara predita é binarizada em `THRESHOLD` (0.30) e depois **reescalada de volta** para a resolução original da imagem (`cv2.INTER_NEAREST`, preservando bordas nítidas da máscara binária).

> ⚠️ **Diferença importante em relação à inferência de produção**: este script de teste **não usa sliding window/tiling** — ele faz resize direto da imagem inteira para 512×512. Isso é adequado quando as imagens de teste já são recortes pequenos (do tamanho de um tile), mas produziria resultados diferentes se aplicado a uma imagem grande de satélite sem tiling prévio. Ao comparar essas métricas com o comportamento em produção (`inferencia_unet.py`, que usa sliding window 512px com overlap), tenha em mente essa diferença metodológica.

### 3. Matriz de confusão acumulada (`atualizar_confusao`)

Para cada par (predição, ground-truth), soma pixel a pixel em um dicionário global:

```python
TP += pred & gt
TN += ~pred & ~gt
FP += pred & ~gt
FN += ~pred & gt
```

As máscaras de ground-truth são binarizadas com `gt > 127`. Se a predição e o GT tiverem tamanhos diferentes (por exemplo, arredondamentos no resize), o GT é redimensionado para bater com a predição.

---

## 📊 Métricas calculadas (globais, ao final de todas as imagens)

```python
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
accuracy  = (TP + TN) / (TP + TN + FP + FN)
iou       = TP / (TP + FP + FN)
dice      = 2*TP / (2*TP + FP + FN)
f1        = 2 * precision * recall / (precision + recall)
```

> Por serem acumuladas em nível de **dataset inteiro** (soma de TP/TN/FP/FN de todas as imagens antes de calcular as razões), essas métricas são "micro-averaged" — imagens com mais pixels de painel pesam proporcionalmente mais no resultado final do que imagens com poucos pixels de painel.

---

## ▶️ Execução

```bash
python teste_metricasunet.py
```

Saída esperada no console:

```
============================================================
RESULTADOS GLOBAIS
============================================================
TP        : ...
TN        : ...
FP        : ...
FN        : ...
------------------------------------------------------------
IoU       : 0.xxxx
Dice      : 0.xxxx
Precision : 0.xxxx
Recall    : 0.xxxx
F1 Score  : 0.xxxx
Accuracy  : 0.xxxx
============================================================
```

---

## 📝 Notas

- `THRESHOLD = 0.30` já reflete o ajuste feito a partir da análise de sweep de threshold (0–1) do projeto — valor escolhido para aproximar o recall da meta de 0,80, em vez do padrão 0,5.
- Como o `Accuracy` inclui os pixels de fundo (`TN`), que são a esmagadora maioria da imagem em um problema de segmentação de objetos pequenos, ele tende a ser um valor alto mesmo com IoU/Recall medianos — **IoU e Dice são as métricas mais informativas** para este problema.
- Para comparação direta e justa com o YOLO, seria necessário aplicar o mesmo pipeline de tiling na avaliação do UNet (ou avaliar o YOLO sobre os mesmos recortes sem tiling) — atualmente os dois scripts de métricas usam estratégias de pré-processamento de imagem diferentes entre si.
