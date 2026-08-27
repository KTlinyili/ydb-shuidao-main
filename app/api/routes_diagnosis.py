from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.schemas_http import ImageProbeResponse, RunResponse
from app.core.errors import RealOutputRequiredError
from app.core.pipeline.diagnosis_pipeline import DiagnosisPipeline


class ClassifyResponse(BaseModel):
    predicted_class_id: int
    predicted_class: str
    predicted_class_en: str
    confidence: float
    top_predictions: list[dict] = Field(default_factory=list)
    classifier_classes: list[str] = Field(default_factory=list)
    classifier_classes_en: list[str] = Field(default_factory=list)
    is_healthy: bool
    model_name: str
    image_size: dict = Field(default_factory=dict)

router = APIRouter(prefix="/api/v1/diagnosis", tags=["diagnosis"])
DEFAULT_PROBLEM_NAME = "水稻病虫害诊断报告"


def get_pipeline(request: Request) -> DiagnosisPipeline:
    return request.app.state.pipeline


@router.post("/run", response_model=RunResponse)
async def run_diagnosis(
    request: Request,
    problem_name: str = Form(DEFAULT_PROBLEM_NAME),
    case_text: str = Form(""),
    stage: str = Form("initial"),
    n_rounds: int = Form(2),
    image: UploadFile = File(...),
) -> RunResponse:
    pipeline = get_pipeline(request)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片内容为空")

    try:
        result = pipeline.run(
            problem_name=problem_name.strip() or DEFAULT_PROBLEM_NAME,
            case_text=case_text.strip(),
            stage=stage.strip() or "initial",
            image_bytes=image_bytes,
            n_rounds=n_rounds,
        )
        return RunResponse(
            run_id=result["run_id"],
            knowledge_write_layer=result["knowledge_write_layer"],
            case_write_layer=result.get("case_write_layer", result["knowledge_write_layer"]),
            final=result["final"],
            reports=result.get("reports", {}),
            execution_meta=result.get("execution_meta", {}),
        )
    except RealOutputRequiredError as err:
        raise HTTPException(status_code=502, detail=err.to_detail()) from err


@router.post("/run_stream")
async def run_diagnosis_stream(
    request: Request,
    problem_name: str = Form(DEFAULT_PROBLEM_NAME),
    case_text: str = Form(""),
    stage: str = Form("initial"),
    n_rounds: int = Form(2),
    image: UploadFile = File(...),
) -> StreamingResponse:
    pipeline = get_pipeline(request)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片内容为空")

    def event_iter():
        for event in pipeline.run_stream(
            problem_name=problem_name.strip() or DEFAULT_PROBLEM_NAME,
            case_text=case_text.strip(),
            stage=stage.strip() or "initial",
            image_bytes=image_bytes,
            n_rounds=n_rounds,
        ):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_iter(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/image_probe", response_model=ImageProbeResponse)
async def probe_image(
    request: Request,
    case_text: str = Form(""),
    image: UploadFile = File(...),
) -> ImageProbeResponse:
    pipeline = get_pipeline(request)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片内容为空")

    try:
        result = pipeline.inspect_image(image_bytes=image_bytes, case_text=case_text.strip())
        return ImageProbeResponse(
            slot_extraction=result.get("slot_extraction", {}),
            image_analysis=result["image_analysis"],
            display=result.get("display", {}),
            caption=result["caption"],
            vision_result=result.get("vision_result", {}),
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.post("/classify", response_model=ClassifyResponse)
async def classify_image(
    request: Request,
    image: UploadFile = File(...),
) -> ClassifyResponse:
    """YOLOv8 分类模型快速识别水稻叶片病害"""
    pipeline = get_pipeline(request)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片内容为空")

    if pipeline.classifier is None or not pipeline.classifier.is_available():
        raise HTTPException(status_code=503, detail="分类模型未加载或不可用")

    try:
        result = pipeline.classifier.classify_image_bytes(image_bytes)
        return ClassifyResponse(**result)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err
