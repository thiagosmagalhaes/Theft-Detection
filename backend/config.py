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
OBJECT_DETECTION_INTERVAL = 3
OBJECT_DETECTION_CONFIDENCE = 0.25
OBJECT_DETECTOR_BACKEND = os.getenv("OBJECT_DETECTOR_BACKEND", "yolo").strip().lower()
RF_DETR_MODEL_ID = os.getenv("RF_DETR_MODEL_ID", "Roboflow/rf-detr-base")

# YOLO model files (configurable via .env)
YOLO_POSE_MODEL = os.getenv("YOLO_POSE_MODEL", "yolo26x-pose.pt").strip()
YOLO_OBJ_MODEL = os.getenv("YOLO_OBJ_MODEL", "yolo26x.pt").strip()
YOLO_SPECIALIZED_MODEL = os.getenv("YOLO_SPECIALIZED_MODEL", "shoplifting.pt").strip()

# Target classes for likely retail items/bags (COCO dataset)
TARGET_CLASSES = [
    24, 25, 26, 28,             # backpack, umbrella, handbag, suitcase
    39, 40, 41, 42, 43, 44, 45, # bottle, wine glass, cup, fork, knife, spoon, bowl
    46, 47, 48, 49, 50, 51, 52, 53, 54, 55, # food items
    56, 57, 58, 59, 60,         # chair, couch, potted plant, bed, dining table
    62, 63, 64, 66, 67,         # tv, laptop, mouse, keyboard, cell phone
    73, 74, 75, 76, 77, 78, 79  # book, clock, vase, scissors, teddy bear, hair drier, toothbrush
]

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
