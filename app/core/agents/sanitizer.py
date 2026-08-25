from __future__ import annotations

import ast
import re
from typing import Any

from app.core.agents.protocol_schema import (
    ActionBoardSchema,
    CallMetaSchema,
    CoordinatorSummarySchema,
    CultivationManagementTurnSchema,
    DiagnosisBoardSchema,
    DiagnosisEvidenceTurnSchema,
    DifferentialTurnSchema,
    EvidenceBoardItemSchema,
    EvidenceGapBoardSchema,
    ExpertTurnSchema,
    FinalDiagnosisSchema,
    RiskBoardSchema,
    RiskComplianceTurnSchema,
    BerryActionTurnSchema,
)


NOISY_PATTERNS = [
    r"<\|start\|>",
    r"<\|channel\|>",
    r"assistant<\|channel\|>analysis",
    r"^\s*we need\b",
    r"^\s*the user\b",
    r"token[s]?\s+truncated",
    r"generator object",
    r"jsondecodeerror",
    r"merge_shared_state",
    r"expecting .* delimiter",
]

TEXT_REPLACEMENTS = {
    "DINOv3": "图像分析",
    "分类头与分割头结果不一致": "整体印象与局部病斑特征并不完全一致",
    "分类头与分割头结果冲突": "整体印象与局部病斑特征并不完全一致",
    "分类头": "整体印象",
    "分割头": "局部病斑特征",
    "补充叶背近景、同叶位复拍图和整株图像": "继续保持审慎判断",
    "补充叶背近景和同叶位复拍图像": "继续保持审慎判断",
    "进一步检验": "进一步观察",
    "进一步检测": "进一步观察",
}


def _clean_text(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    lower = value.lower()
    for pattern in NOISY_PATTERNS:
        if re.search(pattern, lower, flags=re.IGNORECASE):
            return ""
    for source, target in TEXT_REPLACEMENTS.items():
        value = value.replace(source, target)
    return value


def _clean_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in values:
        text = _clean_text(str(item))
        if text:
            cleaned.append(text)
    return cleaned


def _coerce_structured_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
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


def sanitize_expert_turn(turn: dict[str, Any]) -> dict[str, Any]:
    model = ExpertTurnSchema.model_validate(turn)
    data = model.model_dump(mode="json")
    data["supporting_evidence"] = _clean_list(data.get("supporting_evidence", []))
    data["counter_evidence"] = _clean_list(data.get("counter_evidence", []))
    data["actions"] = _clean_list(data.get("actions", []))
    data["risks"] = _clean_list(data.get("risks", []))
    data["questions_to_ask"] = _clean_list(data.get("questions_to_ask", []))
    data["citations"] = _clean_list(data.get("citations", []))
    for cause in data.get("top_k_causes", []):
        cause["name"] = _clean_text(cause.get("name", "")) or "unknown"
        cause["why_like"] = _clean_text(cause.get("why_like", ""))
        cause["why_unlike"] = _clean_text(cause.get("why_unlike", ""))
    if data.get("meta"):
        data["meta"] = CallMetaSchema.model_validate(data["meta"]).model_dump(mode="json")
    return data


def sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    raw_summary = dict(summary)
    if isinstance(raw_summary.get("evidence_board"), list) and "diagnosis_evidence" not in raw_summary:
        raw_summary["diagnosis_evidence"] = raw_summary.get("evidence_board", [])
        raw_summary["evidence_board"] = {
            "missing_evidence": raw_summary.get("evidence_gaps", []),
            "verification_value": raw_summary.get("verification_tasks", []),
        }
    model = CoordinatorSummarySchema.model_validate(raw_summary)
    data = model.model_dump(mode="json")
    for key in (
        "consensus",
        "conflicts",
        "unique_points",
        "next_focus",
        "safety_flags",
        "working_diagnoses",
        "open_questions",
        "evidence_gaps",
        "recommended_experts",
        "action_focus",
        "verification_tasks",
        "uncertainty_triggers",
        "report_priority",
    ):
        data[key] = _clean_list(data.get(key, []))
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))
    cleaned_board: list[dict[str, Any]] = []
    for item in data.get("evidence_board", []):
        if not isinstance(item, dict):
            continue
        diagnosis = _clean_text(str(item.get("diagnosis", "")))
        if not diagnosis:
            continue
        cleaned_board.append(
            {
                "diagnosis": diagnosis,
                "supporting": _clean_list(item.get("supporting", [])),
                "counter": _clean_list(item.get("counter", [])),
                "missing": _clean_list(item.get("missing", [])),
                "sources": _clean_list(item.get("sources", [])),
            }
        )
    data["evidence_board"] = cleaned_board
    return data


def sanitize_final(final_result: dict[str, Any]) -> dict[str, Any]:
    model = FinalDiagnosisSchema.model_validate(final_result)
    data = model.model_dump(mode="json")
    for key in (
        "symptom_summary",
        "visual_evidence",
        "counter_evidence",
        "differential_points",
        "evidence_to_collect",
        "actions",
        "prohibited_actions",
        "monitoring_plan",
        "report_outline",
        "citations",
        "safety_notes",
    ):
        data[key] = _clean_list(data.get(key, []))
    data["top_diagnosis"]["name"] = _clean_text(data["top_diagnosis"]["name"]) or "unknown"
    data["top_diagnosis"]["confidence"] = _clean_text(data["top_diagnosis"]["confidence"]) or "low"
    data["reject_flag"] = _clean_text(data.get("reject_flag", ""))
    data["confidence_statement"] = _clean_text(data.get("confidence_statement", ""))
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))
    cleaned_board: list[dict[str, Any]] = []
    for item in data.get("evidence_board", []):
        diagnosis = _clean_text(str(item.get("diagnosis", "")))
        if not diagnosis:
            continue
        cleaned_board.append(
            {
                "diagnosis": diagnosis,
                "supporting": _clean_list(item.get("supporting", [])),
                "counter": _clean_list(item.get("counter", [])),
                "missing": _clean_list(item.get("missing", [])),
                "sources": _clean_list(item.get("sources", [])),
            }
        )
    data["evidence_board"] = cleaned_board
    cleaned_plan: list[dict[str, Any]] = []
    for item in data.get("rescue_plan", []):
        phase = _clean_text(str(item.get("phase", "")))
        if not phase:
            continue
        cleaned_plan.append(
            {
                "phase": phase,
                "objective": _clean_text(str(item.get("objective", ""))),
                "actions": _clean_list(item.get("actions", [])),
                "rationale": _clean_list(item.get("rationale", [])),
                "risk_level": _clean_text(str(item.get("risk_level", ""))),
            }
        )
    data["rescue_plan"] = cleaned_plan
    return data


