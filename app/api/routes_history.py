"""
历史记录接口
GET /api/v1/history      - 列出检测记录
GET /api/v1/history/{id} - 单条记录详情
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/history", tags=["history"])

_records: list[dict] = []


def add_record(record: dict):
    _records.insert(0, record)
    if len(_records) > 200:
        _records[:] = _records[:200]


@router.get("")
async def list_history(
    task_type: str | None = Query(default=None),
    plot_id: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
):
    result = _records
    if task_type:
        result = [r for r in result if r.get("task_type") == task_type]
    if plot_id:
        result = [r for r in result if r.get("plot_id") == plot_id]
    total = len(result)
    return {"records": result[offset:offset + limit], "total": total}


@router.get("/{record_id}")
async def get_record(record_id: str):
    for r in _records:
        if r.get("id") == record_id:
            return r
    raise HTTPException(status_code=404, detail="Record not found")
