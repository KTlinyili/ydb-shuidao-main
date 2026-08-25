from __future__ import annotations

from typing import Any

from app.core.vision.presentation import (
    build_conflict_analysis,
    build_image_analysis_display,
    class_name_to_cn,
    resolve_primary_visual_diagnosis,
)


def _first_lesion(slot_extraction: dict[str, Any]) -> dict[str, Any]:
    image_evidence = slot_extraction.get("image_evidence", {}) if isinstance(slot_extraction, dict) else {}
    lesions = image_evidence.get("lesions", []) if isinstance(image_evidence, dict) else []
    lesion = lesions[0] if isinstance(lesions, list) and lesions else {}
    return lesion if isinstance(lesion, dict) else {}


def _slot_value(slot: Any) -> str:
    if isinstance(slot, dict):
        return str(slot.get("value", "")).strip()
    if isinstance(slot, str):
        return slot.strip()
    return ""


def _slot_confidence(slot: Any) -> float:
    if isinstance(slot, dict):
        try:
            value = float(slot.get("confidence", 0.0))
        except (TypeError, ValueError):
            value = 0.0
        return max(0.0, min(1.0, value))
    return 0.0


def _clamp_unit(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(1.0, numeric))


def _classification_candidates_over_threshold(
    image_payload: dict[str, Any],
    threshold: float = 0.30,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    top_predictions = image_payload.get("top_predictions", [])
    if isinstance(top_predictions, list):
        for item in top_predictions:
            if not isinstance(item, dict):
                continue
            confidence = _clamp_unit(item.get("confidence", 0.0))
            if confidence < threshold:
                continue
            class_name = str(item.get("class_name", "")).strip()
            if not class_name:
                continue
            candidates.append(
                {
                    "class_id": int(item.get("class_id", 0) or 0),
                    "class_name": class_name,
                    "class_name_cn": class_name_to_cn(class_name),
                    "confidence": confidence,
                }
            )

    if candidates:
        return candidates

    predicted_class = str(image_payload.get("predicted_class", "")).strip()
    predicted_confidence = _clamp_unit(image_payload.get("confidence", 0.0))
    if predicted_class and predicted_confidence >= threshold:
        return [
            {
                "class_id": int(image_payload.get("predicted_class_id", 0) or 0),
                "class_name": predicted_class,
                "class_name_cn": class_name_to_cn(predicted_class),
                "confidence": predicted_confidence,
            }
        ]
    return []


def _caption_answer_confidences(
    lesion: dict[str, Any],
    leaf_level: dict[str, Any],
) -> list[dict[str, Any]]:
    fields = [
        ("color", "病斑颜色", lesion),
        ("tissue_state", "组织状态", lesion),
        ("shape", "斑形", lesion),
        ("boundary", "边界特征", lesion),
        ("distribution_position", "分布位置", lesion),
        ("distribution_pattern", "分布模式", lesion),
        ("morph_change", "叶片形态变化", leaf_level),
        ("pest_or_mechanical_hint", "虫害/机械损伤线索", leaf_level),
        ("other_visible_signs", "其他可见表现", leaf_level),
    ]
    answers: list[dict[str, Any]] = []
    for key, question, source in fields:
        slot = source.get(key) if isinstance(source, dict) else None
        answer = _slot_value(slot)
        if not answer:
            continue
        answers.append(
            {
                "field": key,
                "question": question,
                "answer": answer,
                "confidence": _slot_confidence(slot),
            }
        )
    answers.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
    return answers


def build_vision_result(
    *,
    slot_extraction: dict[str, Any] | None,
    image_analysis: dict[str, Any] | None,
    caption: dict[str, Any] | None,
    display: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slot_payload = slot_extraction or {}
    image_payload = image_analysis or {}
    caption_payload = caption or {}
    display_payload = display or (build_image_analysis_display(image_payload) if image_payload else {})
    resolved = resolve_primary_visual_diagnosis(image_payload) if image_payload else {}
    conflict_analysis = build_conflict_analysis(image_payload) if image_payload else {}
    lesion = _first_lesion(slot_payload)
    leaf_level = slot_payload.get("leaf_level", {}) if isinstance(slot_payload, dict) else {}
    if not isinstance(leaf_level, dict):
        leaf_level = {}
    classification_candidates_over_30 = _classification_candidates_over_threshold(image_payload, threshold=0.30)
    caption_answers = _caption_answer_confidences(lesion, leaf_level)
    damaged_area_ratio = _clamp_unit(image_payload.get("damaged_area_ratio_of_leaf", 0.0))
    dominant_segmentation_ratio = _clamp_unit(image_payload.get("dominant_segmentation_ratio_of_leaf", 0.0))

    visual_evidence_bundle = {
        "classification_candidates_over_30": classification_candidates_over_30,
        "segmentation_area_summary": {
            "damaged_area_ratio_of_leaf": damaged_area_ratio,
            "dominant_segmentation_ratio_of_leaf": dominant_segmentation_ratio,
            "leaf_pixels": int(image_payload.get("leaf_pixels", 0) or 0),
            "diseased_pixels": int(image_payload.get("diseased_pixels", 0) or 0),
        },
        "caption_answer_confidences": caption_answers,
    }

    fusion_summary = {
        "primary_visual_conclusion": str(resolved.get("primary_class_cn", "")).strip(),
        "primary_visual_conclusion_en": str(resolved.get("primary_class", "")).strip(),
        "primary_source": str(resolved.get("primary_source", "")).strip(),
        "classification_result": str(image_payload.get("predicted_class", "")).strip(),
        "classification_confidence": _clamp_unit(image_payload.get("confidence", 0.0)),
        "dominant_segmentation_result": "",
        "damaged_area_ratio_of_leaf": damaged_area_ratio,
        "classification_segmentation_conflict": bool(conflict_analysis.get("has_conflict", False)),
        "conflict_analysis": conflict_analysis,
        "slot_evidence": {
            "color": _slot_value(lesion.get("color")),
            "tissue_state": _slot_value(lesion.get("tissue_state")),
            "shape": _slot_value(lesion.get("shape")),
            "boundary": _slot_value(lesion.get("boundary")),
            "distribution_position": _slot_value(lesion.get("distribution_position")),
            "distribution_pattern": _slot_value(lesion.get("distribution_pattern")),
            "morph_change": _slot_value(leaf_level.get("morph_change")),
            "pest_or_mechanical_hint": _slot_value(leaf_level.get("pest_or_mechanical_hint")),
            "other_visible_signs": _slot_value(leaf_level.get("other_visible_signs")),
        },
        "caption_summary": str(caption_payload.get("visual_summary", "")).strip(),
        "visual_evidence_bundle": visual_evidence_bundle,
    }

    return {
        "task": "berry_multimodel_visual_analysis",
        "models": {
            "slot_extraction_model": str(slot_payload.get("model_name", "")).strip(),
            "disease_analysis_model": str(image_payload.get("model_name", "")).strip(),
        },
        "fusion_summary": fusion_summary,
        "conflict_analysis": conflict_analysis,
        "slot_extraction": slot_payload,
        "image_analysis": image_payload,
        "display": display_payload,
        "caption": caption_payload,
        "structured_visual_evidence": visual_evidence_bundle,
    }
