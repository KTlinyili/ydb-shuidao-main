from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.core.agents.orchestrator import MultiAgentOrchestrator
from app.core.agents.report_quality import validate_markdown_report
from app.core.agents.sanitizer import sanitize_trace
from app.core.caption.dinov3_caption import build_caption_from_dinov3_analysis
from app.core.caption.presentation import localize_caption_payload
from app.core.caption.provider_http_placeholder import HttpPlaceholderCaptionProvider
from app.core.caption.qwen3_vl_provider import LocalQwen3VLCaptionProvider
from app.core.caption.schema import CaptionSchema
from app.core.config import Settings
from app.core.errors import RealOutputRequiredError
from app.core.llm_clients import build_agent_model_routing, build_llm_client
from app.core.retrieval.faceted_retriever import FacetedRetriever
from app.core.retrieval.knowledge_base import GovernanceKnowledgeBase
from app.core.retrieval.reranker_client import RerankerClient
from app.core.storage.case_library import CaseLibrary
from app.core.storage.run_store import RunStore
from app.core.vision.dinov3_service import DinoV3Paths, LocalDinoV3Diagnoser
from app.core.vision.merged_result import build_vision_result
from app.core.vision.presentation import build_image_analysis_display


class DiagnosisPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.run_store = RunStore(settings.run_dir)
        self.case_library = CaseLibrary(settings.cases_dir)
        self.kb = GovernanceKnowledgeBase(settings.kb_dir)
        reranker = RerankerClient(
            base_url=settings.reranker_base_url,
            api_key=settings.reranker_api_key,
            model=settings.reranker_model,
            timeout=settings.request_timeout,
        )
        self.retriever = FacetedRetriever(reranker=reranker)
        self.placeholder_caption_provider = HttpPlaceholderCaptionProvider(
            timeout=settings.request_timeout,
            mock_json_path="" if settings.enable_local_qwen3_vl else settings.caption_mock_json_path,
        )
        self.qwen_caption_provider = self._build_qwen_caption_provider(settings)
        self.image_diagnoser = self._build_image_diagnoser(settings)
        llm_client = build_llm_client(settings)
        agent_model_routing = build_agent_model_routing(settings)
        self.orchestrator = MultiAgentOrchestrator(
            llm_client=llm_client,
            agent_model_routing=agent_model_routing,
            max_retries=settings.max_expert_retries,
            timeout=settings.request_timeout,
            strict_real_output=settings.strict_real_output,
            max_parallel_agents_per_layer=settings.max_parallel_agents_per_layer,
            max_concurrency_per_route=settings.max_concurrency_per_route,
            structured_max_new_tokens=settings.local_llm_structured_max_new_tokens,
            report_max_new_tokens=settings.local_llm_report_max_new_tokens,
        )
        self._migrate_legacy_cases_if_needed()

    def run(
        self,
        problem_name: str,
        case_text: str,
        stage: str = "initial",
        image_bytes: bytes | None = None,
        n_rounds: int | None = None,
    ) -> dict[str, Any]:
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        rounds_to_use = n_rounds or self.settings.n_rounds

        input_payload = {
            "run_id": run_id,
            "problem_name": problem_name,
            "case_text": case_text,
            "stage": stage,
            "n_rounds": rounds_to_use,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            image_analysis = self._analyze_image(image_bytes=image_bytes)
            slot_extraction = self._extract_slot_extraction(case_text=case_text, image_bytes=image_bytes)
            caption = self._build_caption(
                case_text=case_text,
                image_bytes=image_bytes,
                image_analysis=image_analysis,
                slot_extraction=slot_extraction,
            )
            caption_data = localize_caption_payload(caption.model_dump(mode="json"))
            image_display = build_image_analysis_display(image_analysis) if image_analysis else {}
            vision_result = (
                build_vision_result(
                    slot_extraction=slot_extraction,
                    image_analysis=image_analysis,
                    display=image_display,
                    caption=caption_data,
                )
                if image_analysis is not None or slot_extraction is not None
                else None
            )

            query = f"{problem_name}\n{case_text}\n{self.retriever.build_signature(caption)}"
            verified_records = self.case_library.retrieve_text(query, verified=True, k=6)
            unverified_records = self.case_library.retrieve_text(query, verified=False, k=4)
            document_records = self.kb.retrieve_documents(query, k=4)
            kb_evidence = self.retriever.retrieve(
                caption=caption,
                candidates=verified_records + unverified_records + document_records,
                k=4,
            )

            raw_result = self.orchestrator.run(
                case_text=case_text,
                caption=caption,
                kb_evidence=kb_evidence,
                n_rounds=rounds_to_use,
                vision_result=vision_result,
            )
            return self._finalize_and_save(
                run_id=run_id,
                problem_name=problem_name,
                case_text=case_text,
                stage=stage,
                input_payload=input_payload,
                image_bytes=image_bytes,
                caption=caption,
                caption_data=caption_data,
                image_analysis=image_analysis,
                image_display=image_display,
                vision_result=vision_result,
                slot_extraction=slot_extraction,
                kb_evidence=kb_evidence,
                raw_result=raw_result,
            )
        except RealOutputRequiredError as err:
            self._save_error_log(
                error=err,
                problem_name=problem_name,
                case_text=case_text,
                stage=stage,
            )
            raise

    def run_stream(
        self,
        problem_name: str,
        case_text: str,
        stage: str = "initial",
        image_bytes: bytes | None = None,
        n_rounds: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        rounds_to_use = n_rounds or self.settings.n_rounds

        input_payload = {
            "run_id": run_id,
            "problem_name": problem_name,
            "case_text": case_text,
            "stage": stage,
            "n_rounds": rounds_to_use,
            "timestamp": datetime.now().isoformat(),
        }
        yield {
            "type": "run_started",
            "run_id": run_id,
            "problem_name": problem_name,
            "case_text": case_text,
            "stage": stage,
            "n_rounds": rounds_to_use,
        }
        if image_bytes:
            yield {
                "type": "image_processing_started",
                "run_id": run_id,
                "message": "已接收图片，正在执行 Qwen3-VL 槽位抽取和 DINOv3 分类分割。",
            }

        try:
            image_analysis = self._analyze_image(image_bytes=image_bytes)
            slot_extraction = self._extract_slot_extraction(case_text=case_text, image_bytes=image_bytes)
            caption = self._build_caption(
                case_text=case_text,
                image_bytes=image_bytes,
                image_analysis=image_analysis,
                slot_extraction=slot_extraction,
            )
            caption_data = localize_caption_payload(caption.model_dump(mode="json"))
            image_display = build_image_analysis_display(image_analysis) if image_analysis else {}
            vision_result = (
                build_vision_result(
                    slot_extraction=slot_extraction,
                    image_analysis=image_analysis,
                    display=image_display,
                    caption=caption_data,
                )
                if image_analysis is not None or slot_extraction is not None
                else None
            )
            yield {
                "type": "caption_ready",
                "run_id": run_id,
                "caption": caption_data,
                "slot_extraction": slot_extraction or {},
                "image_analysis": image_analysis or {},
                "image_analysis_display": image_display,
                "vision_result": vision_result,
            }
            if slot_extraction is not None:
                yield {"type": "slot_extraction_ready", "run_id": run_id, "slot_extraction": slot_extraction}
            if image_analysis is not None:
                yield {
                    "type": "image_analysis_ready",
                    "run_id": run_id,
                    "image_analysis": image_analysis,
                    "display": image_display,
                }

            query = f"{problem_name}\n{case_text}\n{self.retriever.build_signature(caption)}"
            verified_records = self.case_library.retrieve_text(query, verified=True, k=6)
            unverified_records = self.case_library.retrieve_text(query, verified=False, k=4)
            document_records = self.kb.retrieve_documents(query, k=4)
            kb_evidence = self.retriever.retrieve(
                caption=caption,
                candidates=verified_records + unverified_records + document_records,
                k=4,
            )
            yield {
                "type": "kb_ready",
                "run_id": run_id,
                "kb_evidence_count": len(kb_evidence),
                "kb_evidence": kb_evidence,
            }

            raw_result: dict[str, Any] | None = None
            for event in self.orchestrator.run_iter(
                case_text=case_text,
                caption=caption,
                kb_evidence=kb_evidence,
                n_rounds=rounds_to_use,
                vision_result=vision_result,
            ):
                if event.get("type") == "orchestrator_complete":
                    result = event.get("result")
                    if isinstance(result, dict):
                        raw_result = result
                    continue
                event["run_id"] = run_id
                yield event

            if not isinstance(raw_result, dict):
                raise RealOutputRequiredError(
                    stage="orchestrator_complete",
                    agent_name="system",
                    provider="",
                    model="",
                    reason="编排器未产出最终结果",
                    raw_error_type="RuntimeError",
                )

            yield {"type": "reports_started", "run_id": run_id}
            result = self._finalize_and_save(
                run_id=run_id,
                problem_name=problem_name,
                case_text=case_text,
                stage=stage,
                input_payload=input_payload,
                image_bytes=image_bytes,
                caption=caption,
                caption_data=caption_data,
                image_analysis=image_analysis,
                image_display=image_display,
                vision_result=vision_result,
                slot_extraction=slot_extraction,
                kb_evidence=kb_evidence,
                raw_result=raw_result,
            )
            yield {
                "type": "reports_ready",
                "run_id": run_id,
                "multi_agent_meta": result["reports"].get("multi_agent_meta", {}),
                "baseline_meta": result["reports"].get("baseline_meta", {}),
            }
            yield {"type": "complete", "run_id": run_id, "result": result}
        except RealOutputRequiredError as err:
            self._save_error_log(
                error=err,
                problem_name=problem_name,
                case_text=case_text,
                stage=stage,
            )
            yield {"type": "error", "run_id": run_id, "detail": err.to_detail()}
        except Exception as err:  # noqa: BLE001
            detail = {
                "code": "PIPELINE_STREAM_ERROR",
                "stage": "run_stream",
                "agent_name": "system",
                "provider": "",
                "model": "",
                "message": str(err),
                "error_type": type(err).__name__,
            }
            yield {"type": "error", "run_id": run_id, "detail": detail}

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.run_store.list_runs(limit=limit)

    def list_cases(self) -> dict[str, Any]:
        return self.case_library.load_all_cases()

    def delete_case(self, run_id: str) -> dict[str, Any]:
        removed = self.case_library.delete_by_run_id(run_id)
        if int(removed.get("removed_total", 0)) <= 0:
            raise FileNotFoundError(run_id)
        return {
            "ok": True,
            "run_id": run_id,
            **removed,
        }

    def delete_run(self, run_id: str) -> dict[str, Any]:
        removed_run = self.run_store.delete_run(run_id)
        removed_cases = self.case_library.delete_by_run_id(run_id)
        if not removed_run:
            raise FileNotFoundError(run_id)
        return {
            "ok": True,
            "run_id": run_id,
            "removed_case_records": removed_cases.get("removed_total", 0),
        }

    def load_final(self, run_id: str) -> dict[str, Any]:
        return self.run_store.load_json(run_id, "final.json")

    def load_trace(self, run_id: str) -> dict[str, Any]:
        return self.run_store.load_json(run_id, "trace.json")

    def clear_knowledge_base(self, target: str = "all") -> dict[str, Any]:
        return self.kb.clear_cases(target=target)

    def inspect_image(self, image_bytes: bytes, case_text: str = "") -> dict[str, Any]:
        image_analysis = self._analyze_image(image_bytes=image_bytes)
        if image_analysis is None:
            raise RuntimeError("本地 DINOv3 图像分析不可用")
        slot_extraction = self._extract_slot_extraction(case_text=case_text, image_bytes=image_bytes)
        caption = self._build_caption(
            case_text=case_text,
            image_bytes=image_bytes,
            image_analysis=image_analysis,
            slot_extraction=slot_extraction,
        )
        caption_data = localize_caption_payload(caption.model_dump(mode="json"))
        display = build_image_analysis_display(image_analysis)
        vision_result = build_vision_result(
            slot_extraction=slot_extraction,
            image_analysis=image_analysis,
            display=display,
            caption=caption_data,
        )
        return {
            "slot_extraction": slot_extraction or {},
            "image_analysis": image_analysis,
            "display": display,
            "caption": caption_data,
            "vision_result": vision_result,
        }

    def _build_qwen_caption_provider(self, settings: Settings) -> LocalQwen3VLCaptionProvider | None:
        if not settings.enable_local_qwen3_vl:
            return None
        provider = LocalQwen3VLCaptionProvider(
            model_dir=settings.qwen3_vl_model_dir,
            max_new_tokens=settings.qwen3_vl_max_new_tokens,
            prefer_cuda=True,
            timeout=settings.request_timeout,
        )
        return provider if provider.is_available() else None

    def _build_image_diagnoser(self, settings: Settings) -> LocalDinoV3Diagnoser | None:
        if not settings.enable_local_dinov3:
            return None
        classifier_classes: tuple[str, ...] = ()
        raw_classifier_classes = settings.dinov3_classifier_classes_json.strip()
        if raw_classifier_classes:
            parsed = json.loads(raw_classifier_classes)
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise RuntimeError("DINOV3_CLASSIFIER_CLASSES_JSON 必须是字符串数组 JSON")
            classifier_classes = tuple(item.strip() for item in parsed if item.strip())
        return LocalDinoV3Diagnoser(
            DinoV3Paths(
                repo_dir=Path(settings.dinov3_repo_dir),
                backbone_weights=Path(settings.dinov3_backbone_weights),
                classifier_head_weights=Path(settings.dinov3_classifier_head_weights),
                segmentation_head_weights=Path(settings.dinov3_segmentation_head_weights),
                classes_file=Path(settings.dinov3_classes_file),
                classifier_classes=classifier_classes,
                image_size=settings.dinov3_image_size,
                segmentation_threshold=settings.dinov3_segmentation_threshold,
                prefer_cuda=True,
            )
        )

    def _migrate_legacy_cases_if_needed(self) -> None:
        current_cases = self.case_library.load_all_cases()
        if current_cases.get("total_verified", 0) or current_cases.get("total_unverified", 0):
            return

        legacy_verified = self.kb.load_cases(verified=True)
        legacy_unverified = self.kb.load_cases(verified=False)
        if not legacy_verified and not legacy_unverified:
            return

        for item in legacy_verified:
            if isinstance(item, dict):
                self.case_library.save_case(item, verified=True)
        for item in legacy_unverified:
            if isinstance(item, dict):
                self.case_library.save_case(item, verified=False)

    def _analyze_image(self, image_bytes: bytes | None) -> dict[str, Any] | None:
        if not image_bytes or self.image_diagnoser is None:
            return None
        if not self.image_diagnoser.is_available():
            return None
        return self.image_diagnoser.analyze_image_bytes(image_bytes)

    def _extract_slot_extraction(
        self,
        *,
        case_text: str,
        image_bytes: bytes | None,
    ) -> dict[str, Any] | None:
        if not image_bytes or self.qwen_caption_provider is None:
            return None
        try:
            return self.qwen_caption_provider.extract_slots(case_text=case_text, image_bytes=image_bytes)
        except Exception:
            return None

    def _build_caption(
        self,
        case_text: str,
        image_bytes: bytes | None,
        image_analysis: dict[str, Any] | None = None,
        slot_extraction: dict[str, Any] | None = None,
    ) -> CaptionSchema:
        if slot_extraction is not None and self.qwen_caption_provider is not None:
            fallback_caption = self.qwen_caption_provider.caption_from_slots(slot_extraction, case_text=case_text)
        elif image_analysis is None:
            return self.placeholder_caption_provider.predict(case_text=case_text, image_bytes=image_bytes)
        else:
            fallback_caption = self.placeholder_caption_provider.predict(case_text=case_text, image_bytes=None)
        if image_analysis is None:
            return fallback_caption
        return build_caption_from_dinov3_analysis(
            case_text=case_text,
            image_analysis=image_analysis,
            fallback_caption=fallback_caption,
        )

    def _finalize_and_save(
        self,
        run_id: str,
        problem_name: str,
        case_text: str,
        stage: str,
        input_payload: dict[str, Any],
        image_bytes: bytes | None,
        caption: CaptionSchema,
        caption_data: dict[str, Any],
        image_analysis: dict[str, Any] | None,
        image_display: dict[str, Any] | None,
        vision_result: dict[str, Any] | None,
        slot_extraction: dict[str, Any] | None,
        kb_evidence: list[dict[str, Any]],
        raw_result: dict[str, Any],
    ) -> dict[str, Any]:
        clean_trace = sanitize_trace(raw_result)
        clean_trace["caption"] = caption_data
        if slot_extraction is not None:
            clean_trace["slot_extraction"] = slot_extraction
        if image_analysis is not None:
            clean_trace["image_analysis"] = image_analysis
            clean_trace["image_analysis_display"] = image_display or build_image_analysis_display(image_analysis)
        if vision_result is not None:
            clean_trace["vision_result"] = vision_result
        if isinstance(raw_result.get("decision_packet"), dict):
            clean_trace["decision_packet"] = raw_result["decision_packet"]
        clean_trace["kb_evidence"] = kb_evidence
        safety_payload = raw_result.get(
            "safety",
            {
                "safety_passed": True,
                "flags": [],
                "revised_actions": [],
                "action_level": "fully_supported",
                "review_summary": "",
                "prohibited_actions": [],
                "required_followups": [],
                "evidence_sufficiency": "",
            },
        )
        if self.settings.strict_real_output:
            self._assert_trace_real_output(clean_trace)

        top_nm = str(clean_trace.get("final", {}).get("top_diagnosis", {}).get("name", "") or "").strip()
        kb_query = f"{top_nm}\n{case_text}"[:600].strip()
        kb_docs = self.kb.retrieve_documents(kb_query, k=3) if kb_query else []

        reports_bundle = self.orchestrator.generate_reports(
            case_text=case_text,
            caption=caption,
            kb_evidence=kb_evidence,
            rounds=clean_trace["rounds"],
            final_result=clean_trace["final"],
            safety_result=safety_payload,
            vision_result=vision_result,
            image_bytes=image_bytes,
            kb_documents=kb_docs,
        )
        report_quality_issues = self._collect_report_quality_issues(
            multi_agent_markdown=reports_bundle["multi_agent_markdown"],
            baseline_markdown=reports_bundle["baseline_markdown"],
            baseline_error=reports_bundle.get("baseline_error"),
        )

        clean_trace["report_meta"] = {
            "multi_agent_meta": reports_bundle["multi_agent_meta"],
            "baseline_meta": reports_bundle["baseline_meta"],
            "quality_issues": report_quality_issues,
        }
        if isinstance(reports_bundle.get("baseline_error"), dict):
            clean_trace["report_meta"]["baseline_error"] = reports_bundle["baseline_error"]

        comparison_summary = self._build_comparison_summary(
            final_result=clean_trace["final"],
            baseline_result=reports_bundle["baseline_structured"],
        )
        reports_payload = {
            "multi_agent_markdown": reports_bundle["multi_agent_markdown"],
            "baseline_markdown": reports_bundle["baseline_markdown"],
            "multi_agent_meta": reports_bundle["multi_agent_meta"],
            "baseline_meta": reports_bundle["baseline_meta"],
            "quality_issues": report_quality_issues,
        }
        if isinstance(reports_bundle.get("baseline_error"), dict):
            reports_payload["baseline_error"] = reports_bundle["baseline_error"]
        if isinstance(reports_bundle.get("report_packet"), dict):
            reports_payload["report_packet"] = reports_bundle["report_packet"]
        final_payload = {
            "run_id": run_id,
            "problem_name": problem_name,
            "case_text": case_text,
            "stage": stage,
            **clean_trace["final"],
            "reports_ref": "reports.json",
            "reports": reports_payload,
            "comparison_summary": comparison_summary,
            "shared_state": clean_trace.get("shared_state", {}),
            "execution_meta": clean_trace.get("execution_meta", {}),
        }
        if isinstance(clean_trace.get("decision_packet"), dict):
            final_payload["decision_packet"] = clean_trace["decision_packet"]
        if isinstance(reports_bundle.get("report_packet"), dict):
            final_payload["report_packet"] = reports_bundle["report_packet"]
        if image_analysis is not None:
            final_payload["image_analysis"] = image_analysis
            final_payload["image_analysis_display"] = image_display or build_image_analysis_display(image_analysis)
        if slot_extraction is not None:
            final_payload["slot_extraction"] = slot_extraction
        if vision_result is not None:
            final_payload["vision_result"] = vision_result

        self.run_store.save_json(run_id, "input.json", input_payload)
        self.run_store.save_json(run_id, "caption.json", caption_data)
        self.run_store.save_json(run_id, "trace.json", clean_trace)
        self.run_store.save_json(run_id, "final.json", final_payload)
        self.run_store.save_json(run_id, "safety.json", safety_payload)
        self.run_store.save_json(run_id, "reports.json", reports_payload)

        case_record = self._build_case_record(
            run_id=run_id,
            problem_name=problem_name,
            case_text=case_text,
            caption_data=caption_data,
            final_payload=final_payload,
            reports_payload=reports_payload,
            safety_payload=safety_payload,
            image_display=image_display,
            vision_result=vision_result,
        )
        write_verified = self.case_library.should_write_verified(clean_trace, safety_payload)
        self.case_library.save_case(case_record, verified=write_verified)

        return {
            "run_id": run_id,
            "final": final_payload,
            "trace": clean_trace,
            "reports": reports_payload,
            "execution_meta": clean_trace.get("execution_meta", {}),
            "safety": safety_payload,
            "case_write_layer": "verified" if write_verified else "unverified",
            "knowledge_write_layer": "verified" if write_verified else "unverified",
        }

    def _build_case_record(
        self,
        *,
        run_id: str,
        problem_name: str,
        case_text: str,
        caption_data: dict[str, Any],
        final_payload: dict[str, Any],
        reports_payload: dict[str, Any],
        safety_payload: dict[str, Any],
        image_display: dict[str, Any] | None,
        vision_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        top_diagnosis = final_payload.get("top_diagnosis", {}) if isinstance(final_payload, dict) else {}
        top_name = str(top_diagnosis.get("name", "")).strip() or "未给出主诊断"
        confidence = str(top_diagnosis.get("confidence", "")).strip()
        visual_summary = str(caption_data.get("visual_summary", "")).strip()
        image_summary = ""
        if isinstance(image_display, dict):
            image_summary = str(image_display.get("摘要", "")).strip()
        conflict_summary = ""
        if isinstance(vision_result, dict):
            conflict = vision_result.get("conflict_analysis", {})
            if isinstance(conflict, dict):
                conflict_summary = str(conflict.get("reason_summary", "")).strip()

        summary_parts = [
            f"主诊断倾向：{top_name}" + (f"（置信说明：{confidence}）" if confidence else ""),
            image_summary,
            visual_summary,
            conflict_summary,
            str(final_payload.get("confidence_statement", "")).strip(),
        ]
        case_summary = " ".join(part for part in summary_parts if part)

        return {
            "run_id": run_id,
            "problem_name": problem_name,
            "case_text": case_text,
            "case_summary": case_summary,
            "caption": caption_data,
            "image_analysis_display": image_display or {},
            "top_diagnosis": top_diagnosis,
            "candidates": final_payload.get("candidates", []),
            "actions": final_payload.get("actions", []),
            "rescue_plan": final_payload.get("rescue_plan", []),
            "evidence_sufficiency": final_payload.get("evidence_sufficiency", ""),
            "confidence_statement": final_payload.get("confidence_statement", ""),
            "report_outline": final_payload.get("report_outline", []),
            "report_summary": case_summary,
            "report_excerpt": str(reports_payload.get("multi_agent_markdown", "")).strip()[:1200],
            "safety_passed": bool(safety_payload.get("safety_passed", False)),
            "timestamp": datetime.now().isoformat(),
        }

    def _assert_trace_real_output(self, trace: dict[str, Any]) -> None:
        for round_item in trace.get("rounds", []):
            for turn in round_item.get("expert_turns", []):
                if bool(turn.get("invalid_turn", False)):
                    raise RealOutputRequiredError(
                        stage="trace_validation",
                        agent_name=str(turn.get("agent_name", "")),
                        provider="",
                        model="",
                        reason="检测到 invalid_turn 标记",
                        raw_error_type="ValueError",
                    )
                meta = turn.get("meta", {})
                if not isinstance(meta, dict) or not bool(meta.get("is_real_output", False)):
                    raise RealOutputRequiredError(
                        stage="trace_validation",
                        agent_name=str(turn.get("agent_name", "")),
                        provider=str(meta.get("provider", "")) if isinstance(meta, dict) else "",
                        model=str(meta.get("model", "")) if isinstance(meta, dict) else "",
                        reason="turn 元信息缺失或无效（meta）",
                        raw_error_type="ValueError",
                    )
                for citation in turn.get("citations", []):
                    if str(citation).startswith("fallback_"):
                        raise RealOutputRequiredError(
                            stage="trace_validation",
                            agent_name=str(turn.get("agent_name", "")),
                            provider=str(meta.get("provider", "")),
                            model=str(meta.get("model", "")),
                            reason="检测到 fallback 引用标记",
                            raw_error_type="ValueError",
                        )

        top_name = str(trace.get("final", {}).get("top_diagnosis", {}).get("name", "")).strip().lower()
        if not top_name or top_name == "unknown":
            raise RealOutputRequiredError(
                stage="trace_validation",
                agent_name="coordinator_final",
                provider="",
                model="",
                reason="final.top_diagnosis.name 为空或未知",
                raw_error_type="ValueError",
            )

    def _build_comparison_summary(self, final_result: dict[str, Any], baseline_result: dict[str, Any]) -> dict[str, Any]:
        multi_top = final_result.get("top_diagnosis", {})
        baseline_top = baseline_result.get("top_diagnosis", {})
        multi_name = str(multi_top.get("name", "")).strip()
        baseline_name = str(baseline_top.get("name", "")).strip()
        return {
            "multi_agent_top_diagnosis": multi_top,
            "baseline_top_diagnosis": baseline_top,
            "same_top_diagnosis": bool(multi_name and baseline_name and multi_name == baseline_name),
        }

    def _save_error_log(
        self,
        error: RealOutputRequiredError,
        problem_name: str,
        case_text: str,
        stage: str,
    ) -> None:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "stage": error.stage or stage,
            "agent_name": error.agent_name,
            "provider": error.provider,
            "model": error.model,
            "error_type": error.raw_error_type,
            "error_message": error.reason,
            "request_timeout": self.settings.request_timeout,
            "problem_name": problem_name,
            "case_text_hash": sha256(case_text.encode("utf-8")).hexdigest(),
        }
        self.run_store.save_error_log(payload)

    @staticmethod
    def _collect_report_quality_issues(
        multi_agent_markdown: str,
        baseline_markdown: str,
        baseline_error: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        checks = [("multi_agent_markdown", multi_agent_markdown)]
        if baseline_error:
            issues.append(
                {
                    "source": "baseline_markdown",
                    "code": "BASELINE_REPORT_UNAVAILABLE",
                    "message": str(baseline_error.get("message", "")).strip() or "单模型基线报告不可用",
                }
            )
        else:
            checks.append(("baseline_markdown", baseline_markdown))
        for source, markdown in checks:
            try:
                validate_markdown_report(markdown)
            except ValueError as err:
                issues.append(
                    {
                        "source": source,
                        "code": "REPORT_QUALITY_VALIDATION_FAILED",
                        "message": str(err),
                    }
                )
        return issues
