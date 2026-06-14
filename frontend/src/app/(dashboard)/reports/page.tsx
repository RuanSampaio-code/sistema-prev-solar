"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileDown, FileText, BarChart2, Zap, Layers } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";

async function fetchStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/api/results/dashboard");
  return data;
}

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

export default function ReportsPage() {
  const [downloading, setDownloading] = useState(false);

  const { data: stats } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchStats,
  });

  async function handleDownload() {
    setDownloading(true);
    try {
      await downloadXlsx();
      toast.success("Relatório exportado com sucesso");
    } catch {
      toast.error("Erro ao exportar CSV");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Relatórios</h1>
        <p className="text-muted text-sm mt-1">Exportação de dados para análise externa</p>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4 flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-md">
              <Layers className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted">Imagens processadas</p>
              <p className="text-lg font-bold text-white">{stats.total_images ?? 0}</p>
            </div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4 flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-md">
              <BarChart2 className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted">Total de painéis</p>
              <p className="text-lg font-bold text-white">{stats.total_panels ?? 0}</p>
            </div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4 flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-md">
              <Zap className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted">Potencial total</p>
              <p className="text-lg font-bold text-white">
                {stats.total_kwh_month != null
                  ? `${stats.total_kwh_month.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} kWh`
                  : "—"}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="bg-surface border border-border rounded-lg p-6 flex items-start gap-4">
          <div className="bg-primary/10 p-3 rounded-lg flex-shrink-0">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-semibold">Relatório Consolidado</h3>
            <p className="text-muted text-sm mt-1">
              Exporta todos os resultados processados com nome da imagem, quantidade de painéis,
              área detectada e potencial energético estimado.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {["Imagem", "Painéis", "Área (m²)", "kWh/mês", "Data"].map((col) => (
                <span
                  key={col}
                  className="text-xs bg-background border border-border text-slate-400 px-2 py-0.5 rounded"
                >
                  {col}
                </span>
              ))}
            </div>
          </div>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-2 bg-primary text-black font-semibold px-4 py-2 rounded-md hover:bg-primary/90 transition-colors text-sm flex-shrink-0 disabled:opacity-60"
          >
            <FileDown className="w-4 h-4" />
            {downloading ? "Exportando..." : "Baixar Excel"}
          </button>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <p className="text-slate-400 text-sm">
            Para exportar o resultado de uma imagem específica, use o botão de download
            na página de{" "}
            <a href="/results" className="text-primary hover:underline">
              Resultados
            </a>
            , coluna de ações de cada linha.
          </p>
        </div>
      </div>
    </div>
  );
}
