"use client";

import { useState, useEffect, useRef } from "react";
import { Camera, Maximize2, AlertTriangle, WifiOff } from "lucide-react";

interface CameraFeed {
  camera_id: string;
  name: string;
  data: string;
}

interface AlertData {
  id: string;
  message: string;
  timestamp: string;
  camera_id: string;
}

interface WsPayload {
  type: string;
  cameras: CameraFeed[];
  alert: AlertData | null;
  audio: string | null;
}

export default function CameraGrid() {
  const [cameras, setCameras] = useState<CameraFeed[]>([]);
  const [alertCam, setAlertCam] = useState<string | null>(null);
  const [alertMessage, setAlertMessage] = useState<string>("");
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const alertTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectInterval: NodeJS.Timeout;

    const connectWebSocket = () => {
      ws = new WebSocket("ws://localhost:8000/ws");
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        try {
          const payload: WsPayload = JSON.parse(event.data);
          if (payload.type === "multi_frame") {
            setCameras(payload.cameras);
            
            if (payload.alert) {
              setAlertCam(payload.alert.camera_id);
              setAlertMessage(payload.alert.message);
              
              if (alertTimeoutRef.current) {
                clearTimeout(alertTimeoutRef.current);
              }
              alertTimeoutRef.current = setTimeout(() => {
                setAlertCam(null);
                setAlertMessage("");
              }, 3000);
            }
          }
        } catch (err) {
          console.error("Error parsing WS data", err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log("WebSocket disconnected. Reconnecting...");
        reconnectInterval = setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (err) => {
        console.error("WebSocket error", err);
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      clearTimeout(reconnectInterval);
      if (alertTimeoutRef.current) clearTimeout(alertTimeoutRef.current);
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="mb-6">
      {!isConnected && (
        <div className="mb-4 p-3 bg-danger/20 border border-danger text-danger rounded flex items-center gap-2 text-sm">
          <WifiOff className="w-5 h-5" />
          <span>Disconnected from Surveillance Server. Make sure the backend is running at localhost:8000. Retrying...</span>
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {cameras.length === 0 && isConnected ? (
          <div className="col-span-1 lg:col-span-2 text-center p-10 text-foreground/50 border border-glass-border border-dashed rounded-lg">
            No active cameras. Please add a camera from the backend.
          </div>
        ) : (
          cameras.map((cam) => {
            const isAlerting = alertCam === cam.camera_id;
            return (
              <div 
                key={cam.camera_id} 
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
                        {alertMessage}
                      </span>
                    )}
                    <button className="p-1 hover:bg-white/10 rounded transition-colors">
                      <Maximize2 className="w-4 h-4 text-white/70" />
                    </button>
                  </div>
                </div>
                
                <div className="aspect-video bg-black/40 relative flex items-center justify-center overflow-hidden">
                  <img 
                    src={`data:image/jpeg;base64,${cam.data}`} 
                    alt={cam.name}
                    className="w-full h-full object-contain"
                  />
                  {isAlerting && (
                    <div className="absolute inset-0 border-4 border-danger/50 z-20 pointer-events-none"></div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
