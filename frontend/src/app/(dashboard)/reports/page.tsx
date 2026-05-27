"use client";

import { FileDown, FileText } from "lucide-react";

export default function ReportsPage() {
  function download(imageId?: number) {
    const qs = imageId ? `?image_id=${imageId}` : "";
    window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/reports/csv${qs}`, "_blank");
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Relatórios</h1>
        <p className="text-muted text-sm mt-1">Exportação de dados para análise externa</p>
      </div>

      <div className="space-y-4">
        <div className="bg-surface border border-border rounded-lg p-6 flex items-start gap-4">
          <div className="bg-primary/10 p-3 rounded-lg">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="text-white font-semibold">Relatório Consolidado</h3>
            <p className="text-muted text-sm mt-1">
              Exporta todos os resultados processados com unidade consumidora,
              quantidade de painéis e potencial energético estimado.
            </p>
          </div>
          <button
            onClick={() => download()}
            className="flex items-center gap-2 bg-primary text-black font-semibold px-4 py-2 rounded-md hover:bg-primary/90 transition-colors text-sm flex-shrink-0"
          >
            <FileDown className="w-4 h-4" />
            Baixar CSV
          </button>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <p className="text-slate-400 text-sm">
            Para exportar o resultado de uma imagem específica, use o botão de download
            na coluna de ações da página de{" "}
            <a href="/results" className="text-primary hover:underline">Resultados</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
