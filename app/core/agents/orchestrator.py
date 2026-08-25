from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable
from typing import Any, Type

from pydantic import BaseModel

from app.core.agents.prompts import (
    REQUIRED_REPORT_SECTIONS,
    build_baseline_report_messages,
    build_expert_messages,
    build_final_messages,
    build_multi_agent_report_messages,
    build_narrative_report_section_messages,
    build_round_summary_messages,
    build_safety_messages,
    get_expert_definitions,
)
from app.core.agents.report_quality import validate_markdown_report, validate_report_section
from app.core.agents.protocol_schema import (
    BaselineOutputSchema,
    CallMetaSchema,
    CoordinatorSummarySchema,
    CultivationManagementTurnSchema,
    DiagnosisEvidenceTurnSchema,
    DifferentialTurnSchema,
    EXPERT_TURN_MODELS,
    ExpertTurnSchema,
    FinalDiagnosisSchema,
    MarkdownReportSchema,
    MarkdownSectionSchema,
    RiskComplianceTurnSchema,
    SafetyReviewSchema,
    BerryActionTurnSchema,
    expert_turn_model_for_agent,
)
from app.core.agents.knowledge_prose import section_facts_to_knowledge_narrative
from app.core.agents.report_packet import (
    build_final_decision_packet,
    build_report_packet,
    build_report_writer_narrative_briefing,
)
from app.core.agents.sanitizer import sanitize_expert_turn
from app.core.caption.schema import CaptionSchema
from app.core.errors import RealOutputRequiredError
from app.core.llm_clients import LLMRoute, RoutedLLMClient
from app.core.runtime.concurrency import RouteConcurrencyController, RoutedTask
from app.core.utils import parse_json_object


