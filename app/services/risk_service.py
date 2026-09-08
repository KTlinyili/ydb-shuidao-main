"""
风险预警服务
根据视觉识别结果、环境数据和趋势计算综合风险
"""
import time
import uuid
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from app.core.risk_config import get_risk_weights, get_risk_thresholds

@dataclass
class Warning:
    id: str
    plot_id: str
    level: str  # low, medium, high, critical
    visual_risk: float
    environment_risk: float
    trend_risk: float
    composite_risk: float
    reason: str
    recommendation: str
    status: str  # pending, acknowledged, closed
    created_at: float
    acknowledged_at: Optional[float] = None
    closed_at: Optional[float] = None


class RiskService:
    def __init__(self):
        self.warnings: List[Warning] = []
        self.weights = get_risk_weights()
        self.thresholds = get_risk_thresholds()

    def calculate_visual_risk(self, class_name: str, confidence: float) -> float:
        """根据视觉识别结果计算风险分 (0-1)"""
        risk_map = {
            "healthy": 0.05,
            "brown_spot": 0.4,
            "leaf_blast": 0.7,
            "neck_blast": 0.85,
        }
        base = risk_map.get(class_name, 0.3)
        return round(base * confidence, 3)

    def calculate_environment_risk(self, env_data: Dict) -> float:
        """根据环境数据计算风险分 (0-1)"""
        risk = 0.0
        factors = 0

        temp = env_data.get("temperature", 25)
        humidity = env_data.get("humidity", 60)
        soil = env_data.get("soil_moisture", 50)
        light = env_data.get("light", 5000)

        # 温度风险：高于32度或低于5度风险升高
        if temp > 35:
            temp_risk = 0.9
        elif temp > 32:
            temp_risk = 0.7
        elif temp > 28:
            temp_risk = 0.4
        elif temp < 5:
            temp_risk = 0.7
        elif temp < 10:
            temp_risk = 0.4
        else:
            temp_risk = 0.15
        risk += temp_risk
        factors += 1

        # 湿度风险：高湿容易引发病害
        if humidity > 90:
            hum_risk = 0.9
        elif humidity > 80:
            hum_risk = 0.7
        elif humidity > 70:
            hum_risk = 0.5
        elif humidity < 20:
            hum_risk = 0.4
        else:
            hum_risk = 0.1
        risk += hum_risk
        factors += 1

        # 土壤湿度风险：过湿或过干都有风险
        if soil > 85:
            soil_risk = 0.8
        elif soil > 70:
            soil_risk = 0.5
        elif soil < 20:
            soil_risk = 0.6
        elif soil < 30:
            soil_risk = 0.4
        else:
            soil_risk = 0.1
        risk += soil_risk
        factors += 1

        # 光照风险：光照不足有风险
        if light < 1000:
            light_risk = 0.5
        elif light < 3000:
            light_risk = 0.3
        else:
            light_risk = 0.1
        risk += light_risk
        factors += 1

        return round(risk / factors, 3) if factors > 0 else 0.0

    def calculate_trend_risk(self, series: List[Dict]) -> float:
        """根据趋势计算风险分 (0-1)"""
        if len(series) < 5:
            return 0.0

        recent = series[-10:] if len(series) >= 10 else series
        first_half = recent[:len(recent) // 2]
        second_half = recent[len(recent) // 2:]

        avg_temp_1 = sum(d.get("temperature", 0) for d in first_half) / len(first_half)
        avg_temp_2 = sum(d.get("temperature", 0) for d in second_half) / len(second_half)
        temp_change = avg_temp_2 - avg_temp_1

        avg_hum_1 = sum(d.get("humidity", 0) for d in first_half) / len(first_half)
        avg_hum_2 = sum(d.get("humidity", 0) for d in second_half) / len(second_half)
        hum_change = avg_hum_2 - avg_hum_1

        trend_risk = 0.0
        if temp_change > 2:
            trend_risk += 0.4
        elif temp_change > 1:
            trend_risk += 0.2

        if hum_change > 5:
            trend_risk += 0.4
        elif hum_change > 2:
            trend_risk += 0.2

        return round(min(trend_risk, 1.0), 3)

    def calculate_composite_risk(
        self, visual_risk: float, environment_risk: float, trend_risk: float
    ) -> float:
        """计算综合风险分"""
        composite = (
            visual_risk * self.weights["visual"]
            + environment_risk * self.weights["environment"]
            + trend_risk * self.weights["trend"]
        )
        return round(composite, 3)

    def risk_level(self, composite: float) -> str:
        if composite >= self.thresholds["critical"]:
            return "critical"
        elif composite >= self.thresholds["high"]:
            return "high"
        elif composite >= self.thresholds["medium"]:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(self, level: str, visual_risk: float, env_risk: float, trend_risk: float) -> str:
        recs = []
        if level == "critical":
            recs.append("【紧急】请立即查看现场情况")
        elif level == "high":
            recs.append("【高风险】建议尽快安排田间巡查")
        elif level == "medium":
            recs.append("【中风险】请密切关注环境变化")
        else:
            recs.append("【低风险】环境正常，继续监测")

        if visual_risk > 0.6:
            recs.append("视觉检测发现病害风险，建议进一步确认病害类型并采取防治措施")
        if env_risk > 0.6:
            recs.append("环境条件不利于作物生长，建议调整灌溉/通风策略")
        if trend_risk > 0.3:
            recs.append("环境趋势恶化，建议加强监测频率")

        return "；".join(recs)

    def _generate_reason(self, visual_risk: float, env_risk: float, trend_risk: float) -> str:
        reasons = []
        if visual_risk > 0.5:
            reasons.append(f"视觉风险较高({visual_risk:.1%})")
        if env_risk > 0.5:
            reasons.append(f"环境风险较高({env_risk:.1%})")
        if trend_risk > 0.3:
            reasons.append(f"环境趋势不利({trend_risk:.1%})")
        if not reasons:
            reasons.append("各项指标正常")
        return "，".join(reasons)

    def create_warning(
        self,
        plot_id: str,
        visual_risk: float,
        environment_risk: float,
        trend_risk: float,
        composite_risk: float,
        level: str,
    ) -> Warning:
        warning = Warning(
            id=str(uuid.uuid4())[:8],
            plot_id=plot_id,
            level=level,
            visual_risk=visual_risk,
            environment_risk=environment_risk,
            trend_risk=trend_risk,
            composite_risk=composite_risk,
            reason=self._generate_reason(visual_risk, environment_risk, trend_risk),
            recommendation=self._generate_recommendation(level, visual_risk, environment_risk, trend_risk),
            status="pending",
            created_at=time.time(),
        )
        self.warnings.insert(0, warning)
        if len(self.warnings) > 100:
            self.warnings = self.warnings[:100]
        return warning

    def get_warnings(self, status: Optional[str] = None, limit: int = 20) -> List[Warning]:
        result = self.warnings
        if status:
            result = [w for w in result if w.status == status]
        return result[:limit]

    def acknowledge_warning(self, warning_id: str) -> Optional[Warning]:
        for w in self.warnings:
            if w.id == warning_id:
                w.status = "acknowledged"
                w.acknowledged_at = time.time()
                return w
        return None

    def close_warning(self, warning_id: str) -> Optional[Warning]:
        for w in self.warnings:
            if w.id == warning_id:
                w.status = "closed"
                w.closed_at = time.time()
                return w
        return None

    def pending_count(self) -> int:
        return len([w for w in self.warnings if w.status == "pending"])


# 全局服务实例
_risk_service: Optional[RiskService] = None

def get_risk_service() -> RiskService:
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskService()
    return _risk_service
