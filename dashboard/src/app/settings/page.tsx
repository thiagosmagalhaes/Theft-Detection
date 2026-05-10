import { Save, Bell, Mail, Send } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto pb-10">
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight mb-2">Notification Settings</h2>
        <p className="text-foreground/60">Configure how and where you receive security alerts.</p>
      </header>

      <div className="space-y-6">
        {/* Telegram Settings */}
        <div className="glass-panel p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded bg-blue-500/20 text-blue-400">
              <Send className="w-5 h-5" />
            </div>
            <h3 className="text-xl font-semibold">Telegram Integration</h3>
          </div>
          <p className="text-sm text-foreground/60 mb-6">
            Receive instant photo and caption alerts directly to your Telegram app.
          </p>

          <form className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">Bot Token</label>
                <input 
                  type="password" 
                  defaultValue="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">Chat ID</label>
                <input 
                  type="text" 
                  defaultValue="-100123456789"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <input type="checkbox" id="enable-telegram" className="rounded bg-black/40 border-glass-border text-brand" defaultChecked />
              <label htmlFor="enable-telegram" className="text-sm text-foreground/80">Enable Telegram Alerts</label>
            </div>
          </form>
        </div>

        {/* Email Settings */}
        <div className="glass-panel p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded bg-purple-500/20 text-purple-400">
              <Mail className="w-5 h-5" />
            </div>
            <h3 className="text-xl font-semibold">Email (SMTP) Settings</h3>
          </div>
          <p className="text-sm text-foreground/60 mb-6">
            Receive detailed text alerts and reports via email.
          </p>

          <form className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">SMTP Server</label>
                <input 
                  type="text" 
                  defaultValue="smtp.gmail.com"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">Port</label>
                <input 
                  type="number" 
                  defaultValue={465}
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">Sender Email</label>
                <input 
                  type="email" 
                  defaultValue="security@theftguard.com"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground/80">Password / App Password</label>
                <input 
                  type="password" 
                  defaultValue="********"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <label className="text-sm font-medium text-foreground/80">Recipient Email(s)</label>
                <input 
                  type="text" 
                  defaultValue="admin@company.com, manager@company.com"
                  className="w-full bg-black/40 border border-glass-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" 
                />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <input type="checkbox" id="enable-email" className="rounded bg-black/40 border-glass-border text-brand" />
              <label htmlFor="enable-email" className="text-sm text-foreground/80">Enable Email Alerts</label>
            </div>
          </form>
        </div>

        {/* Global Alert Settings */}
        <div className="glass-panel p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded bg-danger/20 text-danger">
              <Bell className="w-5 h-5" />
            </div>
            <h3 className="text-xl font-semibold">Detection Thresholds</h3>
          </div>
          
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-foreground/80">Minimum Confidence Score</label>
                <span className="text-sm text-brand">75%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="75" className="w-full accent-brand" />
              <p className="text-xs text-foreground/50 mt-1">Only trigger alerts if AI confidence is above this level.</p>
            </div>
            
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-foreground/80">Alert Cooldown (seconds)</label>
                <span className="text-sm text-brand">30s</span>
              </div>
              <input type="range" min="0" max="120" defaultValue="30" className="w-full accent-brand" />
              <p className="text-xs text-foreground/50 mt-1">Time to wait before sending another alert for the same camera.</p>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button className="flex items-center gap-2 bg-brand hover:bg-brand/90 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
