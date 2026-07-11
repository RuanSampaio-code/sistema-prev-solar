# Avaliação de Métricas — YOLO11m (Detecção de Painéis Solares)

Script de avaliação (`teste_metricas_yolo.py`) que roda a validação nativa do Ultralytics sobre o **conjunto de teste** (split separado de treino/validação), reportando métricas de detecção e, quando aplicável, de segmentação.

---

## ⚙️ Configuração

```python
model = YOLO("modelos/modelos_novodataset/NewModelYolo11m.pt")

results = model.val(
    data="newdata/solar/data.yaml",
    split="test",
    imgsz=1024,
    workers=0,
)
```

| Parâmetro | Valor | Observação |
|---|---|---|
| `MODEL_PATH` | `modelos/modelos_novodataset/NewModelYolo11m.pt` | checkpoint treinado a ser avaliado |
| `data` | `newdata/solar/data.yaml` | precisa conter a chave `test:` apontando para o split de teste |
| `split` | `test` | força o Ultralytics a avaliar no conjunto de teste, e não no de validação usado durante o treino |
| `imgsz` | 1024 | resolução de inferência — consistente com o upscaling adotado nos scripts de inferência em produção (ver README de inferência) |
| `workers` | 0 | evita problemas de multiprocessing no Windows |

> ⚠️ O `data.yaml` usado aqui (`newdata/solar/data.yaml`) precisa ter uma chave `test:` definida — diferente do `data.yaml` de treino, que só define `train:`/`val:`. Sem esse split, `split="test"` falha ou cai de volta no `val`.

---

## 📊 Métricas reportadas

O objeto `results` retornado por `model.val()` já traz as métricas agregadas calculadas pelo Ultralytics (baseadas em mAP, não em uma matriz de confusão manual).

### Detecção (bounding boxes)

```python
results.box.mp      # Precision média
results.box.mr      # Recall médio
results.box.map50   # mAP @ IoU 0.5
results.box.map     # mAP @ IoU 0.5:0.95 (COCO-style)
```

### Segmentação (quando o modelo é `-seg`)

```python
results.seg.mp
results.seg.mr
results.seg.map50
results.seg.map
```

O script calcula também o **F1-Score da segmentação** manualmente, a partir de precision/recall médios:

```python
f1 = 2 * (p * r) / (p + r)
```

> Nota técnica: `results.box.mp`/`mr` são médias calculadas internamente pelo Ultralytics ao longo das curvas precision-recall (não uma precision/recall "pontual" em um único threshold de confiança) — portanto não são diretamente comparáveis ao F1 calculado por matriz de confusão simples, como é feito no script do UNet.

---

## ▶️ Execução

```bash
python teste_metricas_yolo.py
```

Saída esperada no console:

```
===== MÉTRICAS DE DETECÇÃO =====
Precision: 0.xxxx
Recall:    0.xxxx
mAP50:     0.xxxx
mAP50-95:  0.xxxx

===== MÉTRICAS DE SEGMENTAÇÃO =====
Precision: 0.xxxx
Recall:    0.xxxx
mAP50:     0.xxxx
mAP50-95:  0.xxxx
F1-Score:  0.xxxx
```

---

## 📝 Notas

- Como o modelo é `-seg` (YOLO11m-seg), a seção de segmentação normalmente é preenchida — o `if hasattr(results, "seg")` é uma salvaguarda para o caso de o checkpoint ser um modelo de detecção pura.
- Manter `imgsz=1024` na avaliação, igual ao usado na inferência de produção, é importante para que o número reportado reflita o desempenho real esperado em campo.
