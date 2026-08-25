"""单一路径：根据病损比例与严重度生成临床叙述，避免在报告包与编排器中重复阈值分支。"""

from __future__ import annotations

from typing import Any

from app.core.caption.schema import CaptionSchema

# 比例与严重度阈值（与历史行为保持一致，集中维护）
RATIO_EXTENSIVE = 0.35
RATIO_MODERATE = 0.15
RATIO_MORPH_HEAVY = 0.40
RATIO_MORPH_CLEAR = 0.25
SEVERITY_EXTENSIVE = 0.65
SEVERITY_MODERATE = 0.40
SEVERITY_PROGNOSIS_HIGH = 0.60

CLASSIFICATION_POLICY_NOTE = (
    "病种倾向仅依据图像分类模型；病损面积为分割模型估计，用于描述受害程度，不作为独立病名依据。"
)


def _format_percent_ratio(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if numeric < 0:
        return ""
    if numeric <= 1.0:
        numeric *= 100.0
    return f"{numeric:.1f}%"


def _text(value: Any) -> str:
    raw = getattr(value, "value", value)
    if raw is None:
        return ""
    return str(raw).strip()


def _enum_values(group: Any) -> set[str]:
    if not group:
        return set()
    return {_text(item) for item in group if _text(item)}


def effective_damage_ratio(caption: CaptionSchema, vision_conflict: dict[str, Any]) -> float:
    try:
        from_vision = float(vision_conflict.get("damaged_area_ratio_of_leaf") or 0.0)
    except (TypeError, ValueError):
        from_vision = 0.0
    try:
        from_caption = float(getattr(caption.numeric, "area_ratio", 0.0) or 0.0)
    except (TypeError, ValueError):
        from_caption = 0.0
    return max(0.0, min(1.0, from_vision if from_vision > 0 else from_caption))


def effective_severity(caption: CaptionSchema) -> float:
    try:
        return max(0.0, min(1.0, float(getattr(caption.numeric, "severity_score", 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def damage_tier(ratio: float, severity: float) -> str:
    if ratio >= RATIO_EXTENSIVE or severity >= SEVERITY_EXTENSIVE:
        return "extensive"
    if ratio >= RATIO_MODERATE or severity >= SEVERITY_MODERATE:
        return "moderate"
    return "localized"


def build_leaf_clinical_profile(caption: CaptionSchema, vision_conflict: dict[str, Any]) -> dict[str, Any]:
    ratio = effective_damage_ratio(caption, vision_conflict)
    severity = effective_severity(caption)
    tier = damage_tier(ratio, severity)
    ratio_text = _format_percent_ratio(ratio)
    high_damage = ratio >= RATIO_EXTENSIVE or severity >= SEVERITY_EXTENSIVE

    if tier == "extensive":
        stage_hint = (
            f"当前病损范围较大{f'，约占叶片面积 {ratio_text}' if ratio_text else ''}，"
            "属于需认真对待的叶部受害。"
        )
    elif tier == "moderate":
        stage_hint = "当前已经出现较明确的病斑和组织受损线索，不能按轻微异常处理。"
    else:
        stage_hint = "当前病变范围相对局部，但仍需按真实病害风险审慎理解。"

    if ratio_text:
        area_source_note = (
            f"基于图像分割估计，当前病损面积约占叶片面积 {ratio_text}，"
            "该数值可作为受害程度参考，不代表田间全部病程范围。"
        )
    else:
        area_source_note = ""

    if ratio > 0:
        local_lesion_area_sentence = f"病损面积约占叶片 {ratio_text}（分割估计，仅述受害范围）。"
    else:
        local_lesion_area_sentence = f"病损面积信号未量化（{CLASSIFICATION_POLICY_NOTE}）"

    tissues = _enum_values(caption.symptoms.tissue_state)
    colors = _enum_values(caption.symptoms.color)
    positions = _enum_values(caption.symptoms.distribution_position)
    has_upper_leaf = "upper_leaf" in positions

    morphology_notes: list[str] = []
    if ratio >= RATIO_MORPH_HEAVY and ({"necrosis", "dry"} & tissues):
        morphology_notes.append(
            "叶片上部可见较大连片坏死，坏死区呈深褐至黑褐色，周围伴有较明显黄化，组织出现干枯塌陷。"
        )
    elif ratio >= RATIO_MORPH_CLEAR and ("necrosis" in tissues or "yellow" in colors):
        morphology_notes.append("叶片存在明显坏死与黄化共存表现，受害区域已超过局部小斑范围。")
    if "upper_leaf" in positions and ratio >= RATIO_MORPH_CLEAR:
        morphology_notes.append("受害重心更偏向叶片上半部分，不属于仅叶缘散在小斑阶段。")

    if ratio_text and severity >= SEVERITY_PROGNOSIS_HIGH:
        prognosis_note = (
            f"从当前受损比例看，约为 {ratio_text}，已受损组织多不可逆，预后重点在于阻止新叶继续受害。"
        )
    elif severity >= SEVERITY_MODERATE:
        prognosis_note = "当前仍有机会通过早期控险和持续复查稳定病情，关键在于尽快阻止新发病斑继续扩展。"
    else:
        prognosis_note = "若后续观察未见明显扩展，整体仍可能维持在较局部的受害范围内。"

    if ratio > 0:
        basis_support_line = (
            f"当前图像可见明显坏死并伴黄化，受损面积估计约 {_format_percent_ratio(ratio)}，"
            "支持“严重坏死性叶部病变”这一层形态学判断（病名仍由分类模型倾向与多源证据共同约束）。"
        )
    else:
        basis_support_line = (
            "当前图像可见明显坏死并伴黄化，支持“严重坏死性叶部病变”这一层形态学判断"
            "（病名仍由分类模型倾向与多源证据共同约束）。"
        )
    basis_limit_line = (
        "但目前缺少叶背霉层、整株蔓延、茎果受害与时序扩展等关键信息，"
        "尚不足以把单一病名写成确诊结论。"
    )

    return {
        "damage_ratio": ratio,
        "severity_score": severity,
        "damage_tier": tier,
        "ratio_percent_text": ratio_text,
        "high_damage_for_symptom_filter": high_damage,
        "has_upper_leaf_distribution": has_upper_leaf,
        "stage_hint": stage_hint,
        "morphology_notes": morphology_notes,
        "prognosis_note": prognosis_note,
        "area_source_note": area_source_note,
        "local_lesion_area_sentence": local_lesion_area_sentence,
        "basis_support_line": basis_support_line,
        "basis_limit_line": basis_limit_line,
        "classification_policy_note": CLASSIFICATION_POLICY_NOTE,
    }


def build_conflict_interpretation_narrative(vision_conflict: dict[str, Any]) -> str:
    from app.core.vision.presentation import class_name_to_cn

    if not isinstance(vision_conflict, dict):
        return ""
    has_conflict = bool(vision_conflict.get("has_conflict", False))
    if not has_conflict:
        return "当前分类病名排序与受害范围描述未见明显冲突，可按首位疑似推进低风险处置。"
    classification_result = str(vision_conflict.get("classification_result") or "").strip()
    confidence_text = _format_percent_ratio(float(vision_conflict.get("classification_confidence") or 0.0))
    try:
        damage_ratio = float(vision_conflict.get("damaged_area_ratio_of_leaf") or 0.0)
    except (TypeError, ValueError):
        damage_ratio = 0.0
    damage_text = _format_percent_ratio(damage_ratio)
    if classification_result:
        cn = class_name_to_cn(classification_result)
        score_sentence = (
            f"分类模型对“{cn}”给出约 {confidence_text} 的类别倾向（仅作病名排序参考）。"
            if confidence_text
            else f"分类模型当前更偏向“{cn}”。"
        )
        area_clause = (
            f"分割估计当前受害面积约 {damage_text}，仅用于描述受害程度。"
            if damage_text
            else "受害面积尚未形成可靠量化，仍以分类病名倾向与可见症状为主。"
        )
        return (
            f"{score_sentence}{area_clause}"
            f"{CLASSIFICATION_POLICY_NOTE}"
            "在实验室或田间复核前，可先按低风险路径管理并持续补证。"
        )
    return "视觉线索存在张力，当前结论应保持审慎并优先补充复核图像。"
