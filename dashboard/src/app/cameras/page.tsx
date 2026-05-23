"use client";

import { useState, useEffect, useRef } from "react";
import { Camera, Plus, Trash2, Edit, Loader2, AlertCircle, CheckCircle, X, RefreshCw, HelpCircle, Sliders, MapPin } from "lucide-react";
import DetectionSetupWizard, { DetectionConfig } from "@/components/DetectionSetupWizard";

// ── Types ─────────────────────────────────────────────────────────────────

type ZoneType = "merchandise" | "forbidden" | "entry";

interface RoiZone {
  name: string;
  zone_type: ZoneType;
  points: number[][];
}

interface CameraData {
  id: string;
  name: string;
  source: string;
  status: "active" | "error";
  roi_points: number[][];
  roi_zones: RoiZone[];
}

interface CameraFeed {
  camera_id: string;
  name: string;
  data: string;
}

const ROI_CANVAS_WIDTH = 1280;
const ROI_CANVAS_HEIGHT = 720;

const toCanvasPoints = (points: number[][], canvasWidth: number, canvasHeight: number): number[][] => {
  if (!Array.isArray(points)) return [];

  return points
    .filter((p) => Array.isArray(p) && p.length >= 2)
    .map((p) => {
      const x = Number(p[0]);
      const y = Number(p[1]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;

      // Normalized points from backend (0..1)
      if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
        return [Math.round(x * canvasWidth), Math.round(y * canvasHeight)];
      }

      // Legacy absolute pixel points
      return [Math.round(x), Math.round(y)];
    })
    .filter((p): p is number[] => p !== null);
};

