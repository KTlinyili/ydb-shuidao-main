"""
风险预警配置
权重和阈值从环境变量读取，不硬编码
"""
import os


def get_risk_weights():
    return {
        "visual": float(os.getenv("RISK_WEIGHT_VISUAL", "0.45")),
        "environment": float(os.getenv("RISK_WEIGHT_ENVIRONMENT", "0.35")),
        "trend": float(os.getenv("RISK_WEIGHT_TREND", "0.20")),
    }


def get_risk_thresholds():
    return {
        "low": float(os.getenv("RISK_THRESHOLD_LOW", "0.3")),
        "medium": float(os.getenv("RISK_THRESHOLD_MEDIUM", "0.5")),
        "high": float(os.getenv("RISK_THRESHOLD_HIGH", "0.7")),
        "critical": float(os.getenv("RISK_THRESHOLD_CRITICAL", "0.85")),
    }
