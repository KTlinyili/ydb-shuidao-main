from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.risk_service import get_risk_service

router = APIRouter(prefix="/api/v1/warnings", tags=["warnings"])


@router.get("")
async def get_warnings(
    status: Optional[str] = Query(default=None, description="pending/acknowledged/closed"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """获取预警列表"""
    service = get_risk_service()
    warnings = service.get_warnings(status=status, limit=limit)
    return {
        "total": len(warnings),
        "pending_count": service.pending_count(),
        "items": [
            {
                "id": w.id,
                "plot_id": w.plot_id,
                "level": w.level,
                "visual_risk": w.visual_risk,
                "environment_risk": w.environment_risk,
                "trend_risk": w.trend_risk,
                "composite_risk": w.composite_risk,
                "reason": w.reason,
                "recommendation": w.recommendation,
                "status": w.status,
                "created_at": w.created_at,
                "acknowledged_at": w.acknowledged_at,
                "closed_at": w.closed_at,
            }
            for w in warnings
        ],
    }


@router.post("/{warning_id}/ack")
async def acknowledge_warning(warning_id: str):
    """确认预警"""
    service = get_risk_service()
    w = service.acknowledge_warning(warning_id)
    if not w:
        raise HTTPException(status_code=404, detail="预警不存在")
    return {"status": "ok", "warning_id": warning_id, "message": "已确认"}


@router.post("/{warning_id}/close")
async def close_warning(warning_id: str):
    """关闭预警"""
    service = get_risk_service()
    w = service.close_warning(warning_id)
    if not w:
        raise HTTPException(status_code=404, detail="预警不存在")
    return {"status": "ok", "warning_id": warning_id, "message": "已关闭"}


@router.get("/risk/compute")
async def compute_risk(
    class_name: str = Query(default="healthy"),
    confidence: float = Query(default=0.9),
    temperature: float = Query(default=26.0),
    humidity: float = Query(default=65.0),
    light: float = Query(default=8000.0),
    soil_moisture: float = Query(default=55.0),
    plot_id: str = Query(default="plot-1"),
    auto_warning: bool = Query(default=True, description="风险达到medium以上自动生成预警"),
):
    """计算综合风险"""
    service = get_risk_service()

    env_data = {
        "temperature": temperature,
        "humidity": humidity,
        "light": light,
        "soil_moisture": soil_moisture,
    }

    visual_risk = service.calculate_visual_risk(class_name, confidence)
    env_risk = service.calculate_environment_risk(env_data)
    trend_risk = 0.15  # 无趋势数据时给个基础值
    composite = service.calculate_composite_risk(visual_risk, env_risk, trend_risk)
    level = service.risk_level(composite)

    warning_id = None
    if auto_warning and level in ("medium", "high", "critical"):
        w = service.create_warning(
            plot_id=plot_id,
            visual_risk=visual_risk,
            environment_risk=env_risk,
            trend_risk=trend_risk,
            composite_risk=composite,
            level=level,
        )
        warning_id = w.id

    return {
        "plot_id": plot_id,
        "visual_risk": visual_risk,
        "environment_risk": env_risk,
        "trend_risk": trend_risk,
        "composite_risk": composite,
        "level": level,
        "warning_id": warning_id,
        "weights": service.weights,
    }


@router.get("/risk/weights")
async def get_risk_weights():
    """获取风险权重配置"""
    service = get_risk_service()
    return {"weights": service.weights, "thresholds": service.thresholds}
