"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { CloudUpload, X, Loader2, CheckCircle2, Info } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FileItem {
  file: File;
  preview: string;
  status: "queued" | "uploading" | "done" | "error";
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [threshold, setThreshold] = useState(0.40);

  const onDrop = useCallback((accepted: File[]) => {
    const newItems = accepted.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      status: "queued" as const,
    }));
    setFiles((prev) => [...prev, ...newItems].slice(0, 10));
  }, []);

  const ALLOWED_EXT = [".png", ".jpg", ".jpeg", ".tif", ".tiff"];

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 10,
    validator: (file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXT.includes(ext)) {
        return { code: "file-invalid-type", message: `Formato não suportado: ${ext}` };
      }
      return null;
    },
  });

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (files.length === 0) {
      toast.error("Selecione ao menos uma imagem");
      return;
    }
    setUploading(true);

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f.file));
    formData.append("threshold", String(threshold));

    try {
      await api.post("/api/images/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`${files.length} imagem(ns) enviada(s) para processamento!`);
      setFiles([]);
    } catch {
      toast.error("Erro ao enviar imagens. Verifique o formato e tamanho.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Upload de Imagens</h1>
        <p className="text-muted text-sm mt-1">Envie imagens de painéis solares para análise</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors",
            isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
          )}
        >
          <input {...getInputProps()} accept=".png,.jpg,.jpeg,.tif,.tiff" />
          <CloudUpload className="w-10 h-10 text-muted mx-auto mb-3" />
          <p className="text-slate-300 font-medium">
            {isDragActive ? "Solte as imagens aqui" : "Arraste imagens ou clique para selecionar"}
          </p>
          <p className="text-muted text-xs mt-1">PNG, JPG, TIFF — máximo 10 arquivos, 200MB no total</p>
        </div>

        {files.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-slate-400">{files.length} arquivo(s) selecionado(s)</p>
            <div className="grid grid-cols-2 gap-3">
              {files.map((item, i) => (
                <div key={i} className="bg-surface border border-border rounded-md p-3 flex items-center gap-3">
                  <img src={item.preview} alt="" className="w-12 h-12 object-cover rounded" />
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-xs truncate">{item.file.name}</p>
                    <p className="text-muted text-xs">{(item.file.size / 1024).toFixed(0)} KB</p>
                  </div>
                  {item.status === "done" ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                  ) : (
                    <button type="button" onClick={() => removeFile(i)}>
                      <X className="w-4 h-4 text-muted hover:text-white" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Threshold */}
        <div className="bg-surface border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <p className="text-white text-sm font-medium">Sensibilidade da detecção</p>
            <div className="relative group">
              <Info className="w-4 h-4 text-muted cursor-help" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-80 p-3 bg-zinc-900 border border-border rounded-md text-xs text-slate-300 leading-relaxed hidden group-hover:block z-20 pointer-events-none shadow-lg">
                <p className="font-semibold text-white mb-1">Threshold de detecção</p>
                <p>
                  Probabilidade mínima para que um pixel seja classificado como painel solar
                  pelo modelo UNet. Controla o equilíbrio entre sensibilidade e precisão:
                </p>
                <ul className="mt-2 space-y-1 list-disc list-inside">
                  <li><span className="text-yellow-400">Valor baixo (0.2–0.35)</span> — detecta mais regiões, mas pode incluir falsos positivos</li>
                  <li><span className="text-green-400">Valor padrão (0.40)</span> — equilibrado, recomendado para a maioria das imagens</li>
                  <li><span className="text-blue-400">Valor alto (0.55–0.80)</span> — mais conservador, só detecta regiões com alta certeza</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <input
              type="range"
              min={0.10}
              max={0.90}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="flex-1 accent-primary h-1.5 cursor-pointer"
            />
            <span className="text-white font-mono text-sm w-10 text-right tabular-nums">
              {threshold.toFixed(2)}
            </span>
            {threshold !== 0.40 && (
              <button
                type="button"
                onClick={() => setThreshold(0.40)}
                className="text-xs text-muted hover:text-white transition-colors whitespace-nowrap"
              >
                Resetar
              </button>
            )}
          </div>

          <div className="flex justify-between text-xs text-muted">
            <span>Mais sensível</span>
            <span>Mais conservador</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={uploading || files.length === 0}
          className="flex items-center gap-2 bg-primary text-black font-semibold px-6 py-2.5 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
          Enviar para análise
        </button>
      </form>
    </div>
  );
}
