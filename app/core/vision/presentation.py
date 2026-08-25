from __future__ import annotations

from typing import Any


def normalize_label(value: str) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


_CLASS_NAME_CN = {
    "healthy": "健康",
    "riceblast": "稻瘟病",
    "sheathblight": "纹枯病",
    "bacterialleafblight": "白叶枯病",
    "brownspot": "褐斑病",
    "bacterialstripe": "细菌性条斑病",
    "riceplanthopper": "稻飞虱",
    "riceleafroller": "稻纵卷叶螟",
    "ricestemborer": "二化螟",
}


def class_name_to_cn(name: str) -> str:
    text = str(name).strip()
    if not text:
        return "未知"
    mapped = _CLASS_NAME_CN.get(normalize_label(text))
    if mapped:
        return mapped
    if any("一" <= ch <= "鿿" for ch in text):
        return text
    return f"未映射类别（{text}）"


def format_percent(value: float) -> str:
    return f"{clamp_unit(value) * 100:.1f}%"


def build_conflict_analysis(image_analysis: dict[str, Any]) -> dict[str, Any]:
    predicted_class = str(image_analysis.get("predicted_class", "")).strip()
    predicted_norm = normalize_label(predicted_class)
    confidence = clamp_unit(float(image_analysis.get("confidence", 0.0)))
    damage_ratio = clamp_unit(float(image_analysis.get("damaged_area_ratio_of_leaf", 0.0)))
    dominant_ratio = clamp_unit(float(image_analysis.get("dominant_segmentation_ratio_of_leaf", 0.0)))
    predicted_damage_ratio = clamp_unit(float(image_analysis.get("predicted_class_damage_ratio_of_leaf", 0.0)))

    has_conflict = False
    reasons: list[str] = []
    if predicted_norm == "healthy" and damage_ratio >= 0.08:
        has_conflict = True
        reasons.append("整体分类结果偏健康，但当前受损区域已经达到可见异常水平。")
    if predicted_norm not in {"", "healthy"} and confidence < 0.55 and damage_ratio >= 0.35:
        has_conflict = True
        reasons.append("分类置信度偏低且受损范围较大，病种判断需要复核。")
    if predicted_damage_ratio > 0 and damage_ratio - predicted_damage_ratio >= 0.15:
        has_conflict = True
        reasons.append("预测病种相关区域与整体受损范围差距较大，建议结合复拍继续确认。")
    if not reasons:
        reasons.append("病种判断与受损范围信息未见明显矛盾。")

    if has_conflict:
        summary = (
            f"当前分类结果更接近“{class_name_to_cn(predicted_class)}”，但当前受损区域约占整体的 {format_percent(damage_ratio)}。"
            "建议先补充图像证据，再提高病种结论强度。"
        )
        recommended_interpretation = "病种判断以分类结果为主，受损范围信息用于辅助复核与观察。"
    else:
        summary = "病种判断与受损范围信息整体一致。"
        recommended_interpretation = "可以保持当前病种倾向，同时持续跟踪受损范围变化。"

    return {
        "has_conflict": has_conflict,
        "classification_result": predicted_class,
        "classification_result_cn": class_name_to_cn(predicted_class),
        "classification_confidence": confidence,
        "segmentation_result": "",
        "segmentation_result_cn": "",
        "damaged_area_ratio_of_leaf": damage_ratio,
        "dominant_segmentation_ratio_of_leaf": dominant_ratio,
        "predicted_class_damage_ratio_of_leaf": predicted_damage_ratio,
        "reason_summary": summary,
        "reason_details": reasons,
        "recommended_interpretation": recommended_interpretation,
        "index_alignment_note": "分割结果不参与病种判读，仅用于估计受损范围。",
    }


