import { Search, Download, ExternalLink, Calendar } from "lucide-react";

export default function HistoryPage() {
  const mockHistory = [
    { id: "EVT-892", date: "2026-05-10 14:23:41", camera: "Electronics Aisle", type: "Suspicious Behavior", confidence: "92%", status: "Unresolved" },
    { id: "EVT-891", date: "2026-05-10 12:15:02", camera: "Main Entrance", type: "Blacklisted Face", confidence: "98%", status: "Resolved" },
    { id: "EVT-890", date: "2026-05-10 10:45:11", camera: "Checkout 1", type: "Item Concealment", confidence: "87%", status: "Resolved" },
    { id: "EVT-889", date: "2026-05-09 18:30:22", camera: "Back Storage", type: "Unauthorized Access", confidence: "95%", status: "Resolved" },
    { id: "EVT-888", date: "2026-05-09 15:10:05", camera: "Electronics Aisle", type: "Suspicious Behavior", confidence: "81%", status: "False Alarm" },
    { id: "EVT-887", date: "2026-05-08 09:22:14", camera: "Main Entrance", type: "VIP Detection", confidence: "99%", status: "Info" },
  ];

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
                <th className="p-4 font-medium">Camera Source</th>
                <th className="p-4 font-medium">Detection Type</th>
                <th className="p-4 font-medium">AI Confidence</th>
                <th className="p-4 font-medium">Status</th>
                <th className="p-4 font-medium text-center">Snapshot</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {mockHistory.map((event) => (
                <tr key={event.id} className="border-b border-glass-border/50 hover:bg-white/[0.02] transition-colors">
                  <td className="p-4 font-mono text-brand">{event.id}</td>
                  <td className="p-4 text-foreground/80">{event.date}</td>
                  <td className="p-4">{event.camera}</td>
                  <td className="p-4">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      event.type === 'Suspicious Behavior' || event.type === 'Item Concealment' ? 'bg-danger/20 text-danger' : 
                      event.type === 'Blacklisted Face' || event.type === 'Unauthorized Access' ? 'bg-orange-500/20 text-orange-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      {event.type}
                    </span>
                  </td>
                  <td className="p-4 font-medium">{event.confidence}</td>
                  <td className="p-4">
                    <span className={`flex items-center gap-1.5 ${
                      event.status === 'Unresolved' ? 'text-danger' :
                      event.status === 'Resolved' ? 'text-green-400' :
                      'text-foreground/50'
                    }`}>
                      <span className={`w-2 h-2 rounded-full ${
                        event.status === 'Unresolved' ? 'bg-danger animate-pulse' :
                        event.status === 'Resolved' ? 'bg-green-400' :
                        'bg-foreground/50'
                      }`}></span>
                      {event.status}
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    <button className="p-1.5 rounded hover:bg-white/10 text-foreground/70 hover:text-foreground transition-colors inline-block">
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="p-4 border-t border-glass-border flex items-center justify-between text-sm text-foreground/60">
          <div>Showing 1 to 6 of 248 entries</div>
          <div className="flex gap-1">
            <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5 disabled:opacity-50">Prev</button>
            <button className="px-3 py-1 bg-brand text-white rounded">1</button>
            <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5">2</button>
            <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5">3</button>
            <span className="px-2 py-1">...</span>
            <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5">42</button>
            <button className="px-3 py-1 border border-glass-border rounded hover:bg-white/5">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
