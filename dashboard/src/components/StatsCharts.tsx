"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

const weeklyData = [
  { name: "Mon", thefts: 4, falseAlarms: 1 },
  { name: "Tue", thefts: 2, falseAlarms: 0 },
  { name: "Wed", thefts: 5, falseAlarms: 2 },
  { name: "Thu", thefts: 3, falseAlarms: 1 },
  { name: "Fri", thefts: 8, falseAlarms: 3 },
  { name: "Sat", thefts: 12, falseAlarms: 4 },
  { name: "Sun", thefts: 9, falseAlarms: 2 },
];

const hourlyData = Array.from({ length: 24 }).map((_, i) => ({
  time: `${i}:00`,
  alerts: Math.floor(Math.random() * 5) + (i > 12 && i < 20 ? 5 : 0),
}));

export default function StatsCharts() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Weekly Stats */}
      <div className="glass-panel p-5">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          Weekly Security Events
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={weeklyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
              <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip 
                cursor={{ fill: "rgba(255,255,255,0.05)" }}
                contentStyle={{ backgroundColor: "rgba(15, 17, 26, 0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
              />
              <Bar dataKey="thefts" fill="#ef4444" radius={[4, 4, 0, 0]} name="Suspicious Activity" />
              <Bar dataKey="falseAlarms" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Reviewed/Cleared" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Hourly Trend */}
      <div className="glass-panel p-5">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          Today's Alert Trend
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
              <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} interval={3} />
              <YAxis stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: "rgba(15, 17, 26, 0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
              />
              <Line type="monotone" dataKey="alerts" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6, fill: "#3b82f6" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
