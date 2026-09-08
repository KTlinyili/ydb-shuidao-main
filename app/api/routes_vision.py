from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from typing import Optional

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


@router.post("/image")
async def classify_image(
    request: Request,
    file: UploadFile = File(...),
    model_id: Optional[str] = None,
):
    """图片分类识别 - 返回病害类别和置信度"""
    pipeline = request.app.state.pipeline

    if pipeline.classifier is None or not pipeline.classifier.is_available():
        raise HTTPException(status_code=503, detail="分类模型未加载")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片内容为空")

    try:
        result = pipeline.classifier.classify_image_bytes(image_bytes)
        return {
            "model_id": model_id or "best_cls",
            "top1_class": result.get("top1_class"),
            "top1_confidence": result.get("top1_confidence"),
            "top5": result.get("top5", []),
            "inference_ms": result.get("inference_ms"),
            "filename": file.filename,
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/models")
async def list_models(request: Request):
    """列出可用的视觉模型"""
    pipeline = request.app.state.pipeline
    models = []
    if pipeline.classifier and pipeline.classifier.is_available():
        models.append({
            "id": "best_cls",
            "type": "classification",
            "name": "水稻病害分类模型",
            "classes": ["brown_spot", "healthy", "leaf_blast", "bacterial_leaf_streak"],
            "status": "ready",
        })
    if pipeline.detector and pipeline.detector.is_available():
        models.append({
            "id": "best",
            "type": "detection",
            "name": "水稻病害检测模型",
            "status": "ready",
        })
    if not models:
        models.append({
            "id": "best_cls",
            "type": "classification",
            "name": "水稻病害分类模型",
            "status": "not_loaded",
        })
    return {"models": models}
