"""
系统状态接口
GET /api/v1/system/status - 数据库、存储、模型、流服务状态
"""
from __future__ import annotations

from fastapi import APIRouter
from pathlib import Path
import os

router = APIRouter(prefix="/api/v1/system", tags=["system"])

APP_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = APP_ROOT / "models"
UPLOAD_DIR = APP_ROOT.parent / "storage" / "uploads"
OUTPUT_DIR = APP_ROOT.parent / "storage" / "outputs"


@router.get("/status")
async def system_status():
    models = {}
    for name in ["best.pt", "best.onnx", "best_cls.pt", "best_cls.onnx"]:
        path = MODELS_DIR / name
        if path.exists():
            models[name] = {"size_mb": round(path.stat().st_size / 1024 / 1024, 1)}
        else:
            models[name] = None

    storage = {
        "uploads_dir": str(UPLOAD_DIR),
        "uploads_exists": UPLOAD_DIR.exists(),
        "outputs_dir": str(OUTPUT_DIR),
        "outputs_exists": OUTPUT_DIR.exists(),
    }

    competition_mode = os.environ.get("COMPETITION_MODE", "false").lower() == "true"

    return {
        "database": "sqlite",
        "database_url": os.environ.get("DATABASE_URL", "sqlite:///./riceguard.db"),
        "models": models,
        "storage": storage,
        "streams": "not_configured",
        "competition_mode": competition_mode,
    }
