"use client";

import { useState, useEffect } from "react";
import { Camera, Maximize2, AlertTriangle } from "lucide-react";

export default function CameraGrid() {
  const [alertCam, setAlertCam] = useState<number | null>(null);

  // Mock an alert every few seconds for demonstration
  useEffect(() => {
    const interval = setInterval(() => {
      setAlertCam(Math.floor(Math.random() * 4) + 1);
      setTimeout(() => setAlertCam(null), 3000);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const cameras = [
    { id: 1, name: "Main Entrance", status: "Active" },
    { id: 2, name: "Electronics Aisle", status: "Active" },
    { id: 3, name: "Checkout 1", status: "Active" },
    { id: 4, name: "Back Storage", status: "Active" },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
      {cameras.map((cam) => {
        const isAlerting = alertCam === cam.id;
        return (
          <div 
            key={cam.id} 
            className={`glass-panel overflow-hidden relative group transition-all duration-300 ${
              isAlerting ? "alert-pulse ring-2 ring-danger" : ""
            }`}
          >
            <div className="absolute top-0 left-0 right-0 glass-header p-2 flex justify-between items-center z-10">
              <div className="flex items-center gap-2">
                <Camera className={`w-4 h-4 ${isAlerting ? "text-danger" : "text-brand"}`} />
                <span className="text-sm font-semibold">{cam.name}</span>
              </div>
              <div className="flex gap-2">
                {isAlerting && (
                  <span className="flex items-center gap-1 text-xs text-danger font-bold animate-pulse bg-danger/20 px-2 rounded">
                    <AlertTriangle className="w-3 h-3" />
                    SUSPICIOUS BEHAVIOR
                  </span>
                )}
                <button className="p-1 hover:bg-white/10 rounded transition-colors">
                  <Maximize2 className="w-4 h-4 text-white/70" />
                </button>
              </div>
            </div>
            
            {/* Mock Camera Feed Background */}
            <div className="aspect-video bg-black/40 relative flex items-center justify-center overflow-hidden">
              <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=1000')] bg-cover bg-center opacity-40 mix-blend-luminosity filter grayscale"></div>
              {/* Overlay grid lines for tech effect */}
              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:20px_20px]"></div>
              
              {isAlerting && (
                <div className="absolute inset-0 border-4 border-danger/50 z-20 pointer-events-none"></div>
              )}
              
              <div className="text-white/20 text-sm font-mono tracking-widest z-10">
                CAM_0{cam.id}_LIVE_FEED
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