def sanitize_trace(raw: dict[str, Any]) -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    for round_item in raw.get("rounds", []):
        turns = [sanitize_expert_turn(turn) for turn in round_item.get("expert_turns", [])]
        summary = sanitize_summary(round_item.get("summary", {}))
        shared_state = round_item.get("shared_state")
        rounds.append(
            {
                "round": int(round_item.get("round", len(rounds) + 1)),
                "active_agents": _clean_list(round_item.get("active_agents", [])),
                "layers": round_item.get("layers", []) if isinstance(round_item.get("layers"), list) else [],
                "expert_turns": turns,
                "summary": summary,
                "shared_state": shared_state if isinstance(shared_state, dict) else {},
            }
        )
    final_result = sanitize_final(raw.get("final", {}))
    clean: dict[str, Any] = {"rounds": rounds, "final": final_result}
    safety = raw.get("safety")
    if isinstance(safety, dict):
        clean["safety"] = safety
    shared_state = raw.get("shared_state")
    if isinstance(shared_state, dict):
        clean["shared_state"] = sanitize_shared_state(shared_state)
    for key in ("round_summary_meta", "final_meta", "safety_meta", "execution_meta"):
        value = raw.get(key)
        if isinstance(value, (dict, list)):
            clean[key] = value
    return clean


def sanitize_shared_state(shared_state: dict[str, Any]) -> dict[str, Any]:
    data = dict(shared_state)
    if isinstance(data.get("evidence_board"), list) and "diagnosis_evidence" not in data:
        data["diagnosis_evidence"] = data.get("evidence_board", [])
        data["evidence_board"] = {
            "missing_evidence": data.get("evidence_gaps", []),
            "verification_value": data.get("verification_tasks", []),
        }
    for key in (
        "consensus",
        "conflicts",
        "unique_points",
        "next_focus",
        "safety_flags",
        "working_diagnoses",
        "open_questions",
        "evidence_gaps",
        "recommended_experts",
        "active_agents",
        "proposed_actions",
        "action_focus",
        "verification_tasks",
        "uncertainty_triggers",
        "report_priority",
    ):
        data[key] = _clean_list(data.get(key, []))
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))
    cleaned_board: list[dict[str, Any]] = []
    for item in data.get("evidence_board", []):
        if not isinstance(item, dict):
            continue
        diagnosis = _clean_text(str(item.get("diagnosis", "")))
        if not diagnosis:
            continue
        cleaned_board.append(
            {
                "diagnosis": diagnosis,
                "supporting": _clean_list(item.get("supporting", [])),
                "counter": _clean_list(item.get("counter", [])),
                "missing": _clean_list(item.get("missing", [])),
                "sources": _clean_list(item.get("sources", [])),
            }
        )
    data["evidence_board"] = cleaned_board
    return data


_ROLE_LIST_FIELDS = {
    "diagnosis_evidence_officer": ["visible_findings", "negative_findings", "citations"],
    "differential_officer": ["why_primary", "why_not_primary", "decisive_missing_evidence", "citations"],
    "berry_qa_expert": [
        "today_actions",
        "control_options",
        "observe_48h",
        "escalation_triggers",
        "key_evidence_gaps",
        "citations",
    ],
    "cultivation_management_officer": [
        "management_timeline",
        "low_risk_actions",
        "environment_adjustments",
        "followup_nodes",
        "citations",
    ],
    "risk_compliance_officer": [
        "prohibited_actions",
        "overtreatment_risks",
        "undertreatment_risks",
        "confidence_boundary",
        "citations",
    ],
}

_ROLE_TEXT_FIELDS = {
    "diagnosis_evidence_officer": ["evidence_strength"],
}

_ROLE_VIOLATION_PATTERNS = {
    "diagnosis_evidence_officer": re.compile(r"(喷|用药|处理|处置|48\s*小时|升级)"),
    "differential_officer": re.compile(r"(喷|用药|处理|处置|今天|48\s*小时|升级)"),
    "berry_qa_expert": re.compile(r"(首要诊断|排第|诊断为|最终诊断|主诊断)"),
    "cultivation_management_officer": re.compile(r"(首要诊断|排第|诊断为|最终诊断|主诊断)"),
    "risk_compliance_officer": re.compile(r"(首要诊断|排第|诊断为|最终诊断|主诊断|病斑呈|病斑为)"),
}

_ROLE_MODELS = {
    "diagnosis_evidence_officer": DiagnosisEvidenceTurnSchema,
    "differential_officer": DifferentialTurnSchema,
    "berry_qa_expert": BerryActionTurnSchema,
    "cultivation_management_officer": CultivationManagementTurnSchema,
    "risk_compliance_officer": RiskComplianceTurnSchema,
}


