from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas_http import FinalResponse, TraceResponse
from app.core.pipeline.diagnosis_pipeline import DiagnosisPipeline

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


def get_pipeline(request: Request) -> DiagnosisPipeline:
    return request.app.state.pipeline


@router.get("", response_model=list[dict])
def list_runs(request: Request, limit: int = 100) -> list[dict]:
    pipeline = get_pipeline(request)
    return pipeline.list_runs(limit=limit)


@router.get("/{run_id}", response_model=FinalResponse)
def get_final(run_id: str, request: Request) -> FinalResponse:
    pipeline = get_pipeline(request)
    try:
        payload = pipeline.load_final(run_id)
        return FinalResponse(run_id=run_id, final=payload)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"未找到运行记录: {run_id}") from err


@router.get("/{run_id}/trace", response_model=TraceResponse)
def get_trace(run_id: str, request: Request) -> TraceResponse:
    pipeline = get_pipeline(request)
    try:
        payload = pipeline.load_trace(run_id)
        return TraceResponse(run_id=run_id, trace=payload)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"未找到运行记录: {run_id}") from err


@router.delete("/{run_id}")
def delete_run(run_id: str, request: Request) -> dict:
    pipeline = get_pipeline(request)
    try:
        return pipeline.delete_run(run_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"未找到运行记录: {run_id}") from err
