from __future__ import annotations

import ast
import re
from typing import Any

from app.core.agents.knowledge_prose import decision_support_to_prose, uncertainty_management_to_prose
from app.core.agents.leaf_clinical_context import (
    build_conflict_interpretation_narrative,
    build_leaf_clinical_profile,
)
from app.core.agents.prompts import REQUIRED_REPORT_SECTIONS
from app.core.caption.schema import CaptionSchema
from app.core.vision.presentation import class_name_to_cn, normalize_label


_CAPTION_VALUE_CN = {
    "green": "绿色",
    "yellow": "黄化",
    "brown": "褐变",
    "black": "黑褐色坏死",
    "gray": "灰霉样表现",
    "white": "白色霉层",
    "mixed": "混合色改变",
    "healthy": "健康",
    "chlorosis": "黄化",
    "necrosis": "坏死",
    "mold": "霉层",
    "water_soaked": "水浸状",
    "dry": "干枯",
    "round": "圆形",
    "irregular": "不规则",
    "angular": "角斑样",
    "concentric": "同心轮纹样",
    "diffuse": "弥散",
    "clear": "边界清楚",
    "blurred": "边界模糊",
    "yellow_halo": "黄色晕圈",
    "dark_ring": "深色环纹",
    "no_clear_boundary": "边界不清",
    "lower_leaf": "中下部叶片",
    "upper_leaf": "上部叶片",
    "leaf_back": "叶背",
    "leaf_edge": "叶缘",
    "stem": "茎部",
    "fruit": "果实",
    "whole_plant": "整株",
    "scattered": "散在分布",
    "clustered": "簇状分布",
    "vein_aligned": "沿叶脉分布",
    "expanding": "有扩展趋势",
    "patchy": "片状分布",
    "curling": "卷曲",
    "wilting": "萎蔫",
    "deformation": "畸形",
    "thickening": "增厚",
    "none": "无明显形态改变",
    "insect_holes": "虫孔",
    "frass": "虫粪",
    "webbing": "蛛网样痕迹",
    "eggs": "虫卵",
    "no_obvious_pest": "无明显虫害线索",
    "humidity_high": "环境湿度偏高",
    "poor_ventilation": "通风不足",
    "overwatering": "浇水偏多",
    "rainy_weather": "近期多雨或叶面持水",
    "neighboring_outbreak": "邻近植株可能有相似情况",
    "unknown": "无法判断",
}

_INTERNAL_TEXT_REPLACEMENTS = {
    "DINOv3": "图像分析",
    "分类头与分割头结果不一致": "整体印象与局部病斑特征并不完全一致",
    "分类头与分割头结果冲突": "整体印象与局部病斑特征并不完全一致",
    "分类头": "整体印象",
    "分割头": "局部病斑特征",
    "补充叶背近景、同叶位复拍图和整株图像": "继续保持审慎判断",
    "补充叶背近景和同叶位复拍图像": "继续保持审慎判断",
    "进一步检验": "进一步观察",
    "进一步检测": "进一步观察",
    "补图": "继续观察",
}

_SUMMARY_CONCLUSION_PATTERN = re.compile(
    r"(倾向于|更偏向|首要诊断|置信|把握度|当前判断|倾向性诊断|相对明确诊断|疑似|考虑为|更像)"
)


def _text(value: Any) -> str:
    raw = getattr(value, "value", value)
    if raw is None:
        return ""
    return str(raw).strip()


def _coerce_structured_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = _text(value)
    if not text:
        return value
    if not (
        (text.startswith("{") and text.endswith("}"))
        or (text.startswith("[") and text.endswith("]"))
    ):
        return value
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return value
    return parsed if isinstance(parsed, (dict, list)) else value


def _coerce_mapping(value: Any) -> dict[str, Any]:
    parsed = _coerce_structured_value(value)
    return parsed if isinstance(parsed, dict) else {}


def _coerce_list(value: Any) -> list[Any]:
    parsed = _coerce_structured_value(value)
    return parsed if isinstance(parsed, list) else []


def _normalize_differential_items(values: Any) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in _coerce_list(values):
        mapping = _coerce_mapping(item)
        if not mapping:
            continue
        name = _normalize_internal_text(class_name_to_cn(_text(mapping.get("name"))))
        if not name or any(existing.get("name") == name for existing in cleaned):
            continue
        cleaned.append(
            {
                "name": name,
                "why_supported": _normalize_internal_text(_text(mapping.get("why_supported"))),
                "why_not_primary": _normalize_internal_text(_text(mapping.get("why_not_primary"))),
            }
        )
    return cleaned


def _normalize_diagnosis_entries(values: Any) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        mapping = _coerce_mapping(item)
        if not mapping:
            continue
        diagnosis = _normalize_internal_text(class_name_to_cn(_text(mapping.get("diagnosis"))))
        if not diagnosis:
            continue
        cleaned.append(
            {
                "diagnosis": diagnosis,
                "supporting": _list_text(mapping.get("supporting", []), limit=6),
                "counter": _list_text(mapping.get("counter", []), limit=5),
                "missing": _list_text(mapping.get("missing", []), limit=5),
                "sources": _list_text(mapping.get("sources", []), limit=6),
            }
        )
    return cleaned


def _looks_mojibake(text: str) -> bool:
    markers = ("閸", "閻", "鐠", "閺", "瑜", "閵", "闂", "缁", "婢", "缂", "褰撳", "浠嶄互", "鐥囩姸")
    return any(marker in text for marker in markers)


def _normalize_internal_text(text: str) -> str:
    value = str(text).strip()
    if not value:
        return ""
    for source, target in _INTERNAL_TEXT_REPLACEMENTS.items():
        value = value.replace(source, target)
    value = value.replace("请补图", "当前结论仍需审慎解释")
    value = value.replace("无法判断", "仍有关键判断点未完全澄清")
    return " ".join(value.split())