def _normalize_agent_name(turn: dict[str, Any]) -> str:
    agent_name = str(turn.get("agent_name", "")).strip()
    if agent_name in _ROLE_MODELS:
        return agent_name

    keys = {str(key).strip() for key in turn.keys()}
    if {"candidate_causes", "visible_findings"} & keys:
        return "diagnosis_evidence_officer"
    if {"ranked_differentials", "why_primary", "decisive_missing_evidence"} & keys:
        return "differential_officer"
    if {"today_actions", "control_options", "observe_48h", "escalation_triggers", "key_evidence_gaps"} & keys:
        return "berry_qa_expert"
    if {"management_timeline", "low_risk_actions", "environment_adjustments", "followup_nodes"} & keys:
        return "cultivation_management_officer"
    if {"prohibited_actions", "overtreatment_risks", "undertreatment_risks", "confidence_boundary"} & keys:
        return "risk_compliance_officer"
    return agent_name


def _role_model_for_turn(turn: dict[str, Any]):
    agent_name = _normalize_agent_name(turn)
    return _ROLE_MODELS.get(agent_name, ExpertTurnSchema)


def _clean_role_lists(agent_name: str, data: dict[str, Any]) -> None:
    pattern = _ROLE_VIOLATION_PATTERNS.get(agent_name)
    for key in _ROLE_LIST_FIELDS.get(agent_name, []):
        cleaned = _clean_list(data.get(key, []))
        if pattern is not None:
            cleaned = [item for item in cleaned if not pattern.search(item)]
        data[key] = cleaned
    for key in _ROLE_TEXT_FIELDS.get(agent_name, []):
        text = _clean_text(str(data.get(key, "")))
        if pattern is not None and pattern.search(text):
            text = ""
        data[key] = text


