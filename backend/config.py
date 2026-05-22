"""Configuration and constants for the application"""

import os
import json
from dotenv import load_dotenv
from .models.settings import SettingsModel

# Load environment variables
load_dotenv()

# Files
SETTINGS_FILE = "settings.json"
DB_NAME = "theft_detection.db"
CAMERAS_FILE = "cameras.json"

# Detection thresholds
LOITERING_THRESHOLD = 5.0
ALERT_COOLDOWN = 3.0
AUTO_REGISTER_DELAY = 3.0
MIN_BOX_SIZE = 80
MIN_VISIBLE_KEYPOINTS = 5

# YOLO model files
YOLO_POSE_MODEL = 'yolov8n-pose.pt'
YOLO_OBJ_MODEL = 'yolov8n.pt'
YOLO_SPECIALIZED_MODEL = 'shoplifting.pt'

# Target classes for stealable items (COCO dataset)
TARGET_CLASSES = [24, 25, 26, 28, 39, 40, 41, 42, 43, 67, 73, 74, 75, 76, 77, 78, 79]

# Optional dependencies
try:
    import insightface
    FACE_REC_AVAILABLE = True
    print("InsightFace loaded successfully.")
except ImportError:
    FACE_REC_AVAILABLE = False
    print("InsightFace not installed. Face recognition disabled.")

# Allow disabling face recognition and face saving via environment variable
# Set FACE_RECOGNITION_ENABLED=false in .env to disable without uninstalling InsightFace
_face_rec_env = os.getenv("FACE_RECOGNITION_ENABLED", "true").strip().lower()
if _face_rec_env in ("false", "0", "no", "off"):
    FACE_REC_AVAILABLE = False
    print("Face recognition disabled via FACE_RECOGNITION_ENABLED env flag.")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil not installed. System resource monitor will run in simulation mode.")

# Create necessary directories
if not os.path.exists("alerts"):
    os.makedirs("alerts")
if not os.path.exists("faces"):
    os.makedirs("faces")

# Load settings
current_settings = SettingsModel()
roi_points = []

try:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings_data = json.load(f)
            current_settings = SettingsModel(**settings_data)
            roi_points = current_settings.roiPoints
except Exception as e:
    print(f"Error loading settings: {e}")
    current_settings = SettingsModel()
