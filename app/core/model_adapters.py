"""
统一模型适配层
ClassificationAdapter  - 分类模型统一接口
DetectionAdapter       - 检测模型统一接口
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import time
import os

MODELS_DIR = Path(__file__).resolve().parents[2] / "app" / "models"


class ClassificationAdapter:
    def __init__(self, model_path: str, model_id: str = "best_cls"):
        self.model_path = model_path
        self.model_id = model_id
        self._model = None
        self._runtime = os.environ.get("MODEL_RUNTIME", "ultralytics")
        self._input_size = 224
        self._classes = ["brown_spot", "healthy", "leaf_blast", "neck_blast"]

    def load(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path, task="classify")
        except ImportError:
            self._model = None

    def predict_image(self, image_path: str) -> dict:
        self.load()
        if self._model is None:
            return {"error": "Model not loaded", "model_id": self.model_id}
        t0 = time.time()
        results = self._model.predict(image_path, imgsz=self._input_size, verbose=False)
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        r = results[0]
        top1 = int(r.probs.top1)
        top1conf = float(r.probs.top1conf)
        top5 = []
        if hasattr(r.probs, 'top5'):
            for i, idx in enumerate(r.probs.top5):
                top5.append({
                    "class_id": int(idx),
                    "class_name": self._classes[int(idx)] if int(idx) < len(self._classes) else str(idx),
                    "confidence": round(float(r.probs.top5conf[i]), 4),
                })
        return {
            "model_id": self.model_id,
            "task_type": "classification",
            "top1_class_id": top1,
            "top1_class_name": self._classes[top1] if top1 < len(self._classes) else str(top1),
            "top1_confidence": round(top1conf, 4),
            "top5": top5,
            "inference_ms": elapsed_ms,
            "input_size": self._input_size,
        }

    def predict_batch(self, image_paths: list[str]) -> list[dict]:
        return [self.predict_image(p) for p in image_paths]

    def get_model_info(self) -> dict:
        return {
            "model_id": self.model_id,
            "task_type": "classification",
            "classes": self._classes,
            "input_size": self._input_size,
            "runtime": self._runtime,
            "weights_path": self.model_path,
        }

    def close(self):
        self._model = None


class DetectionAdapter:
    def __init__(self, model_path: str, model_id: str = "best"):
        self.model_path = model_path
        self.model_id = model_id
        self._model = None
        self._runtime = os.environ.get("MODEL_RUNTIME", "ultralytics")
        self._input_size = 640
        self._classes = [
            "Bhopper", "Ghopper", "Folder", "Rice-bug", "Stem-borer",
            "Whorl-maggot", "False-smut", "Sheath-blight", "Streak",
            "Tungro", "Blast", "Blight", "Brown-spot", "Dead-heart", "Downy-mildew",
        ]
        self._conf_threshold = float(os.environ.get("DETECTION_CONF_THRESHOLD", "0.25"))

    def load(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path, task="detect")
        except ImportError:
            self._model = None

    def predict_image(self, image_path: str) -> dict:
        self.load()
        if self._model is None:
            return {"error": "Model not loaded", "model_id": self.model_id}
        t0 = time.time()
        results = self._model.predict(
            image_path, imgsz=self._input_size, conf=self._conf_threshold, verbose=False
        )
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        r = results[0]
        detections = []
        if r.boxes is not None:
            for i in range(len(r.boxes)):
                box = r.boxes[i]
                detections.append({
                    "class_id": int(box.cls.item()),
                    "class_name": self._classes[int(box.cls.item())] if int(box.cls.item()) < len(self._classes) else str(int(box.cls.item())),
                    "confidence": round(float(box.conf.item()), 4),
                    "bbox": [round(float(x), 1) for x in box.xyxy[0].tolist()],
                    "area_ratio": round(float((box.xywh[0][2] * box.xywh[0][3]).item()) / (self._input_size * self._input_size), 4),
                })
        return {
            "model_id": self.model_id,
            "task_type": "detection",
            "detections": detections,
            "detection_count": len(detections),
            "inference_ms": elapsed_ms,
            "input_size": self._input_size,
            "conf_threshold": self._conf_threshold,
        }

    def predict_batch(self, image_paths: list[str]) -> list[dict]:
        return [self.predict_image(p) for p in image_paths]

    def get_model_info(self) -> dict:
        return {
            "model_id": self.model_id,
            "task_type": "detection",
            "classes": self._classes,
            "input_size": self._input_size,
            "runtime": self._runtime,
            "weights_path": self.model_path,
            "conf_threshold": self._conf_threshold,
        }

    def close(self):
        self._model = None


_classification_adapter: Optional[ClassificationAdapter] = None
_detection_adapter: Optional[DetectionAdapter] = None


def get_classification_adapter() -> ClassificationAdapter:
    global _classification_adapter
    if _classification_adapter is None:
        path = str(MODELS_DIR / "best_cls.pt")
        _classification_adapter = ClassificationAdapter(path)
    return _classification_adapter


def get_detection_adapter() -> DetectionAdapter:
    global _detection_adapter
    if _detection_adapter is None:
        path = str(MODELS_DIR / "best.pt")
        _detection_adapter = DetectionAdapter(path)
    return _detection_adapter