def _clean_candidate_causes(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        item = _coerce_mapping(item)
        if not item:
            continue
        name = _clean_text(str(item.get("name", ""))) or "unknown"
        why_like = _clean_text(str(item.get("why_like", "")))
        why_unlike = _clean_text(str(item.get("why_unlike", "")))
        cleaned.append({"name": name, "why_like": why_like, "why_unlike": why_unlike})
    return cleaned


def _clean_ranked_differentials(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        item = _coerce_mapping(item)
        if not item:
            continue
        name = _clean_text(str(item.get("name", "")))
        if not name:
            continue
        cleaned.append(
            {
                "name": name,
                "why_supported": _clean_text(str(item.get("why_supported", ""))),
                "why_not_primary": _clean_text(str(item.get("why_not_primary", ""))),
            }
        )
    return cleaned


def _build_compat_turn(agent_name: str, data: dict[str, Any]) -> dict[str, Any]:
    compat = {
        "top_k_causes": [],
        "supporting_evidence": [],
        "counter_evidence": [],
        "actions": [],
        "risks": [],
        "questions_to_ask": [],
        "confidence": 0.5,
        "evidence_board": [],
    }
    if agent_name == "diagnosis_evidence_officer":
        compat["top_k_causes"] = list(data.get("candidate_causes", []))
        compat["supporting_evidence"] = list(data.get("visible_findings", []))
        compat["counter_evidence"] = list(data.get("negative_findings", []))
        compat["evidence_board"] = [
            {
                "diagnosis": cause.get("name", ""),
                "supporting": _clean_list(list(data.get("visible_findings", [])) + [cause.get("why_like", "")]),
                "counter": _clean_list(list(data.get("negative_findings", [])) + [cause.get("why_unlike", "")]),
                "missing": [],
                "sources": list(data.get("citations", [])),
            }
            for cause in data.get("candidate_causes", [])
            if str(cause.get("name", "")).strip()
        ]
    elif agent_name == "differential_officer":
        compat["top_k_causes"] = [
            {
                "name": item.get("name", ""),
                "why_like": item.get("why_supported", ""),
                "why_unlike": item.get("why_not_primary", ""),
            }
            for item in data.get("ranked_differentials", [])
        ]
        compat["supporting_evidence"] = list(data.get("why_primary", []))
        compat["counter_evidence"] = list(data.get("why_not_primary", []))
        compat["questions_to_ask"] = list(data.get("decisive_missing_evidence", []))
        compat["evidence_board"] = [
            {
                "diagnosis": item.get("name", ""),
                "supporting": _clean_list(list(data.get("why_primary", [])) + [item.get("why_supported", "")]),
                "counter": _clean_list(list(data.get("why_not_primary", [])) + [item.get("why_not_primary", "")]),
                "missing": list(data.get("decisive_missing_evidence", [])),
                "sources": list(data.get("citations", [])),
            }
            for item in data.get("ranked_differentials", [])
            if str(item.get("name", "")).strip()
        ]
    elif agent_name == "berry_qa_expert":
        compat["actions"] = _clean_list(list(data.get("today_actions", [])) + list(data.get("control_options", [])))
        compat["questions_to_ask"] = list(data.get("observe_48h", [])) or list(data.get("key_evidence_gaps", []))
        compat["risks"] = list(data.get("escalation_triggers", []))
    elif agent_name == "cultivation_management_officer":
        compat["actions"] = _clean_list(
            list(data.get("low_risk_actions", [])) + list(data.get("environment_adjustments", []))
        )
        compat["questions_to_ask"] = list(data.get("followup_nodes", []))
    elif agent_name == "risk_compliance_officer":
        compat["risks"] = _clean_list(
            list(data.get("overtreatment_risks", [])) + list(data.get("undertreatment_risks", []))
        )
        compat["questions_to_ask"] = list(data.get("confidence_boundary", []))
    return compat


def _mark_invalid_if_empty(agent_name: str, data: dict[str, Any]) -> None:
    required_map = {
        "diagnosis_evidence_officer": bool(data.get("candidate_causes")),
        "differential_officer": bool(data.get("ranked_differentials")),
        "berry_qa_expert": bool(data.get("today_actions"))
        or bool(data.get("control_options"))
        or bool(data.get("observe_48h")),
        "cultivation_management_officer": bool(data.get("low_risk_actions")),
        "risk_compliance_officer": bool(data.get("prohibited_actions")) or bool(data.get("confidence_boundary")),
    }
    if agent_name in required_map and not required_map[agent_name]:
        data["invalid_turn"] = True


def sanitize_expert_turn(turn: dict[str, Any]) -> dict[str, Any]:
    agent_name = _normalize_agent_name(turn)
    model_cls = _role_model_for_turn(turn)
    if model_cls is ExpertTurnSchema:
        raw = turn
    else:
        allowed_keys = set(model_cls.model_fields)
        raw = {key: value for key, value in turn.items() if key in allowed_keys}
        raw["agent_name"] = agent_name
    model = model_cls.model_validate(raw)
    data = model.model_dump(mode="json")
    if model_cls is ExpertTurnSchema:
        data["supporting_evidence"] = _clean_list(data.get("supporting_evidence", []))
        data["counter_evidence"] = _clean_list(data.get("counter_evidence", []))
        data["actions"] = _clean_list(data.get("actions", []))
        data["risks"] = _clean_list(data.get("risks", []))
        data["questions_to_ask"] = _clean_list(data.get("questions_to_ask", []))
        data["citations"] = _clean_list(data.get("citations", []))
        data["top_k_causes"] = _clean_candidate_causes(data.get("top_k_causes", []))
    else:
        _clean_role_lists(agent_name, data)
        if agent_name == "diagnosis_evidence_officer":
            data["candidate_causes"] = _clean_candidate_causes(data.get("candidate_causes", []))
        if agent_name == "differential_officer":
            data["ranked_differentials"] = _clean_ranked_differentials(data.get("ranked_differentials", []))
        data.update(_build_compat_turn(agent_name, data))
        _mark_invalid_if_empty(agent_name, data)
    if data.get("meta"):
        data["meta"] = CallMetaSchema.model_validate(data["meta"]).model_dump(mode="json")
    return data


def _clean_diagnosis_evidence_entries(values: Any) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        item = _coerce_mapping(item)
        if not item:
            continue
        diagnosis = _clean_text(str(item.get("diagnosis", "")))
        if not diagnosis:
            continue
        cleaned.append(
            {
                "diagnosis": diagnosis,
                "supporting": _clean_list(item.get("supporting", [])),
                "counter": _clean_list(item.get("counter", [])),
                "missing": _clean_list(item.get("missing", [])),
                "sources": _clean_list(item.get("sources", [])),
            }
        )
    return cleaned


def sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    model = CoordinatorSummarySchema.model_validate(summary)
    data = model.model_dump(mode="json")
    for key in (
        "consensus",
        "conflicts",
        "unique_points",
        "next_focus",
        "safety_flags",
        "working_diagnoses",
        "open_questions",
        "evidence_gaps",
        "recommended_experts",
        "action_focus",
        "verification_tasks",
        "uncertainty_triggers",
        "report_priority",
    ):
        data[key] = _clean_list(data.get(key, []))
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))
    data["diagnosis_board"] = DiagnosisBoardSchema.model_validate(
        {
            "working_diagnoses": _clean_list(data.get("diagnosis_board", {}).get("working_diagnoses", [])),
            "supporting": _clean_list(data.get("diagnosis_board", {}).get("supporting", [])),
            "counter": _clean_list(data.get("diagnosis_board", {}).get("counter", [])),
            "differentials": _clean_ranked_differentials(data.get("diagnosis_board", {}).get("differentials", [])),
        }
    ).model_dump(mode="json")
    data["evidence_board"] = EvidenceGapBoardSchema.model_validate(
        {
            "missing_evidence": _clean_list(data.get("evidence_board", {}).get("missing_evidence", [])),
            "verification_value": _clean_list(data.get("evidence_board", {}).get("verification_value", [])),
        }
    ).model_dump(mode="json")
    data["action_board"] = ActionBoardSchema.model_validate(
        {
            "today_actions": _clean_list(data.get("action_board", {}).get("today_actions", [])),
            "control_options": _clean_list(data.get("action_board", {}).get("control_options", [])),
            "observe_48h": _clean_list(data.get("action_board", {}).get("observe_48h", [])),
            "escalation_triggers": _clean_list(data.get("action_board", {}).get("escalation_triggers", [])),
            "management_timeline": _clean_list(data.get("action_board", {}).get("management_timeline", [])),
            "low_risk_actions": _clean_list(data.get("action_board", {}).get("low_risk_actions", [])),
            "environment_adjustments": _clean_list(data.get("action_board", {}).get("environment_adjustments", [])),
            "followup_nodes": _clean_list(data.get("action_board", {}).get("followup_nodes", [])),
        }
    ).model_dump(mode="json")
    data["risk_board"] = RiskBoardSchema.model_validate(
        {
            "prohibited_actions": _clean_list(data.get("risk_board", {}).get("prohibited_actions", [])),
            "risk_flags": _clean_list(data.get("risk_board", {}).get("risk_flags", [])),
            "confidence_boundary": _clean_list(data.get("risk_board", {}).get("confidence_boundary", [])),
            "overtreatment_risks": _clean_list(data.get("risk_board", {}).get("overtreatment_risks", [])),
            "undertreatment_risks": _clean_list(data.get("risk_board", {}).get("undertreatment_risks", [])),
        }
    ).model_dump(mode="json")
    data["diagnosis_evidence"] = _clean_diagnosis_evidence_entries(data.get("diagnosis_evidence", []))
    return data


