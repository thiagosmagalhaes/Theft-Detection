"""
Theft Detection System - Main Application Entry Point
Reorganized modular version
"""

import asyncio
import json
import threading
import importlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import modules
from backend.database import init_db
from backend.api import (
    settings_router,
    cameras_router,
    faces_router,
    history_router,
    stats_router
)
from backend.api.persons import router as persons_router
video_runtime = importlib.import_module("backend.video.video_loop")

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/alerts", StaticFiles(directory="alerts"), name="alerts")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Include API routers
app.include_router(settings_router, tags=["settings"])
app.include_router(cameras_router, tags=["cameras"])
app.include_router(faces_router, tags=["faces"])
app.include_router(history_router, tags=["history"])
app.include_router(stats_router, tags=["stats"])
app.include_router(persons_router, tags=["persons"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time video streaming"""
    await websocket.accept()
    print("Client connected")
    try:
        while True:
            # Send latest frame
            message_to_send = None
            with video_runtime.lock:
                if video_runtime.latest_frame:
                    message_to_send = json.dumps(video_runtime.latest_frame)
            
            if message_to_send:
                await websocket.send_text(message_to_send)

            await asyncio.sleep(0.04) 
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")


@app.on_event("startup")
def startup_event():
    """Start video processing loop on application startup"""
    t = threading.Thread(target=video_runtime.video_loop, daemon=True)
    t.start()
    print("✓ Theft Detection System Started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