def _to_cn(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return _CAPTION_VALUE_CN.get(text, text)


def _list_text(values: Any, *, limit: int | None = None, to_cn: bool = False) -> list[str]:
    if isinstance(values, str):
        items = [values]
    elif isinstance(values, list):
        items = values
    else:
        return []
    cleaned: list[str] = []
    for item in items:
        text = _to_cn(item) if to_cn else _normalize_internal_text(_text(item))
        text = re.sub(r"^[、，；。:\-]+", "", text).strip()
        if not text or text in cleaned:
            continue
        cleaned.append(text)
        if limit is not None and len(cleaned) >= limit:
            break
    return cleaned


def _caption_symptom_summary(
    caption: CaptionSchema,
    clinical_profile: dict[str, Any] | None = None,
) -> list[str]:
    if clinical_profile is not None:
        high_damage = bool(clinical_profile.get("high_damage_for_symptom_filter"))
        has_upper_leaf = bool(clinical_profile.get("has_upper_leaf_distribution"))
    else:
        try:
            area_ratio = float(getattr(caption.numeric, "area_ratio", 0.0) or 0.0)
        except (TypeError, ValueError):
            area_ratio = 0.0
        try:
            severity = float(getattr(caption.numeric, "severity_score", 0.0) or 0.0)
        except (TypeError, ValueError):
            severity = 0.0
        high_damage = area_ratio >= 0.35 or severity >= 0.65
        has_upper_leaf = any(_text(item) == "upper_leaf" for item in caption.symptoms.distribution_position)

    symptom_groups = [
        caption.symptoms.color,
        caption.symptoms.tissue_state,
        caption.symptoms.spot_shape,
        caption.symptoms.boundary,
        caption.symptoms.distribution_position,
        caption.symptoms.distribution_pattern,
        caption.symptoms.morph_change,
        caption.symptoms.pest_cues,
        caption.symptoms.co_signs,
    ]
    values: list[str] = []
    for group in symptom_groups:
        for item in group:
            text = _to_cn(item)
            if not text or text in {"未知", "无法判断"} or text in values:
                continue
            if high_damage and text == "散在分布":
                continue
            if high_damage and has_upper_leaf and text == "叶缘":
                continue
            values.append(text)
    return values[:8]


def _build_case_summary(
    case_text: str,
    caption: CaptionSchema,
    *,
    clinical_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "crop": "水稻",
        "case_text": _normalize_internal_text(_text(case_text)),
        "visual_summary": _normalize_internal_text(_text(caption.visual_summary)),
        "observed_symptoms": _caption_symptom_summary(caption, clinical_profile=clinical_profile),
        "followup_questions": _list_text(caption.followup_questions, limit=3),
    }


def _format_percent(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if numeric < 0:
        return ""
    if numeric <= 1.0:
        numeric *= 100.0
    return f"{numeric:.1f}%"


def _build_image_specific_basis(
    *,
    clinical_profile: dict[str, Any],
    primary_name: str,
    secondary_name: str,
) -> list[str]:
    support_line = str(clinical_profile.get("basis_support_line") or "").strip()
    limit_line = str(clinical_profile.get("basis_limit_line") or "").strip()
    conclusion_line = (
        f"因此更稳妥的表达是：将“{primary_name}”列为首位疑似候选，"
        f"并继续与“{secondary_name or '其他坏死性叶部病害'}”做并行鉴别。"
    )
    return [support_line, limit_line, conclusion_line]


def _build_consistency_note(case_text: str, caption: CaptionSchema) -> str:
    if _text(case_text) and _text(caption.visual_summary):
        return "文字描述与图像摘要大体同向，可作为当前病例判断的共同基础。"
    if _text(case_text):
        return "当前仍可把文字描述视为重要的辅助线索。"
    return ""


def _normalize_primary_source(value: Any) -> str:
    raw = _text(value)
    if raw == "分类头":
        return "整体视觉印象"
    if raw == "分割头":
        return "局部病斑特征"
    return _normalize_internal_text(raw)


def _disease_name_cn(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return _normalize_internal_text(class_name_to_cn(text))


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _localize_visual_candidates(
    values: Any,
    *,
    include_ratio: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    localized: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        disease_name = _disease_name_cn(item.get("class_name_cn") or item.get("class_name"))
        if not disease_name:
            continue
        payload: dict[str, Any] = {
            "病害名称": disease_name,
            "置信度": _to_float(item.get("confidence", 0.0)),
        }
        if include_ratio:
            payload["病斑面积占叶片比例"] = _to_float(item.get("ratio_of_leaf", 0.0))
        localized.append(payload)
    return localized


def _localize_caption_answer_confidences(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    localized: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        answer = _to_cn(item.get("answer"))
        if not answer:
            continue
        localized.append(
            {
                "问题": _normalize_internal_text(_text(item.get("question"))),
                "答案": _normalize_internal_text(answer),
                "置信度": _to_float(item.get("confidence", 0.0)),
            }
        )
    return localized


def _build_ranked_differentials(final_result: dict[str, Any]) -> list[dict[str, str]]:
    top = final_result.get("top_diagnosis", {}) if isinstance(final_result, dict) else {}
    top_name = _text(top.get("name")).lower()
    ranked: list[dict[str, str]] = []

    for item in final_result.get("candidates", []) if isinstance(final_result, dict) else []:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if not name or name.lower() == top_name or any(existing["name"] == name for existing in ranked):
            continue
        ranked.append(
            {
                "name": name,
                "why_supported": _normalize_internal_text(_text(item.get("why_like"))),
                "why_not_primary": _normalize_internal_text(_text(item.get("why_unlike"))),
            }
        )
        if len(ranked) >= 3:
            return ranked

    evidence_board = final_result.get("evidence_board", []) if isinstance(final_result, dict) else []
    if isinstance(evidence_board, list):
        for item in evidence_board:
            if not isinstance(item, dict):
                continue
            name = _text(item.get("diagnosis"))
            if not name or name.lower() == top_name or any(existing["name"] == name for existing in ranked):
                continue
            supporting = _list_text(item.get("supporting", []), limit=1)
            counter = _list_text(item.get("counter", []), limit=1)
            ranked.append(
                {
                    "name": name,
                    "why_supported": supporting[0] if supporting else "",
                    "why_not_primary": counter[0] if counter else "",
                }
            )
            if len(ranked) >= 3:
                break
    return ranked


def _build_primary_reasoning(final_result: dict[str, Any]) -> str:
    top = final_result.get("top_diagnosis", {}) if isinstance(final_result, dict) else {}
    top_name = _text(top.get("name")).lower()
    for item in final_result.get("candidates", []) if isinstance(final_result, dict) else []:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name")).lower()
        if name == top_name:
            return _normalize_internal_text(_text(item.get("why_like")))
    evidence_board = final_result.get("evidence_board", []) if isinstance(final_result, dict) else []
    if isinstance(evidence_board, list):
        for item in evidence_board:
            if not isinstance(item, dict):
                continue
            name = _text(item.get("diagnosis")).lower()
            if name == top_name:
                supporting = _list_text(item.get("supporting", []), limit=1)
                return supporting[0] if supporting else ""
    return ""


def _build_action_timeline(final_result: dict[str, Any], safety_result: dict[str, Any]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    rescue_plan = final_result.get("rescue_plan", []) if isinstance(final_result, dict) else []
    if isinstance(rescue_plan, list):
        for item in rescue_plan[:3]:
            if not isinstance(item, dict):
                continue
            phase = _normalize_internal_text(_text(item.get("phase")))
            objective = _normalize_internal_text(_text(item.get("objective")))
            actions = _list_text(item.get("actions", []), limit=3)
            rationale = _list_text(item.get("rationale", []), limit=2)
            risk_level = _normalize_internal_text(_text(item.get("risk_level")))
            if phase or objective or actions:
                timeline.append(
                    {
                        "phase": phase or f"阶段 {len(timeline) + 1}",
                        "objective": objective,
                        "actions": actions,
                        "rationale": rationale,
                        "risk_level": risk_level,
                    }
                )
    if timeline:
        return timeline

    immediate_actions = _list_text(final_result.get("actions", []), limit=3) if isinstance(final_result, dict) else []
    followups = _list_text(safety_result.get("required_followups", []), limit=3)
    if immediate_actions:
        timeline.append(
            {
                "phase": "立即处理",
                "objective": "先做低风险控险和现场管理",
                "actions": immediate_actions,
                "rationale": [],
                "risk_level": "低至中",
            }
        )
    if followups:
        timeline.append(
            {
                "phase": "短期复查",
                "objective": "围绕当前未定判断点持续观察",
                "actions": followups,
                "rationale": [],
                "risk_level": "低",
            }
        )
    return timeline


def _build_escalation_conditions(
    final_result: dict[str, Any],
    safety_result: dict[str, Any],
    vision_conflict: dict[str, Any],
) -> list[str]:
    conditions = _list_text(final_result.get("monitoring_plan", []), limit=3) if isinstance(final_result, dict) else []
    conditions += _list_text(safety_result.get("required_followups", []), limit=2)
    if bool(vision_conflict.get("has_conflict")):
        conditions.append("若后续观察仍无法解释当前图像线索分歧，应保持人工审慎复核。")
    return _list_text(conditions, limit=4)


def _iter_expert_turns(rounds: Any) -> list[dict[str, Any]]:
    if not isinstance(rounds, list):
        return []
    turns: list[dict[str, Any]] = []
    for round_item in rounds:
        if not isinstance(round_item, dict):
            continue
        expert_turns = round_item.get("expert_turns", [])
        if not isinstance(expert_turns, list):
            continue
        for turn in expert_turns:
            if isinstance(turn, dict):
                turns.append(turn)
    return turns


def _latest_expert_turn(rounds: Any, agent_name: str) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for turn in _iter_expert_turns(rounds):
        if _text(turn.get("agent_name")) == agent_name:
            latest = turn
    return latest


def _sanitize_summary_fact_text(text: str, *, blocked_terms: list[str]) -> str:
    value = _normalize_internal_text(text)
    if not value:
        return ""
    for term in blocked_terms:
        normalized_term = _normalize_internal_text(term)
        if normalized_term and normalized_term in value:
            return ""
    if _SUMMARY_CONCLUSION_PATTERN.search(value):
        return ""
    return value


def _select_secondary_differential(
    *,
    ranked_differentials: list[dict[str, str]],
    visual_candidates: list[dict[str, Any]],
    primary_name: str,
) -> str:
    for item in ranked_differentials:
        name = _normalize_internal_text(_text(item.get("name")))
        if name and name != primary_name:
            return name
    for item in visual_candidates:
        name = _normalize_internal_text(_text(item.get("name")))
        if name and name != primary_name:
            return name
    return ""


def _gap_diagnostic_value(gap: str, primary_name: str, secondary_name: str, conflict_text: str) -> str:
    text = gap.strip()
    if not text:
        return ""
    if any(token in text for token in ("叶背", "背面", "霉层")):
        return f"这类信息能帮助判断是否存在更支持“{primary_name}”或“{secondary_name or '其他相似叶部病害'}”的典型附着特征。"
    if any(token in text for token in ("整株", "新叶", "叶柄", "茎", "果实", "邻近")):
        return "这类信息能判断病害是局限于单叶，还是已经扩展到整株其他部位，从而影响主诊断排序和处理强度。"
    if any(token in text for token in ("24", "48", "复拍", "时序", "扩展", "变化", "新发")):
        return "这类信息能帮助区分病斑是持续外扩的大块坏死过程，还是相对稳定的小斑型病程。"
    if any(token in text for token in ("湿度", "结露", "通风", "灌溉", "环境")):
        return "这类信息能判断当前环境是否足以持续推动侵染性叶部病害发展，并决定是否需要提高控险强度。"
    if conflict_text:
        return f"这类信息的价值在于进一步解释当前图像线索分歧，即{conflict_text}。"
    return "这类信息能帮助缩小相似病害之间的判断差距，并减少误治风险。"


def _gap_next_step(gap: str) -> str:
    text = gap.strip()
    if not text:
        return ""
    if any(token in text for token in ("叶背", "背面", "霉层")):
        return "优先补看叶背近景，确认是否存在霉层、渗出或其他更有指向性的附着表现。"
    if any(token in text for token in ("整株", "新叶", "叶柄", "茎", "果实", "邻近")):
        return "同步检查同株上部新叶、叶柄、茎秆、果实及邻近叶片，看是否存在同类受害。"
    if any(token in text for token in ("24", "48", "复拍", "时序", "扩展", "变化", "新发")):
        return "在 24 到 48 小时内复拍同叶位，重点看边界、颜色、扩展速度和是否出现新发病斑。"
    if any(token in text for token in ("湿度", "结露", "通风", "灌溉", "环境")):
        return "记录近两天湿度、结露、通风和灌溉方式，评估环境是否持续利于病害推进。"
    return "围绕这个判断点补充针对性观察或必要时送检，优先收集最能改变诊断排序的证据。"


def _build_evidence_gap_items(
    *,
    final_result: dict[str, Any],
    safety_result: dict[str, Any],
    berry_qa_guidance: dict[str, Any],
    vision_conflict: dict[str, Any],
    primary_name: str,
    secondary_name: str,
) -> list[dict[str, str]]:
    raw_items = _list_text(final_result.get("evidence_to_collect", []), limit=4)
    raw_items += _list_text(safety_result.get("required_followups", []), limit=3)
    raw_items += _list_text(berry_qa_guidance.get("evidence_gaps", []), limit=3)
    unique_items = _list_text(raw_items, limit=5)
    conflict_text = _build_conflict_interpretation(vision_conflict)
    return [
        {
            "gap": gap,
            "diagnostic_value": _gap_diagnostic_value(gap, primary_name, secondary_name, conflict_text),
            "next_step": _gap_next_step(gap),
        }
        for gap in unique_items
    ]


_HIGH_RISK_TREATMENT_PATTERN = re.compile(
    r"(喷施|喷雾|药剂|杀菌剂|杀虫剂|铜制剂|抗生素|化学防治|对症用药|药液)"
)
_NEGATIVE_DIRECTIVE_PATTERN = re.compile(r"(暂不|不建议|不要|不宜|先不|避免|谨慎)")


def _is_direct_high_risk_action(text: str) -> bool:
    value = text.strip()
    if not value:
        return False
    if not _HIGH_RISK_TREATMENT_PATTERN.search(value):
        return False
    return _NEGATIVE_DIRECTIVE_PATTERN.search(value) is None


def _to_low_risk_actions(values: list[str], *, limit: int = 5) -> list[str]:
    cleaned = _list_text(values)
    safe_actions: list[str] = []
    removed_high_risk = False
    for item in cleaned:
        if _is_direct_high_risk_action(item):
            removed_high_risk = True
            continue
        safe_actions.append(item)
    if removed_high_risk:
        safe_actions.append("针对性药剂处理应在补齐叶背、整株和时序证据后再决定，当前不前置。")
    return _list_text(safe_actions, limit=limit)


def _build_today_actions(final_result: dict[str, Any], berry_qa_guidance: dict[str, Any]) -> list[str]:
    actions = _to_low_risk_actions(
        berry_qa_guidance.get("today_actions", [])
        + berry_qa_guidance.get("control_options", [])
        + _list_text(final_result.get("actions", []), limit=4),
        limit=5,
    )
    if actions:
        return actions
    return [
        "先摘除重病叶并单独处理，避免与健康叶片混放。",
        "立即改善通风，减少叶面持续潮湿和结露时间。",
        "24 到 48 小时内固定机位复拍同叶位，记录外扩和新发情况。",
    ]


def _build_observe_48h(
    final_result: dict[str, Any],
    safety_result: dict[str, Any],
    berry_qa_guidance: dict[str, Any],
) -> list[str]:
    return _list_text(
        berry_qa_guidance.get("observe_points", [])
        + _list_text(final_result.get("monitoring_plan", []), limit=4)
        + _list_text(safety_result.get("required_followups", []), limit=4),
        limit=5,
    )


def _build_risk_watchpoints(
    final_result: dict[str, Any],
    safety_result: dict[str, Any],
    berry_qa_guidance: dict[str, Any],
) -> list[str]:
    return _list_text(
        berry_qa_guidance.get("risk_flags", [])
        + _list_text(final_result.get("safety_notes", []), limit=4)
        + _list_text(safety_result.get("flags", []), limit=3),
        limit=5,
    )


def _build_upgrade_triggers(
    final_result: dict[str, Any],
    safety_result: dict[str, Any],
    berry_qa_guidance: dict[str, Any],
) -> list[str]:
    raw_items = (
        _list_text(final_result.get("monitoring_plan", []), limit=4)
        + _list_text(safety_result.get("required_followups", []), limit=3)
        + _list_text(berry_qa_guidance.get("risk_flags", []), limit=3)
    )
    triggers: list[str] = []
    for item in raw_items:
        text = item.strip()
        if not text:
            continue
        if any(token in text for token in ("外扩", "加重", "继续", "新叶", "整株", "蔓延", "同步受害")):
            triggers.append(text if text.startswith("若") else f"若{text}")
    if not triggers:
        triggers.append("若 24 到 48 小时内病斑继续外扩或新叶出现同类症状，应及时提高处理强度。")
    return _list_text(triggers, limit=4)


def _rank_shift_hint_for_gap(gap: str, primary_name: str, secondary_name: str) -> str:
    text = gap.strip()
    if not text:
        return ""
    secondary = secondary_name or "替代候选病害"
    if any(token in text for token in ("叶背", "背面", "霉层", "浸润")):
        return f"若叶背出现更典型阳性征象，“{secondary}”排序应上调；若持续缺乏该征象，“{primary_name}”排序更稳。"
    if any(token in text for token in ("24", "48", "复拍", "时序", "扩展", "新发")):
        return "若 24 到 48 小时外扩速度明显加快或连续新发，应上调侵染性候选；若变化轻微且无新发，可下调激进判断。"
    if any(token in text for token in ("整株", "新叶", "叶柄", "茎", "果实", "邻近")):
        return "若整株多叶位同步受累，应提高扩展性病害权重；若仍局限于单叶，应维持保守排序。"
    if any(token in text for token in ("湿度", "结露", "通风", "灌溉", "环境")):
        return "若持续高湿和结露并伴随病斑推进，应提高风险等级；若环境纠偏后病情趋稳，可下调处理强度。"
    return f"该补证结果可直接影响“{primary_name}”与“{secondary}”的排序先后。"


def _build_uncertainty_management(
    *,
    vision_conflict: dict[str, Any],
    gap_items: list[dict[str, str]],
    primary_name: str,
    secondary_name: str,
    clinical_profile: dict[str, Any],
) -> dict[str, Any]:
    classification_result = _normalize_internal_text(_text(vision_conflict.get("classification_result")))
    classification_score_note = _normalize_internal_text(_text(vision_conflict.get("classification_score_note")))
    local_lesion_impression = _normalize_internal_text(
        str(clinical_profile.get("local_lesion_area_sentence") or "").strip()
    )
    conflict_summary = _build_conflict_interpretation(vision_conflict)
    key_discriminators: list[dict[str, str]] = []
    for item in gap_items[:4]:
        if not isinstance(item, dict):
            continue
        gap = _normalize_internal_text(_text(item.get("gap")))
        if not gap:
            continue
        key_discriminators.append(
            {
                "gap": gap,
                "diagnostic_value": _normalize_internal_text(_text(item.get("diagnostic_value"))),
                "next_step": _normalize_internal_text(_text(item.get("next_step"))),
                "rank_shift_hint": _rank_shift_hint_for_gap(gap, primary_name, secondary_name),
            }
        )
    if not key_discriminators:
        key_discriminators = [
            {
                "gap": "叶背特征（霉层/浸润）",
                "diagnostic_value": "用于区分整体印象与局部病斑特征冲突的关键证据。",
                "next_step": "补拍叶背近景并与当前叶面病斑同叶位对照。",
                "rank_shift_hint": _rank_shift_hint_for_gap("叶背特征", primary_name, secondary_name),
            },
            {
                "gap": "24 到 48 小时扩展速度",
                "diagnostic_value": "用于判断病程是否进入快速外扩阶段。",
                "next_step": "固定机位复拍并记录外扩幅度与新发病斑数量。",
                "rank_shift_hint": _rank_shift_hint_for_gap("24-48 小时扩展", primary_name, secondary_name),
            },
        ]
    return {
        "conflict_point": {
            "overall_impression": classification_result or "整体印象未明确",
            "local_lesion_impression": local_lesion_impression,
            "conflict_summary": conflict_summary,
            "model_score_interpretation": classification_score_note
            or "模型分数仅反映类别倾向，不等同于确诊概率。",
            "evidence_ceiling": (
                "当前更稳妥的证据上限是“存在严重叶部坏死性损伤”，病名以分类模型倾向为准并需补证后收敛；"
                + str(clinical_profile.get("classification_policy_note") or "").strip()
            ),
        },
        "key_discriminators": key_discriminators,
    }


def _threshold_hint(observe_item: str) -> str:
    text = observe_item.strip()
    if any(token in text for token in ("外扩", "扩展", "扩大")):
        return "建议阈值：24 到 48 小时外扩面积较基线增加 >=20% 视为升级信号；<5% 且无新发可考虑下调。"
    if any(token in text for token in ("新叶", "新发", "邻近", "整株")):
        return "建议阈值：48 小时内新增同类病斑 >=2 处或邻株同步出现，视为升级信号。"
    if any(token in text for token in ("叶背", "霉层", "浸润")):
        return "建议阈值：一旦出现叶背典型阳性征象，优先上调高风险候选并升级复核。"
    return "建议阈值：连续两次复查同向变化后再调整排序与处置强度。"


def _build_decision_support(
    *,
    today_actions: list[str],
    observe_48h: list[str],
    escalation_conditions: list[str],
    prohibited_actions: list[str],
    required_followups: list[str],
    primary_name: str,
    secondary_name: str,
) -> dict[str, Any]:
    upgrade_conditions = _list_text(
        escalation_conditions
        + [
            "若 24 到 48 小时内病斑外扩面积较基线增加 >=20%，应提高处理强度。",
            "若 48 小时内新增同类病斑 >=2 处或整株多叶位同步受累，应升级复核与处置。",
        ],
        limit=5,
    )
    downgrade_conditions = _list_text(
        [
            "若 48 小时内外扩幅度 <5% 且无新发病斑，可维持或下调处理强度。",
            "若关键分歧证据持续阴性，且环境纠偏后病情趋稳，可降低高风险候选权重。",
        ],
        limit=3,
    )
    post_review_branches = _list_text(
        [
            f"若触发升级条件：上调“{secondary_name or '高风险候选'}”权重，并进入升级处理路径。",
            f"若满足降级条件：维持“{primary_name}”为主排序并继续低风险管理复查。",
        ],
        limit=2,
    )
    return {
        "current_stage_actions": _list_text(today_actions, limit=5),
        "observe_24_48h": [
            {"item": item, "threshold_hint": _threshold_hint(item)}
            for item in _list_text(observe_48h, limit=5)
        ],
        "upgrade_conditions": upgrade_conditions,
        "downgrade_conditions": downgrade_conditions,
        "prohibited_actions": _list_text(prohibited_actions, limit=4),
        "review_nodes": _list_text(required_followups, limit=4),
        "post_review_branches": post_review_branches,
    }


def _latest_shared_state(rounds: Any) -> dict[str, Any]:
    if not isinstance(rounds, list):
        return {}
    for round_item in reversed(rounds):
        if not isinstance(round_item, dict):
            continue
        shared_state = round_item.get("shared_state")
        if isinstance(shared_state, dict):
            return shared_state
    return {}


def _board_dict(shared_state: dict[str, Any], key: str) -> dict[str, Any]:
    value = shared_state.get(key, {}) if isinstance(shared_state, dict) else {}
    board = _coerce_mapping(value)
    if not board:
        return {}
    if key == "diagnosis_board":
        return {
            "working_diagnoses": _list_text(board.get("working_diagnoses", []), limit=5),
            "supporting": _list_text(board.get("supporting", []), limit=6),
            "counter": _list_text(board.get("counter", []), limit=5),
            "differentials": _normalize_differential_items(board.get("differentials", [])),
        }
    if key == "evidence_board":
        return {
            "missing_evidence": _list_text(board.get("missing_evidence", []), limit=6),
            "verification_value": _list_text(board.get("verification_value", []), limit=6),
        }
    if key == "action_board":
        return {
            "today_actions": _list_text(board.get("today_actions", []), limit=6),
            "control_options": _list_text(board.get("control_options", []), limit=6),
            "observe_48h": _list_text(board.get("observe_48h", []), limit=6),
            "escalation_triggers": _list_text(board.get("escalation_triggers", []), limit=5),
            "management_timeline": _list_text(board.get("management_timeline", []), limit=5),
            "low_risk_actions": _list_text(board.get("low_risk_actions", []), limit=5),
            "environment_adjustments": _list_text(board.get("environment_adjustments", []), limit=5),
            "followup_nodes": _list_text(board.get("followup_nodes", []), limit=5),
        }
    if key == "risk_board":
        return {
            "prohibited_actions": _list_text(board.get("prohibited_actions", []), limit=5),
            "risk_flags": _list_text(board.get("risk_flags", []), limit=6),
            "confidence_boundary": _list_text(board.get("confidence_boundary", []), limit=5),
            "overtreatment_risks": _list_text(board.get("overtreatment_risks", []), limit=5),
            "undertreatment_risks": _list_text(board.get("undertreatment_risks", []), limit=5),
            "followup_nodes": _list_text(board.get("followup_nodes", []), limit=5),
        }
    return board


def _diagnosis_entries_from_state(shared_state: dict[str, Any], final_result: dict[str, Any]) -> list[dict[str, Any]]:
    entries = shared_state.get("diagnosis_evidence", []) if isinstance(shared_state, dict) else []
    normalized_entries = _normalize_diagnosis_entries(entries)
    if normalized_entries:
        return normalized_entries
    fallback = final_result.get("evidence_board", []) if isinstance(final_result, dict) else []
    normalized_fallback = _normalize_diagnosis_entries(fallback)
    if normalized_fallback:
        return normalized_fallback
    return []


def _build_berry_qa_guidance(rounds: Any) -> dict[str, Any]:
    turn = _latest_expert_turn(rounds, "berry_qa_expert")
    if not turn:
        return {
            "today_actions": [],
            "control_options": [],
            "observe_points": [],
            "evidence_gaps": [],
            "risk_flags": [],
        }
    return {
        "today_actions": _list_text(turn.get("today_actions", []) or turn.get("actions", []), limit=4),
        "control_options": _list_text(turn.get("control_options", []), limit=4),
        "observe_points": _list_text(turn.get("observe_48h", []) or turn.get("questions_to_ask", []), limit=4),
        "evidence_gaps": _list_text(turn.get("key_evidence_gaps", []) or turn.get("questions_to_ask", []), limit=4),
        "risk_flags": _list_text(turn.get("escalation_triggers", []) or turn.get("risks", []), limit=4),
    }


def _build_candidate_diagnoses(shared_state: dict[str, Any], vision_result: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    diagnosis_board = _board_dict(shared_state, "diagnosis_board")
    evidence_entries = _diagnosis_entries_from_state(shared_state, {})
    candidates: list[dict[str, Any]] = []
    for item in evidence_entries[:3]:
        name = _text(item.get("diagnosis"))
        if not name:
            continue
        candidates.append(
            {
                "name": name,
                "supporting_evidence": _list_text(item.get("supporting", []), limit=3),
                "counter_evidence": _list_text(item.get("counter", []), limit=2),
                "missing_information": _list_text(item.get("missing", []), limit=3),
            }
        )
    for item in diagnosis_board.get("differentials", []) if isinstance(diagnosis_board, dict) else []:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if not name or any(existing.get("name") == name for existing in candidates):
            continue
        candidates.append(
            {
                "name": name,
                "supporting_evidence": _list_text([item.get("why_supported", "")], limit=2),
                "counter_evidence": _list_text([item.get("why_not_primary", "")], limit=2),
                "missing_information": [],
            }
        )
    visual_candidates = _build_visual_candidate_diagnoses(vision_result)
    if candidates:
        merged: list[dict[str, Any]] = []
        seen: dict[str, dict[str, Any]] = {}
        for item in candidates + visual_candidates:
            name = _text(item.get("name"))
            norm = normalize_label(name)
            if not name or not norm:
                continue
            current = seen.get(norm)
            if current is None:
                current = {
                    "name": name,
                    "supporting_evidence": [],
                    "counter_evidence": [],
                    "missing_information": [],
                }
                seen[norm] = current
                merged.append(current)
            current["supporting_evidence"] = _list_text(
                current["supporting_evidence"] + _list_text(item.get("supporting_evidence", []), limit=4),
                limit=4,
            )
            current["counter_evidence"] = _list_text(
                current["counter_evidence"] + _list_text(item.get("counter_evidence", []), limit=3),
                limit=3,
            )
            current["missing_information"] = _list_text(
                current["missing_information"] + _list_text(item.get("missing_information", []), limit=3),
                limit=3,
            )
        return merged[:3]
    working = _list_text(diagnosis_board.get("working_diagnoses", []), limit=2)
    if working:
        return [{"name": name, "supporting_evidence": [], "counter_evidence": [], "missing_information": []} for name in working]
    return visual_candidates


def build_final_decision_packet(
    *,
    case_text: str,
    caption: CaptionSchema,
    shared_state: dict[str, Any],
    vision_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnosis_board = _board_dict(shared_state, "diagnosis_board")
    evidence_board = _board_dict(shared_state, "evidence_board")
    action_board = _board_dict(shared_state, "action_board")
    risk_board = _board_dict(shared_state, "risk_board")
    candidates = _build_candidate_diagnoses(shared_state, vision_result)
    visual_candidates = _build_visual_candidate_diagnoses(vision_result)
    uncertainty_score = float(shared_state.get("uncertainty_score", 0.5) or 0.5)
    primary_name = candidates[0]["name"] if candidates else _text((diagnosis_board.get("working_diagnoses") or [""])[0])
    statement_style = "倾向性诊断，避免确定性表述" if uncertainty_score >= 0.25 else "可给出相对明确的判断，但仍需说明边界"

    evidence_sufficiency = _normalize_internal_text(_text(shared_state.get("evidence_sufficiency")))
    if not evidence_sufficiency or _looks_mojibake(evidence_sufficiency):
        evidence_sufficiency = "当前已可形成首位疑似判断，后续仍需结合复查证据持续校正。"

    return {
        "case_summary": _build_case_summary(case_text, caption),
        "vision_conflict": _build_vision_conflict_section(vision_result),
        "diagnosis_summary": {
            "primary_candidate": primary_name,
            "candidate_diagnoses": candidates,
            "visual_candidates": visual_candidates,
            "uncertainty_score": round(uncertainty_score, 4),
            "statement_style": statement_style,
            "evidence_sufficiency": evidence_sufficiency,
        },
        "missing_information": _list_text(evidence_board.get("missing_evidence", []), limit=4),
        "recommended_actions": _list_text(
            _list_text(action_board.get("today_actions", []), limit=4)
            + _list_text(action_board.get("control_options", []), limit=4),
            limit=5,
        ),
        "verification_tasks": _list_text(evidence_board.get("verification_value", []), limit=4),
        "safety_notes": _list_text(risk_board.get("risk_flags", []), limit=4),
        "report_priority": [],
        "boards": {
            "diagnosis_board": diagnosis_board,
            "evidence_board": evidence_board,
            "action_board": action_board,
            "risk_board": risk_board,
        },
    }


def _build_vision_conflict_section(vision_result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(vision_result, dict):
        return {}
    fusion_summary = vision_result.get("fusion_summary", {})
    conflict_analysis = vision_result.get("conflict_analysis", {})
    structured_visual_evidence = vision_result.get("structured_visual_evidence", {})
    if not isinstance(fusion_summary, dict):
        fusion_summary = {}
    if not isinstance(conflict_analysis, dict):
        conflict_analysis = {}
    if not isinstance(structured_visual_evidence, dict):
        structured_visual_evidence = {}
    bundle = fusion_summary.get("visual_evidence_bundle", {})
    if not isinstance(bundle, dict):
        bundle = structured_visual_evidence if isinstance(structured_visual_evidence, dict) else {}

    primary_source = _normalize_internal_text(_text(fusion_summary.get("primary_source")))
    if not primary_source:
        primary_source = "视觉综合判断"

    classification_candidates = bundle.get("classification_candidates_over_30", [])
    caption_answers = bundle.get("caption_answer_confidences", [])
    area_summary = bundle.get("segmentation_area_summary", {})
    if not isinstance(area_summary, dict):
        area_summary = {}

    conflict_flag = bool(
        conflict_analysis.get("has_conflict")
        or fusion_summary.get("classification_segmentation_conflict")
    )
    reason_summary = _normalize_internal_text(
        _text(conflict_analysis.get("reason_summary") or fusion_summary.get("reason_summary"))
    )
    primary_visual_conclusion = _disease_name_cn(
        fusion_summary.get("primary_visual_conclusion")
        or fusion_summary.get("primary_visual_conclusion_en")
    )
    classification_result = _disease_name_cn(
        fusion_summary.get("classification_result")
        or conflict_analysis.get("classification_result_cn")
        or conflict_analysis.get("classification_result")
    )
    classification_confidence = _to_float(fusion_summary.get("classification_confidence"), default=0.0)
    confidence_text = _format_percent(classification_confidence)
    if classification_result and confidence_text:
        score_note = f"模型对“{classification_result}”给出约 {confidence_text} 的类别倾向，该分数不等同于确诊概率。"
    else:
        score_note = "模型分数仅表示类别倾向，不等同于确诊概率。"
    area_summary_cn = {
        "病损面积占叶片比例": _to_float(
            area_summary.get("damaged_area_ratio_of_leaf", 0.0),
            default=0.0,
        ),
        "主病斑面积占叶片比例": _to_float(
            area_summary.get("dominant_segmentation_ratio_of_leaf", 0.0),
            default=0.0,
        ),
        "叶片像素": int(area_summary.get("leaf_pixels", 0) or 0),
        "病损像素": int(area_summary.get("diseased_pixels", 0) or 0),
    }

    return {
        "has_conflict": conflict_flag,
        "primary_visual_conclusion": primary_visual_conclusion,
        "primary_source": primary_source,
        "classification_result": classification_result,
        "classification_confidence": classification_confidence,
        "classification_score_note": score_note,
        "segmentation_result": "",
        "damaged_area_ratio_of_leaf": fusion_summary.get("damaged_area_ratio_of_leaf")
        if fusion_summary.get("damaged_area_ratio_of_leaf") is not None
        else area_summary.get("damaged_area_ratio_of_leaf"),
        "reason_summary": reason_summary,
        "reason_details": _list_text(
            conflict_analysis.get("reason_details", []),
            limit=4,
        ),
        "recommended_interpretation": _normalize_internal_text(
            _text(conflict_analysis.get("recommended_interpretation"))
        ),
        "visual_model_outputs": {
            "classification_candidates_over_30": _localize_visual_candidates(classification_candidates),
            "segmentation_candidates_over_30": [],
            "caption_answer_confidences": _localize_caption_answer_confidences(caption_answers),
            "segmentation_area_summary": area_summary_cn,
        },
    }


def _build_conflict_interpretation(vision_conflict: dict[str, Any]) -> str:
    return build_conflict_interpretation_narrative(vision_conflict if isinstance(vision_conflict, dict) else {})


def _build_visual_candidate_diagnoses(vision_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(vision_result, dict):
        return []

    image_analysis = vision_result.get("image_analysis", {})
    fusion_summary = vision_result.get("fusion_summary", {})
    structured_visual_evidence = vision_result.get("structured_visual_evidence", {})
    if not isinstance(image_analysis, dict):
        image_analysis = {}
    if not isinstance(fusion_summary, dict):
        fusion_summary = {}
    if not isinstance(structured_visual_evidence, dict):
        structured_visual_evidence = {}
    bundle = fusion_summary.get("visual_evidence_bundle", {})
    if not isinstance(bundle, dict):
        bundle = structured_visual_evidence if isinstance(structured_visual_evidence, dict) else {}

    candidate_map: dict[str, dict[str, Any]] = {}

    def ensure_candidate(raw_name: Any) -> dict[str, Any] | None:
        text = _text(raw_name)
        norm = normalize_label(text)
        if not text or norm in {"", "healthy", "leaf"}:
            return None
        current = candidate_map.get(norm)
        if current is None:
            current = {
                "name": class_name_to_cn(text),
                "supporting_evidence": [],
                "counter_evidence": [],
                "missing_information": [],
                "_score": 0.0,
            }
            candidate_map[norm] = current
        return current

    classification_candidates = bundle.get("classification_candidates_over_30", [])
    if isinstance(classification_candidates, list):
        for item in classification_candidates:
            if not isinstance(item, dict):
                continue
            confidence = float(item.get("confidence", 0.0) or 0.0)
            if confidence < 0.30:
                continue
            candidate = ensure_candidate(item.get("class_name"))
            if candidate is None:
                continue
            evidence = f"分类模型中“{candidate['name']}”呈现较高类别倾向（约 {_format_percent(confidence)}），仅作候选参考。"
            if evidence not in candidate["supporting_evidence"]:
                candidate["supporting_evidence"].append(evidence)
            candidate["_score"] = max(float(candidate["_score"]), confidence)

    if not candidate_map:
        top_predictions = image_analysis.get("top_predictions", [])
        if isinstance(top_predictions, list):
            for item in top_predictions:
                if not isinstance(item, dict):
                    continue
                confidence = float(item.get("confidence", 0.0) or 0.0)
                if confidence < 0.30:
                    continue
                candidate = ensure_candidate(item.get("class_name"))
                if candidate is None:
                    continue
                evidence = f"整体分类结果中，“{candidate['name']}”呈现较高类别倾向（约 {_format_percent(confidence)}），仅作候选参考。"
                if evidence not in candidate["supporting_evidence"]:
                    candidate["supporting_evidence"].append(evidence)
                candidate["_score"] = max(float(candidate["_score"]), confidence)

    primary_visual = _text(fusion_summary.get("primary_visual_conclusion"))
    if primary_visual and normalize_label(primary_visual) not in {"", "healthy", "leaf"}:
        candidate = ensure_candidate(primary_visual)
        if candidate is not None:
            evidence = f"当前视觉病种判断仍以整体分类为主，对“{candidate['name']}”有一定倾向，但证据仍需补齐。"
            if evidence not in candidate["supporting_evidence"]:
                candidate["supporting_evidence"].append(evidence)
            candidate["_score"] = max(float(candidate["_score"]), 2.0)

    damage_ratio = float(
        fusion_summary.get("damaged_area_ratio_of_leaf")
        or image_analysis.get("damaged_area_ratio_of_leaf")
        or 0.0
    )
    ranked = sorted(candidate_map.values(), key=lambda item: float(item.get("_score", 0.0)), reverse=True)
    result: list[dict[str, Any]] = []
    for item in ranked[:3]:
        supporting = _list_text(item.get("supporting_evidence", []), limit=2)
        if damage_ratio > 0:
            supporting.append(
                f"分割估计病损约占叶片 {_format_percent(damage_ratio)}，仅描述受害程度；"
                "病名排序仍以分类模型为主。"
            )
        result.append(
            {
                "name": item["name"],
                "supporting_evidence": _list_text(supporting, limit=3),
                "counter_evidence": ["当前仅基于单张叶片图像，尚缺病种特异性证据，暂不足以确诊。"],
                "missing_information": ["补拍叶背近景", "补拍整株分布图", "24 到 48 小时同叶位复拍"],
            }
        )
    return result


def _build_diagnosis_statement_packet(primary_name: str, classification_confidence: float) -> str:
    if not primary_name:
        return "当前仅形成候选方向，尚待更多图像与田间信息对齐。"
    if classification_confidence >= 0.85:
        return f"当前视觉分类对「{primary_name}」呈极强类别倾向，与可见病斑表型高度一致。"
    if classification_confidence >= 0.65:
        return f"当前将「{primary_name}」列为首位疑似方向，类别倾向明确，仍建议复查对齐田间实际。"
    return f"当前将「{primary_name}」作为首位排序参考，证据闭合前保持审慎口径。"


def _build_confidence_boundary_merged(
    *,
    primary_name: str,
    score_note: str,
    classification_confidence: float,
    extra_lines: list[str],
) -> list[str]:
    lines: list[str] = []
    if score_note:
        lines.append(score_note)
    pn = primary_name or "该病害"
    if classification_confidence >= 0.85:
        lines.append(f"视觉分类对「{pn}」呈极强倾向；结论仍受单张图像局限，建议以复查校准强度。")
    elif classification_confidence >= 0.65:
        lines.append(f"可将「{pn}」作为首位疑似（倾向明确），结合叶背与整株图像便于调整排序。")
    else:
        lines.append(f"类别倾向中等，「{pn}」暂作排序参考，需依赖复拍与时序观察加固。")
    for raw in extra_lines:
        t = _normalize_internal_text(str(raw))
        if t and t not in lines:
            lines.append(t)
    return _list_text(lines, limit=5)


def _second_candidate_brief_note(vision_conflict: dict[str, Any], primary_name: str) -> str:
    vmo = vision_conflict.get("visual_model_outputs") if isinstance(vision_conflict, dict) else {}
    if not isinstance(vmo, dict):
        return ""
    items = vmo.get("classification_candidates_over_30", [])
    if not isinstance(items, list):
        return ""
    ranked = sorted(
        [x for x in items if isinstance(x, dict) and _normalize_internal_text(str(x.get("病害名称", "")))],
        key=lambda x: _to_float(x.get("置信度")),
        reverse=True,
    )
    primary_n = _normalize_internal_text(primary_name or "")
    for x in ranked:
        name = _normalize_internal_text(str(x.get("病害名称", "")))
        if not name or (primary_n and name == primary_n):
            continue
        sc = _to_float(x.get("置信度"))
        if 0 < sc < 0.5:
            pct = _format_percent(sc)
            return f"次位候选「{name}」类别倾向约{pct}，显著弱于首位，正文用一句带过即可。"
        return ""
    return ""


def _disease_snippets_from_kb(documents: list[dict[str, Any]] | None, *, limit: int = 3) -> list[dict[str, str]]:
    if not documents:
        return []
    out: list[dict[str, str]] = []
    for doc in documents[:limit]:
        if not isinstance(doc, dict):
            continue
        title = str(doc.get("title") or "知识条目").strip()
        content = str(doc.get("content") or "").strip().replace("\r\n", " ").replace("\n", " ")
        excerpt = (content[:320] + "…") if len(content) > 320 else content
        if not excerpt:
            continue
        src = str(doc.get("source_name") or "").strip()
        out.append({"title": title, "excerpt": excerpt, "source_name": src})
    return out


def _build_visual_only_bundle_for_summary(
    *,
    visual_summary: str,
    morphology: list[str],
    area_ratio_source_note: str,
    vision_conflict: dict[str, Any],
) -> dict[str, Any]:
    conflict_line = ""
    if isinstance(vision_conflict, dict) and vision_conflict.get("has_conflict"):
        conflict_line = _normalize_internal_text(_text(vision_conflict.get("reason_summary"))) or (
            "分类排序与受害范围等信号存在张力，详见后文诊断与复查部分。"
        )
    return {
        "visual_summary": visual_summary,
        "morphology_cues": _list_text(morphology, limit=5),
        "extent_note": area_ratio_source_note,
        "conflict_one_liner": conflict_line,
        "writing_note": "本节只写图像可直接支撑的形态、分布与受害范围估计，不写确诊结论与具体药肥方案。",
    }


def build_report_packet(
    *,
    case_text: str,
    caption: CaptionSchema,
    rounds: list[dict[str, Any]] | None = None,
    final_result: dict[str, Any],
    safety_result: dict[str, Any],
    vision_result: dict[str, Any] | None = None,
    kb_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    latest_state = _latest_shared_state(rounds)
    diagnosis_board = _board_dict(latest_state, "diagnosis_board")
    evidence_board = _board_dict(latest_state, "evidence_board")
    action_board = _board_dict(latest_state, "action_board")
    risk_board = _board_dict(latest_state, "risk_board")
    diagnosis_entries = _diagnosis_entries_from_state(latest_state, final_result)

    top = final_result.get("top_diagnosis", {}) if isinstance(final_result, dict) else {}
    primary_name = _normalize_internal_text(class_name_to_cn(_text(top.get("name")))) or _normalize_internal_text(
        class_name_to_cn(_text((diagnosis_board.get("working_diagnoses") or [""])[0]))
    )
    vision_conflict = _build_vision_conflict_section(vision_result)
    clinical_profile = build_leaf_clinical_profile(caption, vision_conflict)
    visual_candidates = _build_visual_candidate_diagnoses(vision_result)
    berry_qa_guidance = _build_berry_qa_guidance(rounds)
    ranked_differentials = _list_text(
        [class_name_to_cn(_text(item.get("name", ""))) for item in diagnosis_board.get("differentials", [])],
        limit=3,
    )
    secondary_differential = ranked_differentials[0] if ranked_differentials else _select_secondary_differential(
        ranked_differentials=[],
        visual_candidates=visual_candidates,
        primary_name=primary_name,
    )

    report_outline = _list_text(final_result.get("report_outline", []), limit=5)
    if not report_outline or any(_looks_mojibake(item) for item in report_outline):
        report_outline = [
            "病例摘要：归纳可见表现和受害范围，不写确诊口径。",
            "诊断判断与置信说明：首位疑似、模型倾向、支持/鉴别与知识库摘要（若有）。",
            "复查与补证建议：优先补什么、为何有用、可怎么做（语气务实，少堆「缺口」）。",
            "救治建议与实施路径：可执行步骤、观察与升级条件（证据不足不写具体药剂配方）。",
            "风险边界、预后与复查：禁忌、恶化信号与复查节点。",
        ]

    evidence_sufficiency = _normalize_internal_text(_text(final_result.get("evidence_sufficiency") or safety_result.get("evidence_sufficiency")))
    if not evidence_sufficiency or _looks_mojibake(evidence_sufficiency):
        evidence_sufficiency = "当前判断主要基于单张图像和现有上下文，应按审慎口径理解。"

    case_summary = _build_case_summary(case_text, caption, clinical_profile=clinical_profile)
    area_ratio_source_note = str(clinical_profile.get("area_source_note") or "").strip()
    image_specific_morphology = list(clinical_profile.get("morphology_notes") or [])
    morphology = _list_text(image_specific_morphology + _list_text(case_summary.get("observed_symptoms", []), limit=8), limit=6)
    stage_hint = str(clinical_profile.get("stage_hint") or "").strip()
    consistency_note = _build_consistency_note(case_text, caption)
    summary_blocked_terms = [item for item in [primary_name, secondary_differential] if item]
    visual_summary = _sanitize_summary_fact_text(
        _text(caption.visual_summary),
        blocked_terms=summary_blocked_terms,
    )

    confidence_label = _normalize_internal_text(_text(top.get("confidence")))
    confidence_extra = _list_text(risk_board.get("confidence_boundary", []), limit=4)
    if not confidence_extra:
        confidence_statement = _normalize_internal_text(_text(final_result.get("confidence_statement")))
        if confidence_statement:
            confidence_extra = [confidence_statement]
    score_note = _normalize_internal_text(_text(vision_conflict.get("classification_score_note")))
    classification_confidence = _to_float(vision_conflict.get("classification_confidence"), default=0.0)
    confidence_boundary = _build_confidence_boundary_merged(
        primary_name=primary_name,
        score_note=score_note,
        classification_confidence=classification_confidence,
        extra_lines=confidence_extra,
    )

    verification_values = _list_text(evidence_board.get("verification_value", []), limit=6)
    gap_items: list[dict[str, str]] = []
    for idx, gap in enumerate(_list_text(evidence_board.get("missing_evidence", []), limit=6)):
        gap_items.append(
            {
                "gap": gap,
                "diagnostic_value": verification_values[idx] if idx < len(verification_values) else _gap_diagnostic_value(
                    gap,
                    primary_name,
                    secondary_differential,
                    "",
                ),
                "next_step": _gap_next_step(gap),
            }
        )

    control_options = _to_low_risk_actions(_list_text(action_board.get("control_options", []), limit=5)) or _to_low_risk_actions(_list_text(
        berry_qa_guidance.get("control_options", []),
        limit=5,
    ))
    today_actions = _to_low_risk_actions(_list_text(action_board.get("today_actions", []), limit=5)) or _build_today_actions(
        final_result,
        berry_qa_guidance,
    )
    observe_48h = _list_text(action_board.get("observe_48h", []), limit=5) or _build_observe_48h(final_result, safety_result, berry_qa_guidance)
    escalation_conditions = _list_text(action_board.get("escalation_triggers", []), limit=4) or _build_upgrade_triggers(
        final_result,
        safety_result,
        berry_qa_guidance,
    )
    prohibited_actions = _list_text(risk_board.get("prohibited_actions", []), limit=4)
    safety_notes = _list_text(risk_board.get("risk_flags", []), limit=5) or _build_risk_watchpoints(
        final_result,
        safety_result,
        berry_qa_guidance,
    )
    required_followups = _list_text(risk_board.get("followup_nodes", []), limit=4) or observe_48h
    action_timeline = _build_action_timeline(final_result, safety_result)
    prognosis_note = str(clinical_profile.get("prognosis_note") or "").strip()
    uncertainty_management = _build_uncertainty_management(
        vision_conflict=vision_conflict,
        gap_items=gap_items,
        primary_name=primary_name or "当前首位候选",
        secondary_name=secondary_differential,
        clinical_profile=clinical_profile,
    )
    image_specific_basis = _build_image_specific_basis(
        clinical_profile=clinical_profile,
        primary_name=primary_name or "当前首位候选",
        secondary_name=secondary_differential,
    )
    decision_support = _build_decision_support(
        today_actions=today_actions,
        observe_48h=observe_48h,
        escalation_conditions=escalation_conditions,
        prohibited_actions=prohibited_actions,
        required_followups=required_followups,
        primary_name=primary_name or "当前首位候选",
        secondary_name=secondary_differential,
    )

    diagnosis_statement = _build_diagnosis_statement_packet(primary_name, classification_confidence)
    second_candidate_brief = _second_candidate_brief_note(vision_conflict, primary_name)
    disease_context_snippets = _disease_snippets_from_kb(kb_documents)
    visual_only_bundle = _build_visual_only_bundle_for_summary(
        visual_summary=visual_summary,
        morphology=morphology,
        area_ratio_source_note=area_ratio_source_note,
        vision_conflict=vision_conflict,
    )

    summary_title, diagnosis_title, followup_title, action_title, risk_title = REQUIRED_REPORT_SECTIONS
    section_facts = {
        summary_title: {
            "visual_only_bundle": visual_only_bundle,
            "morphology": morphology,
            "visual_summary": visual_summary,
            "stage_hint": stage_hint,
            "consistency_note": consistency_note,
            "classification_policy_note": clinical_profile.get("classification_policy_note"),
        },
        diagnosis_title: {
            "primary_diagnosis": primary_name,
            "diagnosis_statement": diagnosis_statement,
            "confidence_label": confidence_label,
            "confidence_boundary": confidence_boundary,
            "model_score_note": score_note,
            "secondary_differential": secondary_differential,
            "second_candidate_brief": second_candidate_brief,
            "disease_context_snippets": disease_context_snippets,
            "disease_entity_writing_requirement": (
                "诊断章节必须包含「这种病是什么」的说明：用 2–5 句客观解释病原或病害性质、典型为害方式、"
                "与当前叶片可见征象的对应；禁止只写病名单词或只写排序。可融合下方百科摘录与模型倾向说明。"
            ),
            "kb_snippet_instruction": (
                "若存在病害百科摘录，用一两句融入叙述并标明来源于知识库摘要；若无摘录则说明暂无匹配条目，勿编造。"
            ),
            "diagnosis_board": diagnosis_board,
            "diagnosis_evidence": diagnosis_entries,
            "visual_candidates": visual_candidates,
            "image_specific_basis": image_specific_basis,
            "visual_model_outputs": vision_conflict.get("visual_model_outputs", {}),
            "vision_conflict": {
                "has_conflict": bool(vision_conflict.get("has_conflict", False)),
                "reason_summary": _text(vision_conflict.get("reason_summary")),
                "recommended_interpretation": _text(vision_conflict.get("recommended_interpretation")),
            },
        },
        followup_title: {
            "evidence_board": evidence_board,
            "gap_items": gap_items,
            "berry_focus": _list_text(berry_qa_guidance.get("observe_points", []), limit=3),
            "caption_answer_confidences": _list_text(
                [
                    f"{_text(item.get('question'))}: {_text(item.get('answer'))}（{_format_percent(float(item.get('confidence', 0.0) or 0.0))}）"
                    for item in (
                        vision_conflict.get("visual_model_outputs", {}).get("caption_answer_confidences", [])
                        if isinstance(vision_conflict.get("visual_model_outputs", {}), dict)
                        else []
                    )
                    if isinstance(item, dict)
                ],
                limit=6,
            ),
            "uncertainty_management": uncertainty_management,
            "writing_note": "用复查、补拍、记录等务实表述组织内容，避免通篇「缺口」腔。",
        },
        action_title: {
            "action_board": action_board,
            "today_actions": today_actions,
            "control_options": control_options,
            "observe_48h": observe_48h,
            "escalation_conditions": escalation_conditions,
            "treatment_layers": {
                "first_layer_low_risk": today_actions,
                "second_layer_conditioned": control_options,
            },
            "timeline": action_timeline,
            "decision_support": decision_support,
            "primary_diagnosis_for_narration": primary_name,
            "leaf_clinical_profile": {
                "damage_tier": clinical_profile.get("damage_tier"),
                "ratio_percent_text": clinical_profile.get("ratio_percent_text"),
                "classification_policy_note": clinical_profile.get("classification_policy_note"),
            },
        },
        risk_title: {
            "risk_board": risk_board,
            "prohibited_actions": prohibited_actions,
            "safety_notes": safety_notes,
            "required_followups": required_followups,
            "prognosis_note": prognosis_note,
            "decision_support": decision_support,
        },
    }

    return {
        "case_summary": {
            **case_summary,
            "image_specific_morphology": image_specific_morphology,
            "area_ratio_source_note": area_ratio_source_note,
            "stage_hint": stage_hint,
            "consistency_note": consistency_note,
        },
        "vision_conflict": vision_conflict,
        "final_diagnosis": {
            "name": primary_name,
            "confidence": confidence_label,
            "diagnosis_statement": diagnosis_statement,
            "confidence_statement": _normalize_internal_text(_text(final_result.get("confidence_statement"))),
            "evidence_sufficiency": evidence_sufficiency,
            "model_score_note": score_note,
        },
        "diagnosis_basis": {
            "diagnosis_board": diagnosis_board,
            "diagnosis_evidence": diagnosis_entries,
            "visual_candidates": visual_candidates,
            "image_specific_basis": image_specific_basis,
            "vision_conflict": vision_conflict,
            "visual_model_outputs": vision_conflict.get("visual_model_outputs", {}),
        },
        "action_plan": {
            "action_board": action_board,
            "actions": today_actions,
            "monitoring_plan": observe_48h,
            "escalation_conditions": escalation_conditions,
            "timeline": action_timeline,
            "decision_support": decision_support,
        },
        "safety_and_followup": {
            "risk_board": risk_board,
            "safety_notes": safety_notes,
            "required_followups": required_followups,
            "prognosis_note": prognosis_note,
            "decision_support": decision_support,
        },
        "report_context": {
            "primary_diagnosis": primary_name,
            "diagnosis_statement": diagnosis_statement,
            "confidence_label": confidence_label,
            "confidence_boundary": confidence_boundary,
            "model_score_note": score_note,
            "secondary_differential": secondary_differential,
            "differential_names": ranked_differentials,
            "conflict_interpretation": _build_conflict_interpretation(vision_conflict),
        },
        "uncertainty_management": uncertainty_management,
        "decision_support": decision_support,
        "diagnosis_board": diagnosis_board,
        "evidence_board": evidence_board,
        "action_board": action_board,
        "risk_board": risk_board,
        "berry_qa_guidance": berry_qa_guidance,
        "section_facts": section_facts,
        "report_outline": report_outline,
        "leaf_clinical_profile": clinical_profile,
        "disease_entity_brief": {
            "primary_label": primary_name,
            "secondary_label": secondary_differential,
            "snippets": disease_context_snippets,
            "model_tendency_note": score_note,
            "instruction": (
                "写作时需交代「首位疑似病害」是什么：它属于哪类病原问题、在水稻植株上通常如何表现、"
                "为什么当前图像线索会指向它；无知识库条目时用谨慎的常识级描述，勿虚构检测数据。"
            ),
        },
    }


def _clip_text(text: str, max_len: int = 240) -> str:
    t = str(text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _legacy_collaboration_snippet(turn: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in (
        "visible_findings",
        "negative_findings",
        "evidence_strength",
        "why_primary",
        "why_not_primary",
        "decisive_missing_evidence",
        "today_actions",
        "control_options",
        "observe_48h",
        "escalation_triggers",
        "low_risk_actions",
        "environment_adjustments",
        "confidence_boundary",
    ):
        val = turn.get(key)
        if isinstance(val, list):
            for item in val[:4]:
                t = str(item).strip()
                if t:
                    chunks.append(t)
        elif isinstance(val, str) and val.strip():
            chunks.append(val.strip())
    for key in ("candidate_causes", "ranked_differentials"):
        cand = turn.get(key)
        if not isinstance(cand, list):
            continue
        for item in cand[:3]:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                if name:
                    chunks.append(f"涉及「{name}」的排序或依据。")
    text = " ".join(chunks)
    return text if len(text) > 40 else ""


def _format_expert_turn_for_digest(turn: dict[str, Any]) -> str:
    """按角色保留结构化信息，避免把鉴别排序、防治、农艺混成一锅粥（对照 run_20260329_204816_dca3fc80）。"""
    agent = str(turn.get("agent_name", "")).strip()
    parts: list[str] = []

    if agent == "diagnosis_evidence_officer":
        vf = turn.get("visible_findings")
        if isinstance(vf, list) and vf:
            parts.append("叶面可见：" + _clip_text(str(vf[0]), 320))
        nf = turn.get("negative_findings")
        if isinstance(nf, list) and nf:
            parts.append("当前还没看到或没拍到的关键角度：" + _clip_text(str(nf[0]), 260))
        cc = turn.get("candidate_causes")
        if isinstance(cc, list):
            for c in cc[:4]:
                if not isinstance(c, dict):
                    continue
                nm = str(c.get("name", "")).strip()
                if not nm:
                    continue
                wl = str(c.get("why_like", "")).strip()
                wu = str(c.get("why_unlike", "")).strip()
                parts.append(
                    f"候选「{nm}」：像的地方——{_clip_text(wl, 200)}；不太像或还没看清——{_clip_text(wu, 200)}"
                )
        es = str(turn.get("evidence_strength", "")).strip()
        if es:
            parts.append("单图能说到哪一步：" + _clip_text(es, 220))

    elif agent == "differential_officer":
        rd = turn.get("ranked_differentials")
        if isinstance(rd, list) and rd:
            parts.append("几种病还要怎么分清（写入报告时请改写为客观表述，勿抄此句）：")
            for i, item in enumerate(rd[:5], 1):
                if not isinstance(item, dict):
                    continue
                nm = str(item.get("name", "")).strip()
                if not nm:
                    continue
                ws = str(item.get("why_supported", "")).strip()
                wnp = str(item.get("why_not_primary", "")).strip()
                parts.append(f"{i}. 「{nm}」仍可能：{_clip_text(ws, 200)}；保留位次原因：{_clip_text(wnp, 200)}")
        dme = turn.get("decisive_missing_evidence")
        if isinstance(dme, list) and dme:
            parts.append("补到哪一步，判断会跟着变：")
            for line in dme[:6]:
                if str(line).strip():
                    parts.append("- " + _clip_text(str(line).strip(), 260))
        wp = turn.get("why_primary")
        if isinstance(wp, list) and wp and str(wp[0]).strip():
            parts.append("为何当前更盯着首位方向：" + _clip_text(str(wp[0]), 220))
        wnp = turn.get("why_not_primary")
        if isinstance(wnp, list) and wnp and str(wnp[0]).strip():
            parts.append("其他方向为何先放一放：" + _clip_text(str(wnp[0]), 220))

    elif agent == "berry_qa_expert":
        blocks = [
            ("今天就能做的：", "today_actions", 5),
            ("防治上只写到类别/原则（非开方）：", "control_options", 4),
            ("近两日盯什么：", "observe_48h", 4),
            ("什么情况要加码或送检：", "escalation_triggers", 3),
        ]
        for title, key, lim in blocks:
            xs = turn.get(key)
            if not isinstance(xs, list) or not xs:
                continue
            parts.append(title)
            for x in xs[:lim]:
                if str(x).strip():
                    parts.append("- " + _clip_text(str(x).strip(), 220))

    elif agent == "cultivation_management_officer":
        blocks = [
            ("田间节奏：", "management_timeline", 6),
            ("不伤苗的环控动作：", "low_risk_actions", 5),
            ("温湿水与通风：", "environment_adjustments", 4),
            ("啥时再复查、看哪些数：", "followup_nodes", 4),
        ]
        for title, key, lim in blocks:
            xs = turn.get(key)
            if not isinstance(xs, list) or not xs:
                continue
            parts.append(title)
            for x in xs[:lim]:
                if str(x).strip():
                    parts.append("- " + _clip_text(str(x).strip(), 220))

    else:
        legacy = _legacy_collaboration_snippet(turn)
        if legacy:
            parts.append(legacy)

    body = "\n".join(parts).strip()
    return body if len(body) > 30 else _legacy_collaboration_snippet(turn)


def _coordinator_round_narrative_brief(summary: dict[str, Any]) -> str:
    """把协调器已经合并过的 diagnosis/evidence/action board 喂给报告层，避免只看见专家原文重复。"""
    if not isinstance(summary, dict):
        return ""
    chunks: list[str] = []
    wd = summary.get("working_diagnoses") or []
    if isinstance(wd, list) and wd:
        chunks.append("**协调器·当前工作诊断**：" + "、".join(str(x) for x in wd[:4] if str(x).strip()))

    db = summary.get("diagnosis_board")
    if isinstance(db, dict):
        sup = db.get("supporting") or []
        ctr = db.get("counter") or []
        if isinstance(sup, list) and sup:
            chunks.append("**照片与现场依据（已去重）**：" + " | ".join(_clip_text(str(x), 100) for x in sup[:4] if str(x).strip()))
        if isinstance(ctr, list) and ctr:
            chunks.append("**主要反证/局限**：" + " | ".join(_clip_text(str(x), 100) for x in ctr[:4] if str(x).strip()))
        diffs = db.get("differentials") or []
        if isinstance(diffs, list) and diffs:
            chunks.append("**和相似病害怎么分（协调器汇总）**")
            for d in diffs[:4]:
                if not isinstance(d, dict):
                    continue
                nm = str(d.get("name", "")).strip()
                if not nm:
                    continue
                ws = str(d.get("why_supported", "")).strip()
                wn = str(d.get("why_not_primary", "")).strip()
                chunks.append(f"- {nm}：仍像——{_clip_text(ws, 140)}；未升首位——{_clip_text(wn, 140)}")

    eb = summary.get("evidence_board")
    if isinstance(eb, dict):
        miss = eb.get("missing_evidence") or []
        ver = eb.get("verification_value") or []
        if isinstance(miss, list) and miss:
            chunks.append("**关键补证（协调器单列，报告里写一次即可）**")
            for m in miss[:5]:
                if str(m).strip():
                    chunks.append("- " + _clip_text(str(m).strip(), 220))
        if isinstance(ver, list) and ver:
            chunks.append("**补到之后能校准什么**")
            for v in ver[:4]:
                if str(v).strip():
                    chunks.append("- " + _clip_text(str(v).strip(), 220))

    ab = summary.get("action_board")
    if isinstance(ab, dict):
        ta = ab.get("today_actions") or []
        if isinstance(ta, list) and ta:
            chunks.append(
                "**当日动作（协调器汇总）**："
                + "；".join(_clip_text(str(x), 90) for x in ta[:8] if str(x).strip())
            )

    cf = summary.get("conflicts") or []
    if isinstance(cf, list) and cf:
        chunks.append("**专家间仍存张力**：" + " ‖ ".join(_clip_text(str(x), 180) for x in cf[:4] if str(x).strip()))

    nxf = summary.get("next_focus") or []
    if isinstance(nxf, list) and nxf:
        chunks.append("**下一轮最值得推进**：" + "；".join(_clip_text(str(x), 150) for x in nxf[:5] if str(x).strip()))

    return "\n".join(chunks).strip()


def build_cross_agent_synthesis_lines(rounds: list[dict[str, Any]] | None) -> str:
    """末轮四角色各抽一句，强制报告层「看见」分工（参考 trace 中 tomato vs cultivation 的分歧）。"""
    if not rounds:
        return ""
    last = rounds[-1]
    turns_list = [t for t in (last.get("expert_turns") or []) if isinstance(t, dict)]
    turns = {str(t.get("agent_name", "")).strip(): t for t in turns_list}
    lines: list[str] = []

    deo = turns.get("diagnosis_evidence_officer")
    if isinstance(deo, dict):
        cc = deo.get("candidate_causes") or []
        if isinstance(cc, list) and cc and isinstance(cc[0], dict):
            nm = str(cc[0].get("name", "")).strip()
            wl = str(cc[0].get("why_like", "")).strip()
            if nm:
                lines.append(f"病理归纳：当前图像叙事最贴近「{nm}」——{_clip_text(wl, 280)}")

    diff = turns.get("differential_officer")
    if isinstance(diff, dict):
        dme = diff.get("decisive_missing_evidence") or []
        if isinstance(dme, list) and dme and str(dme[0]).strip():
            lines.append(f"想分清病，优先补齐——{_clip_text(str(dme[0]).strip(), 260)}")
        else:
            rdl = diff.get("ranked_differentials")
            if isinstance(rdl, list) and rdl:
                rd0 = rdl[0]
                if isinstance(rd0, dict) and str(rd0.get("why_not_primary", "")).strip():
                    lines.append(
                        f"对「{rd0.get('name', '')}」为啥还不能拍板——"
                        f"{_clip_text(str(rd0.get('why_not_primary')), 260)}"
                    )

    tom = turns.get("berry_qa_expert")
    if isinstance(tom, dict):
        ta = tom.get("today_actions") or []
        if isinstance(ta, list) and ta:
            seg = _clip_text(str(ta[0]).strip(), 140)
            if len(ta) > 1:
                seg += "；" + _clip_text(str(ta[1]).strip(), 120)
            lines.append(f"防治执行：{seg}")

    cul = turns.get("cultivation_management_officer")
    if isinstance(cul, dict):
        la = cul.get("low_risk_actions") or []
        if isinstance(la, list) and la:
            seg = _clip_text(str(la[0]).strip(), 140)
            if len(la) > 1:
                seg += "；" + _clip_text(str(la[1]).strip(), 120)
            lines.append(f"农艺兜底（弱绑定具体病名）：{seg}")

    if not lines:
        return ""
    header = (
        "## 多视角合成（末轮摘录，写入报告时请改写为客观田间表述）\n"
        "四块分别进不同章节：更像啥病、还没看清啥、今天咋防、环境咋兜底；勿照搬本段措辞。\n"
    )
    return header + "\n".join(f"- {x}" for x in lines)


def build_multiagent_round_narrative_digest(rounds: list[dict[str, Any]] | None, *, max_chars: int = 12000) -> str:
    if not rounds:
        return "多角色讨论摘要：暂无轮次记录。"
    lines: list[str] = [
        "多角色讨论摘要（内部材料）：每轮含协调器合并视图与各专家摘录。"
        "写入报告时分配到对应章节，同一补证（如叶背/整株）全文只说透一次，禁止换腔调重复。",
    ]
    for block in rounds:
        ridx = block.get("round", "?")
        lines.append(f"\n### 第 {ridx} 轮")
        summary = block.get("summary")
        coord = _coordinator_round_narrative_brief(summary) if isinstance(summary, dict) else ""
        if coord:
            lines.append("#### 协调器合并视图（优先阅读）\n" + coord)
        order = [
            "diagnosis_evidence_officer",
            "differential_officer",
            "berry_qa_expert",
            "cultivation_management_officer",
        ]
        by_agent: dict[str, dict[str, Any]] = {}
        for turn in block.get("expert_turns") or []:
            if isinstance(turn, dict):
                nm = str(turn.get("agent_name", "")).strip()
                if nm:
                    by_agent[nm] = turn
        for agent in order:
            turn = by_agent.get(agent)
            if not turn:
                continue
            body = _format_expert_turn_for_digest(turn)
            if body:
                lines.append(f"#### 专家 · {agent}\n{body[:2800]}")
        for agent, turn in by_agent.items():
            if agent in order:
                continue
            body = _format_expert_turn_for_digest(turn)
            if body:
                lines.append(f"#### 专家 · {agent}\n{body[:2000]}")
    text = "\n".join(lines).strip()
    return text if len(text) <= max_chars else text[: max_chars - 20] + "\n…（摘要已截断）"


def build_report_writer_narrative_briefing(
    report_packet: dict[str, Any],
    rounds: list[dict[str, Any]] | None = None,
) -> str:
    """供报告 LLM 使用的自然语言材料包（非 JSON 协议），强调病害实体与协作脉络。"""
    ctx = report_packet.get("report_context", {}) if isinstance(report_packet, dict) else {}
    deb = report_packet.get("disease_entity_brief", {}) if isinstance(report_packet, dict) else {}
    primary = str(ctx.get("primary_diagnosis", "") or deb.get("primary_label", "")).strip()
    secondary = str(ctx.get("secondary_differential", "") or deb.get("secondary_label", "")).strip()
    snippets = deb.get("snippets") if isinstance(deb, dict) else []
    if not isinstance(snippets, list):
        snippets = []
    snippet_text = "\n".join(f"- {str(s)}" for s in snippets[:6] if str(s).strip()) or "（知识库未返回匹配摘录）"
    model_note = str(deb.get("model_tendency_note", "") or ctx.get("model_score_note", "")).strip()
    synthesis = build_cross_agent_synthesis_lines(rounds)
    digest = build_multiagent_round_narrative_digest(rounds)
    conf_boundary = ctx.get("confidence_boundary")
    cb_lines = ""
    if isinstance(conf_boundary, list) and conf_boundary:
        cb_lines = "；".join(str(x) for x in conf_boundary[:5])

    parts = [
        "## 写作任务总览",
        "你正在撰写《农业救治报告》的一个章节。材料 below 来自多智能体讨论、视觉模型与知识库检索；"
        "请用连贯中文段落输出，不要输出 JSON、不要复述键名。",
        "",
        "**读者与分工**：农户与一线植保；报告无单独开篇决策卡，五章顺排。"
        "本章只写**本节职责内**信息，与他节勿整段复读同一套总述；落实短句、若则绑定，勿用【】标签式小标题。",
        "",
        "## 病害实体（全篇尤其是「诊断判断」必须交代清楚）",
        f"- 当前首位疑似：**{primary or '（待材料）'}**",
        f"- 主要对照/鉴别：**{secondary or '（待材料）'}**",
        f"- 分类分数/边界提示（写作时写成「更像哪类≠确诊」）：{model_note or '（无单独分数句）'}{('；' + cb_lines) if cb_lines else ''}",
        "- 知识库病害摘录（可融入叙述，无则勿编造）：",
        snippet_text,
        str(deb.get("instruction", "")).strip(),
        "",
        "## 不确定性与决策（知识叙述，非 JSON）",
        uncertainty_management_to_prose(report_packet.get("uncertainty_management"))
        if isinstance(report_packet, dict)
        else uncertainty_management_to_prose(None),
        "",
        decision_support_to_prose(report_packet.get("decision_support"))
        if isinstance(report_packet, dict)
        else decision_support_to_prose(None),
        "",
        synthesis,
        "",
        digest,
    ]
    return "\n".join(p for p in parts if p is not None).strip()