def _sanitize_summary_v3(summary: dict[str, Any]) -> dict[str, Any]:
    model = CoordinatorSummarySchema.model_validate(summary)
    data = model.model_dump(mode="json")
    for key in ("consensus", "unique_points", "safety_flags", "recommended_experts", "action_focus", "report_priority"):
        data[key] = _clean_list(data.get(key, []))

    working_diagnoses = _clean_diagnosis_names(data.get("working_diagnoses", []))
    data["working_diagnoses"] = working_diagnoses
    data["open_questions"] = _clean_gap_like_list(data.get("open_questions", []))
    data["evidence_gaps"] = _clean_gap_like_list(data.get("evidence_gaps", []))
    data["verification_tasks"] = _clean_verification_value_list(data.get("verification_tasks", []))
    data["conflicts"] = _clean_counter_like_list(data.get("conflicts", []), working_diagnoses)
    data["next_focus"] = _clean_counter_like_list(data.get("next_focus", []), working_diagnoses)
    data["uncertainty_triggers"] = _clean_counter_like_list(data.get("uncertainty_triggers", []), working_diagnoses)
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))

    diagnosis_board = data.get("diagnosis_board", {}) if isinstance(data.get("diagnosis_board"), dict) else {}
    board_diagnoses = _clean_diagnosis_names(diagnosis_board.get("working_diagnoses", [])) or working_diagnoses
    data["diagnosis_board"] = DiagnosisBoardSchema.model_validate(
        {
            "working_diagnoses": board_diagnoses,
            "supporting": _clean_list(diagnosis_board.get("supporting", [])),
            "counter": _clean_counter_like_list(diagnosis_board.get("counter", []), board_diagnoses),
            "differentials": _clean_ranked_differentials(diagnosis_board.get("differentials", [])),
        }
    ).model_dump(mode="json")
    data["evidence_board"] = EvidenceGapBoardSchema.model_validate(
        {
            "missing_evidence": _clean_gap_like_list(data.get("evidence_board", {}).get("missing_evidence", [])),
            "verification_value": _clean_verification_value_list(data.get("evidence_board", {}).get("verification_value", [])),
        }
    ).model_dump(mode="json")
    data["action_board"] = ActionBoardSchema.model_validate(
        {
            "today_actions": _clean_list(data.get("action_board", {}).get("today_actions", [])),
            "control_options": _clean_list(data.get("action_board", {}).get("control_options", [])),
            "observe_48h": _clean_gap_like_list(data.get("action_board", {}).get("observe_48h", [])),
            "escalation_triggers": _clean_action_trigger_list(data.get("action_board", {}).get("escalation_triggers", [])),
            "management_timeline": _clean_list(data.get("action_board", {}).get("management_timeline", [])),
            "low_risk_actions": _clean_list(data.get("action_board", {}).get("low_risk_actions", [])),
            "environment_adjustments": _clean_list(data.get("action_board", {}).get("environment_adjustments", [])),
            "followup_nodes": _clean_gap_like_list(data.get("action_board", {}).get("followup_nodes", [])),
        }
    ).model_dump(mode="json")
    data["risk_board"] = RiskBoardSchema.model_validate(
        {
            "prohibited_actions": _clean_list(data.get("risk_board", {}).get("prohibited_actions", [])),
            "risk_flags": _clean_list(data.get("risk_board", {}).get("risk_flags", [])),
            "confidence_boundary": _clean_gap_like_list(data.get("risk_board", {}).get("confidence_boundary", [])),
            "overtreatment_risks": _clean_list(data.get("risk_board", {}).get("overtreatment_risks", [])),
            "undertreatment_risks": _clean_list(data.get("risk_board", {}).get("undertreatment_risks", [])),
        }
    ).model_dump(mode="json")
    data["diagnosis_evidence"] = _clean_diagnosis_evidence_entries(data.get("diagnosis_evidence", []))
    return data


def _sanitize_shared_state_v3(shared_state: dict[str, Any]) -> dict[str, Any]:
    data = dict(shared_state)
    for key in ("consensus", "unique_points", "safety_flags", "recommended_experts", "active_agents", "proposed_actions", "action_focus", "report_priority"):
        data[key] = _clean_list(data.get(key, []))

    working_diagnoses = _clean_diagnosis_names(data.get("working_diagnoses", []))
    data["working_diagnoses"] = working_diagnoses
    data["open_questions"] = _clean_gap_like_list(data.get("open_questions", []))
    data["evidence_gaps"] = _clean_gap_like_list(data.get("evidence_gaps", []))
    data["verification_tasks"] = _clean_verification_value_list(data.get("verification_tasks", []))
    data["conflicts"] = _clean_counter_like_list(data.get("conflicts", []), working_diagnoses)
    data["next_focus"] = _clean_counter_like_list(data.get("next_focus", []), working_diagnoses)
    data["uncertainty_triggers"] = _clean_counter_like_list(data.get("uncertainty_triggers", []), working_diagnoses)
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))

    diagnosis_board = data.get("diagnosis_board", {}) if isinstance(data.get("diagnosis_board"), dict) else {}
    board_diagnoses = _clean_diagnosis_names(diagnosis_board.get("working_diagnoses", [])) or working_diagnoses
    data["diagnosis_board"] = DiagnosisBoardSchema.model_validate(
        {
            "working_diagnoses": board_diagnoses,
            "supporting": _clean_list(diagnosis_board.get("supporting", [])),
            "counter": _clean_counter_like_list(diagnosis_board.get("counter", []), board_diagnoses),
            "differentials": _clean_ranked_differentials(diagnosis_board.get("differentials", [])),
        }
    ).model_dump(mode="json")
    data["evidence_board"] = EvidenceGapBoardSchema.model_validate(
        {
            "missing_evidence": _clean_gap_like_list(data.get("evidence_board", {}).get("missing_evidence", [])),
            "verification_value": _clean_verification_value_list(data.get("evidence_board", {}).get("verification_value", [])),
        }
    ).model_dump(mode="json")
    data["action_board"] = ActionBoardSchema.model_validate(
        {
            "today_actions": _clean_list(data.get("action_board", {}).get("today_actions", [])),
            "control_options": _clean_list(data.get("action_board", {}).get("control_options", [])),
            "observe_48h": _clean_gap_like_list(data.get("action_board", {}).get("observe_48h", [])),
            "escalation_triggers": _clean_action_trigger_list(data.get("action_board", {}).get("escalation_triggers", [])),
            "management_timeline": _clean_list(data.get("action_board", {}).get("management_timeline", [])),
            "low_risk_actions": _clean_list(data.get("action_board", {}).get("low_risk_actions", [])),
            "environment_adjustments": _clean_list(data.get("action_board", {}).get("environment_adjustments", [])),
            "followup_nodes": _clean_gap_like_list(data.get("action_board", {}).get("followup_nodes", [])),
        }
    ).model_dump(mode="json")
    data["risk_board"] = RiskBoardSchema.model_validate(
        {
            "prohibited_actions": _clean_list(data.get("risk_board", {}).get("prohibited_actions", [])),
            "risk_flags": _clean_list(data.get("risk_board", {}).get("risk_flags", [])),
            "confidence_boundary": _clean_gap_like_list(data.get("risk_board", {}).get("confidence_boundary", [])),
            "overtreatment_risks": _clean_list(data.get("risk_board", {}).get("overtreatment_risks", [])),
            "undertreatment_risks": _clean_list(data.get("risk_board", {}).get("undertreatment_risks", [])),
        }
    ).model_dump(mode="json")
    data["diagnosis_evidence"] = _clean_diagnosis_evidence_entries(data.get("diagnosis_evidence", []))
    return data


