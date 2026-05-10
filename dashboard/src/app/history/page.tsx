"use client";

import { useState, useEffect } from "react";
import { Search, Download, ExternalLink, Calendar, Loader2, Image as ImageIcon } from "lucide-react";

interface AlertHistory {
  id: string;
  message: string;
  timestamp: string;
  image_path: string;
}

export default function HistoryPage() {
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch("http://localhost:8000/history");
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
          <button className="flex items-center gap-2 px-4 py-2 bg-glass border border-glass-border rounded-lg hover:bg-white/5 transition-colors text-sm font-medium">
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
              placeholder="Search by event ID, type, or camera..." 
              className="w-full bg-black/40 border border-glass-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>
          <select className="bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand">
            <option>All Event Types</option>
            <option>Suspicious Behavior</option>
            <option>Blacklisted Face</option>
            <option>Item Concealment</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-black/20 border-b border-glass-border text-sm text-foreground/70">
                <th className="p-4 font-medium">Event ID</th>
                <th className="p-4 font-medium">Date & Time</th>
                <th className="p-4 font-medium">Detection Type</th>
                <th className="p-4 font-medium">Image Path</th>
                <th className="p-4 font-medium text-center">Snapshot</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {loading ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-foreground/60">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading history...
                  </td>
                </tr>
              ) : history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-foreground/60">
                    No alert history found.
                  </td>
                </tr>
              ) : (
                history.map((event) => (
                  <tr key={event.id} className="border-b border-glass-border/50 hover:bg-white/[0.02] transition-colors">
                    <td className="p-4 font-mono text-brand text-xs">{event.id.slice(0, 8)}...</td>
                    <td className="p-4 text-foreground/80">{formatTime(event.timestamp)}</td>
                    <td className="p-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        event.message.includes('THEFT') || event.message.includes('CRIMINAL') ? 'bg-danger/20 text-danger' : 
                        event.message.includes('BLACKLIST') || event.message.includes('RESTRICTED') ? 'bg-orange-500/20 text-orange-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {event.message}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-xs text-foreground/60">{event.image_path}</td>
                    <td className="p-4 text-center">
                      <a href={`http://localhost:8000/${event.image_path}`} target="_blank" rel="noreferrer" className="p-1.5 rounded hover:bg-white/10 text-foreground/70 hover:text-brand transition-colors inline-block">
                        <ImageIcon className="w-4 h-4" />
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {!loading && history.length > 0 && (
          <div className="p-4 border-t border-glass-border flex items-center justify-between text-sm text-foreground/60">
            <div>Showing {history.length} entries</div>
            <div className="flex gap-1">
              <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5 disabled:opacity-50" disabled>Prev</button>
              <button className="px-3 py-1 bg-brand text-white rounded">1</button>
              <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5 disabled:opacity-50" disabled>Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
