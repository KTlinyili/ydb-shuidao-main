from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any

RICE_CLS_NAMES = [
    "brown_spot",    # 棕色斑点
    "healthy",       # 健康
    "leaf_blast",    # 叶斑病/稻瘟病
    "neck_blast",    # 水稻细菌性条斑病
]

RICE_CLS_CN = {
    "brown_spot": "棕色斑点",
    "healthy": "健康",
    "leaf_blast": "叶斑病（稻瘟病）",
    "neck_blast": "细菌性条斑病",
}


@dataclass(frozen=True)
class YoloClsPaths:
    model_weights: Path
    class_names: tuple[str, ...] = ()
    image_size: int = 224


class YoloClassifier:
    """YOLOv8 分类模型服务"""

    def __init__(self, paths: YoloClsPaths):
        self.paths = paths
        self._lock = Lock()
        self._loaded = False
        self._model: Any | None = None
        self._class_names: list[str] = []

    @classmethod
    def from_project_root(cls, project_root: Path) -> YoloClassifier:
        model_path = project_root / "app" / "models" / "best_cls.pt"
        return cls(
            YoloClsPaths(
                model_weights=model_path,
                class_names=tuple(RICE_CLS_NAMES),
            )
        )

    def is_available(self) -> bool:
        return self.paths.model_weights.exists()

    def classify_image_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        if not image_bytes:
            raise ValueError("图像字节内容为空")
        self._ensure_loaded()
        from PIL import Image
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return self._classify_pil_image(image)

    def classify_image_path(self, image_path: str | Path) -> dict[str, Any]:
        self._ensure_loaded()
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        return self._classify_pil_image(image)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            from ultralytics import YOLO
            self._model = YOLO(str(self.paths.model_weights))
            self._class_names = list(self.paths.class_names) or RICE_CLS_NAMES
            self._loaded = True

    def _classify_pil_image(self, image: Any) -> dict[str, Any]:
        results = self._model(image, verbose=False)
        if not results:
            return self._empty_result(image)

        result = results[0]
        width, height = image.size

        # 分类结果
        probs = result.probs
        if probs is None:
            return self._empty_result(image)

        top1_idx = int(probs.top1)
        top1_conf = float(probs.top1conf)
        all_probs = probs.data.tolist()

        # 构建所有类别的预测结果
        all_predictions = []
        for idx, prob in enumerate(all_probs):
            cname = self._class_names[idx] if idx < len(self._class_names) else f"class_{idx}"
            cn_name = RICE_CLS_CN.get(cname, cname)
            all_predictions.append({
                "class_id": idx,
                "class_name": cn_name,
                "class_name_en": cname,
                "confidence": round(float(prob), 4),
            })

        all_predictions.sort(key=lambda x: x["confidence"], reverse=True)

        top1_name = self._class_names[top1_idx] if top1_idx < len(self._class_names) else f"class_{top1_idx}"
        top1_cn = RICE_CLS_CN.get(top1_name, top1_name)

        return {
            "model_name": "yolov8n_cls_rice",
            "device": str(self._model.device if self._model else "cpu"),
            "image_size": {"width": width, "height": height},
            "predicted_class_id": top1_idx,
            "predicted_class": top1_cn,
            "predicted_class_en": top1_name,
            "confidence": round(top1_conf, 4),
            "top_predictions": all_predictions[:5],
            "classifier_classes": [RICE_CLS_CN.get(c, c) for c in self._class_names],
            "classifier_classes_en": self._class_names,
            "is_healthy": top1_name == "healthy",
        }

    def _empty_result(self, image: Any) -> dict[str, Any]:
        width, height = image.size
        return {
            "model_name": "yolov8n_cls_rice",
            "device": "cpu",
            "image_size": {"width": width, "height": height},
            "predicted_class_id": -1,
            "predicted_class": "未知",
            "predicted_class_en": "unknown",
            "confidence": 0.0,
            "top_predictions": [],
            "classifier_classes": [RICE_CLS_CN.get(c, c) for c in self._class_names],
            "classifier_classes_en": self._class_names,
            "is_healthy": False,
        }
