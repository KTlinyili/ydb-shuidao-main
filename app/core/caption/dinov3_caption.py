from __future__ import annotations

from typing import Any

from app.core.caption.schema import CaptionSchema
from app.core.vision.presentation import class_name_to_cn, format_percent, normalize_label, resolve_primary_visual_diagnosis


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


_DISEASE_SYMPTOM_MAP: dict[str, dict[str, list[str]]] = {
    "bacterialspot": {
        "color": ["brown"],
        "tissue_state": ["necrosis"],
        "spot_shape": ["angular"],
        "boundary": ["yellow_halo"],
        "distribution_position": ["lower_leaf"],
        "distribution_pattern": ["scattered"],
        "morph_change": ["none"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["humidity_high"],
    },
    "earlyblight": {
        "color": ["brown"],
        "tissue_state": ["necrosis"],
        "spot_shape": ["concentric"],
        "boundary": ["dark_ring"],
        "distribution_position": ["lower_leaf"],
        "distribution_pattern": ["expanding"],
        "morph_change": ["none"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["humidity_high"],
    },
    "healthy": {
        "color": ["green"],
        "tissue_state": ["healthy"],
        "spot_shape": ["diffuse"],
        "boundary": ["no_clear_boundary"],
        "distribution_position": ["whole_plant"],
        "distribution_pattern": ["scattered"],
        "morph_change": ["none"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["unknown"],
    },
    "lateblight": {
        "color": ["brown"],
        "tissue_state": ["water_soaked"],
        "spot_shape": ["diffuse"],
        "boundary": ["blurred"],
        "distribution_position": ["lower_leaf"],
        "distribution_pattern": ["expanding"],
        "morph_change": ["wilting"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["humidity_high"],
    },
    "leafmold": {
        "color": ["gray"],
        "tissue_state": ["mold"],
        "spot_shape": ["diffuse"],
        "boundary": ["blurred"],
        "distribution_position": ["leaf_back"],
        "distribution_pattern": ["patchy"],
        "morph_change": ["none"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["humidity_high", "poor_ventilation"],
    },
    "septorialeafspot": {
        "color": ["brown"],
        "tissue_state": ["necrosis"],
        "spot_shape": ["round"],
        "boundary": ["dark_ring"],
        "distribution_position": ["lower_leaf"],
        "distribution_pattern": ["scattered"],
        "morph_change": ["none"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["humidity_high"],
    },
    "spidermitestwospottedspidermite": {
        "color": ["yellow"],
        "tissue_state": ["dry"],
        "spot_shape": ["diffuse"],
        "boundary": ["no_clear_boundary"],
        "distribution_position": ["leaf_back"],
        "distribution_pattern": ["patchy"],
        "morph_change": ["none"],
        "pest_cues": ["webbing"],
        "co_signs": ["unknown"],
    },
    "targetspot": {
        "color": ["brown"],
        "tissue_state": ["necrosis"],
        "spot_shape": ["round"],
        "boundary": ["dark_ring"],
        "distribution_position": ["lower_leaf"],
        "distribution_pattern": ["scattered"],
        "morph_change": ["none"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["humidity_high"],
    },
    "tomatomosaicvirus": {
        "color": ["mixed"],
        "tissue_state": ["chlorosis"],
        "spot_shape": ["irregular"],
        "boundary": ["no_clear_boundary"],
        "distribution_position": ["whole_plant"],
        "distribution_pattern": ["patchy"],
        "morph_change": ["deformation"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["unknown"],
    },
    "tomatoyellowleafcurlvirus": {
        "color": ["yellow"],
        "tissue_state": ["chlorosis"],
        "spot_shape": ["diffuse"],
        "boundary": ["no_clear_boundary"],
        "distribution_position": ["upper_leaf"],
        "distribution_pattern": ["patchy"],
        "morph_change": ["curling"],
        "pest_cues": ["no_obvious_pest"],
        "co_signs": ["unknown"],
    },
}


def build_caption_from_dinov3_analysis(
    *,
    case_text: str,
    image_analysis: dict[str, Any],
    fallback_caption: CaptionSchema,
) -> CaptionSchema:
    payload = fallback_caption.model_dump(mode="json")
    predicted_class = str(image_analysis.get("predicted_class", "")).strip() or "unknown"
    damage_ratio = _clamp_unit(float(image_analysis.get("damaged_area_ratio_of_leaf", 0.0)))
    base_confidence = _clamp_unit(float(image_analysis.get("confidence", 0.0)))

    resolved = resolve_primary_visual_diagnosis(image_analysis)
    primary_class = str(resolved["primary_class"]).strip() or predicted_class
    primary_class_cn = str(resolved["primary_class_cn"]).strip() or class_name_to_cn(primary_class)
    predicted_class_cn = str(resolved["predicted_class_cn"]).strip() or class_name_to_cn(predicted_class)
    has_conflict = bool(resolved["has_conflict"])
    has_qwen_slots = any(str(item).startswith("qwen3vl:slot_extraction") for item in payload.get("evidence_refs", []))

    if has_conflict:
        payload["visual_summary"] = (
            f"当前图像病种判断主要依据分类结果，当前更接近“{predicted_class_cn}”；"
            f"病损面积约占叶片面积 {format_percent(damage_ratio)}。"
            f" 由于病种判断与面积信号存在不一致，当前仍以“{primary_class_cn}”作为倾向判断，但结论需保持审慎。"
        )
    else:
        payload["visual_summary"] = (
            f"当前图像整体更偏向“{primary_class_cn}”，"
            f"当前可信度约为 {format_percent(base_confidence)}，"
            f"病损面积约占叶片面积 {format_percent(damage_ratio)}。"
        )

    if not has_qwen_slots:
        normalized = normalize_label(primary_class)
        disease_symptoms = _DISEASE_SYMPTOM_MAP.get(normalized)
        if disease_symptoms is not None:
            payload["symptoms"] = disease_symptoms

    confidence = base_confidence * 0.72 if has_conflict else base_confidence
    payload["numeric"] = {
        "area_ratio": damage_ratio,
        "severity_score": _clamp_unit(max(damage_ratio, confidence * 0.75)),
    }
    payload["confidence"] = confidence
    payload["ood_score"] = _clamp_unit(max(0.25 if has_conflict else 0.05, 1.0 - confidence))

    internal_focus: list[str] = []
    if has_conflict:
        internal_focus.append("当前需要优先解释病种判断与受损面积信号为何出现分歧。")
    elif confidence < 0.65:
        internal_focus.append("当前图像线索较弱，结论应保持审慎，不宜下过强定论。")
    if damage_ratio < 0.03 and normalize_label(primary_class) != "healthy":
        internal_focus.append("当前病损范围较小，应避免把轻微异常过度解释为重病。")
    internal_focus.extend(str(item) for item in payload.get("followup_questions", []) if str(item).strip())
    payload["followup_questions"] = list(dict.fromkeys(internal_focus))[:4]

    evidence_refs = [
        f"dinov3:predicted_class:{predicted_class}",
        f"dinov3:primary_class:{primary_class}",
        f"dinov3:confidence:{base_confidence:.4f}",
        f"dinov3:damaged_area_ratio_of_leaf:{damage_ratio:.4f}",
    ]
    if has_conflict:
        evidence_refs.append("dinov3:classification_segmentation_conflict:true")
    evidence_refs.extend(str(item) for item in payload.get("evidence_refs", []) if str(item).strip())
    payload["evidence_refs"] = list(dict.fromkeys(evidence_refs))

    _ = case_text
    return CaptionSchema.model_validate(payload)
