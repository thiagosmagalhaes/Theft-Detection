"""Camera manager for handling multiple camera streams"""

import json
import os
import uuid
import threading
from .threaded_camera import ThreadedCamera
from ..config import CAMERAS_FILE


class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.lock = threading.Lock()
        self.load_cameras()

    def load_cameras(self):
        """Load cameras from configuration file"""
        if os.path.exists(CAMERAS_FILE):
            try:
                with open(CAMERAS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cam in data:
                        self.add_camera_internal(
                            cam["id"], 
                            cam["source"], 
                            cam["name"], 
                            cam.get("roi_points", [])
                        )
                print(f"Loaded {len(self.cameras)} cameras from cameras.json.")
                return
            except Exception as e:
                print(f"Error loading cameras.json: {e}")

        # Fallback to default webcam if no file exists
        self.add_camera_internal("0", "0", "Kamera 1", [])
        self.save_cameras()

    def save_cameras(self):
        """Save cameras to configuration file (synchronous - call from background thread)"""
        try:
            data = []
            with self.lock:
                for cam_id, cam_data in self.cameras.items():
                    data.append({
                        "id": cam_id,
                        "name": cam_data["name"],
                        "source": cam_data["source"],
                        "roi_points": cam_data.get("roi_points", [])
                    })
            with open(CAMERAS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving cameras.json: {e}")

    def add_camera_internal(self, cam_id, source, name, roi_points):
        """Add camera with specified ID (internal use)"""
        threaded_cap = ThreadedCamera(source)
        self.cameras[cam_id] = {
            "cap": threaded_cap,
            "name": name,
            "source": source,
            "status": "active" if threaded_cap.isOpened() else "error",
            "roi_points": roi_points,
            "heatmap_accumulator": None,
            "roi_entry_times": {},
            "last_alert_time": 0,
            "last_objects": []
        }

    def add_camera(self, source, name):
        """Add a new camera with auto-generated ID"""
        cam_id = str(uuid.uuid4())
        threaded_cap = ThreadedCamera(source)
        if threaded_cap.isOpened():
            with self.lock:
                self.cameras[cam_id] = {
                    "cap": threaded_cap,
                    "name": name,
                    "source": source,
                    "status": "active",
                    "roi_points": [],
                    "heatmap_accumulator": None,
                    "roi_entry_times": {},
                    "last_alert_time": 0,
                    "last_objects": []
                }
            self.save_cameras()
            print(f"Kamera eklendi: {name} ({source}) ID: {cam_id}")
            return {"id": cam_id, "status": "connected"}
        else:
            print(f"Kamera açılamadı: {source}")
            return {"id": None, "status": "failed"}

    def remove_camera(self, cam_id):
        """Remove a camera by ID"""
        with self.lock:
            if cam_id in self.cameras:
                self.cameras[cam_id]["cap"].release()
                del self.cameras[cam_id]
                status = True
            else:
                status = False
        if status:
            self.save_cameras()
        return status

    def get_active_cameras(self):
        """Get list of all active cameras"""
        with self.lock:
            return [{
                "id": k, 
                "name": v["name"], 
                "source": v["source"], 
                "status": "active" if v["cap"].isOpened() else "error",
                "roi_points": v.get("roi_points", [])
            } for k, v in self.cameras.items()]
