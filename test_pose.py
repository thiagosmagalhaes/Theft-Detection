from ultralytics import YOLO
from backend.config import YOLO_POSE_MODEL
try:
    print("Loading model...")
    model = YOLO(YOLO_POSE_MODEL)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error: {e}")
