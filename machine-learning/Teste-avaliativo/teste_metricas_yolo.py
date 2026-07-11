from ultralytics import YOLO

def main():
    # Carrega o modelo treinado
    model = YOLO("modelos/modelos_novodataset/NewModelYolo11m.pt")

    # Executa a validação no conjunto de teste
    results = model.val(
        data="newdata/solar/data.yaml",
        split="test",
        imgsz=1024,# (1024)
        workers=0, # evita problemas de multiprocessing no Windows
    )

    print("\n===== MÉTRICAS DE DETECÇÃO =====")
    print(f"Precision: {results.box.mp:.4f}")
    print(f"Recall:    {results.box.mr:.4f}")
    print(f"mAP50:     {results.box.map50:.4f}")
    print(f"mAP50-95:  {results.box.map:.4f}")

    # Caso seja um modelo de segmentação
    if hasattr(results, "seg"):
        print("\n===== MÉTRICAS DE SEGMENTAÇÃO =====")
        print(f"Precision: {results.seg.mp:.4f}")
        print(f"Recall:    {results.seg.mr:.4f}")
        print(f"mAP50:     {results.seg.map50:.4f}")
        print(f"mAP50-95:  {results.seg.map:.4f}")

        # F1 Score da segmentação
        p = results.seg.mp
        r = results.seg.mr

        if (p + r) > 0:
            f1 = 2 * (p * r) / (p + r)
            print(f"F1-Score:  {f1:.4f}")

if __name__ == "__main__":
    main()