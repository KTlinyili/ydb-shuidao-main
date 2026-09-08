"""
文字症状诊断 API 路由
用户输入症状描述文字 → 规则匹配+知识库 → 返回候选病害、风险等级、建议措施
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.text_diagnosis import diagnose_text, to_dict

router = APIRouter(prefix="/api/v1/multimodal", tags=["multimodal-text"])


class TextDiagnosisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="症状描述文字")
    plot_id: str = Field(default="P01", description="地块ID")
    crop: str = Field(default="rice", description="作物类型")
    growth_stage: str = Field(default="", description="生育阶段")
    attach_latest_environment: bool = Field(default=False, description="是否附加最新环境数据")
    attach_latest_visual: bool = Field(default=False, description="是否附加最新视觉检测")


class TextDiagnosisResponse(BaseModel):
    input_text: str
    matches: list[dict] = Field(default_factory=list)
    top_match: dict | None = None
    risk_level: str = "low"
    risk_score: int = 0
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)


@router.post("/text", response_model=TextDiagnosisResponse)
async def diagnose_by_text(payload: TextDiagnosisRequest) -> TextDiagnosisResponse:
    """文字症状分析：输入症状描述，返回匹配病害、风险等级和建议"""
    result = diagnose_text(payload.text)
    return TextDiagnosisResponse(**to_dict(result))


@router.get("/text/keywords")
async def list_keywords() -> dict:
    """列出所有支持的关键词和病害，供前端展示"""
    from app.services.text_diagnosis import DISEASE_RULES
    diseases = []
    for rule in DISEASE_RULES:
        diseases.append({
            "key": rule.key,
            "name": rule.name,
            "name_en": rule.name_en,
            "keywords": rule.keywords,
            "symptoms": rule.symptoms,
            "favorable": rule.favorable,
        })
    return {"diseases": diseases, "total": len(diseases)}
