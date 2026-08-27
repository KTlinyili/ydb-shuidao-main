from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any

RICE_DISEASE_NAMES = [
    "Bhopper", "Ghopper", "Folder", "Rice-bug", "Stem-borer", "Whorl-maggot",
    "False-smut", "Sheath-blight", "Streak", "Tungro", "Blast", "Blight",
    "Brown-spot", "Dead-heart", "Downy-mildew",
]

RICE_DISEASE_CN = {
    "Bhopper": "稻飞虱", "Ghopper": "稻飞虱", "Folder": "稻纵卷叶螟",
    "Rice-bug": "稻蝽", "Stem-borer": "二化螟", "Whorl-maggot": "稻秆蝇",
    "False-smut": "稻曲病", "Sheath-blight": "纹枯病", "Streak": "水稻条纹叶枯病",
    "Tungro": "水稻东格鲁病毒病", "Blast": "稻瘟病", "Blight": "白叶枯病",
    "Brown-spot": "褐斑病", "Dead-heart": "枯心苗", "Downy-mildew": "霜霉病",
}


@dataclass(frozen=True)
class YoloPaths:
    model_weights: Path
    class_names: tuple[str, ...] = ()
    image_size: int = 640
    conf_threshold: float = 0.25


class YoloDiagnoser:
    def __init__(self, paths: YoloPaths):
        self.paths = paths
        self._lock = Lock()
        self._loaded = False
        self._model: Any | None = None
        self._class_names: list[str] = []

    @classmethod
    def from_project_root(cls, project_root: Path) -> YoloDiagnoser:
        model_path = project_root / "app" / "models" / "best.pt"
        return cls(
            YoloPaths(
                model_weights=model_path,
                class_names=tuple(RICE_DISEASE_NAMES),
            )
        )

    def is_available(self) -> bool:
        return self.paths.model_weights.exists()

    def analyze_image_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        if not image_bytes:
            raise ValueError("图像字节内容为空")
        self._ensure_loaded()
        from PIL import Image
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return self._analyze_pil_image(image)

    def analyze_image_path(self, image_path: str | Path) -> dict[str, Any]:
        self._ensure_loaded()
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        return self._analyze_pil_image(image)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            from ultralytics import YOLO
            self._model = YOLO(str(self.paths.model_weights))
            self._class_names = list(self.paths.class_names) or RICE_DISEASE_NAMES
            self._loaded = True

    def _analyze_pil_image(self, image: Any) -> dict[str, Any]:
        results = self._model(image, conf=self.paths.conf_threshold, verbose=False)
        if not results:
            return self._empty_result(image)

        result = results[0]
        width, height = image.size
        boxes = result.boxes

        if len(boxes) == 0:
            return self._empty_result(image)

        cls_ids = boxes.cls.tolist()
        confs = boxes.conf.tolist()
        xyxy = boxes.xyxy.tolist()

        disease_area_details: list[dict[str, Any]] = []
        top_predictions: list[dict[str, Any]] = []
        for idx, (cls_id, conf, box) in enumerate(zip(cls_ids, confs, xyxy)):
            cid = int(cls_id)
            cname = self._class_names[cid] if cid < len(self._class_names) else f"class_{cid}"
            cn_name = RICE_DISEASE_CN.get(cname, cname)
            x1, y1, x2, y2 = box
            box_area = max(0.0, (x2 - x1) * (y2 - y1))
            img_area = float(width * height)
            ratio = box_area / img_area if img_area > 0 else 0.0
            disease_area_details.append({
                "class_id": cid,
                "class_name": cn_name,
                "class_name_en": cname,
                "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                "confidence": round(conf, 4),
                "box_area_ratio": round(ratio, 4),
            })
            top_predictions.append({
                "class_id": cid,
                "class_name": cn_name,
                "confidence": round(conf, 4),
            })

        top_predictions.sort(key=lambda x: x["confidence"], reverse=True)
        best = top_predictions[0]
        total_disease_ratio = sum(d["box_area_ratio"] for d in disease_area_details)

        return {
            "model_name": "yolov8n_rice_pest",
            "device": str(self._model.device if self._model else "cpu"),
            "image_size": {"width": width, "height": height},
            "predicted_class_id": best["class_id"],
            "predicted_class": best["class_name"],
            "predicted_class_en": self._class_names[best["class_id"]] if best["class_id"] < len(self._class_names) else "",
            "confidence": best["confidence"],
            "top_predictions": top_predictions[:5],
            "detection_count": len(disease_area_details),
            "damaged_area_ratio_of_leaf": round(min(1.0, total_disease_ratio), 4),
            "predicted_class_damage_ratio_of_leaf": best["confidence"],
            "dominant_segmentation_class": best["class_name"],
            "dominant_segmentation_ratio_of_leaf": round(min(1.0, total_disease_ratio), 4),
            "disease_area_details": disease_area_details,
            "segmentation_classes": list(self._class_names),
            "classifier_classes": list(self._class_names),
        }

    def _empty_result(self, image: Any) -> dict[str, Any]:
        width, height = image.size
        return {
            "model_name": "yolov8n_rice_pest",
            "device": "cpu",
            "image_size": {"width": width, "height": height},
            "predicted_class_id": -1,
            "predicted_class": "未检测到病虫害",
            "predicted_class_en": "no_pest_detected",
            "confidence": 0.0,
            "top_predictions": [],
            "detection_count": 0,
            "damaged_area_ratio_of_leaf": 0.0,
            "predicted_class_damage_ratio_of_leaf": 0.0,
            "dominant_segmentation_class": "",
            "dominant_segmentation_ratio_of_leaf": 0.0,
            "disease_area_details": [],
            "segmentation_classes": list(self._class_names),
            "classifier_classes": list(self._class_names),
        }
