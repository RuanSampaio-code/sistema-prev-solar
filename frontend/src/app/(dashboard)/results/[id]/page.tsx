"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { ImageRecord, Panel } from "@/types";
import { ArrowLeft, Zap, ScanLine, SquareStack, FileDown, Loader2, Trash2, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

const MODEL_LABELS: Record<string, string> = {
  default: "UNet Padrão (ResNet34)",
  new: "UNet v2",
  yolo: "YOLO v11",
};

export default function ResultDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [selectedPanel, setSelectedPanel] = useState<Panel | null>(null);

  const { data: image, isLoading } = useQuery<ImageRecord>({
    queryKey: ["image", id],
    queryFn: () => api.get(`/api/images/${id}`).then((r) => r.data),
    refetchInterval: (data) => (data?.status === "done" ? false : 5000),
  });

  useEffect(() => {
    setSelectedPanel(null);
  }, [id]);

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

  const panels = image.result?.panels ?? [];

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
        <>
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

            {/* imagem processada */}
            <div className="xl:col-span-2 bg-surface border border-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-white font-medium text-sm">Resultado da análise — painéis destacados</p>
              </div>
              <VizImage
                imageId={id}
                selectedPanel={selectedPanel}
                onClearSelection={() => setSelectedPanel(null)}
              />
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
                <p className="text-muted font-medium mt-3">Modelo usado</p>
                <p className="text-slate-300">
                  {MODEL_LABELS[image.result?.model_name ?? ""] ?? "—"}
                </p>
                <p className="text-muted font-medium mt-3">GSD usado</p>
                <p className="text-slate-300 font-mono">
                  {image.result?.gsd_used_m_px != null
                    ? `${image.result.gsd_used_m_px.toFixed(4)} m/px`
                    : "—"}
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

          <PanelsTable
            panels={panels}
            selectedPanelId={selectedPanel?.panel_id ?? null}
            onSelectPanel={(p) =>
              setSelectedPanel((prev) => (prev?.panel_id === p?.panel_id ? null : p))
            }
          />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// VizImage — viewport com zoom/pan + canvas overlay para painel selecionado
// ---------------------------------------------------------------------------

const ZOOM_MIN = 1;
const ZOOM_MAX = 8;
const ZOOM_STEP = 0.3;

function VizImage({
  imageId,
  selectedPanel,
  onClearSelection,
}: {
  imageId: string;
  selectedPanel: Panel | null;
  onClearSelection: () => void;
}) {
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

  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const lastPos = useRef({ x: 0, y: 0 });
  const wasDragged = useRef(false);

  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

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
    wasDragged.current = false;
    if (zoomRef.current <= 1) return;
    setIsDragging(true);
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: { clientX: number; clientY: number }) => {
    if (!isDragging) return;
    wasDragged.current = true;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    lastPos.current = { x: e.clientX, y: e.clientY };
    const clamped = clamp(zoomRef.current, panRef.current.x + dx, panRef.current.y + dy);
    panRef.current = clamped;
    setPan(clamped);
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleClick = () => {
    if (!wasDragged.current) onClearSelection();
  };

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

  const drawPanel = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || img.naturalWidth === 0) return;

    canvas.width = img.offsetWidth;
    canvas.height = img.offsetHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!selectedPanel) return;

    const sx = img.offsetWidth / img.naturalWidth;
    const sy = img.offsetHeight / img.naturalHeight;
    const { bbox_x: bx, bbox_y: by, bbox_width: bw, bbox_height: bh, panel_id } = selectedPanel;

    const rx = bx * sx;
    const ry = by * sy;
    const rw = bw * sx;
    const rh = bh * sy;

    ctx.strokeStyle = "#facc15";
    ctx.lineWidth = 2;
    ctx.strokeRect(rx, ry, rw, rh);

    const label = `#${panel_id}`;
    ctx.font = "bold 10px monospace";
    const tw = ctx.measureText(label).width;
    const lx = rx;
    const ly = ry;
    ctx.fillStyle = "rgba(0,0,0,0.75)";
    ctx.fillRect(lx, Math.max(0, ly - 14), tw + 6, 14);
    ctx.fillStyle = "#facc15";
    ctx.fillText(label, lx + 3, Math.max(11, ly - 3));
  }, [selectedPanel]);

  useEffect(() => { drawPanel(); }, [drawPanel]);

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
        onClick={handleClick}
        onDoubleClick={reset}
      >
        {/* wrapper compartilha o transform entre img e canvas */}
        <div
          style={{
            position: "relative",
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
            transition: isDragging ? "none" : "transform 0.12s ease-out",
          }}
        >
          <img
            ref={imgRef}
            src={url}
            alt="Resultado da análise"
            draggable={false}
            style={{ width: "100%", display: "block" }}
            onLoad={drawPanel}
          />
          <canvas
            ref={canvasRef}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
            }}
          />
        </div>
      </div>

      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-black/70 backdrop-blur-sm rounded-full px-3 py-1.5 border border-white/10 z-10">
        <button
          onClick={(e) => { e.stopPropagation(); zoomOut(); }}
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
          onClick={(e) => { e.stopPropagation(); zoomIn(); }}
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
              onClick={(e) => { e.stopPropagation(); reset(); }}
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

// ---------------------------------------------------------------------------
// PanelsTable — tabela de painéis individuais com destaque interativo
// ---------------------------------------------------------------------------

function PanelsTable({
  panels,
  selectedPanelId,
  onSelectPanel,
}: {
  panels: Panel[];
  selectedPanelId: number | null;
  onSelectPanel: (panel: Panel | null) => void;
}) {
  const sorted = useMemo(
    () => [...panels].sort((a, b) => b.area_m2 - a.area_m2),
    [panels]
  );

  if (panels.length === 0) {
    return (
      <div className="bg-surface border border-border rounded-lg p-8 text-center text-muted text-sm">
        Dados individuais não disponíveis para esta imagem
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <p className="text-white font-medium text-sm">Painéis individuais</p>
        <span className="text-muted text-xs">{panels.length} painéis · ordenados por área</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface z-10">
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2.5 text-muted font-medium w-14">#</th>
              <th className="text-right px-4 py-2.5 text-muted font-medium">Área (m²)</th>
              <th className="text-right px-4 py-2.5 text-muted font-medium">Geração (kWh/mês)</th>
              <th className="px-4 py-2.5 text-muted font-medium w-48">Confiança</th>
            </tr>
          </thead>
          <tbody className="max-h-96 overflow-y-auto">
            {sorted.map((panel) => {
              const isSelected = panel.panel_id === selectedPanelId;
              const conf = panel.confidence_mean;
              const barColor =
                conf >= 0.8 ? "bg-green-500" : conf >= 0.5 ? "bg-yellow-500" : "bg-red-500";

              return (
                <tr
                  key={panel.panel_id}
                  onClick={() => onSelectPanel(panel)}
                  className={`border-b border-border/40 cursor-pointer transition-colors ${
                    isSelected ? "bg-primary/10" : "hover:bg-white/5"
                  }`}
                >
                  <td className="px-4 py-2.5 font-mono text-slate-400">{panel.panel_id}</td>
                  <td className="px-4 py-2.5 text-right text-slate-300 tabular-nums">
                    {panel.area_m2.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-300 tabular-nums">
                    {panel.kwh_month.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${barColor}`}
                          style={{ width: `${conf * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted w-9 text-right tabular-nums">
                        {(conf * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

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
