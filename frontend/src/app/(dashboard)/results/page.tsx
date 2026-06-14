"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ImageRecord, PaginatedImages } from "@/types";
import { formatDate } from "@/lib/utils";
import { Search, ChevronLeft, ChevronRight, FileDown, Eye, Trash2, Check, X } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

async function downloadXlsx(imageId?: number) {
  const qs = imageId ? `?image_id=${imageId}` : "";
  const response = await api.get(`/api/reports/xlsx${qs}`, { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([response.data], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `prevsolar_relatorio_${imageId ?? "completo"}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  pending:    { label: "Aguardando", color: "text-yellow-400 bg-yellow-400/10" },
  processing: { label: "Processando", color: "text-blue-400 bg-blue-400/10" },
  done:       { label: "Concluído",  color: "text-green-400 bg-green-400/10" },
  error:      { label: "Erro",       color: "text-red-400 bg-red-400/10" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_LABEL[status] ?? { label: status, color: "text-slate-400 bg-slate-400/10" };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${s.color}`}>{s.label}</span>
  );
}

export default function ResultsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [orderBy, setOrderBy] = useState("energy");
  const [exportingId, setExportingId] = useState<number | "all" | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.post(`/api/images/${id}/delete`),
    onSuccess: () => {
      toast.success("Imagem deletada com sucesso");
      setConfirmDeleteId(null);
      queryClient.invalidateQueries({ queryKey: ["images"] });
    },
    onError: () => {
      toast.error("Erro ao deletar imagem");
      setConfirmDeleteId(null);
    },
  });

  async function handleDownload(imageId?: number) {
    const key = imageId ?? "all";
    setExportingId(key);
    try {
      await downloadXlsx(imageId);
      toast.success("Relatório exportado com sucesso");
    } catch {
      toast.error("Erro ao exportar relatório");
    } finally {
      setExportingId(null);
    }
  }

  const { data, isLoading } = useQuery<PaginatedImages>({
    queryKey: ["images", page, search, statusFilter, orderBy],
    queryFn: () =>
      api.get("/api/images", {
        params: { page, page_size: 20, search: search || undefined, status: statusFilter || undefined, order_by: orderBy },
      }).then((r) => r.data),
    refetchInterval: 10_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Resultados</h1>
          <p className="text-muted text-sm mt-1">{data?.total ?? 0} registros encontrados</p>
        </div>
        <button
          onClick={() => handleDownload()}
          disabled={exportingId === "all"}
          className="flex items-center gap-2 bg-surface border border-border text-slate-300 px-4 py-2 rounded-md hover:border-primary hover:text-white transition-colors text-sm disabled:opacity-60"
        >
          <FileDown className="w-4 h-4" />
          {exportingId === "all" ? "Exportando..." : "Exportar tudo"}
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Buscar imagem..."
            className="w-full bg-surface border border-border rounded-md pl-9 pr-3 py-2 text-white placeholder:text-muted text-sm focus:outline-none focus:border-primary"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-surface border border-border rounded-md px-3 py-2 text-white text-sm focus:outline-none"
        >
          <option value="">Todos os status</option>
          <option value="pending">Aguardando</option>
          <option value="processing">Processando</option>
          <option value="done">Concluído</option>
          <option value="error">Erro</option>
        </select>

        <select
          value={orderBy}
          onChange={(e) => setOrderBy(e.target.value)}
          className="bg-surface border border-border rounded-md px-3 py-2 text-white text-sm focus:outline-none"
        >
          <option value="energy">Maior potencial</option>
          <option value="date">Mais recente</option>
        </select>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-muted text-left">
              <th className="px-4 py-3 font-medium">Imagem</th>
              <th className="px-4 py-3 font-medium">Painéis</th>
              <th className="px-4 py-3 font-medium">kWh/mês</th>
              <th className="px-4 py-3 font-medium">Data</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="text-center text-muted py-12">Carregando...</td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center text-muted py-12">Nenhum resultado encontrado</td>
              </tr>
            ) : (
              data?.items.map((img: ImageRecord) => (
                <tr key={img.id} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{img.original_name}</td>
                  <td className="px-4 py-3 text-slate-300">{img.result?.panel_count ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {img.result ? (
                      <span className="text-primary font-semibold">{img.result.estimated_kwh_month.toFixed(1)}</span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(img.uploaded_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={img.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Link
                        href={`/results/${img.id}`}
                        className="text-muted hover:text-primary transition-colors"
                        title="Ver detalhes"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                      {img.status === "done" && (
                        <button
                          onClick={() => handleDownload(img.id)}
                          disabled={exportingId === img.id}
                          className="text-muted hover:text-primary transition-colors disabled:opacity-40"
                          title="Exportar relatório XLSX"
                        >
                          <FileDown className="w-4 h-4" />
                        </button>
                      )}
                      {confirmDeleteId === img.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => deleteMutation.mutate(img.id)}
                            disabled={deleteMutation.isPending}
                            className="p-0.5 text-red-400 hover:text-red-300 transition-colors disabled:opacity-40"
                            title="Confirmar exclusão"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="p-0.5 text-muted hover:text-white transition-colors"
                            title="Cancelar"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDeleteId(img.id)}
                          className="text-muted hover:text-red-400 transition-colors"
                          title="Deletar imagem"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-muted">
          <span>Página {page} de {data.total_pages}</span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="p-1.5 rounded border border-border hover:border-primary disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 rounded border border-border hover:border-primary disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