def resolve_primary_visual_diagnosis(image_analysis: dict[str, Any]) -> dict[str, Any]:
    predicted_class = str(image_analysis.get("predicted_class", "")).strip() or "unknown"
    damage_ratio = clamp_unit(float(image_analysis.get("damaged_area_ratio_of_leaf", 0.0)))
    dominant_ratio = clamp_unit(float(image_analysis.get("dominant_segmentation_ratio_of_leaf", 0.0)))
    conflict = build_conflict_analysis(image_analysis)

    consistency_note = "病种判断以分类结果为主，分割结果仅用于估计受损范围和严重程度。"
    if conflict["has_conflict"]:
        consistency_note = "当前病种判断仍以分类结果为主，但建议在 24 到 48 小时内补图复核。"

    return {
        "primary_class": predicted_class,
        "primary_class_cn": class_name_to_cn(predicted_class),
        "primary_source": "分类头",
        "predicted_class_cn": class_name_to_cn(predicted_class),
        "dominant_segmentation_class_cn": "",
        "has_conflict": conflict["has_conflict"],
        "consistency_note": consistency_note,
        "damage_ratio": damage_ratio,
        "dominant_ratio": dominant_ratio,
        "conflict_analysis": conflict,
    }


def build_image_analysis_display(image_analysis: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_primary_visual_diagnosis(image_analysis)
    conflict = resolved["conflict_analysis"]
    confidence = clamp_unit(float(image_analysis.get("confidence", 0.0)))
    damage_ratio = clamp_unit(float(image_analysis.get("damaged_area_ratio_of_leaf", 0.0)))
    leaf_pixels = int(image_analysis.get("leaf_pixels", 0) or 0)
    diseased_pixels = int(image_analysis.get("diseased_pixels", 0) or 0)

    top_predictions = [
        {
            "名称": class_name_to_cn(str(item.get("class_name", ""))),
            "置信度": format_percent(float(item.get("confidence", 0.0))),
        }
        for item in image_analysis.get("top_predictions", [])
        if isinstance(item, dict)
    ]

    segmentation_findings: list[dict[str, Any]] = []
    for idx, item in enumerate(image_analysis.get("disease_area_details", []), start=1):
        if not isinstance(item, dict):
            continue
        ratio = clamp_unit(float(item.get("ratio_of_leaf", 0.0)))
        if ratio <= 0.0:
            continue
        segmentation_findings.append(
            {
                "区域": f"受损区域{idx}",
                "受损区域占比": format_percent(ratio),
                "受损像素": int(item.get("pixels", 0) or 0),
                "平均概率": format_percent(float(item.get("mean_probability", 0.0))),
            }
        )

    summary_text = (
        f"当前图像病种判断更偏向“{resolved['primary_class_cn']}”，主要依据来自分类头；"
        f"分类置信度为 {format_percent(confidence)}，当前受损区域约占整体 {format_percent(damage_ratio)}。"
        "分割结果仅用于受损范围估计，不参与病种类型判读。"
    )
    if conflict["has_conflict"]:
        summary_text += " 当前病种结论与受损范围信号存在张力，建议继续补图复核。"

    return {
        "摘要": summary_text,
        "结论卡片": {
            "综合判断": resolved["primary_class_cn"],
            "综合判断来源": resolved["primary_source"],
            "分类结果": resolved["predicted_class_cn"],
            "分类置信度": format_percent(confidence),
            "分割用途": "仅用于受损范围估计",
            "受损区域占比": format_percent(damage_ratio),
            "叶片像素": leaf_pixels,
            "受损像素": diseased_pixels,
            "结果一致性": "需要复核" if conflict["has_conflict"] else "基本一致",
        },
        "一致性说明": resolved["consistency_note"],
        "结果差异分析": {
            "差异摘要": conflict["reason_summary"],
            "差异原因": conflict["reason_details"],
            "解释建议": conflict["recommended_interpretation"],
            "索引说明": conflict["index_alignment_note"],
        },
        "分类候选": top_predictions,
        "受损范围明细": segmentation_findings,
    }
