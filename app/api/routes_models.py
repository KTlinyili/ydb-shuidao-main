"""
统一模型管理接口
GET /api/v1/models         - 列出所有可用模型
GET /api/v1/models/current - 当前模型信息
POST /api/v1/models/select - 切换当前模型
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os

router = APIRouter(prefix="/api/v1/models", tags=["models"])

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

AVAILABLE_MODELS = [
    {
        "model_id": "best_cls",
        "model_name": "YOLOv8n-cls 水稻4类分类",
        "task_type": "classification",
        "classes": ["brown_spot", "healthy", "leaf_blast", "neck_blast"],
        "input_size": 224,
        "runtime": "ultralytics",
        "quantization": "none",
        "version": "v1.0",
        "weights_path": "app/models/best_cls.pt",
    },
    {
        "model_id": "best",
        "model_name": "YOLOv8n 水稻15类检测",
        "task_type": "detection",
        "classes": [
            "Bhopper", "Ghopper", "Folder", "Rice-bug", "Stem-borer",
            "Whorl-maggot", "False-smut", "Sheath-blight", "Streak",
            "Tungro", "Blast", "Blight", "Brown-spot", "Dead-heart", "Downy-mildew",
        ],
        "input_size": 640,
        "runtime": "ultralytics",
        "quantization": "none",
        "version": "v1.0",
        "weights_path": "app/models/best.pt",
    },
]

_current_model_id = "best_cls"


class ModelSelectRequest(BaseModel):
    model_id: str


@router.get("")
async def list_models():
    models = []
    for m in AVAILABLE_MODELS:
        exists = (MODELS_DIR / Path(m["weights_path"]).name).exists()
        models.append({**m, "available": exists})
    return {"models": models, "total": len(models)}


@router.get("/current")
async def get_current_model():
    for m in AVAILABLE_MODELS:
        if m["model_id"] == _current_model_id:
            exists = (MODELS_DIR / Path(m["weights_path"]).name).exists()
            return {**m, "available": exists}
    raise HTTPException(status_code=404, detail="Current model not found")


@router.post("/select")
async def select_model(req: ModelSelectRequest):
    global _current_model_id
    for m in AVAILABLE_MODELS:
        if m["model_id"] == req.model_id:
            exists = (MODELS_DIR / Path(m["weights_path"]).name).exists()
            if not exists:
                raise HTTPException(status_code=400, detail=f"Model weights not found: {m['weights_path']}")
            _current_model_id = req.model_id
            return {"status": "ok", "current_model_id": _current_model_id}
    raise HTTPException(status_code=404, detail=f"Model not found: {req.model_id}")