const toNormalizedPoints = (points: number[][], canvasWidth: number, canvasHeight: number): number[][] => {
  if (!Array.isArray(points) || canvasWidth <= 0 || canvasHeight <= 0) return [];

  return points
    .filter((p) => Array.isArray(p) && p.length >= 2)
    .map((p) => {
      const x = Number(p[0]);
      const y = Number(p[1]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;

      const nx = Math.max(0, Math.min(1, x / canvasWidth));
      const ny = Math.max(0, Math.min(1, y / canvasHeight));
      return [Number(nx.toFixed(6)), Number(ny.toFixed(6))];
    })
    .filter((p): p is number[] => p !== null);
};

const ensureNormalizedPoints = (points: number[][]): number[][] => {
  if (!Array.isArray(points)) return [];
  const valid = points.filter((p) => Array.isArray(p) && p.length >= 2);
  if (valid.length === 0) return [];

  const alreadyNormalized = valid.every((p) => {
    const x = Number(p[0]);
    const y = Number(p[1]);
    return Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 1 && y >= 0 && y <= 1;
  });

  if (alreadyNormalized) {
    return valid.map((p) => [Number(Number(p[0]).toFixed(6)), Number(Number(p[1]).toFixed(6))]);
  }

  // Legacy absolute coordinates fallback (historically edited on 1280x720 canvas).
  return toNormalizedPoints(valid, ROI_CANVAS_WIDTH, ROI_CANVAS_HEIGHT);
};

export default function CamerasPage() {
  const [cameras, setCameras] = useState<CameraData[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Add Camera Form
  const [name, setName] = useState("");
  const [source, setSource] = useState("");

  // ROI Canvas Drawer Modal States
  const [selectedCam, setSelectedCam] = useState<CameraData | null>(null);
  // Multi-zone state
  const [roiZones, setRoiZones] = useState<RoiZone[]>([]);
  const [activeZoneIdx, setActiveZoneIdx] = useState<number>(0); // which zone is being drawn
  const [activeFrameBase64, setActiveFrameBase64] = useState<string | null>(null);
  const [frameResolution, setFrameResolution] = useState<{ width: number; height: number }>({
    width: ROI_CANVAS_WIDTH,
    height: ROI_CANVAS_HEIGHT,
  });
  const wsRef = useRef<WebSocket | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [detectionConfig, setDetectionConfig] = useState<DetectionConfig | null>(null);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const getWebSocketUrl = () => {
    try {
      const apiUrl = new URL(apiBaseUrl);
      const wsProtocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
      return `${wsProtocol}//${apiUrl.host}/ws`;
    } catch {
      return "ws://localhost:8000/ws";
    }
  };

  const fetchCameras = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/cameras`);
      if (res.ok) {
        const data = await res.json();
        setCameras(data);
      }
    } catch (err) {
      console.error("Error fetching cameras:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  // Listen to live camera frames when ROI Modal is open
  useEffect(() => {
    if (!selectedCam) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setActiveFrameBase64(null);
      return;
    }

    const wsUrl = getWebSocketUrl();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "multi_frame" && payload.cameras) {
          const matched = payload.cameras.find((c: CameraFeed) => c.camera_id === selectedCam.id);
          if (matched) {
            setActiveFrameBase64(matched.data);
          }
        }
      } catch (err) {
        console.error("Error parsing WS in ROI modal", err);
      }
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [selectedCam]);

  // Redraw Canvas when points or frames change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const ZONE_COLOURS: Record<ZoneType, { fill: string; stroke: string; label: string }> = {
      merchandise: { fill: "rgba(251,146,60,0.2)", stroke: "#fb923c", label: "🛍️" },
      forbidden: { fill: "rgba(239,68,68,0.2)", stroke: "#ef4444", label: "🚫" },
      entry: { fill: "rgba(34,197,94,0.2)", stroke: "#22c55e", label: "🚪" },
    };

    const drawCanvas = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (activeFrameBase64) {
        const img = new Image();
        img.src = `data:image/jpeg;base64,${activeFrameBase64}`;
        img.onload = () => {
          if (img.naturalWidth > 0 && img.naturalHeight > 0) {
            setFrameResolution((prev) =>
              prev.width === img.naturalWidth && prev.height === img.naturalHeight
                ? prev
                : { width: img.naturalWidth, height: img.naturalHeight }
            );
          }
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          drawAllZones();
        };
      } else {
        ctx.fillStyle = "#151824";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "rgba(255,255,255,0.4)";
        ctx.font = "20px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Surveillance Feed Loading...", canvas.width / 2, canvas.height / 2 - 10);
        ctx.font = "14px sans-serif";
        ctx.fillText("(Ensure backend is active & transmitting live stream)", canvas.width / 2, canvas.height / 2 + 20);
        drawAllZones();
      }
    };

    const drawAllZones = () => {
      roiZones.forEach((zone, zIdx) => {
        if (zone.points.length === 0) return;
        const colours = ZONE_COLOURS[zone.zone_type];
        const isActive = zIdx === activeZoneIdx;
        const canvasPoints = toCanvasPoints(zone.points, canvas.width, canvas.height);
        if (canvasPoints.length === 0) return;

        ctx.beginPath();
        ctx.moveTo(canvasPoints[0][0], canvasPoints[0][1]);
        for (let i = 1; i < canvasPoints.length; i++) {
          ctx.lineTo(canvasPoints[i][0], canvasPoints[i][1]);
        }
        ctx.closePath();
        ctx.fillStyle = colours.fill;
        ctx.fill();
        ctx.strokeStyle = colours.stroke;
        ctx.lineWidth = isActive ? 3 : 1.5;
        ctx.setLineDash(isActive ? [] : [6, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Zone name label
        const minX = Math.min(...canvasPoints.map((p) => p[0]));
        const minY = Math.min(...canvasPoints.map((p) => p[1]));
        ctx.fillStyle = colours.stroke;
        ctx.font = "bold 13px sans-serif";
        ctx.textAlign = "left";
        ctx.fillText(`${colours.label} ${zone.name}`, minX + 4, minY - 6);

        // Draw anchor dots for the active zone only (so it's clear which one you're editing)
        if (isActive) {
          canvasPoints.forEach((pt, idx) => {
            ctx.beginPath();
            ctx.arc(pt[0], pt[1], 6, 0, 2 * Math.PI);
            ctx.fillStyle = "#ffffff";
            ctx.fill();
            ctx.strokeStyle = colours.stroke;
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 11px sans-serif";
            ctx.textAlign = "left";
            ctx.fillText((idx + 1).toString(), pt[0] + 9, pt[1] - 5);
          });
        }
      });
    };

    drawCanvas();
  }, [roiZones, activeZoneIdx, activeFrameBase64, selectedCam]);

  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !source) {
      setMessage({ text: "Please enter a name and source value.", type: "error" });
      return;
    }

    setSubmitting(true);
    setMessage(null);
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    try {
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 15000);

      const res = await fetch(`${apiBaseUrl}/cameras`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, source }),
        signal: controller.signal,
      });

      const data = await res.json();

      if (res.ok) {
        setMessage({ text: "Camera added successfully!", type: "success" });
        setName("");
        setSource("");
        await fetchCameras();
      } else {
        setMessage({ text: data.detail || "Failed to add camera.", type: "error" });
      }
    } catch (err) {
      console.error(err);
      if (err instanceof Error && err.name === "AbortError") {
        setMessage({ text: "Camera connection timed out. Check source/RTSP URL and try again.", type: "error" });
      } else {
        setMessage({ text: "Connection error. Make sure backend is running.", type: "error" });
      }
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
      setSubmitting(false);
    }
  };

  const handleDeleteCamera = async (id: string) => {
    if (!confirm("Are you sure you want to delete this camera stream?")) return;
    setMessage(null);

    try {
      const res = await fetch(`${apiBaseUrl}/cameras/${id}`, {
        method: "DELETE",
      });
      const data = await res.json();

      if (res.ok) {
        setMessage({ text: "Camera deleted successfully.", type: "success" });
        await fetchCameras();
      } else {
        setMessage({ text: data.detail || "Failed to delete camera.", type: "error" });
      }
    } catch (err) {
      console.error(err);
      setMessage({ text: "Connection error.", type: "error" });
    }
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (canvas.width / rect.width);
    const py = (e.clientY - rect.top) * (canvas.height / rect.height);
    const x = Math.max(0, Math.min(1, px / canvas.width));
    const y = Math.max(0, Math.min(1, py / canvas.height));

    setRoiZones((prev) => {
      const updated = [...prev];
      if (updated.length === 0) return prev; // no zone selected yet
      updated[activeZoneIdx] = {
        ...updated[activeZoneIdx],
        points: [...updated[activeZoneIdx].points, [Number(x.toFixed(6)), Number(y.toFixed(6))]],
      };
      return updated;
    });
  };

  const clearActiveZonePoints = () => {
    setRoiZones((prev) => {
      const updated = [...prev];
      if (updated[activeZoneIdx]) {
        updated[activeZoneIdx] = { ...updated[activeZoneIdx], points: [] };
      }
      return updated;
    });
  };

  const addNewZone = (type: ZoneType) => {
    const labels: Record<ZoneType, string> = {
      merchandise: "Área de Mercadoria",
      forbidden: "Zona Proibida",
      entry: "Entrada / Balcão",
    };
    const newZone: RoiZone = { name: labels[type], zone_type: type, points: [] };
    setRoiZones((prev) => {
      const updated = [...prev, newZone];
      setActiveZoneIdx(updated.length - 1);
      return updated;
    });
  };

  const removeZone = (idx: number) => {
    setRoiZones((prev) => {
      const updated = prev.filter((_, i) => i !== idx);
      setActiveZoneIdx(Math.max(0, Math.min(activeZoneIdx, updated.length - 1)));
      return updated;
    });
  };

  const openRoiModal = (cam: CameraData) => {
    setSelectedCam(cam);
    const canvasWidth = frameResolution.width || ROI_CANVAS_WIDTH;
    const canvasHeight = frameResolution.height || ROI_CANVAS_HEIGHT;

    const mappedZones = (cam.roi_zones || []).map((zone) => ({
      ...zone,
      points: ensureNormalizedPoints(zone.points),
    }));

    const hasUsableZones = mappedZones.some((zone) => {
      if (zone.points.length < 3) return false;
      return zone.points.some((p) => p[0] > 0 || p[1] > 0);
    });

    // Load existing zones; fall back to legacy roi_points as a merchandise zone
    const existingZones: RoiZone[] = hasUsableZones
      ? mappedZones
      : cam.roi_points && cam.roi_points.length >= 3
        ? [{
          name: "Área de Mercadoria",
          zone_type: "merchandise",
          points: ensureNormalizedPoints(cam.roi_points),
        }]
        : [];

    setRoiZones(existingZones);
    setActiveZoneIdx(0);
    setFrameResolution({ width: ROI_CANVAS_WIDTH, height: ROI_CANVAS_HEIGHT });
  };

  const handleSaveRoi = async () => {
    if (!selectedCam) return;
    // Validate at least one complete zone (≥3 points)
    const validZones = roiZones.filter((z) => z.points.length >= 3);
    if (validZones.length === 0) {
      alert("Desenhe pelo menos uma zona com 3 ou mais pontos antes de salvar.");
      return;
    }

    const payloadZones = validZones.map((zone) => ({
      ...zone,
      points: ensureNormalizedPoints(zone.points),
    }));

    try {
      const res = await fetch(`${apiBaseUrl}/cameras/${selectedCam.id}/roi-zones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zones: payloadZones }),
      });
      const data = await res.json();

      if (res.ok && data.status === "success") {
        setMessage({ text: "Zonas de ROI salvas com sucesso!", type: "success" });
        setSelectedCam(null);
        await fetchCameras();
      } else {
        alert(data.detail || "Falha ao salvar zonas.");
      }
    } catch (err) {
      console.error(err);
      alert("Erro de rede ao salvar zonas.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-brand" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto pb-10">
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight mb-2">Camera Setup & Configuration</h2>
            <p className="text-foreground/60">
              Manage dynamic USB index/RTSP streams and define camera-specific Regions of Interest (ROI) interactively.
            </p>
          </div>
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand/15 border border-brand/30 text-brand hover:bg-brand/25 transition-colors text-sm font-semibold flex-shrink-0 shadow-sm"
          >
            <Sliders className="w-4 h-4" />
            Configurar Detecção
          </button>
        </div>
        {detectionConfig && (
          <div className="mt-3 flex items-center gap-2 text-xs text-green-400">
            <CheckCircle className="w-3.5 h-3.5" />
            Configuração de detecção salva
            <button onClick={() => setShowWizard(true)} className="underline hover:no-underline text-green-400/70">Editar</button>
          </div>
        )}
      </header>

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg flex items-center gap-3 border ${message.type === "success"
            ? "bg-green-500/10 border-green-500/30 text-green-400"
            : "bg-danger/10 border-danger/30 text-danger"
            }`}
        >
          {message.type === "success" ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          <span className="text-sm font-medium">{message.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Add Camera Form */}
        <div className="lg:col-span-1">
          <div className="glass-panel p-6 sticky top-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded bg-brand/20 text-brand">
                <Camera className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-semibold">Connect New Camera</h3>
            </div>

            <form onSubmit={handleAddCamera} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">Camera Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Checkout Desk A"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand text-foreground placeholder:text-foreground/30"
                  required
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-medium text-foreground/80">Input Source</label>
                  <span className="text-[10px] text-foreground/45 flex items-center gap-1">
                    <HelpCircle className="w-3 h-3" />
                    Webcam index or RTSP url
                  </span>
                </div>
                <input
                  type="text"
                  value={source}
                  onChange={e => setSource(e.target.value)}
                  placeholder="e.g. 0 or rtsp://username:pwd@ip:port/h264"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand text-foreground placeholder:text-foreground/30"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-4 flex items-center justify-center gap-2 bg-brand hover:bg-brand/90 disabled:opacity-50 text-white py-2 rounded-lg font-medium transition-colors cursor-pointer"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {submitting ? "Connecting stream..." : "Add Camera Stream"}
              </button>
            </form>
          </div>
        </div>

        {/* Cameras List */}
        <div className="lg:col-span-2">
          <div className="glass-panel p-6">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-purple-500/20 text-purple-400">
                  <Plus className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-semibold">Active Camera Feeds</h3>
              </div>
              <button
                onClick={fetchCameras}
                className="p-2 hover:bg-glass border border-glass-border rounded-lg text-foreground/60 hover:text-foreground transition-colors cursor-pointer"
                title="Yenile"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {cameras.length === 0 ? (
              <div className="text-center p-12 text-foreground/40 border border-glass-border border-dashed rounded-lg bg-black/10">
                No active camera streams configured. Use the form to link a local webcam (0) or network RTSP stream.
              </div>
            ) : (
              <div className="space-y-4">
                {cameras.map(cam => (
                  <div
                    key={cam.id}
                    className="glass-panel p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border border-glass-border bg-black/20"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center border ${cam.status === "active"
                          ? "bg-green-500/10 border-green-500/30 text-green-400"
                          : "bg-danger/10 border-danger/30 text-danger"
                          }`}
                      >
                        <Camera className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground flex items-center gap-2">
                          {cam.name}
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${cam.status === "active"
                            ? "bg-green-500/10 border-green-500/20 text-green-400"
                            : "bg-danger/10 border-danger/20 text-danger"
                            }`}>
                            {cam.status === "active" ? "Active" : "Offline / Error"}
                          </span>
                        </h4>
                        <p className="text-xs text-foreground/50 mt-1 font-mono">Source: {cam.source}</p>
                        <p className="text-xs text-brand font-medium mt-1">
                          {(cam.roi_zones && cam.roi_zones.length > 0)
                            ? `✓ ${cam.roi_zones.length} zona(s) ROI configurada(s): ${cam.roi_zones.map(z => z.name).join(", ")}`
                            : cam.roi_points && cam.roi_points.length > 0
                              ? `✓ ROI legado: ${cam.roi_points.length} pontos`
                              : "⚠️ Sem ROI configurado. Tela inteira monitorada."}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-auto">
                      <button
                        onClick={() => openRoiModal(cam)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-brand/20 border border-brand/35 text-brand hover:bg-brand/30 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                      >
                        <Edit className="w-3.5 h-3.5" />
                        Configure ROI
                      </button>
                      <button
                        onClick={() => handleDeleteCamera(cam.id)}
                        className="p-2 text-foreground/50 hover:text-danger hover:bg-danger/10 rounded-lg transition-colors cursor-pointer"
                        title="Delete camera feed"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detection Setup Wizard */}
      {showWizard && (
        <DetectionSetupWizard
          apiBaseUrl={apiBaseUrl}
          onClose={() => setShowWizard(false)}
          onSave={(cfg) => {
            setDetectionConfig(cfg);
            setShowWizard(false);
          }}
          initialConfig={detectionConfig ?? undefined}
        />
      )}

      {/* ROI Drawing Canvas Modal */}
      {selectedCam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md transition-all duration-300">
          <div className="glass-panel w-full max-w-5xl overflow-hidden border border-glass-border shadow-2xl relative">
            {/* Modal Header */}
            <div className="glass-header px-6 py-4 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold text-foreground">Editor de Zonas ROI</h3>
                <p className="text-xs text-foreground/60">{selectedCam.name} ({selectedCam.source})</p>
              </div>
              <button
                onClick={() => setSelectedCam(null)}
                className="p-1.5 hover:bg-white/10 rounded-lg text-foreground/70 hover:text-foreground transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex gap-0 h-[calc(100vh-12rem)] max-h-[680px]">
              {/* Left sidebar: zone list */}
              <div className="w-64 flex-shrink-0 border-r border-white/8 flex flex-col">
                <div className="p-4 border-b border-white/8">
                  <p className="text-xs font-semibold text-foreground/60 uppercase tracking-wider mb-3">Zonas Definidas</p>
                  <div className="space-y-1.5">
                    {([
                      { type: "merchandise" as ZoneType, icon: "🛍️", label: "Área de Mercadoria", colour: "text-orange-400 bg-orange-500/10 border-orange-500/25" },
                      { type: "forbidden" as ZoneType, icon: "🚫", label: "Zona Proibida", colour: "text-red-400 bg-red-500/10 border-red-500/25" },
                      { type: "entry" as ZoneType, icon: "🚪", label: "Entrada / Balcão", colour: "text-green-400 bg-green-500/10 border-green-500/25" },
                    ]).map(({ type, icon, label, colour }) => (
                      <button
                        key={type}
                        onClick={() => addNewZone(type)}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-colors hover:brightness-125 ${colour}`}
                      >
                        <Plus className="w-3.5 h-3.5" />
                        {icon} {label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {roiZones.length === 0 && (
                    <p className="text-xs text-foreground/35 text-center pt-4 leading-relaxed">
                      Clique nos botões acima para adicionar zonas, depois clique no vídeo para desenhar os pontos.
                    </p>
                  )}
                  {roiZones.map((zone, idx) => {
                    const colourMap: Record<ZoneType, string> = {
                      merchandise: "border-orange-500/40 bg-orange-500/8 text-orange-300",
                      forbidden: "border-red-500/40 bg-red-500/8 text-red-300",
                      entry: "border-green-500/40 bg-green-500/8 text-green-300",
                    };
                    const iconMap: Record<ZoneType, string> = {
                      merchandise: "🛍️", forbidden: "🚫", entry: "🚪",
                    };
                    const isActive = idx === activeZoneIdx;
                    return (
                      <button
                        key={idx}
                        onClick={() => setActiveZoneIdx(idx)}
                        className={`w-full text-left rounded-lg border p-3 transition-all ${colourMap[zone.zone_type]} ${isActive ? "ring-2 ring-white/30 brightness-125" : "opacity-70 hover:opacity-100"}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold truncate">
                            {iconMap[zone.zone_type]} {zone.name}
                          </span>
                          <button
                            onClick={(e) => { e.stopPropagation(); removeZone(idx); }}
                            className="p-0.5 hover:text-red-400 text-foreground/40 transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <p className="text-[10px] mt-1 text-foreground/50">
                          {zone.points.length} {zone.points.length === 1 ? "ponto" : "pontos"}
                          {zone.points.length < 3 && zone.points.length > 0 && (
                            <span className="text-amber-400"> · precisa de {3 - zone.points.length} mais</span>
                          )}
                          {zone.points.length === 0 && <span className="text-foreground/35"> · clique no vídeo</span>}
                        </p>
                        {isActive && zone.points.length > 0 && (
                          <button
                            onClick={(e) => { e.stopPropagation(); clearActiveZonePoints(); }}
                            className="mt-1.5 text-[10px] text-foreground/40 hover:text-red-400 transition-colors"
                          >
                            Limpar pontos
                          </button>
                        )}
                        {isActive && (
                          <p className="mt-1 text-[10px] font-semibold text-white/60">✏️ Editando</p>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Legend */}
                <div className="p-3 border-t border-white/8 space-y-1">
                  <p className="text-[10px] text-foreground/40 font-semibold uppercase tracking-wider mb-1">Legenda</p>
                  {[
                    { colour: "bg-orange-400", label: "Mercadoria — ativa scoring" },
                    { colour: "bg-red-400", label: "Proibida — alerta imediato" },
                    { colour: "bg-green-400", label: "Entrada — sem pontuação" },
                  ].map(({ colour, label }) => (
                    <div key={label} className="flex items-center gap-2 text-[10px] text-foreground/50">
                      <span className={`w-2.5 h-2.5 rounded-sm flex-shrink-0 ${colour}`} />
                      {label}
                    </div>
                  ))}
                </div>
              </div>

              {/* Canvas area */}
              <div className="flex-1 flex flex-col min-w-0">
                {roiZones.length > 0 && (
                  <div className="px-4 pt-3 pb-2 border-b border-white/8 flex items-center gap-2 text-xs">
                    <MapPin className="w-3.5 h-3.5 text-brand" />
                    <span>
                      Clique no vídeo para adicionar pontos à zona{" "}
                      <strong className="text-foreground">
                        {roiZones[activeZoneIdx]?.name || "—"}
                      </strong>
                    </span>
                  </div>
                )}
                {roiZones.length === 0 && (
                  <div className="px-4 pt-3 pb-2 border-b border-white/8">
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-brand/8 border border-brand/20 text-brand text-xs">
                      <HelpCircle className="w-3.5 h-3.5 flex-shrink-0" />
                      Adicione uma zona na lateral esquerda, depois clique no vídeo para desenhar o polígono.
                    </div>
                  </div>
                )}
                <div className="flex-1 p-4 flex items-center justify-center bg-black/20">
                  <div className="w-full aspect-video bg-black/60 rounded-lg overflow-hidden border border-glass-border relative">
                    <canvas
                      ref={canvasRef}
                      width={frameResolution.width}
                      height={frameResolution.height}
                      onClick={roiZones.length > 0 ? handleCanvasClick : undefined}
                      className={`w-full h-full object-contain ${roiZones.length > 0 ? "cursor-crosshair" : "cursor-default"}`}
                    />
                  </div>
                </div>
                <div className="px-4 pb-3 text-[10px] text-foreground/35 text-right">
                  {roiZones[activeZoneIdx]
                    ? `Zona ativa: ${roiZones[activeZoneIdx].name} · ${roiZones[activeZoneIdx].points.length} pontos`
                    : "Nenhuma zona selecionada"}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="glass-header border-t border-b-0 px-6 py-4 flex justify-between items-center gap-4">
              <p className="text-xs text-foreground/40">
                {roiZones.filter(z => z.points.length >= 3).length} de {roiZones.length} zona(s) prontas para salvar
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedCam(null)}
                  className="px-4 py-2 border border-glass-border hover:bg-glass rounded-lg text-sm font-semibold transition-colors cursor-pointer text-foreground/80 hover:text-foreground"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSaveRoi}
                  disabled={roiZones.filter(z => z.points.length >= 3).length === 0}
                  className="px-6 py-2 bg-brand hover:bg-brand/90 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-bold transition-colors cursor-pointer"
                >
                  Salvar Zonas ROI
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
