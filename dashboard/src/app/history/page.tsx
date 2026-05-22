"use client";

import { useState, useEffect } from "react";
import {
  Search,
  Download,
  Calendar,
  Loader2,
  Image as ImageIcon,
  Video,
  ZoomIn,
  ZoomOut,
  X,
} from "lucide-react";

interface AlertHistory {
  id: string;
  message: string;
  timestamp: string;
  image_path: string;
  video_path?: string | null;
}

type MediaPreview = {
  type: "image" | "video";
  title: string;
  url: string;
};

export default function HistoryPage() {
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState("All Event Types");
  const [preview, setPreview] = useState<MediaPreview | null>(null);
  const [zoom, setZoom] = useState(1);
  const [videoPlaybackError, setVideoPlaybackError] = useState(false);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const buildMediaUrl = (path?: string | null) => {
    if (!path) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    return `${apiBaseUrl}/${path}`;
  };

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/history`);
        if (response.ok) {
          const data = await response.json();
          setHistory(data);
        }
      } catch (err) {
        console.error("Failed to fetch history:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const formatTime = (ts: string) => {
    if (!ts || ts.length !== 15) return ts;
    const year = ts.slice(0, 4);
    const month = ts.slice(4, 6);
    const day = ts.slice(6, 8);
    const hour = ts.slice(9, 11);
    const min = ts.slice(11, 13);
    const sec = ts.slice(13, 15);
    return `${year}-${month}-${day} ${hour}:${min}:${sec}`;
  };

  // Advanced client-side filtering matching logic
  const filteredHistory = history.filter((event) => {
    const matchesSearch = 
      event.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      event.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      event.image_path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (event.video_path || "").toLowerCase().includes(searchQuery.toLowerCase());

    let matchesType = true;
    if (selectedType === "Suspicious Behavior") {
      matchesType = event.message.includes("SUSPICION") || event.message.includes("RESTRICTED") || event.message.includes("CRIMINAL");
    } else if (selectedType === "Blacklisted Face") {
      matchesType = event.message.includes("BLACKLIST");
    } else if (selectedType === "Item Concealment") {
      matchesType = event.message.includes("THEFT") || event.message.includes("Concealed");
    }

    return matchesSearch && matchesType;
  });

  // Client-side CSV export trigger
  const handleExportCSV = () => {
    if (filteredHistory.length === 0) return;
    const headers = ["Event ID", "Timestamp", "Alert Message", "Image Path", "Video Path"];
    const rows = filteredHistory.map(event => [
      event.id,
      formatTime(event.timestamp),
      event.message,
      event.image_path,
      event.video_path || ""
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8,\uFEFF" 
      + [headers.join(","), ...rows.map(r => r.map(val => `"${val.replace(/"/g, '""')}"`).join(","))].join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `TheftGuard_Alarmlar_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="max-w-6xl mx-auto pb-10">
      <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2">Alert History</h2>
          <p className="text-foreground/60">Review past security events and export evidence.</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-glass border border-glass-border rounded-lg hover:bg-white/5 transition-colors text-sm font-medium">
            <Calendar className="w-4 h-4" />
            Last 7 Days
          </button>
          <button 
            onClick={handleExportCSV}
            disabled={filteredHistory.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-brand/20 border border-brand/35 hover:bg-brand/30 text-brand rounded-lg transition-colors text-sm font-bold cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </header>

      <div className="glass-panel overflow-hidden">
        <div className="p-4 border-b border-glass-border flex gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50" />
            <input 
              type="text" 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by event ID, type, or camera..." 
              className="w-full bg-black/40 border border-glass-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>
          <select 
            value={selectedType}
            onChange={e => setSelectedType(e.target.value)}
            className="bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand text-foreground"
          >
            <option className="bg-[#0f111a]">All Event Types</option>
            <option className="bg-[#0f111a]">Suspicious Behavior</option>
            <option className="bg-[#0f111a]">Blacklisted Face</option>
            <option className="bg-[#0f111a]">Item Concealment</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-black/20 border-b border-glass-border text-sm text-foreground/70">
                <th className="p-4 font-medium">Event ID</th>
                <th className="p-4 font-medium">Date & Time</th>
                <th className="p-4 font-medium">Detection Type</th>
                <th className="p-4 font-medium">Evidence</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {loading ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-foreground/60">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading history...
                  </td>
                </tr>
              ) : filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-foreground/60">
                    No alert history found matching search criteria.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((event) => (
                  <tr key={event.id} className="border-b border-glass-border/50 hover:bg-white/[0.02] transition-colors">
                    <td className="p-4 font-mono text-brand text-xs">{event.id.slice(0, 8)}...</td>
                    <td className="p-4 text-foreground/80">{formatTime(event.timestamp)}</td>
                    <td className="p-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                        event.message.includes('THEFT') || event.message.includes('CRIMINAL') ? 'bg-danger/20 text-danger border border-danger/20' : 
                        event.message.includes('BLACKLIST') || event.message.includes('RESTRICTED') ? 'bg-orange-500/20 text-orange-400 border border-orange-500/20' :
                        'bg-blue-500/20 text-blue-400 border border-blue-500/20'
                      }`}>
                        {event.message}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-col gap-3 min-w-[330px]">
                        <div>
                          <div className="text-[11px] uppercase tracking-wide text-foreground/50 mb-1">Image</div>
                          <div className="flex items-start gap-2">
                            <button
                              onClick={() => {
                                setZoom(1);
                                setVideoPlaybackError(false);
                                setPreview({
                                  type: "image",
                                  title: `Image - ${event.id.slice(0, 8)}`,
                                  url: buildMediaUrl(event.image_path),
                                });
                              }}
                              className="group relative overflow-hidden rounded border border-glass-border bg-black/30 w-[110px] h-[68px]"
                            >
                              <img
                                src={buildMediaUrl(event.image_path)}
                                alt={`Snapshot ${event.id}`}
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                              />
                            </button>
                            <div className="flex gap-1">
                              <button
                                onClick={() => {
                                  setZoom(1);
                                  setVideoPlaybackError(false);
                                  setPreview({
                                    type: "image",
                                    title: `Image - ${event.id.slice(0, 8)}`,
                                    url: buildMediaUrl(event.image_path),
                                  });
                                }}
                                className="p-1.5 rounded hover:bg-white/10 text-foreground/70 hover:text-brand transition-colors"
                                title="Open image"
                              >
                                <ImageIcon className="w-4 h-4" />
                              </button>
                              <a
                                href={buildMediaUrl(event.image_path)}
                                target="_blank"
                                rel="noreferrer"
                                download
                                className="p-1.5 rounded hover:bg-white/10 text-foreground/70 hover:text-brand transition-colors"
                                title="Download image"
                              >
                                <Download className="w-4 h-4" />
                              </a>
                            </div>
                          </div>
                        </div>

                        <div>
                          <div className="text-[11px] uppercase tracking-wide text-foreground/50 mb-1">Video</div>
                          {event.video_path ? (
                            <div className="flex items-start gap-2">
                              <button
                                onClick={() => {
                                  setZoom(1);
                                  setVideoPlaybackError(false);
                                  setPreview({
                                    type: "video",
                                    title: `Video - ${event.id.slice(0, 8)}`,
                                    url: buildMediaUrl(event.video_path),
                                  });
                                }}
                                className="group relative overflow-hidden rounded border border-glass-border bg-black/30 w-[110px] h-[68px] flex items-center justify-center"
                              >
                                <Video className="w-6 h-6 text-foreground/70 group-hover:text-brand transition-colors" />
                              </button>
                              <div className="flex gap-1">
                                <button
                                  onClick={() => {
                                    setZoom(1);
                                    setVideoPlaybackError(false);
                                    setPreview({
                                      type: "video",
                                      title: `Video - ${event.id.slice(0, 8)}`,
                                      url: buildMediaUrl(event.video_path),
                                    });
                                  }}
                                  className="p-1.5 rounded hover:bg-white/10 text-foreground/70 hover:text-brand transition-colors"
                                  title="Open video"
                                >
                                  <Video className="w-4 h-4" />
                                </button>
                                <a
                                  href={buildMediaUrl(event.video_path)}
                                  target="_blank"
                                  rel="noreferrer"
                                  download
                                  className="p-1.5 rounded hover:bg-white/10 text-foreground/70 hover:text-brand transition-colors"
                                  title="Download video"
                                >
                                  <Download className="w-4 h-4" />
                                </a>
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-foreground/50">No video for this event</span>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {!loading && filteredHistory.length > 0 && (
          <div className="p-4 border-t border-glass-border flex items-center justify-between text-sm text-foreground/60">
            <div>Showing {filteredHistory.length} of {history.length} entries</div>
            <div className="flex gap-1">
              <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5 disabled:opacity-50" disabled>Prev</button>
              <button className="px-3 py-1 bg-brand text-white rounded font-bold">1</button>
              <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5 disabled:opacity-50" disabled>Next</button>
            </div>
          </div>
        )}
      </div>

      {preview && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setPreview(null)}
        >
          <div
            className="w-full max-w-6xl max-h-[92vh] glass-panel overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-3 border-b border-glass-border bg-black/30">
              <div className="text-sm font-semibold text-foreground/90">{preview.title}</div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setZoom((z) => Math.min(3, Number((z + 0.25).toFixed(2))))}
                  className="p-2 rounded hover:bg-white/10 text-foreground/70 hover:text-brand"
                  title="Zoom in"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setZoom((z) => Math.max(0.5, Number((z - 0.25).toFixed(2))))}
                  className="p-2 rounded hover:bg-white/10 text-foreground/70 hover:text-brand"
                  title="Zoom out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <a
                  href={preview.url}
                  target="_blank"
                  rel="noreferrer"
                  download
                  className="p-2 rounded hover:bg-white/10 text-foreground/70 hover:text-brand"
                  title="Download file"
                >
                  <Download className="w-4 h-4" />
                </a>
                <button
                  onClick={() => setPreview(null)}
                  className="p-2 rounded hover:bg-white/10 text-foreground/70 hover:text-danger"
                  title="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="p-4 overflow-auto max-h-[80vh] bg-black/20">
              <div
                className="w-full flex items-center justify-center origin-center"
                style={{ transform: `scale(${zoom})`, transformOrigin: "center center" }}
              >
                {preview.type === "image" ? (
                  <img
                    src={preview.url}
                    alt={preview.title}
                    className="max-w-full max-h-[72vh] object-contain rounded border border-glass-border"
                  />
                ) : (
                  <div className="w-full flex flex-col items-center gap-3">
                    <video
                      controls
                      className="max-w-full max-h-[72vh] rounded border border-glass-border bg-black"
                      onError={() => setVideoPlaybackError(true)}
                    >
                      <source src={preview.url} type="video/mp4" />
                      Your browser does not support video playback.
                    </video>
                    {videoPlaybackError && (
                      <div className="text-xs text-orange-300 bg-orange-500/10 border border-orange-500/30 rounded px-3 py-2">
                        Browser could not decode this video codec. Download the file to view locally.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
