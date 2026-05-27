"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { ImageRecord } from "@/types";
import { ArrowLeft, Zap, ScanLine, SquareStack, FileDown, Loader2, Trash2 } from "lucide-react";

export default function ResultDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: image, isLoading } = useQuery<ImageRecord>({
    queryKey: ["image", id],
    queryFn: () => api.get(`/api/images/${id}`).then((r) => r.data),
    refetchInterval: (data) => (data?.status === "done" ? false : 5000),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.post(`/api/images/${id}/delete`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["images"] });
      router.push("/dashboard");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted" />
      </div>
    );
  }

  if (!image) return null;

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="text-muted hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">{image.original_name}</h1>
            <p className="text-muted text-sm">{formatDate(image.uploaded_at)}</p>
          </div>
        </div>
        <button
          onClick={() => setConfirmDelete(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-md border border-red-800 text-red-400 hover:bg-red-900/30 hover:text-red-300 transition-colors text-sm"
        >
          <Trash2 className="w-4 h-4" />
          Deletar
        </button>
      </div>

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-surface border border-border rounded-lg p-6 max-w-sm w-full mx-4 space-y-4">
            <h2 className="text-white font-semibold text-lg">Deletar imagem?</h2>
            <p className="text-muted text-sm">
              A análise de <span className="text-slate-300 font-medium">{image.original_name}</span> e todos
              os arquivos associados serão removidos permanentemente.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 rounded-md border border-border text-slate-300 hover:text-white transition-colors text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-red-700 hover:bg-red-600 text-white text-sm transition-colors disabled:opacity-60"
              >
                {deleteMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {image.status !== "done" ? (
        <div className="bg-surface border border-border rounded-lg p-12 flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-slate-300 font-medium">Processando com o modelo de IA...</p>
          <p className="text-muted text-sm">Status atual: {image.status}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* imagem processada */}
          <div className="xl:col-span-2 bg-surface border border-border rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <p className="text-white font-medium text-sm">Resultado da análise — painéis destacados</p>
            </div>
            <VizImage imageId={id} />
          </div>

          {/* stats */}
          <div className="space-y-4">
            <StatCard
              icon={SquareStack}
              label="Painéis detectados"
              value={String(image.result?.panel_count ?? 0)}
              color="bg-yellow-500"
            />
            <StatCard
              icon={ScanLine}
              label="Área estimada"
              value={`${image.result?.detected_area_m2?.toFixed(2) ?? "0"} m²`}
              color="bg-blue-600"
            />
            <StatCard
              icon={Zap}
              label="Potencial energético"
              value={`${image.result?.estimated_kwh_month?.toFixed(1) ?? "0"} kWh/mês`}
              color="bg-primary"
            />

            <div className="bg-surface border border-border rounded-lg p-4 space-y-2 text-sm">
              <p className="text-muted font-medium">Arquivo</p>
              <p className="text-slate-300 break-all">{image.original_name}</p>
              <p className="text-muted font-medium mt-3">Tamanho</p>
              <p className="text-slate-300">{(image.file_size_kb / 1024).toFixed(1)} MB</p>
              <p className="text-muted font-medium mt-3">Processado em</p>
              <p className="text-slate-300">
                {image.result?.processed_at ? formatDate(image.result.processed_at) : "—"}
              </p>
            </div>

            <a
              href={`${process.env.NEXT_PUBLIC_API_URL}/api/reports/csv?image_id=${id}`}
              target="_blank"
              className="flex items-center justify-center gap-2 w-full bg-surface border border-border text-slate-300 px-4 py-2.5 rounded-md hover:border-primary hover:text-white transition-colors text-sm"
            >
              <FileDown className="w-4 h-4" />
              Exportar CSV
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function VizImage({ imageId }: { imageId: string }) {
  const { data: url, isLoading, isError } = useQuery<string>({
    queryKey: ["viz", imageId],
    queryFn: async () => {
      const token = localStorage.getItem("access_token");
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/images/${imageId}/visualization`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error("Erro ao carregar visualização");
      const blob = await res.blob();
      return URL.createObjectURL(blob);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-80">
        <Loader2 className="w-6 h-6 animate-spin text-muted" />
      </div>
    );
  }

  if (isError || !url) {
    return (
      <div className="flex items-center justify-center h-80 text-muted text-sm">
        Erro ao carregar imagem processada
      </div>
    );
  }

  return (
    <img
      src={url}
      alt="Resultado da análise"
      className="w-full object-contain max-h-[520px]"
    />
  );
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ElementType; label: string; value: string; color: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="text-muted text-xs">{label}</p>
        <p className="text-white text-xl font-bold">{value}</p>
      </div>
    </div>
  );
}