sanitize_summary = _sanitize_summary_v3
sanitize_shared_state = _sanitize_shared_state_v3


_DIAGNOSIS_NAME_MAP = {
    "rice_blast": "稻瘟病",
    "sheath_blight": "纹枯病",
    "bacterial_leaf_blight": "白叶枯病",
    "brown_spot": "褐斑病",
    "bacterial_stripe": "细菌性条斑病",
    "rice_planthopper": "稻飞虱",
    "rice_leaf_roller": "稻纵卷叶螟",
    "rice_stem_borer": "二化螟",
    "healthy": "健康",
}

_PLACEHOLDER_TOKENS = {"无法判断", "未知", "unknown", "待确认", "待进一步确认"}
_PEST_ABSENCE_HINTS = ("未观察到明显的虫害迹象", "未见明显虫害", "无明显虫害", "未见虫害")
_PEST_DIAGNOSIS_HINTS = ("螨", "虫")


def _normalize_diagnosis_name(value: Any) -> str:
    text = _clean_text(str(value))
    if not text:
        return ""
    return _DIAGNOSIS_NAME_MAP.get(text, text)


def _clean_diagnosis_names(values: Any) -> list[str]:
    names: list[str] = []
    for item in _coerce_list(values) if not isinstance(values, list) else values:
        name = _normalize_diagnosis_name(item)
        if name and name not in names:
            names.append(name)
    return names


def _is_placeholder_text(value: Any) -> bool:
    text = _clean_text(str(value))
    if not text:
        return True
    lowered = text.lower()
    if lowered in _PLACEHOLDER_TOKENS:
        return True
    if "请复核以下不确定信息" in text and "无法判断" in text:
        return True
    if "需复核以下不确定信息" in text and "无法判断" in text:
        return True
    return False


def _has_pest_diagnosis(diagnoses: list[str]) -> bool:
    return any(any(hint in name for hint in _PEST_DIAGNOSIS_HINTS) for name in diagnoses)


def _clean_gap_like_list(values: Any) -> list[str]:
    cleaned: list[str] = []
    source = _coerce_list(values) if not isinstance(values, list) else values
    for item in source:
        text = _clean_text(str(item))
        if not text or _is_placeholder_text(text):
            continue
        cleaned.append(text)
    return cleaned


def _clean_verification_value_list(values: Any) -> list[str]:
    cleaned: list[str] = []
    source = _coerce_list(values) if not isinstance(values, list) else values
    for item in source:
        text = _clean_text(str(item))
        if not text:
            continue
        if "无法判断" in text and "补齐" in text:
            continue
        cleaned.append(text)
    return cleaned


def _clean_counter_like_list(values: Any, diagnoses: list[str]) -> list[str]:
    cleaned: list[str] = []
    pest_case = _has_pest_diagnosis(diagnoses)
    source = _coerce_list(values) if not isinstance(values, list) else values
    for item in source:
        text = _clean_text(str(item))
        if not text or _is_placeholder_text(text):
            continue
        if not pest_case and any(hint in text for hint in _PEST_ABSENCE_HINTS):
            continue
        cleaned.append(text)
    return cleaned


def _clean_action_trigger_list(values: Any) -> list[str]:
    cleaned: list[str] = []
    source = _coerce_list(values) if not isinstance(values, list) else values
    for item in source:
        text = _clean_text(str(item))
        if not text or _is_placeholder_text(text):
            continue
        cleaned.append(text)
    return cleaned


