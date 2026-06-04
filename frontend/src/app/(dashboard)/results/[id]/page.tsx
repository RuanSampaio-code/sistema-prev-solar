"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { ImageRecord } from "@/types";
import { ArrowLeft, Zap, ScanLine, SquareStack, FileDown, Loader2, Trash2, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

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

const ZOOM_MIN = 1;
const ZOOM_MAX = 8;
const ZOOM_STEP = 0.3;

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

  // Refs para zoom/pan — lidos pelo handler nativo sem closure stale
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });

  // State só para re-renderizar o JSX
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const lastPos = useRef({ x: 0, y: 0 });

  // Mantém refs sincronizados com state
  useEffect(() => { zoomRef.current = zoom; }, [zoom]);
  useEffect(() => { panRef.current = pan; }, [pan]);

  const clamp = (z: number, px: number, py: number) => {
    const el = containerRef.current;
    if (!el) return { x: px, y: py };
    const { width: cw, height: ch } = el.getBoundingClientRect();
    return {
      x: Math.min(0, Math.max(cw - cw * z, px)),
      y: Math.min(0, Math.max(ch - ch * z, py)),
    };
  };

  const applyZoom = useCallback((nextZoom: number, cx: number, cy: number) => {
    const prevZoom = zoomRef.current;
    const prevPan = panRef.current;
    const nx = cx - (cx - prevPan.x) * (nextZoom / prevZoom);
    const ny = cy - (cy - prevPan.y) * (nextZoom / prevZoom);
    const clamped = clamp(nextZoom, nx, ny);
    zoomRef.current = nextZoom;
    panRef.current = clamped;
    setZoom(nextZoom);
    setPan(clamped);
  }, []);

  const reset = useCallback(() => {
    zoomRef.current = 1;
    panRef.current = { x: 0, y: 0 };
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Wheel nativo com passive:false — único jeito de preventDefault funcionar
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
      const next = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoomRef.current + delta));
      applyZoom(next, cx, cy);
    };
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, [applyZoom]);

  const handleMouseDown = (e: { clientX: number; clientY: number }) => {
    if (zoomRef.current <= 1) return;
    setIsDragging(true);
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: { clientX: number; clientY: number }) => {
    if (!isDragging) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    lastPos.current = { x: e.clientX, y: e.clientY };
    const clamped = clamp(zoomRef.current, panRef.current.x + dx, panRef.current.y + dy);
    panRef.current = clamped;
    setPan(clamped);
  };

  const handleMouseUp = () => setIsDragging(false);

  const zoomIn = () => {
    const next = Math.min(ZOOM_MAX, zoomRef.current + ZOOM_STEP * 2);
    const el = containerRef.current;
    const cx = el ? el.getBoundingClientRect().width / 2 : 0;
    const cy = el ? el.getBoundingClientRect().height / 2 : 0;
    applyZoom(next, cx, cy);
  };

  const zoomOut = () => {
    const next = Math.max(ZOOM_MIN, zoomRef.current - ZOOM_STEP * 2);
    if (next <= 1) { reset(); return; }
    const el = containerRef.current;
    const cx = el ? el.getBoundingClientRect().width / 2 : 0;
    const cy = el ? el.getBoundingClientRect().height / 2 : 0;
    applyZoom(next, cx, cy);
  };

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

  const isZoomed = zoom > 1;

  return (
    <div className="relative select-none">
      {/* viewport — overflow hidden contém a imagem transformada */}
      <div
        ref={containerRef}
        className="overflow-hidden"
        style={{
          maxHeight: 520,
          cursor: isDragging ? "grabbing" : isZoomed ? "grab" : "default",
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={reset}
      >
        <img
          src={url}
          alt="Resultado da análise"
          draggable={false}
          style={{
            width: "100%",
            display: "block",
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
            transition: isDragging ? "none" : "transform 0.12s ease-out",
          }}
        />
      </div>

      {/* barra de controles */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-black/70 backdrop-blur-sm rounded-full px-3 py-1.5 border border-white/10 z-10">
        <button
          onClick={zoomOut}
          disabled={!isZoomed}
          title="Diminuir zoom"
          className="p-1 rounded-full text-slate-300 hover:text-white disabled:opacity-30 transition-colors"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <span className="text-xs text-slate-300 w-12 text-center tabular-nums">
          {Math.round(zoom * 100)}%
        </span>

        <button
          onClick={zoomIn}
          disabled={zoom >= ZOOM_MAX}
          title="Aumentar zoom"
          className="p-1 rounded-full text-slate-300 hover:text-white disabled:opacity-30 transition-colors"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        {isZoomed && (
          <>
            <div className="w-px h-4 bg-white/20 mx-1" />
            <button
              onClick={reset}
              title="Resetar zoom (duplo clique)"
              className="p-1 rounded-full text-slate-300 hover:text-white transition-colors"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </>
        )}
      </div>

      {!isZoomed && (
        <p className="absolute bottom-3 right-3 text-[11px] text-white/35 pointer-events-none">
          Scroll ou botões para zoom · Arraste para mover
        </p>
      )}
    </div>
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
