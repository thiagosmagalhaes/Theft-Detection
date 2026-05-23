import cv2
from ultralytics import YOLO
import numpy as np
from backend.config import YOLO_OBJ_MODEL

try:
    print("OpenCV imported.")
    print("Loading YOLO model...")
    model = YOLO(YOLO_OBJ_MODEL)
    print("Model loaded.")
    
    # Create dummy image
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    
    print("Running prediction...")
    results = model.predict(img, verbose=False)
    print("Prediction successful.")
    print("SETUP_SUCCESS")
except Exception as e:
    print(f"SETUP_FAILED: {e}")
