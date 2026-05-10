import CameraGrid from "@/components/CameraGrid";
import StatsCharts from "@/components/StatsCharts";
import { Activity, Camera, ShieldAlert, Users } from "lucide-react";

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto pb-10">
      <header className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2">Dashboard Overview</h2>
          <p className="text-foreground/60">Live surveillance feeds and system analytics.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-danger"></span>
          </span>
          <span className="text-sm font-medium text-danger">Monitoring Active</span>
        </div>
      </header>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Active Cameras", value: "4/4", icon: Camera, color: "text-blue-400" },
          { label: "Today's Alerts", value: "14", icon: ShieldAlert, color: "text-danger" },
          { label: "Faces Tracked", value: "1,204", icon: Users, color: "text-purple-400" },
          { label: "System Load", value: "42%", icon: Activity, color: "text-green-400" },
        ].map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="glass-panel p-4 flex items-center gap-4">
              <div className={`p-3 rounded-lg bg-black/20 ${stat.color}`}>
                <Icon className="w-6 h-6" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-sm text-foreground/60">{stat.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      <h3 className="text-xl font-semibold mb-4">Live Feeds</h3>
      <CameraGrid />
      
      <div className="mt-8">
        <StatsCharts />
      </div>
    </div>
  );
}
