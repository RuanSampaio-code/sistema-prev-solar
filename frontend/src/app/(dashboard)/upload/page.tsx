"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { CloudUpload, X, ImageIcon, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const schema = z.object({ consumer_unit: z.string().min(3, "Informe a unidade consumidora") });
type Form = z.infer<typeof schema>;

interface FileItem {
  file: File;
  preview: string;
  status: "queued" | "uploading" | "done" | "error";
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [uploading, setUploading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  });

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

  async function onSubmit(data: Form) {
    if (files.length === 0) {
      toast.error("Selecione ao menos uma imagem");
      return;
    }
    setUploading(true);

    const formData = new FormData();
    formData.append("consumer_unit", data.consumer_unit);
    files.forEach((f) => formData.append("files", f.file));

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

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div>
          <label className="block text-sm text-slate-300 mb-1.5">Unidade Consumidora *</label>
          <input
            {...register("consumer_unit")}
            placeholder="Ex: Rua das Flores, 42 – Fortaleza / CE"
            className="w-full bg-surface border border-border rounded-md px-3 py-2.5 text-white placeholder:text-muted focus:outline-none focus:border-primary transition-colors"
          />
          {errors.consumer_unit && (
            <p className="text-red-400 text-xs mt-1">{errors.consumer_unit.message}</p>
          )}
        </div>

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