def _clean_candidate_causes(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        item = _coerce_mapping(item)
        if not item:
            continue
        name = _normalize_diagnosis_name(item.get("name", "")) or "unknown"
        why_like = _clean_text(str(item.get("why_like", "")))
        why_unlike = _clean_text(str(item.get("why_unlike", "")))
        cleaned.append({"name": name, "why_like": why_like, "why_unlike": why_unlike})
    return cleaned


def _clean_ranked_differentials(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        item = _coerce_mapping(item)
        if not item:
            continue
        name = _normalize_diagnosis_name(item.get("name", ""))
        if not name:
            continue
        cleaned.append(
            {
                "name": name,
                "why_supported": _clean_text(str(item.get("why_supported", ""))),
                "why_not_primary": _clean_text(str(item.get("why_not_primary", ""))),
            }
        )
    return cleaned


def _clean_diagnosis_evidence_entries(values: Any) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in _coerce_list(values):
        item = _coerce_mapping(item)
        if not item:
            continue
        diagnosis = _normalize_diagnosis_name(item.get("diagnosis", ""))
        if not diagnosis:
            continue
        cleaned.append(
            {
                "diagnosis": diagnosis,
                "supporting": _clean_list(item.get("supporting", [])),
                "counter": _clean_counter_like_list(item.get("counter", []), [diagnosis]),
                "missing": _clean_gap_like_list(item.get("missing", [])),
                "sources": _clean_list(item.get("sources", [])),
            }
        )
    return cleaned


def sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    model = CoordinatorSummarySchema.model_validate(summary)
    data = model.model_dump(mode="json")
    for key in ("consensus", "unique_points", "safety_flags", "recommended_experts", "action_focus", "report_priority"):
        data[key] = _clean_list(data.get(key, []))

    working_diagnoses = _clean_diagnosis_names(data.get("working_diagnoses", []))
    data["working_diagnoses"] = working_diagnoses
    data["open_questions"] = _clean_gap_like_list(data.get("open_questions", []))
    data["evidence_gaps"] = _clean_gap_like_list(data.get("evidence_gaps", []))
    data["verification_tasks"] = _clean_verification_value_list(data.get("verification_tasks", []))
    data["conflicts"] = _clean_counter_like_list(data.get("conflicts", []), working_diagnoses)
    data["next_focus"] = _clean_counter_like_list(data.get("next_focus", []), working_diagnoses)
    data["uncertainty_triggers"] = _clean_counter_like_list(data.get("uncertainty_triggers", []), working_diagnoses)
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))

    diagnosis_board = data.get("diagnosis_board", {}) if isinstance(data.get("diagnosis_board"), dict) else {}
    board_diagnoses = _clean_diagnosis_names(diagnosis_board.get("working_diagnoses", [])) or working_diagnoses
    data["diagnosis_board"] = DiagnosisBoardSchema.model_validate(
        {
            "working_diagnoses": board_diagnoses,
            "supporting": _clean_list(diagnosis_board.get("supporting", [])),
            "counter": _clean_counter_like_list(diagnosis_board.get("counter", []), board_diagnoses),
            "differentials": _clean_ranked_differentials(diagnosis_board.get("differentials", [])),
        }
    ).model_dump(mode="json")
    data["evidence_board"] = EvidenceGapBoardSchema.model_validate(
        {
            "missing_evidence": _clean_gap_like_list(data.get("evidence_board", {}).get("missing_evidence", [])),
            "verification_value": _clean_verification_value_list(data.get("evidence_board", {}).get("verification_value", [])),
        }
    ).model_dump(mode="json")
    data["action_board"] = ActionBoardSchema.model_validate(
        {
            "today_actions": _clean_list(data.get("action_board", {}).get("today_actions", [])),
            "control_options": _clean_list(data.get("action_board", {}).get("control_options", [])),
            "observe_48h": _clean_gap_like_list(data.get("action_board", {}).get("observe_48h", [])),
            "escalation_triggers": _clean_action_trigger_list(data.get("action_board", {}).get("escalation_triggers", [])),
            "management_timeline": _clean_list(data.get("action_board", {}).get("management_timeline", [])),
            "low_risk_actions": _clean_list(data.get("action_board", {}).get("low_risk_actions", [])),
            "environment_adjustments": _clean_list(data.get("action_board", {}).get("environment_adjustments", [])),
            "followup_nodes": _clean_gap_like_list(data.get("action_board", {}).get("followup_nodes", [])),
        }
    ).model_dump(mode="json")
    data["risk_board"] = RiskBoardSchema.model_validate(
        {
            "prohibited_actions": _clean_list(data.get("risk_board", {}).get("prohibited_actions", [])),
            "risk_flags": _clean_list(data.get("risk_board", {}).get("risk_flags", [])),
            "confidence_boundary": _clean_gap_like_list(data.get("risk_board", {}).get("confidence_boundary", [])),
            "overtreatment_risks": _clean_list(data.get("risk_board", {}).get("overtreatment_risks", [])),
            "undertreatment_risks": _clean_list(data.get("risk_board", {}).get("undertreatment_risks", [])),
        }
    ).model_dump(mode="json")
    data["diagnosis_evidence"] = _clean_diagnosis_evidence_entries(data.get("diagnosis_evidence", []))
    return data