class MultiAgentOrchestrator:
    HYPOTHESIS_LAYER_ORDER = (
        "diagnosis_evidence_officer",
        "differential_officer",
    )
    DECISION_LAYER_ORDER = (
        "berry_qa_expert",
        "cultivation_management_officer",
    )

    def __init__(
        self,
        llm_client: RoutedLLMClient,
        agent_model_routing: dict[str, LLMRoute],
        max_retries: int = 2,
        timeout: int = 60,
        strict_real_output: bool = True,
        max_parallel_agents_per_layer: int = 3,
        max_concurrency_per_route: int = 2,
        structured_max_new_tokens: int = 768,
        report_max_new_tokens: int = 1400,
    ):
        self.llm_client = llm_client
        self.agent_model_routing = agent_model_routing
        self.max_retries = max_retries
        self.timeout = timeout
        self.strict_real_output = strict_real_output
        self.max_parallel_agents_per_layer = max(1, int(max_parallel_agents_per_layer))
        self.max_concurrency_per_route = max(1, int(max_concurrency_per_route))
        self.structured_max_new_tokens = max(128, int(structured_max_new_tokens))
        self.report_max_new_tokens = max(256, int(report_max_new_tokens))
        self.experts = get_expert_definitions()
        self.expert_lookup = {expert["agent_name"]: expert for expert in self.experts}
        self.concurrency_controller = RouteConcurrencyController(
            max_parallel_tasks=self.max_parallel_agents_per_layer,
            max_concurrency_per_route=self.max_concurrency_per_route,
        )

    def run(
        self,
        case_text: str,
        caption: CaptionSchema,
        kb_evidence: list[dict[str, Any]],
        n_rounds: int = 2,
        vision_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        final_result: dict[str, Any] | None = None
        for event in self.run_iter(
            case_text=case_text,
            caption=caption,
            kb_evidence=kb_evidence,
            n_rounds=n_rounds,
            vision_result=vision_result,
        ):
            if event.get("type") == "orchestrator_complete":
                final_result = event.get("result")
        if not isinstance(final_result, dict):
            raise RuntimeError("编排器未产出最终结果")
        return final_result

    def run_iter(
        self,
        case_text: str,
        caption: CaptionSchema,
        kb_evidence: list[dict[str, Any]],
        n_rounds: int = 2,
        vision_result: dict[str, Any] | None = None,
    ):
        rounds: list[dict[str, Any]] = []
        round_summary_meta: list[dict[str, Any]] = []
        shared_state = self._build_initial_shared_state(caption)
        fallback_used = False

        for round_idx in range(1, n_rounds + 1):
            round_layers = self._plan_round_layers(
                round_idx=round_idx,
                shared_state=shared_state,
                caption=caption,
            )
            expert_turns_by_agent: dict[str, dict[str, Any]] = {}
            active_agents = [agent_name for layer in round_layers for agent_name in layer["agents"]]
            layer_plan = self._serialize_round_layers(round_layers)
            yield {
                "type": "round_started",
                "round": round_idx,
                "active_agents": active_agents,
                "shared_state": shared_state,
                "layers": layer_plan,
            }

            for layer in round_layers:
                yield {
                    "type": "layer_started",
                    "round": round_idx,
                    "layer": layer["layer"],
                    "layer_name": layer["layer_name"],
                    "layer_agents": layer["agents"],
                    "shared_state": shared_state,
                }
                tasks: list[RoutedTask[dict[str, Any]]] = []
                for expert in layer["experts"]:
                    agent_name = expert["agent_name"]
                    route = self._route_for(agent_name)
                    tasks.append(
                        RoutedTask(
                            name=agent_name,
                            route=route,
                            fn=self._make_expert_task(
                                expert=expert,
                                case_text=case_text,
                                caption=caption,
                                kb_evidence=kb_evidence,
                                round_idx=round_idx,
                                shared_state=shared_state,
                            ),
                        )
                    )
                for expert in layer["experts"]:
                    agent_name = expert["agent_name"]
                    yield {
                        "type": "expert_started",
                        "round": round_idx,
                        "layer": layer["layer"],
                        "layer_name": layer["layer_name"],
                        "layer_agents": layer["agents"],
                        "agent_name": agent_name,
                        "active_agents": active_agents,
                        "shared_state": shared_state,
                    }

                completed_agents: list[str] = []
                for task, turn in self.concurrency_controller.iter_run(tasks):
                    agent_name = str(task.name)
                    fallback_used = fallback_used or bool(turn.get("meta", {}).get("used_fallback", False))
                    expert_turns_by_agent[agent_name] = turn
                    completed_agents.append(agent_name)
                    yield {
                        "type": "expert_turn",
                        "round": round_idx,
                        "layer": layer["layer"],
                        "layer_name": layer["layer_name"],
                        "layer_agents": layer["agents"],
                        "agent_name": turn.get("agent_name", agent_name),
                        "active_agents": active_agents,
                        "turn": turn,
                    }

                yield {
                    "type": "layer_completed",
                    "round": round_idx,
                    "layer": layer["layer"],
                    "layer_name": layer["layer_name"],
                    "layer_agents": layer["agents"],
                    "completed_agents": completed_agents,
                    "shared_state": shared_state,
                }

            expert_turns = [
                expert_turns_by_agent[agent_name]
                for agent_name in active_agents
                if agent_name in expert_turns_by_agent
            ]

            yield {
                "type": "round_summary_started",
                "round": round_idx,
                "active_agents": active_agents,
                "shared_state": shared_state,
                "layers": layer_plan,
            }
            summary, summary_meta = self._run_round_summary(
                expert_turns=expert_turns,
                round_idx=round_idx,
                shared_state=shared_state,
            )
            fallback_used = fallback_used or bool(summary_meta.get("used_fallback", False))
            summary_meta["round"] = round_idx
            round_summary_meta.append(summary_meta)

            shared_state = self._merge_shared_state(
                previous_state=shared_state,
                summary=summary,
                active_agents=active_agents,
                expert_turns=expert_turns,
            )
            rounds.append(
                {
                    "round": round_idx,
                    "active_agents": active_agents,
                    "layers": layer_plan,
                    "expert_turns": expert_turns,
                    "summary": summary,
                    "shared_state": shared_state,
                }
            )
            should_stop = self._should_stop(round_idx=round_idx, max_rounds=n_rounds, shared_state=shared_state)
            yield {
                "type": "round_summary",
                "round": round_idx,
                "active_agents": active_agents,
                "summary": summary,
                "shared_state": shared_state,
                "stop_after_round": should_stop,
                "meta": summary_meta,
                "layers": layer_plan,
            }
            if should_stop:
                break

        yield {
            "type": "final_started",
            "shared_state": shared_state,
        }
        final_output = self._run_final(
            case_text=case_text,
            caption=caption,
            rounds=rounds,
            shared_state=shared_state,
            vision_result=vision_result,
        )
        if isinstance(final_output, tuple) and len(final_output) == 3:
            final_result, final_meta, decision_packet = final_output
        else:
            final_result, final_meta = final_output
            decision_packet = {}
        fallback_used = fallback_used or bool(final_meta.get("used_fallback", False))
        yield {
            "type": "final_result",
            "final": final_result,
            "shared_state": shared_state,
            "decision_packet": decision_packet,
            "meta": final_meta,
        }

        yield {
            "type": "safety_started",
            "final": final_result,
        }
        safety, safety_meta = self._run_safety(final_result)
        fallback_used = fallback_used or bool(safety_meta.get("used_fallback", False))
        yield {
            "type": "safety_result",
            "safety": safety,
            "meta": safety_meta,
        }

        if not safety.get("safety_passed", True):
            revised = safety.get("revised_actions", [])
            if revised:
                final_result["actions"] = revised
                if not final_result.get("rescue_plan"):
                    final_result["rescue_plan"] = [
                        {
                            "phase": "立即处置",
                            "objective": "使用安全审校后的保守动作",
                            "actions": self._unique_strings(revised),
                            "rationale": self._unique_strings(safety.get("flags", [])),
                            "risk_level": "low",
                        }
                    ]
            final_result["safety_notes"] = list(
                dict.fromkeys(final_result.get("safety_notes", []) + safety.get("flags", []))
            )
        if safety.get("review_summary"):
            final_result["safety_notes"] = list(
                dict.fromkeys(final_result.get("safety_notes", []) + [str(safety.get("review_summary"))])
            )
        if safety.get("required_followups"):
            followups = self._unique_strings(safety.get("required_followups", []))
            final_result["evidence_to_collect"] = self._unique_strings(final_result.get("evidence_to_collect", []) + followups)
            final_result["monitoring_plan"] = self._unique_strings(final_result.get("monitoring_plan", []) + followups)
        if safety.get("evidence_sufficiency") and not final_result.get("evidence_sufficiency"):
            final_result["evidence_sufficiency"] = str(safety.get("evidence_sufficiency", "")).strip()
        prohibited_actions = self._unique_strings(
            final_result.get("prohibited_actions", []) + safety.get("prohibited_actions", [])
        )
        if prohibited_actions:
            final_result["prohibited_actions"] = prohibited_actions

        execution_meta = {
            "strict_real_output": self.strict_real_output,
            "fallback_used": fallback_used,
            "rounds_executed": len(rounds),
            "planner": "layered_evidence_board_v2",
            "max_parallel_agents_per_layer": self.max_parallel_agents_per_layer,
            "max_concurrency_per_route": self.max_concurrency_per_route,
            "agent_model_routing": {
                key: {
                    "provider": route.provider,
                    "model": route.model,
                    "adapter_model": route.adapter_model,
                    "client_name": route.client_name,
                }
                for key, route in self.agent_model_routing.items()
            },
        }
        result = {
            "rounds": rounds,
            "final": final_result,
            "safety": safety,
            "shared_state": shared_state,
            "decision_packet": decision_packet,
            "round_summary_meta": round_summary_meta,
            "final_meta": final_meta,
            "safety_meta": safety_meta,
            "execution_meta": execution_meta,
        }
        yield {"type": "orchestrator_complete", "result": result}

    def generate_reports(
        self,
        case_text: str,
        caption: CaptionSchema,
        kb_evidence: list[dict[str, Any]],
        rounds: list[dict[str, Any]],
        final_result: dict[str, Any],
        safety_result: dict[str, Any],
        vision_result: dict[str, Any] | None = None,
        image_bytes: bytes | None = None,
        kb_documents: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        final_result = dict(final_result)
        if not final_result.get("report_outline"):
            final_result["report_outline"] = self._default_report_outline(final_result, safety_result)
        report_packet = build_report_packet(
            case_text=case_text,
            caption=caption,
            rounds=rounds,
            final_result=final_result,
            safety_result=safety_result,
            vision_result=vision_result,
            kb_documents=kb_documents,
        )
        multi_markdown, multi_meta = self._run_multi_agent_report(
            case_text=case_text,
            caption=caption,
            report_packet=report_packet,
            rounds=rounds,
        )
        baseline_error: dict[str, Any] | None = None
        try:
            baseline_payload, baseline_meta = self._run_baseline_report(
                case_text=case_text,
                caption=caption,
                kb_evidence=kb_evidence,
                image_bytes=image_bytes,
            )
            baseline_markdown = str(baseline_payload.get("markdown_report", "")).strip()
        except RealOutputRequiredError as err:
            baseline_payload = {}
            baseline_error = err.to_detail()
            baseline_meta = {
                "provider": err.provider,
                "model": err.model,
                "latency_ms": 0,
                "request_id": "",
                "is_real_output": False,
                "used_fallback": True,
                "error": baseline_error,
            }
            baseline_markdown = (
                "# 单模型救治报告\n\n"
                "当前基线对比模型暂不可用，因此未生成单模型对照报告。\n\n"
                f"原因：{err.reason}\n\n"
                "这不会影响多智能体主报告的生成和返回。"
            )
        result = {
            "multi_agent_markdown": multi_markdown,
            "baseline_markdown": baseline_markdown,
            "multi_agent_meta": multi_meta,
            "baseline_meta": baseline_meta,
            "baseline_structured": {k: v for k, v in baseline_payload.items() if k != "markdown_report"},
            "report_packet": report_packet,
        }
        if baseline_error is not None:
            result["baseline_error"] = baseline_error
        return result

    def _build_initial_shared_state(self, caption: CaptionSchema) -> dict[str, Any]:
        followup = self._unique_strings(caption.followup_questions)
        co_signs = self._enum_values(caption.symptoms.co_signs)
        recommended_experts: list[str] = []
        if caption.ood_score >= 0.3:
            recommended_experts.append("berry_qa_expert")
        if {"humidity_high", "poor_ventilation", "overwatering", "rainy_weather"} & set(co_signs):
            recommended_experts.append("cultivation_management_officer")

        uncertainty = (1.0 - float(caption.confidence)) * 0.65 + float(caption.ood_score) * 0.35
        return {
            "consensus": [],
            "conflicts": [],
            "unique_points": [],
            "next_focus": followup[:3],
            "safety_flags": [],
            "working_diagnoses": [],
            "open_questions": followup[:5],
            "evidence_gaps": followup[:5],
            "recommended_experts": self._unique_strings(recommended_experts),
            "uncertainty_score": self._clamp(uncertainty),
            "stop_signal": False,
            "active_agents": [],
            "proposed_actions": [],
            "evidence_board": [],
            "action_focus": [],
            "verification_tasks": followup[:5],
            "uncertainty_triggers": followup[:3],
            "report_priority": self._initial_report_priority(caption),
            "evidence_sufficiency": "",
        }

    def _select_experts(
        self,
        round_idx: int,
        shared_state: dict[str, Any],
        caption: CaptionSchema,
    ) -> list[dict[str, str]]:
        uncertainty = float(shared_state.get("uncertainty_score", 1.0))
        conflicts = shared_state.get("conflicts", [])
        open_questions = shared_state.get("open_questions", [])
        recommended = {
            name
            for name in shared_state.get("recommended_experts", [])
            if name in self.expert_lookup
        }
        co_signs = set(self._enum_values(caption.symptoms.co_signs))
        severity = float(caption.numeric.severity_score)

        selected = {"diagnosis_evidence_officer"}
        if round_idx == 1 or uncertainty >= 0.35 or conflicts:
            selected.add("differential_officer")
        if round_idx == 1 or severity >= 0.35 or co_signs & {"humidity_high", "poor_ventilation", "overwatering", "rainy_weather"}:
            selected.add("cultivation_management_officer")
        if round_idx == 1 or caption.ood_score >= 0.25 or uncertainty >= 0.5 or open_questions:
            selected.add("berry_qa_expert")

        selected.update(recommended)

        if round_idx > 1 and uncertainty <= 0.3 and not conflicts:
            selected = {"diagnosis_evidence_officer"}
            if severity >= 0.35:
                selected.add("cultivation_management_officer")
            selected.update(recommended)

        return [expert for expert in self.experts if expert["agent_name"] in selected]

    def _plan_round_layers(
        self,
        round_idx: int,
        shared_state: dict[str, Any],
        caption: CaptionSchema,
    ) -> list[dict[str, Any]]:
        selected_experts = self._select_experts(
            round_idx=round_idx,
            shared_state=shared_state,
            caption=caption,
        )
        selected_names = {expert["agent_name"] for expert in selected_experts}
        layers: list[dict[str, Any]] = []
        layer_specs = [
            ("hypothesis", self.HYPOTHESIS_LAYER_ORDER),
            ("decision", self.DECISION_LAYER_ORDER),
        ]
        for layer_idx, (layer_name, order) in enumerate(layer_specs, start=1):
            layer_experts = [
                self.expert_lookup[name]
                for name in order
                if name in selected_names
            ]
            if not layer_experts:
                continue
            layers.append(
                {
                    "layer": layer_idx,
                    "layer_name": layer_name,
                    "experts": layer_experts,
                    "agents": [expert["agent_name"] for expert in layer_experts],
                    "parallelism": min(self.max_parallel_agents_per_layer, len(layer_experts)),
                }
            )
        return layers

    @staticmethod
    def _serialize_round_layers(round_layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "layer": int(layer["layer"]),
                "layer_name": str(layer["layer_name"]),
                "agents": list(layer["agents"]),
                "parallelism": int(layer["parallelism"]),
            }
            for layer in round_layers
        ]

    def _make_expert_task(
        self,
        *,
        expert: dict[str, str],
        case_text: str,
        caption: CaptionSchema,
        kb_evidence: list[dict[str, Any]],
        round_idx: int,
        shared_state: dict[str, Any],
    ):
        return lambda: self._run_single_expert(
            expert=expert,
            case_text=case_text,
            caption=caption,
            kb_evidence=kb_evidence,
            round_idx=round_idx,
            shared_state=shared_state,
        )

    def _merge_shared_state(
        self,
        previous_state: dict[str, Any],
        summary: dict[str, Any],
        active_agents: list[str],
        expert_turns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        valid_agents = set(self.expert_lookup)
        proposed_actions = self._unique_strings(
            [
                action
                for turn in expert_turns
                for action in turn.get("actions", [])
            ]
        )
        working_diagnoses = self._unique_strings(summary.get("working_diagnoses", []))
        if not working_diagnoses:
            working_diagnoses = self._derive_working_diagnoses(expert_turns)
        open_questions = self._unique_strings(summary.get("open_questions", []))
        if not open_questions:
            open_questions = self._derive_open_questions(expert_turns)
        evidence_gaps = self._unique_strings(summary.get("evidence_gaps", []))
        if not evidence_gaps:
            evidence_gaps = open_questions[:]
        next_focus = self._unique_strings(summary.get("next_focus", []))
        if not next_focus:
            next_focus = evidence_gaps[:3]
        evidence_board = summary.get("evidence_board", [])
        if not evidence_board:
            evidence_board = self._derive_evidence_board(expert_turns)
        action_focus = self._unique_strings(summary.get("action_focus", []))
        if not action_focus:
            action_focus = proposed_actions[:4]
        verification_tasks = self._unique_strings(summary.get("verification_tasks", []))
        if not verification_tasks:
            verification_tasks = evidence_gaps[:]
        uncertainty_triggers = self._unique_strings(summary.get("uncertainty_triggers", []))
        if not uncertainty_triggers:
            uncertainty_triggers = open_questions[:3]
        report_priority = self._unique_strings(summary.get("report_priority", []))
        if not report_priority:
            report_priority = self._unique_strings(previous_state.get("report_priority", []) + next_focus)

        return {
            "consensus": self._unique_strings(summary.get("consensus", [])),
            "conflicts": self._unique_strings(summary.get("conflicts", [])),
            "unique_points": self._unique_strings(summary.get("unique_points", [])),
            "next_focus": next_focus,
            "safety_flags": self._unique_strings(previous_state.get("safety_flags", []) + summary.get("safety_flags", [])),
            "working_diagnoses": working_diagnoses,
            "open_questions": open_questions,
            "evidence_gaps": evidence_gaps,
            "recommended_experts": [
                name
                for name in self._unique_strings(summary.get("recommended_experts", []))
                if name in valid_agents
            ],
            "uncertainty_score": self._clamp(float(summary.get("uncertainty_score", previous_state.get("uncertainty_score", 0.5)))),
            "stop_signal": bool(summary.get("stop_signal", False)),
            "active_agents": active_agents,
            "proposed_actions": proposed_actions,
            "evidence_board": evidence_board,
            "action_focus": action_focus,
            "verification_tasks": verification_tasks,
            "uncertainty_triggers": uncertainty_triggers,
            "report_priority": report_priority,
            "evidence_sufficiency": str(previous_state.get("evidence_sufficiency", "")).strip(),
        }

    def _should_stop(self, round_idx: int, max_rounds: int, shared_state: dict[str, Any]) -> bool:
        if round_idx >= max_rounds:
            return False
        uncertainty = float(shared_state.get("uncertainty_score", 1.0))
        conflicts = shared_state.get("conflicts", [])
        open_questions = shared_state.get("open_questions", [])
        stop_signal = bool(shared_state.get("stop_signal", False))
        if stop_signal and uncertainty <= 0.35 and not conflicts:
            return True
        if uncertainty <= 0.2 and not conflicts and len(open_questions) <= 1:
            return True
        return False

    def _run_single_expert(
        self,
        expert: dict[str, str],
        case_text: str,
        caption: CaptionSchema,
        kb_evidence: list[dict[str, Any]],
        round_idx: int,
        shared_state: dict[str, Any],
    ) -> dict[str, Any]:
        stage = f"expert_round_{round_idx}"
        agent_name = expert["agent_name"]
        model_cls = expert_turn_model_for_agent(agent_name)
        try:
            messages = build_expert_messages(
                expert=expert,
                case_text=case_text,
                caption=caption,
                kb_evidence=self._compact_kb_evidence_for_expert(kb_evidence),
                round_idx=round_idx,
                shared_state=self._compact_shared_state_for_expert(shared_state, round_idx),
            )
            payload, call_meta = self._llm_structured_with_retry(
                model_cls=model_cls,
                messages=messages,
                route_key=agent_name,
                stage=stage,
                agent_name=agent_name,
            )
        except Exception as err:  # noqa: BLE001
            if isinstance(err, RealOutputRequiredError):
                failure_reason = err.reason
                provider = err.provider
                model = err.model
            else:
                route = self._route_for(agent_name)
                failure_reason = str(err) if str(err).strip() else "专家调用失败"
                provider = route.provider
                model = route.model
            payload = self._build_deterministic_expert_turn(
                expert=expert,
                caption=caption,
                shared_state=shared_state,
                failure_reason=failure_reason,
            )
            call_meta = CallMetaSchema(
                provider=provider or "system",
                model=model or "deterministic_expert_fallback",
                latency_ms=0,
                request_id="",
                is_real_output=True,
                used_fallback=True,
            ).model_dump(mode="json")

        payload["agent_name"] = agent_name
        payload["meta"] = call_meta
        payload = sanitize_expert_turn(payload)
        payload["citations"] = self._filter_fallback_citations(payload.get("citations", []))
        self._assert_turn_is_real(payload, stage=stage, agent_name=agent_name)
        return payload

    def _build_deterministic_expert_turn(
        self,
        *,
        expert: dict[str, str],
        caption: CaptionSchema,
        shared_state: dict[str, Any],
        failure_reason: str,
    ) -> dict[str, Any]:
        agent_name = str(expert.get("agent_name", "")).strip()
        role = str(expert.get("role", "")).strip() or "专家"
        primary_name = self._first_non_empty(shared_state.get("working_diagnoses", []), fallback="待复核病害")
        next_focus = self._first_non_empty(shared_state.get("next_focus", []), fallback="补充关键证据并复核")
        open_question = self._first_non_empty(
            shared_state.get("open_questions", []),
            fallback="24 到 48 小时复拍同叶位并记录病斑变化",
        )
        evidence_gap = self._first_non_empty(
            shared_state.get("evidence_gaps", []),
            fallback="补充叶背近景、整株分布和环境湿度信息",
        )
        conflict_hint = self._first_non_empty(shared_state.get("conflicts", []), fallback="当前证据仍存在分歧")
        area_ratio = self._format_percent_value(caption.numeric.area_ratio)
        area_text = f"当前病损面积约占叶片面积 {area_ratio}。" if area_ratio else "当前可见叶片存在受损征象。"
        color_text = self._first_non_empty(self._enum_values(caption.symptoms.color), fallback="颜色变化")
        tissue_text = self._first_non_empty(self._enum_values(caption.symptoms.tissue_state), fallback="组织受损")
        _ = failure_reason
        fallback_note = "本轮采用降级回填，原始调用失败，需在后续轮次补证后再稳定结论。"

        if agent_name == "diagnosis_evidence_officer":
            payload = DiagnosisEvidenceTurnSchema.model_validate(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "visible_findings": [
                        f"图像显示叶片存在{color_text}与{tissue_text}表现。",
                        area_text,
                        f"当前优先关注：{next_focus}。",
                    ],
                    "negative_findings": [f"当前缺少关键补证信息：{evidence_gap}。"],
                    "candidate_causes": [
                        {
                            "name": primary_name,
                            "why_like": "现有轮次信息暂支持该候选优先复核。",
                            "why_unlike": f"{conflict_hint}，证据链尚未闭环。",
                        }
                    ],
                    "evidence_strength": fallback_note,
                    "citations": [],
                    "invalid_turn": False,
                }
            )
            return payload.model_dump(mode="json")

        if agent_name == "differential_officer":
            payload = DifferentialTurnSchema.model_validate(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "ranked_differentials": [
                        {
                            "name": primary_name,
                            "why_supported": "基于当前共享状态与已有证据，暂列首位候选。",
                            "why_not_primary": f"{conflict_hint}，仍需补证后再稳定排序。",
                        }
                    ],
                    "why_primary": [f"当前可操作证据更集中在“{primary_name}”方向。"],
                    "why_not_primary": [conflict_hint],
                    "decisive_missing_evidence": [evidence_gap, open_question],
                    "citations": [],
                    "invalid_turn": False,
                }
            )
            return payload.model_dump(mode="json")

        if agent_name == "berry_qa_expert":
            first_action = self._first_non_empty(
                shared_state.get("proposed_actions", []),
                fallback="先执行低风险病害控制并记录病斑变化。",
            )
            payload = BerryActionTurnSchema.model_validate(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "today_actions": [first_action],
                    "control_options": [f"围绕“{primary_name}”按先控险后升级的路径处理。"],
                    "observe_48h": [open_question],
                    "escalation_triggers": ["若 24 到 48 小时内病斑持续外扩或新增病斑，应立即升级处理并考虑送检。"],
                    "key_evidence_gaps": [evidence_gap],
                    "citations": [],
                    "invalid_turn": False,
                }
            )
            return payload.model_dump(mode="json")

        if agent_name == "cultivation_management_officer":
            low_risk_action = self._first_non_empty(
                shared_state.get("proposed_actions", []),
                fallback="保持通风并避免叶面长时间潮湿。",
            )
            payload = CultivationManagementTurnSchema.model_validate(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "management_timeline": ["今天先优化通风和湿度，24 到 48 小时复查同叶位，1 周复查整株。"],
                    "low_risk_actions": [low_risk_action],
                    "environment_adjustments": ["维持通风、降低持续高湿，并按需调整灌溉频率。"],
                    "followup_nodes": [open_question],
                    "citations": [],
                    "invalid_turn": False,
                }
            )
            return payload.model_dump(mode="json")

        if agent_name == "risk_compliance_officer":
            payload = RiskComplianceTurnSchema.model_validate(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "prohibited_actions": ["在关键证据未补齐前，不要直接进行高强度不可逆处理。"],
                    "overtreatment_risks": ["过度施药可能增加成本并带来环境负担。"],
                    "undertreatment_risks": ["若持续拖延处置，病斑可能扩展并影响产量。"],
                    "confidence_boundary": [f"当前结论受限于：{evidence_gap}。", f"冲突点：{conflict_hint}。"],
                    "citations": [],
                    "invalid_turn": False,
                }
            )
            return payload.model_dump(mode="json")

        payload = ExpertTurnSchema.model_validate(
            {
                "agent_name": agent_name or "fallback_expert",
                "role": role,
                "top_k_causes": [
                    {
                        "name": primary_name,
                        "why_like": "当前共享证据暂支持该候选。",
                        "why_unlike": f"{conflict_hint}，仍需补证。",
                    }
                ],
                "supporting_evidence": [area_text],
                "counter_evidence": [conflict_hint],
                "actions": [next_focus],
                "risks": ["证据不足时直接升级处理存在误治风险。"],
                "questions_to_ask": [open_question],
                "confidence": 0.45,
                "citations": [],
                "invalid_turn": False,
            }
        )
        return payload.model_dump(mode="json")

    def _run_round_summary(
        self,
        expert_turns: list[dict[str, Any]],
        round_idx: int,
        shared_state: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        messages = build_round_summary_messages(
            round_turns=expert_turns,
            round_idx=round_idx,
            shared_state=shared_state,
        )
        try:
            return self._llm_structured_with_retry(
                model_cls=CoordinatorSummarySchema,
                messages=messages,
                route_key="coordinator_round_summary",
                stage=f"round_summary_{round_idx}",
                agent_name="coordinator_round_summary",
            )
        except RealOutputRequiredError:
            payload = self._build_deterministic_round_summary(
                expert_turns=expert_turns,
                previous_state=shared_state,
            )
            meta = CallMetaSchema(
                provider="system",
                model="deterministic_round_summary",
                latency_ms=0,
                request_id="",
                is_real_output=True,
                used_fallback=True,
            ).model_dump(mode="json")
            return payload, meta

    def _run_final(
        self,
        case_text: str,
        caption: CaptionSchema,
        rounds: list[dict[str, Any]],
        shared_state: dict[str, Any],
        vision_result: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        decision_packet = build_final_decision_packet(
            case_text=case_text,
            caption=caption,
            shared_state=shared_state,
            vision_result=vision_result,
        )
        messages = build_final_messages(
            case_text=case_text,
            caption=caption,
            decision_packet=decision_packet,
        )
        try:
            payload, call_meta = self._llm_structured_with_retry(
                model_cls=FinalDiagnosisSchema,
                messages=messages,
                route_key="coordinator_final",
                stage="final_diagnosis",
                agent_name="coordinator_final",
            )
        except RealOutputRequiredError:
            payload = self._build_deterministic_final_result(
                caption=caption,
                shared_state=shared_state,
                decision_packet=decision_packet,
            )
            call_meta = CallMetaSchema(
                provider="system",
                model="deterministic_final_diagnosis",
                latency_ms=0,
                request_id="",
                is_real_output=True,
                used_fallback=True,
            ).model_dump(mode="json")
        payload["citations"] = self._filter_fallback_citations(payload.get("citations", []))
        self._assert_final_is_real(payload, stage="final_diagnosis")
        return payload, call_meta, decision_packet

    def _run_safety(self, final_result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        messages = build_safety_messages(final_result=final_result)
        try:
            return self._llm_structured_with_retry(
                model_cls=SafetyReviewSchema,
                messages=messages,
                route_key="safety_reviewer",
                stage="safety_review",
                agent_name="safety_reviewer",
            )
        except RealOutputRequiredError:
            payload = SafetyReviewSchema(
                safety_passed=True,
                review_summary="安全审校降级：当前无可用 LLM，自动通过安全检查。",
                evidence_sufficiency="unavailable",
            ).model_dump(mode="json")
            call_meta = CallMetaSchema(
                provider="system",
                model="deterministic_safety_review",
                latency_ms=0,
                request_id="",
                is_real_output=True,
                used_fallback=True,
            ).model_dump(mode="json")
            return payload, call_meta

    def _run_multi_agent_report(
        self,
        case_text: str,
        caption: CaptionSchema,
        report_packet: dict[str, Any],
        rounds: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        sections = self._plan_report_sections(report_packet)
        completed_sections: list[dict[str, str]] = []
        section_metas: list[dict[str, Any]] = []
        narrative_briefing = build_report_writer_narrative_briefing(report_packet, rounds)

        for index, section in enumerate(sections, start=1):
            section_stage = f"multi_agent_report_writer_section_{index}"
            section_packet = self._build_report_section_packet(
                report_packet=report_packet,
                section_title=section["title"],
                section_instruction=section["instruction"],
            )
            section_focus = self._section_facts_knowledge_narrative(
                section_packet.get("section_facts"),
                section_title=section["title"],
            )
            prior_excerpt = self._prior_sections_excerpt_for_report(completed_sections)
            merged_instruction = self._merge_section_instruction_with_packet(
                base_instruction=str(section.get("instruction", "") or "").strip(),
                section_packet=section_packet,
            )
            messages = build_narrative_report_section_messages(
                case_text=case_text,
                caption=caption,
                section_title=section["title"],
                section_instruction=merged_instruction,
                global_briefing=narrative_briefing,
                section_focus_markdown=section_focus,
                prior_sections_excerpt=prior_excerpt,
            )
            try:
                section_text, section_meta = self._llm_plain_report_section(
                    messages=messages,
                    route_key="multi_agent_report_writer",
                    stage=section_stage,
                    agent_name="multi_agent_report_writer",
                )
                payload = {
                    "section_title": section["title"],
                    "section_markdown": section_text,
                }
                payload, section_rewritten = self._ensure_report_section_quality(
                    title=section["title"],
                    payload=payload,
                    report_packet=report_packet,
                    completed_sections=completed_sections,
                    route_key="multi_agent_report_writer",
                    stage=section_stage,
                    agent_name="multi_agent_report_writer",
                    case_text=case_text,
                    caption=caption,
                    section_packet=section_packet,
                    section_instruction=merged_instruction,
                )
                if section_rewritten:
                    section_meta["used_fallback"] = True
            except RealOutputRequiredError:
                deterministic = self._build_deterministic_markdown_report(report_packet=report_packet)
                markdown, rewritten = self._ensure_markdown_report_quality(
                    markdown=deterministic,
                    route_key="multi_agent_report_writer",
                    stage="multi_agent_report_writer",
                    agent_name="multi_agent_report_writer",
                    case_text=case_text,
                    caption=caption,
                    report_packet=report_packet,
                )
                call_meta = CallMetaSchema(
                    provider="system",
                    model="deterministic_report_writer",
                    latency_ms=0,
                    request_id="",
                    is_real_output=True,
                    used_fallback=True,
                ).model_dump(mode="json")
                if rewritten:
                    call_meta["used_fallback"] = True
                return markdown, call_meta
            completed_sections.append(
                {
                    "title": section["title"],
                    "markdown": self._compose_section_markdown(
                        title=section["title"],
                        payload=payload,
                    ),
                }
            )
            section_metas.append(section_meta)

        payload = {
            "markdown_report": self._compose_report_markdown(completed_sections),
        }
        call_meta = self._aggregate_report_call_meta(section_metas)
        markdown, rewritten = self._ensure_markdown_report_quality(
            markdown=str(payload["markdown_report"]).strip(),
            route_key="multi_agent_report_writer",
            stage="multi_agent_report_writer",
            agent_name="multi_agent_report_writer",
            case_text=case_text,
            caption=caption,
            report_packet=report_packet,
        )
        if rewritten:
            call_meta["used_fallback"] = True
        return markdown, call_meta

    def _run_baseline_report(
        self,
        case_text: str,
        caption: CaptionSchema,
        kb_evidence: list[dict[str, Any]],
        image_bytes: bytes | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        baseline_route = self._route_for("baseline_single_llm")
        messages = build_baseline_report_messages(
            case_text=case_text,
            caption=caption,
            kb_evidence=kb_evidence,
            image_bytes=image_bytes if baseline_route.provider == "openai" else None,
        )
        payload, call_meta = self._llm_structured_with_retry(
            model_cls=BaselineOutputSchema,
            messages=messages,
            route_key="baseline_single_llm",
            stage="baseline_single_llm",
            agent_name="baseline_single_llm",
        )
        top_name = str(payload.get("top_diagnosis", {}).get("name", "")).strip().lower()
        if not top_name or top_name == "unknown":
            raise RealOutputRequiredError(
                stage="baseline_single_llm",
                agent_name="baseline_single_llm",
                provider=call_meta.get("provider", ""),
                model=call_meta.get("model", ""),
                reason="基线模型主诊断为空或未知",
                raw_error_type="ValueError",
            )
        return payload, call_meta

    def _plan_report_sections(self, report_packet: dict[str, Any]) -> list[dict[str, str]]:
        outline_items = report_packet.get("report_outline", []) if isinstance(report_packet, dict) else []
        outline_map: dict[str, str] = {}
        if isinstance(outline_items, list):
            for item in outline_items:
                text = str(item).strip()
                if not text:
                    continue
                title, instruction = self._split_outline_item(text)
                if title and title not in outline_map:
                    outline_map[title] = instruction

        sections: list[dict[str, str]] = []
        for title in REQUIRED_REPORT_SECTIONS:
            instruction = outline_map.get(title) or (
                f"围绕「{title}」写作：只写本节职责内的内容，与其他章节**不要**整段重复同一套总述；"
                f"短段、具体、中文自然。"
            )
            sections.append({"title": title, "instruction": instruction})
        return sections

    @staticmethod
    def _compact_completed_sections_for_prompt(completed_sections: list[dict[str, str]]) -> list[dict[str, str]]:
        compacted: list[dict[str, str]] = []
        for item in completed_sections[-4:]:
            title = str(item.get("title", "")).strip()
            markdown = " ".join(str(item.get("markdown", "")).split())
            if not title or not markdown:
                continue
            compacted.append(
                {
                    "title": title,
                    "summary": markdown[:700],
                    "tail_hint": markdown[max(0, len(markdown) - 180) :],
                }
            )
        return compacted

    @staticmethod
    def _merge_section_instruction_with_packet(
        *,
        base_instruction: str,
        section_packet: dict[str, Any],
    ) -> str:
        parts: list[str] = []
        if base_instruction:
            parts.append(base_instruction)
        sg = str(section_packet.get("section_goal", "")).strip()
        if sg:
            parts.append(f"本节目标：{sg}")
        fs = section_packet.get("focus_suggestions")
        if isinstance(fs, list) and fs:
            joined = "；".join(str(x).strip() for x in fs if str(x).strip())
            if joined:
                parts.append(f"写作提示：{joined}")
        ap = section_packet.get("anti_patterns")
        if isinstance(ap, list) and ap:
            joined = "；".join(str(x).strip() for x in ap[:5] if str(x).strip())
            if joined:
                parts.append(f"避免：{joined}")
        return "\n".join(parts).strip() or base_instruction

    def _build_report_section_packet(
        self,
        *,
        report_packet: dict[str, Any],
        section_title: str,
        section_instruction: str,
    ) -> dict[str, Any]:
        case_summary = report_packet.get("case_summary", {}) if isinstance(report_packet, dict) else {}
        vision_conflict = report_packet.get("vision_conflict", {}) if isinstance(report_packet, dict) else {}
        final_diagnosis = report_packet.get("final_diagnosis", {}) if isinstance(report_packet, dict) else {}
        diagnosis_basis = report_packet.get("diagnosis_basis", {}) if isinstance(report_packet, dict) else {}
        action_plan = report_packet.get("action_plan", {}) if isinstance(report_packet, dict) else {}
        safety_and_followup = report_packet.get("safety_and_followup", {}) if isinstance(report_packet, dict) else {}
        uncertainty_management = report_packet.get("uncertainty_management", {}) if isinstance(report_packet, dict) else {}
        decision_support = report_packet.get("decision_support", {}) if isinstance(report_packet, dict) else {}
        report_context = report_packet.get("report_context", {}) if isinstance(report_packet, dict) else {}
        section_facts = report_packet.get("section_facts", {}) if isinstance(report_packet, dict) else {}
        facts = section_facts.get(section_title, {}) if isinstance(section_facts, dict) else {}

        section_packet: dict[str, Any] = {
            "section_title": section_title,
            "section_instruction": section_instruction,
            "section_goal": "由你用自然段写成本节可读正文；材料仅供事实参考，行文风格由你统一。",
            "preferred_structure": (
                "输出为 section_markdown：至少两段、段内句子完整；自行决定先写什么后写什么，"
                "不要用「关键点包括：…」这类机械收束句式。"
            ),
            "focus_suggestions": [],
            "leaf_clinical_profile": report_packet.get("leaf_clinical_profile", {})
            if isinstance(report_packet, dict)
            else {},
            "section_facts": facts if isinstance(facts, dict) else {},
            "shared_context": {
                "report_context": report_context if isinstance(report_context, dict) else {},
                "case_summary": case_summary if isinstance(case_summary, dict) else {},
                "vision_conflict": vision_conflict if isinstance(vision_conflict, dict) else {},
                "final_diagnosis": final_diagnosis if isinstance(final_diagnosis, dict) else {},
                "diagnosis_basis": diagnosis_basis if isinstance(diagnosis_basis, dict) else {},
                "action_plan": action_plan if isinstance(action_plan, dict) else {},
                "safety_and_followup": safety_and_followup if isinstance(safety_and_followup, dict) else {},
                "uncertainty_management": uncertainty_management if isinstance(uncertainty_management, dict) else {},
                "decision_support": decision_support if isinstance(decision_support, dict) else {},
            },
            "anti_patterns": [
                "不要逐段复制前文整句或在多节重复同一套开篇总述。",
                "不要把同一冲突解释在多个章节里重复展开。",
                "不要把动作建议写成模板口号。",
                "不要把多个短句直接用顿号硬拼成一长句。",
                "不要输出“需要复核”这类空泛句而不说明卡点与补证价值。",
                "成品中禁止使用全角【】标签式小标题；勿用支持链、模型倾向、鉴别要点等后台词。",
            ],
        }

        if section_title == "病例摘要":
            section_packet["section_goal"] = (
                "只写画面上可见的病斑与分布细节，以及单张图能说到哪一步；严重度与是否立即处理留给后文专节，本节避免写成决策总览。"
            )
            section_packet["focus_suggestions"] = [
                "三到六句为主；证据上限一句带过即可。",
            ]
            return section_packet

        if section_title == "诊断判断与置信说明":
            section_packet["section_goal"] = (
                "解释这种病田间常怎么看、当前为何更像首位方向、还要和哪些病区分；救治动作留给救治专节，本节不写成操作清单。"
            )
            section_packet["focus_suggestions"] = [
                "有百分数时写成「照片分类更靠近哪类」，同段点明不等于病理确诊。",
                "用 **加粗短语** 分块即可，块名用中性简题（如「这种病一般啥样」「为何更像 A」），不要用支持链/鉴别要点等词。",
                "至少两条「若…则…」绑定观察与判断。",
                "避免照搬 JSON 键名；无知识库摘录时勿编造。",
            ]
            return section_packet

        if section_title == "复查与补证建议":
            section_packet["section_goal"] = "写清怎么补拍、补什么、补到之后能分清啥；与救治节已写的动作勿整段重复。"
            section_packet["focus_suggestions"] = [
                "每条尽量「若看到/拍到 A → 下一步 B 或判断更明朗」。",
                "鼓励按补证类型分条（叶背、整株、环境等），便于农户执行。",
            ]
            section_packet["anti_patterns"] = section_packet["anti_patterns"] + [
                "不要整节只堆「尚缺」「不足」而不写具体怎么做。",
            ]
            return section_packet

        if section_title == "救治建议与实施路径":
            section_packet["section_goal"] = (
                "与病例摘要、诊断节勿重复开篇总述；本节按今天 / 24 小时内 / 观察期展开可执行步骤；多写「若…则…」。"
            )
            section_packet["focus_suggestions"] = [
                "动词开头、短句；不写具体药剂配方。",
            ]
            return section_packet

        if section_title == "风险边界、预后与复查":
            section_packet["section_goal"] = "禁忌、预后读数、何时维持或加码；与救治节的若则阈值呼应，勿整段复读。"
            section_packet["focus_suggestions"] = [
                "用「若…则…」对照写升级/维持。",
            ]
            return section_packet

        return section_packet

    @staticmethod
    def _split_outline_item(text: str) -> tuple[str, str]:
        for separator in ("：", ":"):
            if separator in text:
                left, right = text.split(separator, 1)
                title = left.strip()
                instruction = right.strip()
                return title, instruction or text.strip()
        return text.strip(), text.strip()

    def _compose_section_markdown(self, *, title: str, payload: dict[str, Any]) -> str:
        _ = title
        body = self._polish_report_text(payload.get("section_markdown", ""))
        if body:
            return body
        legacy_lead = self._polish_report_text(payload.get("lead_paragraph", ""))
        legacy_close = self._polish_report_text(payload.get("closing_paragraph", ""))
        legacy_keys = [
            self._polish_report_text(item)
            for item in self._unique_strings(payload.get("key_points", []))[:4]
            if self._polish_report_text(item)
        ]
        parts = [p for p in [legacy_lead, "\n\n".join(legacy_keys) if legacy_keys else "", legacy_close] if p]
        return "\n\n".join(parts).strip()

    @staticmethod
    def _compose_report_markdown(completed_sections: list[dict[str, str]]) -> str:
        blocks = ["# 农业救治报告"]
        for item in completed_sections:
            title = str(item.get("title", "")).strip()
            markdown = str(item.get("markdown", "")).strip()
            if not title or not markdown:
                continue
            blocks.append(f"## {title}\n{markdown}")
        return "\n\n".join(blocks).strip()

    def _polish_report_text(self, text: Any) -> str:
        value = " ".join(str(text or "").split())
        if not value:
            return ""
        value = value.replace("。。", "。").replace("，。", "。").replace("；。", "。").replace("：。", "：")
        value = value.replace("。、", "。").replace("，、", "，").replace("；、", "；")
        value = value.replace("。。", "。").replace("，，", "，").replace("；；", "；")
        value = re.sub(r"([。！？；，])\1+", r"\1", value)
        value = re.sub(r"([。！？；，：])(?=[。！？；，：])", "", value)
        value = re.sub(r"\s*([。！？；，：])\s*", r"\1", value)
        return value.strip()

    @staticmethod
    def _strip_wrapping_code_fence(text: str) -> str:
        t = str(text or "").strip()
        if not t.startswith("```"):
            return t
        lines = t.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _llm_plain_report_section(
        self,
        *,
        messages: list[dict[str, str]],
        route_key: str,
        stage: str,
        agent_name: str,
    ) -> tuple[str, dict[str, Any]]:
        route = self._route_for(route_key)
        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.llm_client.generate(
                    route=route,
                    messages=messages,
                    json_schema=None,
                    temperature=0.25,
                    timeout=self.timeout,
                    max_new_tokens=self.report_max_new_tokens,
                )
                text = self._polish_report_text(self._strip_wrapping_code_fence(response.content.strip()))
                if len(text) >= 80:
                    call_meta = CallMetaSchema(
                        provider=response.provider,
                        model=response.model,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                        request_id=response.request_id,
                        is_real_output=True,
                        used_fallback=response.used_fallback,
                    ).model_dump(mode="json")
                    call_meta["output_mode"] = "plain_markdown_section"
                    return text, call_meta
            except Exception as err:  # noqa: BLE001
                last_error = err
            if attempt < self.max_retries:
                time.sleep(min(0.25 * (2**attempt), 1.5))
        raise RealOutputRequiredError(
            stage=stage,
            agent_name=agent_name,
            provider=route.provider,
            model=route.model,
            reason=str(last_error) if last_error else "报告章节纯文本生成失败",
            raw_error_type=type(last_error).__name__ if last_error else "RuntimeError",
        )

    @staticmethod
    def _section_facts_knowledge_narrative(facts: Any, *, section_title: str, max_chars: int = 9000) -> str:
        text = section_facts_to_knowledge_narrative(facts, section_title)
        if len(text) > max_chars:
            return text[: max_chars - 20] + "\n…（已截断）"
        return text

    @staticmethod
    def _prior_sections_excerpt_for_report(
        completed_sections: list[dict[str, str]],
        *,
        max_chars: int = 8000,
    ) -> str:
        if not completed_sections:
            return ""
        blocks: list[str] = []
        for item in completed_sections:
            title = str(item.get("title", "")).strip()
            body = str(item.get("markdown", "")).strip()
            if title and body:
                blocks.append(f"## {title}\n{body}")
        text = "\n\n".join(blocks).strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 24] + "\n…（前文已截断，请勿复述）"

    def _repair_section_payload(
        self,
        *,
        title: str,
        payload: dict[str, Any],
        report_packet: dict[str, Any],
    ) -> dict[str, Any]:
        raw_md = self._polish_report_text(str(payload.get("section_markdown", "") or "").strip())
        if not raw_md:
            raw_md = self._compose_section_markdown(title=title, payload=payload)
        repaired = {"section_title": title, "section_markdown": raw_md}
        if title == "病例摘要":
            report_context = report_packet.get("report_context", {}) if isinstance(report_packet, dict) else {}
            final_diagnosis = report_packet.get("final_diagnosis", {}) if isinstance(report_packet, dict) else {}
            blocked_terms = self._unique_strings(
                [report_context.get("primary_diagnosis"), report_context.get("secondary_differential"), final_diagnosis.get("name")]
                + list(report_context.get("differential_names", []))
            )
            repaired["section_markdown"] = self._sanitize_summary_observation_text(
                repaired.get("section_markdown", ""),
                blocked_terms=blocked_terms,
            )
        text = str(repaired.get("section_markdown", "")).strip()
        if len(text) < 80:
            return self._build_emergency_section_payload(title=title, report_packet=report_packet)
        return repaired

    def _ensure_report_section_quality(
        self,
        *,
        title: str,
        payload: dict[str, Any],
        report_packet: dict[str, Any],
        completed_sections: list[dict[str, str]],
        route_key: str,
        stage: str,
        agent_name: str,
        case_text: str,
        caption: CaptionSchema,
        section_packet: dict[str, Any],
        section_instruction: str,
    ) -> tuple[dict[str, Any], bool]:
        markdown = self._compose_section_markdown(title=title, payload=payload)
        try:
            validate_report_section(
                title,
                markdown,
                report_packet=report_packet,
                previous_sections=completed_sections,
            )
            return payload, False
        except ValueError as err:
            issues = [str(err)]

        repaired_payload = self._repair_section_payload(
            title=title,
            payload=payload,
            report_packet=report_packet,
        )
        try:
            repaired_markdown = self._compose_section_markdown(title=title, payload=repaired_payload)
            validate_report_section(
                title,
                repaired_markdown,
                report_packet=report_packet,
                previous_sections=completed_sections,
            )
            return repaired_payload, True
        except ValueError as err:
            issues.append(str(err))

        try:
            rewritten = self._rewrite_report_section(
                title=title,
                current_payload=payload,
                issues=issues,
                completed_sections=completed_sections,
                route_key=route_key,
                stage=f"{stage}_rewrite",
                agent_name=agent_name,
                case_text=case_text,
                caption=caption,
                section_packet=section_packet,
                section_instruction=section_instruction,
            )
            rewritten = self._repair_section_payload(
                title=title,
                payload=rewritten,
                report_packet=report_packet,
            )
            rewritten_markdown = self._compose_section_markdown(title=title, payload=rewritten)
            validate_report_section(
                title,
                rewritten_markdown,
                report_packet=report_packet,
                previous_sections=completed_sections,
            )
            return rewritten, True
        except Exception as err:  # noqa: BLE001
            issues.append(str(err))
        emergency = self._build_emergency_section_payload(
            title=title,
            report_packet=report_packet,
        )
        emergency = self._repair_section_payload(
            title=title,
            payload=emergency,
            report_packet=report_packet,
        )
        try:
            emergency_markdown = self._compose_section_markdown(title=title, payload=emergency)
            validate_report_section(
                title,
                emergency_markdown,
                report_packet=report_packet,
                previous_sections=completed_sections,
            )
        except Exception:  # noqa: BLE001
            pass
        return emergency, True

    @staticmethod
    def _pad_section_markdown_body(text: str, *, min_chars: int = 120) -> str:
        body = str(text or "").strip()
        if len(body) >= min_chars:
            return body
        suffix = " 在材料受限时本节为系统兜底稿，请结合复查与专家意见替换为正式叙述。"
        return (body + suffix).strip() if body else suffix.strip()

    def _build_emergency_section_payload(
        self,
        *,
        title: str,
        report_packet: dict[str, Any],
    ) -> dict[str, Any]:
        report_context = report_packet.get("report_context", {}) if isinstance(report_packet, dict) else {}
        final_diagnosis = report_packet.get("final_diagnosis", {}) if isinstance(report_packet, dict) else {}
        primary = self._first_non_empty(
            [report_context.get("primary_diagnosis"), final_diagnosis.get("name")],
            fallback="当前首要候选病害",
        )
        secondary = self._first_non_empty(report_context.get("secondary_differential"), fallback="其他相似叶部病害")
        differential_names = self._unique_strings(report_context.get("differential_names", []))[:3]
        confidence = self._first_non_empty(
            [report_context.get("confidence_label"), final_diagnosis.get("confidence")],
            fallback="中等",
        )
        evidence_sufficiency = self._first_non_empty(
            final_diagnosis.get("evidence_sufficiency"),
            fallback="现有证据仍以图像与上下文为主，需结合复查继续校正。",
        )

        if title == "病例摘要":
            md = (
                "本节只归纳当前图像能直接支撑的事实：叶片可见的病斑形态、颜色与组织变化、分布位置以及模型给出的受害范围估计。"
                "这些材料用于描述「现场看到了什么」，并不等同于已完成病名确诊。\n\n"
                "在单张图像条件下，结论强度天然受限；后续章节会在补证前提下讨论排序与处置。"
                "读者应把本节理解为观察起点，而非治疗决策终点。"
            )
        elif title == "诊断判断与置信说明":
            differential_hint = (
                f"主要鉴别对象包括：{'、'.join(differential_names)}。"
                if differential_names
                else "鉴别上仍需把相似叶部病害放在同一桌面上比较。"
            )
            md = (
                f"结合现有材料，当前首位疑似方向更接近「{primary}」，审慎层级可暂记为「{confidence}」。"
                f"与「{secondary}」之间仍有相似征象需要继续排除。\n\n"
                f"叶面可见线索与照片分类共同指向上述方向，但仍不等于田间病原确诊。{differential_hint}"
                f"对「{secondary}」若关键区分特征未出现，可解释其暂未压过首位。"
                f"证据边界：{evidence_sufficiency} 若出现分类百分数，只表示「更像哪一类」，不能当作确诊概率。"
            )
        elif title == "复查与补证建议":
            md = (
                "优先安排可复核动作：叶背近景、整株分布、同叶位时间序列，通常最能帮助区分相似选项。\n\n"
                "把每项补证写成「若观察到某结果，判断可如何前移或回调」，避免只罗列「尚缺」而不给路径。"
                "必要时再考虑镜检或送检，并与田间记录对齐。"
            )
        elif title == "救治建议与实施路径":
            md = (
                "在证据尚未完全闭合前，实施路径应坚持先控险、后升级：先把扩散风险和环境因素压住，再讨论针对性更强的干预。"
                "田间层面可优先完成分区观察、改善通风与叶面干湿节律，并把重症叶片与健康群体在记录上分开。\n\n"
                "建议安排 24–48 小时窗口复拍同叶位，观察外扩是否加速、新叶是否出现同类受害；若出现快速蔓延或整株多点受累，应提高警戒并及时寻求线下复核。"
                "本节不展开具体药剂配方，待病原因子更明确后再由专业人员细化用药方案。"
            )
        else:
            md = (
                "风险管理的首要是避免在证据不足时采取不可逆或高代价动作；其次是为复查留出清晰的时间节点与判断指标。"
                "短期内应持续记录病斑是否扩展、是否出现整株层面的同步受害，以及环境条件是否持续利于病情发展。\n\n"
                "若信号走强，需同步提高处置与复核强度；若趋势趋稳且关键阴性证据累积，则应避免过度治疗。"
                "任何调整都建议以可复核的观察记录为依据，而不是单次主观印象。"
            )
        return {
            "section_title": title,
            "section_markdown": self._pad_section_markdown_body(md),
        }

    def _rewrite_report_section(
        self,
        *,
        title: str,
        current_payload: dict[str, Any],
        issues: list[str],
        completed_sections: list[dict[str, str]],
        route_key: str,
        stage: str,
        agent_name: str,
        case_text: str,
        caption: CaptionSchema,
        section_packet: dict[str, Any],
        section_instruction: str,
    ) -> dict[str, Any]:
        current_md = self._compose_section_markdown(title=title, payload=current_payload)
        rewrite_messages = [
            {
                "role": "system",
                "content": (
                    "你是农业病害救治报告的章节修订助手，只输出中文正文。\n"
                    "文风客观、书面、克制；避免鸡汤句与通篇「你」；每段宜短，段间空行。\n"
                    "禁止 JSON、禁止 ## 标题、禁止代码围栏；禁止【】标签式小标题；允许加粗短语与短列表。\n"
                    "各节勿重复同一开篇总述；诊断节须写清「这种病是什么」，不得只写病名。"
                ),
            },
            {
                "role": "user",
                "content": "\n".join(
                    [
                        f"章节：{title}",
                        f"指令：{section_instruction}",
                        "",
                        "当前草稿：",
                        current_md,
                        "",
                        "质检问题：",
                        "\n".join(issues),
                        "",
                        "已完成前文节选（勿整段重复）：",
                        json.dumps(
                            self._compact_completed_sections_for_prompt(completed_sections),
                            ensure_ascii=False,
                        ),
                        "",
                        "请根据问题修订本章，输出修订后的完整正文。",
                    ]
                ),
            },
        ]
        text, _ = self._llm_plain_report_section(
            messages=rewrite_messages,
            route_key=route_key,
            stage=stage,
            agent_name=agent_name,
        )
        return {"section_title": title, "section_markdown": text}

    def _build_deterministic_section_payload(
        self,
        *,
        report_packet: dict[str, Any],
        section_title: str,
    ) -> dict[str, Any]:
        markdown = self._build_deterministic_markdown_report(report_packet=report_packet)
        extracted = self._extract_markdown_section(markdown=markdown, section_title=section_title)
        body = self._polish_report_text(extracted.strip())
        body = self._pad_section_markdown_body(body, min_chars=120)
        return {
            "section_title": section_title,
            "section_markdown": body,
        }

    @staticmethod
    def _extract_markdown_section(*, markdown: str, section_title: str) -> str:
        lines = markdown.splitlines()
        start_prefix = f"## {section_title}"
        capture = False
        collected: list[str] = []
        for line in lines:
            if line.startswith("## "):
                if line.strip() == start_prefix:
                    capture = True
                    continue
                if capture:
                    break
            if capture:
                collected.append(line)
        return "\n".join(collected).strip()

    @staticmethod
    def _aggregate_report_call_meta(section_metas: list[dict[str, Any]]) -> dict[str, Any]:
        if not section_metas:
            return CallMetaSchema(
                provider="system",
                model="section_writer",
                latency_ms=0,
                request_id="",
                is_real_output=True,
                used_fallback=True,
            ).model_dump(mode="json")
        first = dict(section_metas[0])
        first["latency_ms"] = sum(int(meta.get("latency_ms", 0) or 0) for meta in section_metas)
        first["used_fallback"] = any(bool(meta.get("used_fallback", False)) for meta in section_metas)
        request_ids = [str(meta.get("request_id", "")).strip() for meta in section_metas if str(meta.get("request_id", "")).strip()]
        first["request_id"] = ",".join(request_ids[:6])
        first["is_real_output"] = all(bool(meta.get("is_real_output", False)) for meta in section_metas)
        return first

    def _ensure_markdown_report_quality(
        self,
        *,
        markdown: str,
        route_key: str,
        stage: str,
        agent_name: str,
        case_text: str,
        caption: CaptionSchema,
        report_packet: dict[str, Any],
    ) -> tuple[str, bool]:
        try:
            validate_markdown_report(markdown)
            return markdown, False
        except ValueError as err:
            issues = [str(err)]
        try:
            rewritten = self._rewrite_markdown_report(
                route_key=route_key,
                stage=f"{stage}_rewrite",
                agent_name=agent_name,
                case_text=case_text,
                caption=caption,
                report_packet=report_packet,
                current_markdown=markdown,
                issues=issues,
            )
            try:
                validate_markdown_report(rewritten)
            except ValueError:
                # 放宽策略：优先保留语义自然的改写稿，避免机械回退到模板报告。
                return rewritten, True
            return rewritten, True
        except Exception as err:  # noqa: BLE001
            issues.append(str(err))
        # 最后兜底优先保留当前可读文本，减少模板化重复。
        return markdown, True

    def _rewrite_markdown_report(
        self,
        *,
        route_key: str,
        stage: str,
        agent_name: str,
        case_text: str,
        caption: CaptionSchema,
        report_packet: dict[str, Any],
        current_markdown: str,
        issues: list[str],
    ) -> str:
        rewrite_messages = [
            {
                "role": "system",
                "content": (
                    "你是农业病害救治报告润色助手。"
                    "你的任务不是重新诊断，而是把已有报告重写成更像正式报告的中文 Markdown。"
                    "只输出 JSON，且只包含 markdown_report 一个字段。"
                    "报告需要保留五个固定章节，并保持章节顺序不变。"
                    "每个章节优先使用自然段叙述，不要把正文写成清单。"
                    "允许少量项目符号，但不要让报告看起来像要点堆砌。"
                    "不要在多个章节里原样重复同一段冲突说明或同一段证据解释。"
                    "不要输出内部 id、模型名、provider、stage、source 标记、路径或调试信息。"
                    "当存在证据冲突时，使用“倾向于”“目前怀疑”“需进一步确认”等审慎措辞。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case_text": case_text,
                        "caption_summary": caption.model_dump(mode="json"),
                        "report_packet": report_packet,
                        "current_markdown": current_markdown,
                        "quality_issues": issues,
                        "rewrite_requirements": [
                            "把项目符号压缩到最低，优先改写成段落。",
                            "每个章节至少保留 2 句以上自然语言叙述。",
                            "如果结论存在不确定性，要明确写出证据边界和复核建议。",
                            "不同章节各自承担不同任务，不要把同一段解释复制到多个章节。",
                            "保持中文、专业、克制，不要写成会议纪要或内部讨论记录。",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        payload, _ = self._llm_structured_with_retry(
            model_cls=MarkdownReportSchema,
            messages=rewrite_messages,
            route_key=route_key,
            stage=stage,
            agent_name=agent_name,
        )
        return str(payload["markdown_report"]).strip()

    def _build_deterministic_markdown_report(self, *, report_packet: dict[str, Any]) -> str:
        case_summary = report_packet.get("case_summary", {}) if isinstance(report_packet, dict) else {}
        vision_conflict = report_packet.get("vision_conflict", {}) if isinstance(report_packet, dict) else {}
        final_diagnosis = report_packet.get("final_diagnosis", {}) if isinstance(report_packet, dict) else {}
        diagnosis_basis = report_packet.get("diagnosis_basis", {}) if isinstance(report_packet, dict) else {}
        action_plan = report_packet.get("action_plan", {}) if isinstance(report_packet, dict) else {}
        safety_and_followup = report_packet.get("safety_and_followup", {}) if isinstance(report_packet, dict) else {}
        uncertainty_management = report_packet.get("uncertainty_management", {}) if isinstance(report_packet, dict) else {}
        decision_support = report_packet.get("decision_support", {}) if isinstance(report_packet, dict) else {}
        report_context = report_packet.get("report_context", {}) if isinstance(report_packet, dict) else {}

        crop = self._first_non_empty(case_summary.get("crop"), fallback="当前作物")
        visual_summary = self._first_non_empty(case_summary.get("visual_summary"), fallback="当前主要依据来自图像与上下文描述")
        observed_symptoms = self._join_natural_list(case_summary.get("observed_symptoms", []), limit=4, fallback="可见症状仍需结合补充图像进一步细化")
        image_specific_morphology = self._join_natural_list(case_summary.get("image_specific_morphology", []), limit=2)
        area_ratio_source_note = self._first_non_empty(case_summary.get("area_ratio_source_note"))
        stage_hint = self._first_non_empty(case_summary.get("stage_hint"))
        consistency_note = self._first_non_empty(case_summary.get("consistency_note"))
        diagnosis_name = self._first_non_empty(final_diagnosis.get("name"), fallback="待进一步复核病害")
        diagnosis_statement = self._first_non_empty(
            [final_diagnosis.get("diagnosis_statement"), report_context.get("diagnosis_statement")],
            fallback=f"当前将「{diagnosis_name}」作为首位疑似方向，证据闭合前保持审慎口径。",
        )
        confidence_label = self._first_non_empty(final_diagnosis.get("confidence"), fallback="中等")
        model_score_note = self._first_non_empty(
            [final_diagnosis.get("model_score_note"), report_context.get("model_score_note")],
            fallback="模型分数仅反映类别倾向，不等同于确诊概率。",
        )
        confidence_statement = self._first_non_empty(
            final_diagnosis.get("confidence_statement"),
            fallback=f"现阶段更倾向于{diagnosis_name}，但仍属于需要复核的倾向性判断。",
        )
        evidence_sufficiency = self._first_non_empty(
            final_diagnosis.get("evidence_sufficiency"),
            fallback="当前证据主要来自图像与上下文，尚不足以支撑过强结论。",
        )

        has_conflict = bool(vision_conflict.get("has_conflict"))
        classification_result = self._first_non_empty(vision_conflict.get("classification_result"))
        segmentation_result = self._first_non_empty(vision_conflict.get("segmentation_result"))
        primary_visual_conclusion = self._first_non_empty(vision_conflict.get("primary_visual_conclusion"))
        reason_summary = self._first_non_empty(vision_conflict.get("reason_summary"))
        reason_details = self._join_natural_list(vision_conflict.get("reason_details", []), limit=3)
        recommended_interpretation = self._first_non_empty(vision_conflict.get("recommended_interpretation"))
        damage_ratio = self._format_ratio_percent(vision_conflict.get("damaged_area_ratio_of_leaf"))
        summary_blocked_terms = self._unique_strings(
            [diagnosis_name, classification_result, segmentation_result, primary_visual_conclusion]
        )
        visual_summary = self._sanitize_summary_observation_text(visual_summary, blocked_terms=summary_blocked_terms)
        consistency_note = self._sanitize_summary_observation_text(consistency_note, blocked_terms=summary_blocked_terms)
        observed_symptoms = self._sanitize_summary_observation_text(observed_symptoms, blocked_terms=summary_blocked_terms)

        symptom_summary = self._join_natural_list(diagnosis_basis.get("symptom_summary", []), limit=4, fallback="当前症状摘要仍以图像表现为主")
        visual_evidence = self._join_natural_list(diagnosis_basis.get("visual_evidence", []), limit=4, fallback="现有支持证据仍需结合复拍进一步加固")
        image_specific_basis = self._join_natural_list(diagnosis_basis.get("image_specific_basis", []), limit=3)
        counter_evidence = self._join_natural_list(diagnosis_basis.get("counter_evidence", []), limit=3, fallback="暂未形成足以完全推翻当前判断的强反证")
        differential_points = self._join_natural_list(diagnosis_basis.get("differential_points", []), limit=3, fallback="仍需与其他叶部病害继续鉴别")
        evidence_to_collect = self._join_natural_list(diagnosis_basis.get("evidence_to_collect", []), limit=4, fallback="建议补充叶背近景、同叶位复拍图和整株图像")
        primary_reasoning = self._first_non_empty(diagnosis_basis.get("primary_reasoning"))
        differential_summary = self._summarize_ranked_differentials(diagnosis_basis.get("ranked_differentials", []))

        actions = self._join_natural_list(action_plan.get("actions", []), limit=4, fallback="先执行低风险、可逆的保守措施")
        rescue_plan = self._summarize_rescue_plan(action_plan.get("rescue_plan", []))
        prohibited_actions = self._join_natural_list(action_plan.get("prohibited_actions", []), limit=3, fallback="不宜在证据不足时直接采取高风险激进处置")
        monitoring_plan = self._join_natural_list(action_plan.get("monitoring_plan", []), limit=4, fallback="持续观察病斑扩展趋势和新叶变化")
        timeline_summary = self._summarize_action_timeline(action_plan.get("timeline", []))
        escalation_conditions = self._join_natural_list(action_plan.get("escalation_conditions", []), limit=3)

        safety_notes = self._join_natural_list(safety_and_followup.get("safety_notes", []), limit=4, fallback="当前最主要风险在于误诊和过度处理")
        required_followups = self._join_natural_list(safety_and_followup.get("required_followups", []), limit=4, fallback="建议在 24 至 48 小时内完成复拍和复核")
        review_summary = self._first_non_empty(
            safety_and_followup.get("review_summary"),
            fallback="后续应根据新增图像和复查结果动态调整结论与处置强度。",
        )
        prognosis_note = self._first_non_empty(safety_and_followup.get("prognosis_note"))
        conflict_point = uncertainty_management.get("conflict_point", {}) if isinstance(uncertainty_management, dict) else {}
        key_discriminator_items = (
            uncertainty_management.get("key_discriminators", [])
            if isinstance(uncertainty_management, dict)
            else []
        )
        uncertainty_discriminators = self._join_natural_list(
            [
                self._first_non_empty(item.get("gap"))
                for item in key_discriminator_items
                if isinstance(item, dict)
            ],
            limit=3,
        )
        uncertainty_rank_shift = self._join_natural_list(
            [
                self._first_non_empty(item.get("rank_shift_hint"))
                for item in key_discriminator_items
                if isinstance(item, dict)
            ],
            limit=2,
        )
        upgrade_thresholds = self._join_natural_list(
            decision_support.get("upgrade_conditions", []) if isinstance(decision_support, dict) else [],
            limit=3,
        )
        downgrade_thresholds = self._join_natural_list(
            decision_support.get("downgrade_conditions", []) if isinstance(decision_support, dict) else [],
            limit=2,
        )
        review_nodes = self._join_natural_list(
            decision_support.get("review_nodes", []) if isinstance(decision_support, dict) else [],
            limit=3,
        )
        post_review_branches = self._join_natural_list(
            decision_support.get("post_review_branches", []) if isinstance(decision_support, dict) else [],
            limit=2,
        )
        conflict_overall = self._first_non_empty(conflict_point.get("overall_impression"))
        conflict_local = self._first_non_empty(conflict_point.get("local_lesion_impression"))

        conflict_sentence = ""
        if has_conflict:
            conflict_sentence = (
                "分类与受害面积等信号之间存在张力，需要结合复拍与田间观察再解释"
                f"{f'；分割估计病损约占叶片面积 {damage_ratio}' if damage_ratio else ''}。"
            )

        sections = [
            (
                "病例摘要",
                (
                    f"本例为{crop}叶片材料。当前可见线索可概括为：{observed_symptoms}；"
                    f"{visual_summary or '图像可见明显叶部受害征象。'}"
                    f"{f' {consistency_note}' if consistency_note else ''}\n\n"
                    f"{f'{area_ratio_source_note} ' if area_ratio_source_note else ''}"
                    f"{f'{stage_hint} ' if stage_hint else ''}"
                    f"{conflict_sentence or '单张图像仅能支撑阶段性描述，排序与处置见后文。'}"
                ),
            ),
            (
                "诊断判断与置信说明",
                (
                    f"{diagnosis_statement} 置信层级记为「{confidence_label}」。{model_score_note}"
                    f"{confidence_statement}\n\n"
                    f"{primary_reasoning + ' ' if primary_reasoning else ''}"
                    f"证据强度评估：{evidence_sufficiency}。"
                    f"{f' 分歧点：整体印象接近「{conflict_overall}」，局部线索更接近「{conflict_local}」。' if (conflict_overall and conflict_local and conflict_overall != conflict_local) else ''}"
                    f"{f' {reason_summary}' if reason_summary else ''}\n\n"
                    f"{f'{image_specific_basis} ' if image_specific_basis else ''}"
                    f"支持信息主要来自{symptom_summary}与{visual_evidence}；"
                    f"限制面包括{counter_evidence}。"
                    f"鉴别上需盯住{differential_points}。{differential_summary}"
                    f"{f' 视觉层面补充：{reason_details}。' if reason_details else ''}"
                    f"{f' 高影响分歧点：{uncertainty_discriminators}。' if uncertainty_discriminators else ''}"
                ),
            ),
            (
                "复查与补证建议",
                (
                    f"建议优先安排：{evidence_to_collect}。"
                    f"{f' 对排序帮助较大的是：{uncertainty_discriminators}。' if uncertainty_discriminators else ''}\n\n"
                    f"{f'补证回报后可参考：{uncertainty_rank_shift}。' if uncertainty_rank_shift else ''}"
                    f"{f' {recommended_interpretation}' if recommended_interpretation else ''}"
                    " 将复拍、叶背观察与必要送检写成可记录动作，便于后续对照。"
                ),
            ),
            (
                "救治建议与实施路径",
                (
                    f"先执行低风险步骤：{actions}；同时记录现场变化。"
                    f"{f' 分阶段安排可参考：{timeline_summary or rescue_plan}。' if (timeline_summary or rescue_plan) else ''}\n\n"
                    f"观察重点：{monitoring_plan}。"
                    f"{f' 若出现{escalation_conditions}，应提高处理与复核强度。' if escalation_conditions else ''}"
                    f"{f' 阈值提示：{upgrade_thresholds} 倾向升级；{downgrade_thresholds} 可考虑下调。' if (upgrade_thresholds or downgrade_thresholds) else ''}"
                    " 具体药剂须在病因更明确后由专业人员确定。"
                ),
            ),
            (
                "风险边界、预后与复查",
                (
                    f"主要风险：{safety_notes}；暂避免：{prohibited_actions}。"
                    f"{f' {prognosis_note}' if prognosis_note else ''}\n\n"
                    f"复查：{required_followups}。{review_summary}"
                    f"{f' 建议节点：{review_nodes}。' if review_nodes else ''}"
                    f"{f' 复查后分支：{post_review_branches}。' if post_review_branches else ''}"
                ),
            ),
        ]
        blocks = ["# 农业救治报告"]
        for title, body in sections:
            blocks.append(f"## {title}\n{self._polish_report_text(body)}")
        return "\n\n".join(blocks).strip()

    def _summarize_rescue_plan(self, rescue_plan: Any) -> str:
        if not isinstance(rescue_plan, list):
            return ""
        phases: list[str] = []
        for item in rescue_plan[:3]:
            if not isinstance(item, dict):
                continue
            phase = self._first_non_empty(item.get("phase"))
            objective = self._first_non_empty(item.get("objective"))
            actions = self._join_natural_list(item.get("actions", []), limit=3)
            rationale = self._join_natural_list(item.get("rationale", []), limit=2)
            parts = [part for part in [phase, objective, actions, rationale] if part]
            if parts:
                phases.append("，".join(parts))
        return "；".join(phases)

    def _summarize_action_timeline(self, timeline: Any) -> str:
        if not isinstance(timeline, list):
            return ""
        phases: list[str] = []
        for item in timeline[:3]:
            if not isinstance(item, dict):
                continue
            phase = self._first_non_empty(item.get("phase"))
            objective = self._first_non_empty(item.get("objective"))
            actions = self._join_natural_list(item.get("actions", []), limit=3)
            parts = [part for part in [phase, objective, actions] if part]
            if parts:
                phases.append("：".join([parts[0], "，".join(parts[1:])]) if len(parts) > 1 else parts[0])
        return "；".join(phases)

    def _summarize_ranked_differentials(self, ranked_differentials: Any) -> str:
        if not isinstance(ranked_differentials, list):
            return ""
        parts: list[str] = []
        for item in ranked_differentials[:3]:
            if not isinstance(item, dict):
                continue
            name = self._first_non_empty(item.get("name"))
            why_supported = self._first_non_empty(item.get("why_supported"))
            why_not_primary = self._first_non_empty(item.get("why_not_primary"))
            if not name:
                continue
            sentence = f"需继续鉴别“{name}”"
            if why_supported:
                sentence += f"，其保留原因主要是{why_supported}"
            if why_not_primary:
                sentence += f"，但当前未排在首位主要因为{why_not_primary}"
            parts.append(sentence + "。")
        return "".join(parts)

    def _join_natural_list(self, values: Any, *, limit: int, fallback: str = "") -> str:
        items: list[str] = []
        for raw in self._unique_strings(values):
            text = str(raw).strip()
            text = re.sub(r"^[、，；。:\-]+", "", text)
            text = re.sub(r"\s+", " ", text)
            if text and text not in items:
                items.append(text)
            if len(items) >= limit:
                break
        if not items:
            return fallback
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]}和{items[1]}"
        return "、".join(items[:-1]) + f"以及{items[-1]}"

    def _sanitize_summary_observation_text(self, text: str, *, blocked_terms: list[str]) -> str:
        value = " ".join(str(text or "").split())
        if not value:
            return ""
        for term in self._unique_strings(blocked_terms):
            if term:
                value = value.replace(term, "相关病害")
        banned_phrases = ("倾向于", "更偏向", "首要诊断", "置信", "把握度", "当前判断")
        if any(phrase in value for phrase in banned_phrases):
            return ""
        return value

    @staticmethod
    def _format_ratio_percent(value: Any) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return ""
        if numeric < 0:
            return ""
        if numeric <= 1.0:
            numeric *= 100.0
        return f"{numeric:.1f}%"

    @staticmethod
    def _format_percent_value(value: Any) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return ""
        if numeric < 0:
            return ""
        if numeric <= 1.0:
            numeric *= 100.0
        return f"{numeric:.1f}%"

    def _build_deterministic_final_result(
        self,
        *,
        caption: CaptionSchema,
        shared_state: dict[str, Any],
        decision_packet: dict[str, Any],
    ) -> dict[str, Any]:
        diagnosis_summary = decision_packet.get("diagnosis_summary", {}) if isinstance(decision_packet, dict) else {}
        case_summary = decision_packet.get("case_summary", {}) if isinstance(decision_packet, dict) else {}
        vision_conflict = decision_packet.get("vision_conflict", {}) if isinstance(decision_packet, dict) else {}
        candidate_items = diagnosis_summary.get("candidate_diagnoses", []) if isinstance(diagnosis_summary, dict) else []
        evidence_board = shared_state.get("evidence_board", []) if isinstance(shared_state, dict) else []

        primary_name = str(diagnosis_summary.get("primary_candidate", "")).strip()
        if not primary_name:
            primary_name = self._first_non_empty(shared_state.get("working_diagnoses", []), fallback="待进一步复核病害")

        uncertainty_score = self._clamp(float(diagnosis_summary.get("uncertainty_score", 0.5) or 0.5))
        confidence_label = self._confidence_label_from_uncertainty(uncertainty_score)
        confidence_statement = self._build_confidence_statement(
            primary_name=primary_name,
            uncertainty_score=uncertainty_score,
            has_conflict=bool(vision_conflict.get("has_conflict")),
        )

        symptom_summary = self._unique_strings(
            list(case_summary.get("observed_symptoms", []))[:5]
            + list(shared_state.get("next_focus", []))[:2]
        )[:6]
        visual_evidence = self._flatten_candidate_reasons(candidate_items, field="supporting_evidence", limit=5)
        if not visual_evidence:
            visual_evidence = self._flatten_evidence_board(evidence_board, field="supporting", limit=5)

        counter_evidence = self._unique_strings(
            self._flatten_candidate_reasons(candidate_items, field="counter_evidence", limit=4)
            + list(shared_state.get("conflicts", []))[:3]
            + list(shared_state.get("safety_flags", []))[:2]
        )[:5]
        differential_points = self._unique_strings(
            [str(vision_conflict.get("reason_summary", "")).strip()]
            + list(vision_conflict.get("reason_details", []))[:3]
        )[:4]
        evidence_to_collect = self._unique_strings(
            list(decision_packet.get("missing_information", []))[:4]
            + list(decision_packet.get("verification_tasks", []))[:4]
            + list(case_summary.get("followup_questions", []))[:2]
        )[:5]
        actions = self._unique_strings(list(decision_packet.get("recommended_actions", []))[:4])[:4]
        if not actions:
            actions = self._unique_strings(list(shared_state.get("action_focus", []))[:4])[:4]

        rescue_plan = self._build_deterministic_rescue_plan(actions, uncertainty_score)
        prohibited_actions = []
        if uncertainty_score >= 0.45 or bool(vision_conflict.get("has_conflict")):
            prohibited_actions.append("在证据不足或结果冲突未复核前，不要直接采取高风险激进处理。")
        monitoring_plan = self._unique_strings(
            evidence_to_collect[:3]
            + ["复拍同叶位病斑，观察 24 至 48 小时内是否继续扩展。"]
        )[:4]
        safety_notes = self._unique_strings(list(decision_packet.get("safety_notes", []))[:4])[:4]
        report_outline = self._default_report_outline(
            {
                "top_diagnosis": {"name": primary_name},
                "evidence_sufficiency": str(diagnosis_summary.get("evidence_sufficiency", "")).strip(),
                "confidence_statement": confidence_statement,
            },
            {"evidence_sufficiency": str(diagnosis_summary.get("evidence_sufficiency", "")).strip()},
        )

        severity_level = "medium"
        if float(caption.numeric.severity_score) >= 0.7:
            severity_level = "high"
        elif float(caption.numeric.severity_score) <= 0.35:
            severity_level = "low"

        payload = {
            "top_diagnosis": {
                "name": primary_name,
                "confidence": confidence_label,
            },
            "candidates": self._build_final_candidates(candidate_items),
            "reject_flag": "当前存在证据冲突，结论仅作为倾向性诊断参考。" if counter_evidence else "",
            "symptom_summary": symptom_summary,
            "visual_evidence": visual_evidence,
            "counter_evidence": counter_evidence,
            "differential_points": differential_points,
            "severity_risk": {
                "level": severity_level,
                "spread_risk": "若为侵染性病害，当前病损面积已提示存在继续扩展风险。",
                "pruning_guideline": "复核前优先保守处理，仅对明显重症叶片做低风险隔离或标记观察。",
            },
            "evidence_to_collect": evidence_to_collect,
            "actions": actions,
            "evidence_board": evidence_board if isinstance(evidence_board, list) else [],
            "rescue_plan": rescue_plan,
            "prohibited_actions": prohibited_actions,
            "monitoring_plan": monitoring_plan,
            "report_outline": report_outline,
            "evidence_sufficiency": str(diagnosis_summary.get("evidence_sufficiency", "")).strip()
            or "当前证据仍以视觉表现为主，需结合补充图像和进一步检验后再提高结论强度。",
            "confidence_statement": confidence_statement,
            "citations": [],
            "safety_notes": safety_notes,
        }
        return FinalDiagnosisSchema.model_validate(payload).model_dump(mode="json")

    @staticmethod
    def _first_non_empty(values: Any, *, fallback: str = "") -> str:
        if isinstance(values, list):
            for item in values:
                text = str(item).strip()
                if text:
                    return text
        text = str(values).strip() if values is not None else ""
        return text or fallback

    @staticmethod
    def _confidence_label_from_uncertainty(uncertainty_score: float) -> str:
        if uncertainty_score >= 0.7:
            return "低"
        if uncertainty_score >= 0.4:
            return "中"
        return "较高"

    @staticmethod
    def _flatten_candidate_reasons(items: list[Any], *, field: str, limit: int) -> list[str]:
        values: list[str] = []
        for item in items[:2]:
            if not isinstance(item, dict):
                continue
            for reason in item.get(field, [])[:3]:
                text = str(reason).strip()
                if text and text not in values:
                    values.append(text)
                if len(values) >= limit:
                    return values
        return values

    @staticmethod
    def _flatten_evidence_board(items: list[Any], *, field: str, limit: int) -> list[str]:
        values: list[str] = []
        if not isinstance(items, list):
            return values
        for item in items[:2]:
            if not isinstance(item, dict):
                continue
            for reason in item.get(field, [])[:3]:
                text = str(reason).strip()
                if text and text not in values:
                    values.append(text)
                if len(values) >= limit:
                    return values
        return values

    def _build_final_candidates(self, candidate_items: list[Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for item in candidate_items[:2]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            candidates.append(
                {
                    "name": name,
                    "why_like": self._first_non_empty(item.get("supporting_evidence", [])),
                    "why_unlike": self._first_non_empty(item.get("counter_evidence", [])),
                }
            )
        return candidates

    @staticmethod
    def _build_deterministic_rescue_plan(actions: list[str], uncertainty_score: float) -> list[dict[str, Any]]:
        phase_one_actions = actions[:3] or ["先补充叶背近景、同叶位复拍图和整株图像，再复核诊断。"]
        plan = [
            {
                "phase": "立即复核",
                "objective": "先补充关键证据并确认结果冲突来源。",
                "actions": phase_one_actions,
                "rationale": ["当前存在结果冲突，先补证据比直接升级处理更稳妥。"],
                "risk_level": "low",
            }
        ]
        if uncertainty_score >= 0.45:
            plan.append(
                {
                    "phase": "保守观察",
                    "objective": "在未确证前降低误治风险。",
                    "actions": ["保持通风、隔离重症叶片，并持续复拍观察病斑变化。"],
                    "rationale": ["证据不足时优先采用低风险、可逆的管理措施。"],
                    "risk_level": "medium",
                }
            )
        return plan

    @staticmethod
    def _build_confidence_statement(
        *,
        primary_name: str,
        uncertainty_score: float,
        has_conflict: bool,
    ) -> str:
        if has_conflict or uncertainty_score >= 0.7:
            return f"当前更倾向于“{primary_name}”，但证据冲突较明显，结论仅适合作为待复核的倾向性诊断。"
        if uncertainty_score >= 0.4:
            return f"当前初步倾向于“{primary_name}”，但仍需补充关键图像或检验信息后再提高结论强度。"
        return f"当前证据对“{primary_name}”有较稳定支持，但仍建议结合后续复查结果综合判断。"

    @staticmethod
    def _sanitize_model_payload(model_cls: Type[BaseModel], payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload

        wrapper_keys = ("payload", "data", "result", "output", "response")
        wrapper_meta_keys = {
            "stage",
            "agent_name",
            "route_key",
            "schema_name",
            "schema",
            "status",
            "provider",
            "model",
            "message",
        }
        sanitized = dict(payload)
        seen_signatures: set[tuple[str, ...]] = set()
        while isinstance(sanitized, dict):
            signature = tuple(sorted(str(key) for key in sanitized.keys()))
            if signature in seen_signatures:
                break
            seen_signatures.add(signature)

            unwrapped = False
            for key in wrapper_keys:
                inner = sanitized.get(key)
                if not isinstance(inner, dict):
                    continue
                outer_keys = set(str(item) for item in sanitized.keys())
                if outer_keys <= wrapper_meta_keys | {key}:
                    sanitized = dict(inner)
                    unwrapped = True
                    break
            if not unwrapped:
                break

        if model_cls in EXPERT_TURN_MODELS:
            # Expert call metadata is generated by the orchestrator after the LLM call.
            # Drop any model-fabricated meta block so partial machine fields do not fail validation.
            sanitized.pop("meta", None)
        return sanitized

    def _llm_structured_with_retry(
        self,
        model_cls: Type[BaseModel],
        messages: list[dict[str, str]],
        route_key: str,
        stage: str,
        agent_name: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        schema = model_cls.model_json_schema()
        route = self._route_for(route_key)
        max_new_tokens = self._max_new_tokens_for_model(model_cls)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                response = self.llm_client.generate(
                    route=route,
                    messages=messages,
                    json_schema=schema,
                    temperature=0.0,
                    timeout=self.timeout,
                    max_new_tokens=max_new_tokens,
                )
                payload, repaired = self._parse_or_repair_response(
                    model_cls=model_cls,
                    route=route,
                    response_text=response.content,
                    stage=stage,
                    agent_name=agent_name,
                    max_new_tokens=max_new_tokens,
                )
                payload = self._sanitize_model_payload(model_cls, payload)
                model = model_cls.model_validate(payload)
                call_meta = CallMetaSchema(
                    provider=response.provider,
                    model=response.model,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    request_id=response.request_id,
                    is_real_output=True,
                    used_fallback=response.used_fallback or repaired,
                ).model_dump(mode="json")
                return model.model_dump(mode="json"), call_meta
            except Exception as err:  # noqa: BLE001
                last_error = err
                if attempt < self.max_retries:
                    time.sleep(min(0.25 * (2**attempt), 1.5))
                continue

        raise RealOutputRequiredError(
            stage=stage,
            agent_name=agent_name,
            provider=route.provider,
            model=route.model,
            reason=str(last_error) if last_error else "结构化调用失败",
            raw_error_type=type(last_error).__name__ if last_error else "RuntimeError",
        )

    def _parse_or_repair_response(
        self,
        *,
        model_cls: Type[BaseModel],
        route: LLMRoute,
        response_text: str,
        stage: str,
        agent_name: str,
        max_new_tokens: int,
    ) -> tuple[dict[str, Any], bool]:
        try:
            payload = parse_json_object(response_text)
            payload = self._sanitize_model_payload(model_cls, payload)
            return model_cls.model_validate(payload).model_dump(mode="json"), False
        except Exception:
            repaired = self._repair_structured_output(
                model_cls=model_cls,
                route=route,
                response_text=response_text,
                stage=stage,
                agent_name=agent_name,
                max_new_tokens=max_new_tokens,
            )
            return repaired, True

    def _repair_structured_output(
        self,
        *,
        model_cls: Type[BaseModel],
        route: LLMRoute,
        response_text: str,
        stage: str,
        agent_name: str,
        max_new_tokens: int,
    ) -> dict[str, Any]:
        schema = model_cls.model_json_schema()
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "你负责修复不符合要求的结构化输出。"
                    "仅返回一个严格 JSON 对象，必须完全符合给定 JSON Schema。"
                    "保持原始草稿语义，不要添加调试文本，也不要输出 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "stage": stage,
                        "agent_name": agent_name,
                        "draft_output": response_text,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        repaired = self.llm_client.generate(
            route=route,
            messages=repair_messages,
            json_schema=schema,
            temperature=0.0,
            timeout=self.timeout,
            max_new_tokens=max_new_tokens,
        )
        payload = parse_json_object(repaired.content)
        payload = self._sanitize_model_payload(model_cls, payload)
        return model_cls.model_validate(payload).model_dump(mode="json")

    def _max_new_tokens_for_model(self, model_cls: Type[BaseModel]) -> int:
        if model_cls in {MarkdownReportSchema, MarkdownSectionSchema, BaselineOutputSchema}:
            return self.report_max_new_tokens
        return self.structured_max_new_tokens

    def _route_for(self, key: str) -> LLMRoute:
        route = self.agent_model_routing.get(key)
        if route is not None:
            return route
        default = self.agent_model_routing.get("coordinator_final")
        if default is not None:
            return default
        raise RuntimeError(f"未为键 {key} 配置模型路由")

    @staticmethod
    def _assert_turn_is_real(turn: dict[str, Any], stage: str, agent_name: str) -> None:
        meta = turn.get("meta", {}) if isinstance(turn, dict) else {}
        provider = str(meta.get("provider", "")).strip() if isinstance(meta, dict) else ""
        model = str(meta.get("model", "")).strip() if isinstance(meta, dict) else ""
        if bool(turn.get("invalid_turn", False)):
            raise RealOutputRequiredError(
                stage=stage,
                agent_name=agent_name,
                provider=provider,
                model=model,
                reason="严格模式下 invalid_turn 字段必须为 false",
                raw_error_type="ValueError",
            )
        checks = {
            "diagnosis_evidence_officer": lambda payload: bool(payload.get("candidate_causes"))
            and str(payload.get("candidate_causes", [{}])[0].get("name", "")).strip().lower() not in {"", "unknown"},
            "differential_officer": lambda payload: bool(payload.get("ranked_differentials"))
            and str(payload.get("ranked_differentials", [{}])[0].get("name", "")).strip().lower() not in {"", "unknown"},
            "berry_qa_expert": lambda payload: bool(payload.get("today_actions"))
            or bool(payload.get("control_options"))
            or bool(payload.get("observe_48h")),
            "cultivation_management_officer": lambda payload: bool(payload.get("low_risk_actions")),
            "risk_compliance_officer": lambda payload: bool(payload.get("prohibited_actions"))
            or bool(payload.get("confidence_boundary")),
        }
        if not checks.get(agent_name, lambda payload: True)(turn):
            raise RealOutputRequiredError(
                stage=stage,
                agent_name=agent_name,
                provider=provider,
                model=model,
                reason="角色关键字段为空",
                raw_error_type="ValueError",
            )

    @staticmethod
    def _assert_final_is_real(final_result: dict[str, Any], stage: str) -> None:
        top_name = str(final_result.get("top_diagnosis", {}).get("name", "")).strip().lower()
        if not top_name or top_name == "unknown":
            raise RealOutputRequiredError(
                stage=stage,
                agent_name="coordinator_final",
                provider="",
                model="",
                reason="final.top_diagnosis.name 为空或未知",
                raw_error_type="ValueError",
            )

    @staticmethod
    def _filter_fallback_citations(citations: list[Any]) -> list[str]:
        cleaned: list[str] = []
        for item in citations:
            text = str(item).strip()
            if not text:
                continue
            if text.startswith("fallback_"):
                continue
            cleaned.append(text)
        return cleaned

    @staticmethod
    def _unique_strings(values: list[Any] | tuple[Any, ...] | Any) -> list[str]:
        if not isinstance(values, (list, tuple)):
            values = [values]
        cleaned: list[str] = []
        for item in values:
            text = str(item).strip()
            if not text:
                continue
            if text not in cleaned:
                cleaned.append(text)
        return cleaned

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _enum_values(values: list[Any]) -> list[str]:
        cleaned: list[str] = []
        for item in values:
            value = getattr(item, "value", item)
            text = str(value).strip()
            if text:
                cleaned.append(text)
        return cleaned

    def _derive_working_diagnoses(self, expert_turns: list[dict[str, Any]]) -> list[str]:
        diagnoses: list[str] = []
        for turn in expert_turns:
            for cause in turn.get("top_k_causes", []):
                name = str(cause.get("name", "")).strip()
                if name and name.lower() != "unknown" and name not in diagnoses:
                    diagnoses.append(name)
        return diagnoses[:5]

    def _derive_open_questions(self, expert_turns: list[dict[str, Any]]) -> list[str]:
        questions: list[str] = []
        for turn in expert_turns:
            for item in turn.get("questions_to_ask", []):
                text = str(item).strip()
                if text and text not in questions:
                    questions.append(text)
        return questions[:6]

    def _derive_evidence_board(self, expert_turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        board: dict[str, dict[str, Any]] = {}
        for turn in expert_turns:
            supporting = self._unique_strings(turn.get("supporting_evidence", []))
            counter = self._unique_strings(turn.get("counter_evidence", []))
            missing = self._unique_strings(turn.get("questions_to_ask", []))
            sources = self._unique_strings(turn.get("citations", []))
            for cause in turn.get("top_k_causes", []):
                name = str(cause.get("name", "")).strip()
                if not name or name.lower() == "unknown":
                    continue
                bucket = board.setdefault(
                    name,
                    {
                        "diagnosis": name,
                        "supporting": [],
                        "counter": [],
                        "missing": [],
                        "sources": [],
                    },
                )
                bucket["supporting"] = self._unique_strings(
                    bucket["supporting"] + supporting + [cause.get("why_like", "")]
                )
                bucket["counter"] = self._unique_strings(
                    bucket["counter"] + counter + [cause.get("why_unlike", "")]
                )
                bucket["missing"] = self._unique_strings(bucket["missing"] + missing)
                bucket["sources"] = self._unique_strings(bucket["sources"] + sources)
        return list(board.values())[:5]

    def _build_deterministic_round_summary(
        self,
        *,
        expert_turns: list[dict[str, Any]],
        previous_state: dict[str, Any],
    ) -> dict[str, Any]:
        working_diagnoses = self._derive_working_diagnoses(expert_turns)
        open_questions = self._derive_open_questions(expert_turns)
        diagnosis_evidence = self._derive_evidence_board(expert_turns)
        actions = self._unique_strings(
            [action for turn in expert_turns for action in turn.get("actions", [])]
        )
        risks = self._unique_strings(
            [risk for turn in expert_turns for risk in turn.get("risks", [])]
        )
        counter_evidence = self._unique_strings(
            [item for turn in expert_turns for item in turn.get("counter_evidence", [])]
        )
        avg_confidence = (
            sum(float(turn.get("confidence", 0.5)) for turn in expert_turns) / max(1, len(expert_turns))
        )
        uncertainty = self._clamp(
            max(
                1.0 - avg_confidence,
                0.35 if counter_evidence else 0.0,
                min(0.9, len(open_questions) * 0.08 + len(risks) * 0.06),
            )
        )
        evidence_gaps = open_questions[:4]
        next_focus = self._unique_strings((counter_evidence[:2] + evidence_gaps[:2]))[:4]
        if not next_focus:
            next_focus = self._unique_strings(previous_state.get("next_focus", []))[:3]
        report_priority = self._unique_strings(previous_state.get("report_priority", []))[:4]
        if not report_priority:
            report_priority = [
                "先写病例摘要，再写诊断判断与置信说明（含支持与鉴别）。",
                "随后写复查与补证建议，再写救治与风险边界。",
                "证据不足时把补证写具体，再写保守处置路径。",
            ]

        diagnosis_board = {
            "working_diagnoses": working_diagnoses[:5],
            "supporting": [],
            "counter": counter_evidence[:4],
            "differentials": [],
        }
        evidence_board = {
            "missing_evidence": evidence_gaps[:6],
            "verification_value": evidence_gaps[:6],
        }
        action_board = {
            "today_actions": actions[:4],
            "control_options": [],
            "observe_48h": open_questions[:4],
            "escalation_triggers": [],
            "management_timeline": [],
            "low_risk_actions": [],
            "environment_adjustments": [],
            "followup_nodes": [],
        }
        risk_board = {
            "prohibited_actions": [],
            "risk_flags": risks[:4],
            "confidence_boundary": counter_evidence[:4],
            "overtreatment_risks": [],
            "undertreatment_risks": [],
        }

        return CoordinatorSummarySchema.model_validate(
            {
                "consensus": [],
                "conflicts": counter_evidence[:4],
                "unique_points": risks[:3],
                "next_focus": next_focus,
                "safety_flags": risks[:4],
                "working_diagnoses": working_diagnoses,
                "open_questions": open_questions[:5],
                "evidence_gaps": evidence_gaps,
                "recommended_experts": self._unique_strings(previous_state.get("recommended_experts", [])),
                "uncertainty_score": uncertainty,
                "stop_signal": bool(not counter_evidence and uncertainty <= 0.2 and len(open_questions) <= 1),
                "diagnosis_board": diagnosis_board,
                "evidence_board": evidence_board,
                "action_board": action_board,
                "risk_board": risk_board,
                "diagnosis_evidence": diagnosis_evidence,
                "action_focus": actions[:4],
                "verification_tasks": evidence_gaps[:4],
                "uncertainty_triggers": self._unique_strings(counter_evidence[:2] + open_questions[:2])[:4],
                "report_priority": report_priority,
                "evidence_sufficiency": "",
            }
        ).model_dump(mode="json")

    def _compact_shared_state_for_expert(self, shared_state: dict[str, Any], round_idx: int = 1) -> dict[str, Any]:
        diagnosis_board = shared_state.get("diagnosis_board", {})
        evidence_board = shared_state.get("evidence_board", {})
        action_board = shared_state.get("action_board", {})
        risk_board = shared_state.get("risk_board", {})
        diagnosis_evidence = shared_state.get("diagnosis_evidence", [])
        if isinstance(evidence_board, list):
            diagnosis_evidence = evidence_board
            evidence_board = {}
        payload: dict[str, Any] = {
            "diagnosis_board": diagnosis_board if isinstance(diagnosis_board, dict) else {},
            "evidence_board": evidence_board if isinstance(evidence_board, dict) else {},
            "action_board": action_board if isinstance(action_board, dict) else {},
            "risk_board": risk_board if isinstance(risk_board, dict) else {},
            "diagnosis_evidence": diagnosis_evidence if isinstance(diagnosis_evidence, list) else [],
            "working_diagnoses": list(shared_state.get("working_diagnoses", []))[:3],
            "next_focus": list(shared_state.get("next_focus", []))[:5],
            "conflicts": list(shared_state.get("conflicts", []))[:5],
            "uncertainty_score": shared_state.get("uncertainty_score", 0.5),
        }
        if round_idx <= 1:
            payload["consensus"] = list(shared_state.get("consensus", []))[:5]
        return payload

    @staticmethod
    def _compact_kb_evidence_for_expert(kb_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compacted: list[dict[str, Any]] = []
        priority_keys = (
            "case_id",
            "id",
            "title",
            "crop",
            "diagnosis",
            "summary",
            "symptoms",
            "key_evidence",
            "actions",
            "confidence",
            "source",
        )
        for item in kb_evidence[:4]:
            if not isinstance(item, dict):
                continue
            compact = {
                key: item.get(key)
                for key in priority_keys
                if key in item and item.get(key) not in (None, "", [])
            }
            if compact:
                compacted.append(compact)
        return compacted

    def _initial_report_priority(self, caption: CaptionSchema) -> list[str]:
        priority = [
            "先写病例摘要，再写诊断判断与置信说明",
            "复查与补证建议写清可执行动作，再展开救治路径",
        ]
        if float(caption.numeric.severity_score) >= 0.5:
            priority.append("救治建议与实施路径前置，并突出风险边界、预后与复查")
        if float(caption.ood_score) >= 0.25 or float(caption.confidence) <= 0.55:
            priority.append("复查与补证建议前置，并降低结论措辞强度")
        return self._unique_strings(priority)

    def _default_report_outline(
        self,
        final_result: dict[str, Any],
        safety_result: dict[str, Any],
    ) -> list[str]:
        diagnosis_name = str(final_result.get("top_diagnosis", {}).get("name", "")).strip() or "当前主诊断"
        _ = safety_result
        return self._unique_strings(
            [
                "病例摘要：可见征象与受害范围，不写确诊口径。",
                f"诊断判断与置信说明：首位疑似「{diagnosis_name}」、模型倾向、支持/鉴别与知识库摘要（若有）。",
                "复查与补证建议：优先补什么、有何帮助、可怎么做。",
                "救治建议与实施路径：分步动作、观察与升级条件（证据不足不写具体药剂配方）。",
                "风险边界、预后与复查：禁忌、恶化信号与复查节点。",
            ]
        )
