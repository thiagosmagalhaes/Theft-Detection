"""Object detector abstraction supporting YOLO and RF-DETR backends."""

from dataclasses import dataclass
from typing import Dict, List

import cv2
import numpy as np
from ultralytics import YOLO

from ..config import (
    YOLO_OBJ_MODEL,
    YOLO_SPECIALIZED_MODEL,
    OBJECT_DETECTION_CONFIDENCE,
    OBJECT_DETECTOR_BACKEND,
    RF_DETR_MODEL_ID,
)


@dataclass
class ObjectDetection:
    box: List[int]
    class_id: int
    class_name: str
    confidence: float


class YoloObjectDetector:
    """YOLO object detector with optional specialized shoplifting model."""

    backend_name = "yolo"

    def __init__(self):
        self.model = None
        self.is_specialized = False

        try:
            self.model = YOLO(YOLO_SPECIALIZED_MODEL)
            self.is_specialized = True
            print(f"Specialized YOLO model loaded ({YOLO_SPECIALIZED_MODEL}).")
        except Exception:
            print(f"Specialized model not found ({YOLO_SPECIALIZED_MODEL}). Falling back to {YOLO_OBJ_MODEL}.")
            self.model = YOLO(YOLO_OBJ_MODEL)
            self.is_specialized = False

        names = getattr(self.model, "names", {}) or {}
        self.class_names: Dict[int, str] = {int(k): str(v) for k, v in names.items()}

    def predict(self, frame: np.ndarray) -> List[ObjectDetection]:
        results = self.model(frame, verbose=False, conf=OBJECT_DETECTION_CONFIDENCE)
        detections: List[ObjectDetection] = []

        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        clss = boxes.cls.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()

        for box, class_id, conf in zip(xyxy, clss, confs):
            detections.append(
                ObjectDetection(
                    box=[int(box[0]), int(box[1]), int(box[2]), int(box[3])],
                    class_id=int(class_id),
                    class_name=self.class_names.get(int(class_id), str(class_id)),
                    confidence=float(conf),
                )
            )

        return detections


class RFDetrObjectDetector:
    """RF-DETR detector using Hugging Face transformers."""

    backend_name = "rf-detr"
    is_specialized = False

    def __init__(self):
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
        except Exception as exc:
            raise RuntimeError(
                "RF-DETR backend requires torch and transformers. Install them first."
            ) from exc

        self.torch = torch
        self.processor = AutoImageProcessor.from_pretrained(RF_DETR_MODEL_ID)
        self.model = AutoModelForObjectDetection.from_pretrained(RF_DETR_MODEL_ID)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

        names = getattr(self.model.config, "id2label", {}) or {}
        self.class_names: Dict[int, str] = {int(k): str(v) for k, v in names.items()}

        print(f"RF-DETR model loaded: {RF_DETR_MODEL_ID} on {self.device}")

    def predict(self, frame: np.ndarray) -> List[ObjectDetection]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = self.processor(images=rgb, return_tensors="pt").to(self.device)

        with self.torch.no_grad():
            outputs = self.model(**inputs)

        h, w = frame.shape[:2]
        target_sizes = self.torch.tensor([(h, w)], device=self.device)
        processed = self.processor.post_process_object_detection(
            outputs,
            threshold=OBJECT_DETECTION_CONFIDENCE,
            target_sizes=target_sizes,
        )[0]

        boxes = processed["boxes"].detach().cpu().numpy().astype(int)
        scores = processed["scores"].detach().cpu().numpy()
        labels = processed["labels"].detach().cpu().numpy().astype(int)

        detections: List[ObjectDetection] = []
        for box, class_id, score in zip(boxes, labels, scores):
            detections.append(
                ObjectDetection(
                    box=[int(box[0]), int(box[1]), int(box[2]), int(box[3])],
                    class_id=int(class_id),
                    class_name=self.class_names.get(int(class_id), str(class_id)),
                    confidence=float(score),
                )
            )

        return detections


def load_object_detector():
    """Create object detector from configuration with safe fallback to YOLO."""
    backend = OBJECT_DETECTOR_BACKEND

    if backend in {"rf-detr", "rfdetr"}:
        try:
            return RFDetrObjectDetector()
        except Exception as exc:
            print(f"RF-DETR load failed: {exc}. Falling back to YOLO.")
            return YoloObjectDetector()

    return YoloObjectDetector()