def sanitize_shared_state(shared_state: dict[str, Any]) -> dict[str, Any]:
    data = dict(shared_state)
    for key in ("consensus", "unique_points", "safety_flags", "recommended_experts", "active_agents", "proposed_actions", "action_focus", "report_priority"):
        data[key] = _clean_list(data.get(key, []))

    working_diagnoses = _clean_diagnosis_names(data.get("working_diagnoses", []))
    data["working_diagnoses"] = working_diagnoses
    data["open_questions"] = _clean_gap_like_list(data.get("open_questions", []))
    data["evidence_gaps"] = _clean_gap_like_list(data.get("evidence_gaps", []))
    data["verification_tasks"] = _clean_verification_value_list(data.get("verification_tasks", []))
    data["conflicts"] = _clean_counter_like_list(data.get("conflicts", []), working_diagnoses)
    data["next_focus"] = _clean_counter_like_list(data.get("next_focus", []), working_diagnoses)
    data["uncertainty_triggers"] = _clean_counter_like_list(data.get("uncertainty_triggers", []), working_diagnoses)
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))

    diagnosis_board = data.get("diagnosis_board", {}) if isinstance(data.get("diagnosis_board"), dict) else {}
    board_diagnoses = _clean_diagnosis_names(diagnosis_board.get("working_diagnoses", [])) or working_diagnoses
    data["diagnosis_board"] = DiagnosisBoardSchema.model_validate(
        {
            "working_diagnoses": board_diagnoses,
            "supporting": _clean_list(diagnosis_board.get("supporting", [])),
            "counter": _clean_counter_like_list(diagnosis_board.get("counter", []), board_diagnoses),
            "differentials": _clean_ranked_differentials(diagnosis_board.get("differentials", [])),
        }
    ).model_dump(mode="json")
    data["evidence_board"] = EvidenceGapBoardSchema.model_validate(
        {
            "missing_evidence": _clean_gap_like_list(data.get("evidence_board", {}).get("missing_evidence", [])),
            "verification_value": _clean_verification_value_list(data.get("evidence_board", {}).get("verification_value", [])),
        }
    ).model_dump(mode="json")
    data["action_board"] = ActionBoardSchema.model_validate(
        {
            "today_actions": _clean_list(data.get("action_board", {}).get("today_actions", [])),
            "control_options": _clean_list(data.get("action_board", {}).get("control_options", [])),
            "observe_48h": _clean_gap_like_list(data.get("action_board", {}).get("observe_48h", [])),
            "escalation_triggers": _clean_action_trigger_list(data.get("action_board", {}).get("escalation_triggers", [])),
            "management_timeline": _clean_list(data.get("action_board", {}).get("management_timeline", [])),
            "low_risk_actions": _clean_list(data.get("action_board", {}).get("low_risk_actions", [])),
            "environment_adjustments": _clean_list(data.get("action_board", {}).get("environment_adjustments", [])),
            "followup_nodes": _clean_gap_like_list(data.get("action_board", {}).get("followup_nodes", [])),
        }
    ).model_dump(mode="json")
    data["risk_board"] = RiskBoardSchema.model_validate(
        {
            "prohibited_actions": _clean_list(data.get("risk_board", {}).get("prohibited_actions", [])),
            "risk_flags": _clean_list(data.get("risk_board", {}).get("risk_flags", [])),
            "confidence_boundary": _clean_gap_like_list(data.get("risk_board", {}).get("confidence_boundary", [])),
            "overtreatment_risks": _clean_list(data.get("risk_board", {}).get("overtreatment_risks", [])),
            "undertreatment_risks": _clean_list(data.get("risk_board", {}).get("undertreatment_risks", [])),
        }
    ).model_dump(mode="json")
    data["diagnosis_evidence"] = _clean_diagnosis_evidence_entries(data.get("diagnosis_evidence", []))
    return data


def sanitize_shared_state(shared_state: dict[str, Any]) -> dict[str, Any]:
    data = dict(shared_state)
    for key in (
        "consensus",
        "conflicts",
        "unique_points",
        "next_focus",
        "safety_flags",
        "working_diagnoses",
        "open_questions",
        "evidence_gaps",
        "recommended_experts",
        "active_agents",
        "proposed_actions",
        "action_focus",
        "verification_tasks",
        "uncertainty_triggers",
        "report_priority",
    ):
        data[key] = _clean_list(data.get(key, []))
    data["evidence_sufficiency"] = _clean_text(str(data.get("evidence_sufficiency", "")))
    data["diagnosis_board"] = DiagnosisBoardSchema.model_validate(
        {
            "working_diagnoses": _clean_list(data.get("diagnosis_board", {}).get("working_diagnoses", [])),
            "supporting": _clean_list(data.get("diagnosis_board", {}).get("supporting", [])),
            "counter": _clean_list(data.get("diagnosis_board", {}).get("counter", [])),
            "differentials": _clean_ranked_differentials(data.get("diagnosis_board", {}).get("differentials", [])),
        }
    ).model_dump(mode="json")
    data["evidence_board"] = EvidenceGapBoardSchema.model_validate(
        {
            "missing_evidence": _clean_list(data.get("evidence_board", {}).get("missing_evidence", [])),
            "verification_value": _clean_list(data.get("evidence_board", {}).get("verification_value", [])),
        }
    ).model_dump(mode="json")
    data["action_board"] = ActionBoardSchema.model_validate(
        {
            "today_actions": _clean_list(data.get("action_board", {}).get("today_actions", [])),
            "control_options": _clean_list(data.get("action_board", {}).get("control_options", [])),
            "observe_48h": _clean_list(data.get("action_board", {}).get("observe_48h", [])),
            "escalation_triggers": _clean_list(data.get("action_board", {}).get("escalation_triggers", [])),
            "management_timeline": _clean_list(data.get("action_board", {}).get("management_timeline", [])),
            "low_risk_actions": _clean_list(data.get("action_board", {}).get("low_risk_actions", [])),
            "environment_adjustments": _clean_list(data.get("action_board", {}).get("environment_adjustments", [])),
            "followup_nodes": _clean_list(data.get("action_board", {}).get("followup_nodes", [])),
        }
    ).model_dump(mode="json")
    data["risk_board"] = RiskBoardSchema.model_validate(
        {
            "prohibited_actions": _clean_list(data.get("risk_board", {}).get("prohibited_actions", [])),
            "risk_flags": _clean_list(data.get("risk_board", {}).get("risk_flags", [])),
            "confidence_boundary": _clean_list(data.get("risk_board", {}).get("confidence_boundary", [])),
            "overtreatment_risks": _clean_list(data.get("risk_board", {}).get("overtreatment_risks", [])),
            "undertreatment_risks": _clean_list(data.get("risk_board", {}).get("undertreatment_risks", [])),
        }
    ).model_dump(mode="json")
    data["diagnosis_evidence"] = _clean_diagnosis_evidence_entries(data.get("diagnosis_evidence", []))
    return data
