from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.services.environment_simulator import get_simulator

router = APIRouter(prefix="/api/v1/environment", tags=["environment"])


class EnvironmentIngestRequest(BaseModel):
    device_id: str = "ENV01"
    plot_id: str = "plot-1"
    temperature: float
    humidity: float
    light: float
    soil_moisture: float
    source: str = "sensor"


@router.post("/ingest")
async def ingest_environment(req: EnvironmentIngestRequest):
    """接收传感器/模拟器上报的环境数据"""
    sim = get_simulator()
    sim.inject_reading(
        device_id=req.device_id,
        plot_id=req.plot_id,
        temperature=req.temperature,
        humidity=req.humidity,
        light=req.light,
        soil_moisture=req.soil_moisture,
        source=req.source,
    )
    return {"status": "ok", "message": "Data ingested", "timestamp": datetime.now().isoformat()}



@router.get("/current")
async def get_current_environment(plot_id: Optional[str] = Query(default="plot-1")):
    """获取当前环境数据（温度、湿度、光照、土壤含水率）"""
    sim = get_simulator()
    return sim.get_current()


@router.get("/series")
async def get_environment_series(
    plot_id: Optional[str] = Query(default="plot-1"),
    limit: int = Query(default=60, ge=1, le=288),
):
    """获取环境数据历史序列"""
    sim = get_simulator()
    return {
        "plot_id": plot_id,
        "count": len(sim.get_series(limit)),
        "data": sim.get_series(limit),
    }


@router.get("/devices")
async def get_devices():
    """获取设备列表"""
    sim = get_simulator()
    return {
        "devices": [
            {
                "device_id": sim.device_id,
                "plot_id": sim.plot_id,
                "name": "边缘节点-001",
                "status": "online" if sim.running else "offline",
                "source": "simulator",
            }
        ]
    }


@router.get("/simulator/status")
async def get_simulator_status():
    """获取模拟器状态"""
    sim = get_simulator()
    return sim.get_status()


@router.post("/simulator/anomaly")
async def set_simulator_anomaly(
    anomaly: Optional[str] = Query(
        default=None,
        description="异常类型: high_temp(高温), high_humidity(高湿), soil_wet(土壤过湿), low_light(光照不足), normal(恢复正常)"
    ),
):
    """设置模拟器异常状态"""
    sim = get_simulator()
    if anomaly == "normal":
        anomaly = None
    sim.set_anomaly(anomaly)
    return {
        "status": "ok",
        "anomaly": anomaly,
        "message": f"已设置异常状态: {anomaly if anomaly else '正常'}"
    }


@router.post("/simulator/config")
async def set_simulator_config(
    base_temp: Optional[float] = Query(default=None),
    base_humidity: Optional[float] = Query(default=None),
    base_light: Optional[float] = Query(default=None),
    base_soil_moisture: Optional[float] = Query(default=None),
    interval: Optional[int] = Query(default=None, ge=1, le=60),
):
    """配置模拟器参数"""
    sim = get_simulator()
    sim.set_base_values(
        temp=base_temp,
        humidity=base_humidity,
        light=base_light,
        soil=base_soil_moisture,
    )
    if interval is not None:
        sim.interval = interval
    return {
        "status": "ok",
        "config": sim.get_status(),
    }
