from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.pipeline.diagnosis_pipeline import DiagnosisPipeline

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def get_pipeline(request: Request) -> DiagnosisPipeline:
    return request.app.state.pipeline


@router.get("")
def list_cases(request: Request) -> dict:
    pipeline = get_pipeline(request)
    return pipeline.list_cases()


@router.delete("/{run_id}")
def delete_case(run_id: str, request: Request) -> dict:
    pipeline = get_pipeline(request)
    try:
        return pipeline.delete_case(run_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"未找到病例记录: {run_id}") from err
