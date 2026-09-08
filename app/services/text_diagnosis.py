"""
文字症状分析引擎：基于规则匹配+知识库，对用户输入的症状描述进行分析，
返回可能的病害、风险等级和建议措施。

规则匹配流程：
1. 对用户输入进行分词和关键词提取
2. 与病害症状关键词库进行匹配
3. 按匹配度排序，返回 Top-N 候选病害
4. 生成风险评级和建议措施
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiseaseRule:
    """病害规则定义"""
    key: str
    name: str
    name_en: str
    keywords: list[str]
    symptoms: list[str]
    severity_weight: float
    treatment: list[str]
    prevention: list[str]
    favorable: str


DISEASE_RULES: list[DiseaseRule] = [
    DiseaseRule(
        key="rice_blast",
        name="稻瘟病",
        name_en="Rice Blast",
        keywords=["稻瘟", "梭形", "病斑", "褐色", "斑点", "叶瘟", "穗颈瘟", "节瘟",
                  "白穗", "枯死", "纺锤", "暗绿", "黄褐"],
        symptoms=["叶片出现梭形病斑", "病斑中央灰白，边缘褐色", "穗颈变褐枯死"],
        severity_weight=0.9,
        treatment=[
            "喷施三环唑或稻瘟灵杀菌剂",
            "发病初期每7天喷施一次，连续2-3次",
            "穗颈瘟在破口期和齐穗期各喷药一次",
        ],
        prevention=[
            "选用抗病品种",
            "合理施肥，避免偏施氮肥",
            "浅水勤灌，适时晒田",
        ],
        favorable="适温（24-28°C）高湿（RH>90%）易发",
    ),
    DiseaseRule(
        key="sheath_blight",
        name="纹枯病",
        name_en="Sheath Blight",
        keywords=["纹枯", "云纹", "菌核", "叶鞘", "暗绿", "灰白", "蛛丝", "霉层",
                  "基部", "腐烂", "倒伏"],
        symptoms=["叶鞘出现云纹状病斑", "病斑灰白，边缘暗绿", "基部叶鞘腐烂"],
        severity_weight=0.85,
        treatment=[
            "喷施井冈霉素或己唑醇",
            "重点喷施植株基部",
            "发病初期施药，间隔7-10天",
        ],
        prevention=[
            "合理密植，保持通风透光",
            "浅水勤灌，适时晒田",
            "清除田间菌核",
        ],
        favorable="高温（28-32°C）高湿环境下易发",
    ),
    DiseaseRule(
        key="brown_spot",
        name="褐斑病",
        name_en="Brown Spot",
        keywords=["褐斑", "褐色", "小点", "椭圆", "黄褐", "暗褐", "病斑", "叶尖",
                  "枯黄", "衰老"],
        symptoms=["叶片出现褐色小斑点", "病斑椭圆形，边缘深褐", "严重时叶片枯黄"],
        severity_weight=0.7,
        treatment=[
            "喷施苯醚甲环唑或咪鲜胺",
            "增施钾肥和硅肥提高抗性",
            "间隔7天喷施，连续2次",
        ],
        prevention=[
            "增施有机肥和钾肥",
            "避免缺肥导致植株衰弱",
            "及时清除病残体",
        ],
        favorable="缺肥、植株衰弱时易发",
    ),
    DiseaseRule(
        key="bacterial_leaf_streak",
        name="细菌性条斑病",
        name_en="Bacterial Leaf Streak",
        keywords=["细菌", "条斑", "水渍", "透明", "黄褐", "条状", "菌脓", "溢出",
                  "叶脉", "蔓延"],
        symptoms=["叶脉间出现水渍状条斑", "对光观察病斑半透明", "有菌脓溢出"],
        severity_weight=0.8,
        treatment=[
            "喷施噻菌铜或中生菌素",
            "避免田间漫灌减少传播",
            "发病初期施药，间隔5-7天",
        ],
        prevention=[
            "种子消毒处理",
            "避免深水漫灌",
            "及时清除病株残体",
        ],
        favorable="暴风雨后易发",
    ),
    DiseaseRule(
        key="rice_planthopper",
        name="稻飞虱",
        name_en="Rice Planthopper",
        keywords=["飞虱", "虫", "虫体", "群集", "茎基", "黄化", "矮缩", "褐色",
                  "飞虫", "蜜露", "煤污"],
        symptoms=["茎基部群集虫体", "叶片黄化矮缩", "有蜜露和煤污"],
        severity_weight=0.75,
        treatment=[
            "喷施吡蚜酮或烯啶虫胺",
            "重点喷施植株中下部",
            "分蘖期至孕穗期注意监测",
        ],
        prevention=[
            "种植抗虫品种",
            "保护天敌如蜘蛛等",
            "合理使用农药避免抗药性",
        ],
        favorable="高温干旱条件下易暴发",
    ),
    DiseaseRule(
        key="rice_leaf_roller",
        name="稻纵卷叶螟",
        name_en="Rice Leaf Roller",
        keywords=["卷叶", "纵卷", "虫苞", "虫", "白色", "蛾", "幼虫", "啃食",
                  "纵缀", "叶肉"],
        symptoms=["叶片纵卷成虫苞", "幼虫在苞内啃食叶肉", "严重时全田发白"],
        severity_weight=0.7,
        treatment=[
            "喷施氯虫苯甲酰胺或阿维菌素",
            "卵孵化盛期至低龄幼虫期施药",
            "傍晚施药效果更好",
        ],
        prevention=[
            "利用频振式杀虫灯诱杀成虫",
            "保护寄生蜂等天敌",
            "及时除草减少产卵场所",
        ],
        favorable="适温多雨条件下易发",
    ),
    DiseaseRule(
        key="stem_borer",
        name="二化螟",
        name_en="Stem Borer",
        keywords=["二化螟", "螟虫", "枯心", "白穗", "蛀孔", "虫粪", "茎内",
                  "幼虫", "枯鞘"],
        symptoms=["茎秆内蛀孔有虫粪", "造成枯心苗或白穗", "茎基部枯鞘"],
        severity_weight=0.75,
        treatment=[
            "喷施氯虫苯甲酰胺或甲维盐",
            "卵孵化盛期施药",
            "重点喷施茎基部",
        ],
        prevention=[
            "及时处理稻桩减少越冬虫源",
            "利用性诱剂诱杀成虫",
            "适时晒田减少危害",
        ],
        favorable="温暖干旱条件下易发",
    ),
    DiseaseRule(
        key="false_smut",
        name="稻曲病",
        name_en="False Smut",
        keywords=["稻曲", "球", "黄色", "绿色", "橙色", "粉状", "孢子", "稻粒",
                  "膨大"],
        symptoms=["稻粒形成黄色至绿色球状稻曲", "表面有粉状孢子"],
        severity_weight=0.6,
        treatment=[
            "破口前3-5天喷施苯醚甲环唑",
            "齐穗期补施一次",
        ],
        prevention=[
            "选用抗病品种",
            "避免偏施氮肥",
            "及时处理病谷",
        ],
        favorable="抽穗扬花期遇雨易发",
    ),
]


def _tokenize(text: str) -> list[str]:
    """简单分词：按标点空格分割，保留2-4字词组"""
    text = text.lower().strip()
    tokens = re.split(r'[，,。.!！？?；;\s、（）()\[\]【】]+', text)
    result = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if len(t) <= 4:
            result.append(t)
        else:
            for i in range(len(t) - 1):
                result.append(t[i:i+2])
            for i in range(len(t) - 2):
                result.append(t[i:i+3])
    return list(set(result))


def _match_score(tokens: list[str], rule: DiseaseRule) -> tuple[float, list[str]]:
    """计算匹配分数和命中的关键词"""
    hit_keywords = []
    for kw in rule.keywords:
        for token in tokens:
            if kw in token or token in kw:
                hit_keywords.append(kw)
                break
    if not hit_keywords:
        return 0.0, []
    score = len(hit_keywords) / len(rule.keywords)
    score = min(score, 1.0)
    return score, list(set(hit_keywords))


@dataclass
class TextDiagnosisResult:
    """文字诊断结果"""
    input_text: str
    matches: list[dict] = field(default_factory=list)
    top_match: Optional[dict] = None
    risk_level: str = "low"
    risk_score: int = 0
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)


def diagnose_text(text: str) -> TextDiagnosisResult:
    """
    分析用户输入的症状描述，返回匹配的病害列表和建议。
    """
    if not text or not text.strip():
        return TextDiagnosisResult(
            input_text=text or "",
            summary="输入为空，请描述您观察到的水稻症状",
        )

    tokens = _tokenize(text)
    if not tokens:
        return TextDiagnosisResult(
            input_text=text,
            summary="无法解析输入内容，请尝试更详细的描述",
        )

    scored: list[tuple[float, DiseaseRule, list[str]]] = []
    for rule in DISEASE_RULES:
        score, hits = _match_score(tokens, rule)
        if score > 0:
            scored.append((score, rule, hits))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return TextDiagnosisResult(
            input_text=text,
            summary="未匹配到已知病害，建议上传叶片照片进行AI图像识别",
        )

    matches = []
    for score, rule, hits in scored[:5]:
        matches.append({
            "disease_key": rule.key,
            "disease_name": rule.name,
            "disease_name_en": rule.name_en,
            "match_score": round(score, 4),
            "matched_keywords": hits,
            "symptoms": rule.symptoms,
            "severity_weight": rule.severity_weight,
            "treatment": rule.treatment,
            "prevention": rule.prevention,
            "favorable": rule.favorable,
        })

    top = matches[0]
    risk_score = int(top["match_score"] * top["severity_weight"] * 100)
    if risk_score >= 75:
        risk_level = "critical"
        risk_label = "严重"
    elif risk_score >= 55:
        risk_level = "high"
        risk_label = "高"
    elif risk_score >= 35:
        risk_level = "medium"
        risk_label = "中"
    else:
        risk_level = "low"
        risk_label = "低"

    summary = (
        f"根据症状描述，最可能的病害为「{top['disease_name']}」"
        f"（{top['disease_name_en']}），"
        f"匹配度 {top['match_score']*100:.0f}%，"
        f"风险等级：{risk_label}（风险分 {risk_score}）。"
    )

    recommendations = top["treatment"][:3]

    return TextDiagnosisResult(
        input_text=text,
        matches=matches,
        top_match=top,
        risk_level=risk_level,
        risk_score=risk_score,
        summary=summary,
        recommendations=recommendations,
    )


def to_dict(result: TextDiagnosisResult) -> dict:
    """转换为 API 响应字典"""
    return {
        "input_text": result.input_text,
        "matches": result.matches,
        "top_match": result.top_match,
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "summary": result.summary,
        "recommendations": result.recommendations,
    }
