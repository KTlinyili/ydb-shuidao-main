from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CauseItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    why_like: str = Field(min_length=1)
    why_unlike: str = ""


class CallMetaSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)
    request_id: str = ""
    is_real_output: bool = True
    used_fallback: bool = False


class DifferentialItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    why_supported: str = ""
    why_not_primary: str = ""


class EvidenceBoardItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: str = Field(min_length=1)
    supporting: list[str] = Field(default_factory=list)
    counter: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class DiagnosisBoardSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    working_diagnoses: list[str] = Field(default_factory=list)
    supporting: list[str] = Field(default_factory=list)
    counter: list[str] = Field(default_factory=list)
    differentials: list[DifferentialItemSchema] = Field(default_factory=list)


class EvidenceGapBoardSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_evidence: list[str] = Field(default_factory=list)
    verification_value: list[str] = Field(default_factory=list)


class ActionBoardSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    today_actions: list[str] = Field(default_factory=list)
    control_options: list[str] = Field(default_factory=list)
    observe_48h: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    management_timeline: list[str] = Field(default_factory=list)
    low_risk_actions: list[str] = Field(default_factory=list)
    environment_adjustments: list[str] = Field(default_factory=list)
    followup_nodes: list[str] = Field(default_factory=list)


class RiskBoardSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prohibited_actions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    confidence_boundary: list[str] = Field(default_factory=list)
    overtreatment_risks: list[str] = Field(default_factory=list)
    undertreatment_risks: list[str] = Field(default_factory=list)


class ExpertTurnBaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)
    invalid_turn: bool = False
    meta: CallMetaSchema | None = None


class DiagnosisEvidenceTurnSchema(ExpertTurnBaseSchema):
    visible_findings: list[str] = Field(default_factory=list)
    negative_findings: list[str] = Field(default_factory=list)
    candidate_causes: list[CauseItem] = Field(min_length=1, max_length=5)
    evidence_strength: str = ""


class DifferentialTurnSchema(ExpertTurnBaseSchema):
    ranked_differentials: list[DifferentialItemSchema] = Field(min_length=1, max_length=5)
    why_primary: list[str] = Field(default_factory=list)
    why_not_primary: list[str] = Field(default_factory=list)
    decisive_missing_evidence: list[str] = Field(default_factory=list)


class BerryActionTurnSchema(ExpertTurnBaseSchema):
    today_actions: list[str] = Field(default_factory=list)
    control_options: list[str] = Field(default_factory=list)
    observe_48h: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    key_evidence_gaps: list[str] = Field(default_factory=list)


class CultivationManagementTurnSchema(ExpertTurnBaseSchema):
    management_timeline: list[str] = Field(default_factory=list)
    low_risk_actions: list[str] = Field(default_factory=list)
    environment_adjustments: list[str] = Field(default_factory=list)
    followup_nodes: list[str] = Field(default_factory=list)


class RiskComplianceTurnSchema(ExpertTurnBaseSchema):
    prohibited_actions: list[str] = Field(default_factory=list)
    overtreatment_risks: list[str] = Field(default_factory=list)
    undertreatment_risks: list[str] = Field(default_factory=list)
    confidence_boundary: list[str] = Field(default_factory=list)


class ExpertTurnSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    top_k_causes: list[CauseItem] = Field(min_length=1, max_length=5)
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)
    invalid_turn: bool = False
    meta: CallMetaSchema | None = None


class CoordinatorSummarySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consensus: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    unique_points: list[str] = Field(default_factory=list)
    next_focus: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    working_diagnoses: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    recommended_experts: list[str] = Field(default_factory=list)
    uncertainty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    stop_signal: bool = False
    diagnosis_board: DiagnosisBoardSchema = Field(default_factory=DiagnosisBoardSchema)
    evidence_board: EvidenceGapBoardSchema = Field(default_factory=EvidenceGapBoardSchema)
    action_board: ActionBoardSchema = Field(default_factory=ActionBoardSchema)
    risk_board: RiskBoardSchema = Field(default_factory=RiskBoardSchema)
    diagnosis_evidence: list[EvidenceBoardItemSchema] = Field(default_factory=list)
    action_focus: list[str] = Field(default_factory=list)
    verification_tasks: list[str] = Field(default_factory=list)
    uncertainty_triggers: list[str] = Field(default_factory=list)
    report_priority: list[str] = Field(default_factory=list)
    evidence_sufficiency: str = ""


class TopDiagnosisSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    confidence: str = Field(min_length=1)


class CandidateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    why_like: str = ""
    why_unlike: str = ""


class SeverityRiskSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = ""
    spread_risk: str = ""
    pruning_guideline: str = ""


class RescuePlanItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str = Field(min_length=1)
    objective: str = ""
    actions: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    risk_level: str = ""


class FinalDiagnosisSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_diagnosis: TopDiagnosisSchema
    candidates: list[CandidateSchema] = Field(default_factory=list)
    reject_flag: str = ""
    symptom_summary: list[str] = Field(default_factory=list)
    visual_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    differential_points: list[str] = Field(default_factory=list)
    severity_risk: SeverityRiskSchema
    evidence_to_collect: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    evidence_board: list[EvidenceBoardItemSchema] = Field(default_factory=list)
    rescue_plan: list[RescuePlanItemSchema] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
    monitoring_plan: list[str] = Field(default_factory=list)
    report_outline: list[str] = Field(default_factory=list)
    evidence_sufficiency: str = ""
    confidence_statement: str = ""
    citations: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class SafetyReviewSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety_passed: bool
    flags: list[str] = Field(default_factory=list)
    revised_actions: list[str] = Field(default_factory=list)
    action_level: str = ""
    review_summary: str = ""
    prohibited_actions: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    evidence_sufficiency: str = ""


class MarkdownReportSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown_report: str = Field(min_length=120)


class MarkdownSectionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_title: str = Field(min_length=1)
    section_markdown: str = Field(
        min_length=120,
        description="本节全部可见正文，多段自然语言；勿写二级标题；勿重复章节名。",
    )


class BaselineOutputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_diagnosis: TopDiagnosisSchema
    candidates: list[CandidateSchema] = Field(default_factory=list)
    key_evidence: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    report_outline: list[str] = Field(default_factory=list)
    evidence_sufficiency: str = ""
    risks: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    markdown_report: str = Field(min_length=120)


AGENT_TURN_MODEL_BY_AGENT = {
    "diagnosis_evidence_officer": DiagnosisEvidenceTurnSchema,
    "differential_officer": DifferentialTurnSchema,
    "berry_qa_expert": BerryActionTurnSchema,
    "cultivation_management_officer": CultivationManagementTurnSchema,
    "risk_compliance_officer": RiskComplianceTurnSchema,  # kept for backward compat with saved runs
}


EXPERT_TURN_MODELS = tuple(AGENT_TURN_MODEL_BY_AGENT.values()) + (ExpertTurnSchema,)


def expert_turn_model_for_agent(agent_name: str):
    return AGENT_TURN_MODEL_BY_AGENT.get(str(agent_name).strip(), ExpertTurnSchema)
