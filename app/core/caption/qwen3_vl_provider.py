from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.caption.provider_base import CaptionProvider
from app.core.caption.schema import CaptionSchema


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mean(values: list[float], default: float) -> float:
    clean = [float(item) for item in values]
    if not clean:
        return default
    return sum(clean) / len(clean)


class LocalQwen3VLCaptionProvider(CaptionProvider):
    _FIELD_VOCAB = {
        "color": ["绿色", "黄化", "褐变", "黑斑", "灰霉", "白色霉层", "混合", "无法判断"],
        "tissue_state": ["健康", "黄化", "坏死", "霉层", "水浸状", "干枯", "无法判断"],
        "shape": ["圆形", "不规则", "角斑", "同心轮纹", "弥散", "无法判断"],
        "boundary": ["清晰", "模糊", "黄色晕圈", "深色环纹", "无明显边界", "无法判断"],
        "distribution_position": ["中下部叶片", "上部叶片", "叶背", "叶缘", "茎部", "果实", "整株", "无法判断"],
        "distribution_pattern": ["散在", "簇状", "沿叶脉", "扩展", "片状", "无法判断"],
        "morph_change": ["卷曲", "萎蔫", "畸形", "增厚", "无明显变化", "无法判断"],
        "pest_or_mechanical_hint": ["虫孔", "虫粪", "蛛网", "虫卵", "无明显虫害线索", "机械损伤疑似", "无法判断"],
    }

    _LEGACY_TEMPLATE_SIGNATURE = {
        "lesion": {
            "color": ("褐变", 0.91),
            "tissue_state": ("坏死", 0.88),
            "shape": ("同心轮纹", 0.82),
            "boundary": ("深色环纹", 0.77),
            "distribution_position": ("中下部叶片", 0.72),
            "distribution_pattern": ("散在", 0.70),
        },
        "leaf_level": {
            "morph_change": ("卷曲", 0.66),
            "pest_or_mechanical_hint": ("无明显虫害线索", 0.74),
            "other_visible_signs": ("无法判断", 0.20),
        },
        "uncertainty_flags": ["光照反光影响边界判断"],
    }

    _COLOR_MAP = {
        "绿色": "green",
        "黄化": "yellow",
        "褐变": "brown",
        "黑斑": "black",
        "灰霉": "gray",
        "白色霉层": "white",
        "混合": "mixed",
        "无法判断": "mixed",
    }
    _TISSUE_MAP = {
        "健康": "healthy",
        "黄化": "chlorosis",
        "坏死": "necrosis",
        "霉层": "mold",
        "水浸状": "water_soaked",
        "干枯": "dry",
        "无法判断": "healthy",
    }
    _SHAPE_MAP = {
        "圆形": "round",
        "不规则": "irregular",
        "角斑": "angular",
        "同心轮纹": "concentric",
        "弥散": "diffuse",
        "无法判断": "irregular",
    }
    _BOUNDARY_MAP = {
        "清晰": "clear",
        "模糊": "blurred",
        "黄色晕圈": "yellow_halo",
        "深色环纹": "dark_ring",
        "无明显边界": "no_clear_boundary",
        "无法判断": "no_clear_boundary",
    }
    _POSITION_MAP = {
        "中下部叶片": "lower_leaf",
        "上部叶片": "upper_leaf",
        "叶背": "leaf_back",
        "叶缘": "leaf_edge",
        "茎部": "stem",
        "果实": "fruit",
        "整株": "whole_plant",
        "无法判断": "whole_plant",
    }
    _PATTERN_MAP = {
        "散在": "scattered",
        "簇状": "clustered",
        "沿叶脉": "vein_aligned",
        "扩展": "expanding",
        "片状": "patchy",
        "无法判断": "scattered",
    }
    _MORPH_MAP = {
        "卷曲": "curling",
        "萎蔫": "wilting",
        "畸形": "deformation",
        "增厚": "thickening",
        "无明显变化": "none",
        "无法判断": "none",
    }
    _PEST_MAP = {
        "虫孔": "insect_holes",
        "虫粪": "frass",
        "蛛网": "webbing",
        "虫卵": "eggs",
        "无明显虫害线索": "no_obvious_pest",
        "机械损伤疑似": "no_obvious_pest",
        "无法判断": "no_obvious_pest",
    }

    def __init__(
        self,
        model_dir: str | Path,
        *,
        max_new_tokens: int = 512,
        prefer_cuda: bool = True,
        timeout: int = 60,
    ):
        self.model_dir = Path(model_dir)
        self.max_new_tokens = max_new_tokens
        self.prefer_cuda = prefer_cuda
        self.timeout = timeout
        self._lock = Lock()
        self._loaded = False
        self._torch: Any | None = None
        self._model: Any | None = None
        self._processor: Any | None = None
        self._Image: Any | None = None

    def is_available(self) -> bool:
        required = [
            self.model_dir,
            self.model_dir / "config.json",
            self.model_dir / "preprocessor_config.json",
            self.model_dir / "model.safetensors.index.json",
        ]
        return all(path.exists() for path in required)

    def predict(self, case_text: str, image_bytes: bytes | None = None) -> CaptionSchema:
        if not image_bytes:
            raise ValueError("LocalQwen3VLCaptionProvider 需要提供图像字节")
        slot_payload = self.extract_slots(case_text=case_text, image_bytes=image_bytes)
        return self.caption_from_slots(slot_payload, case_text=case_text)

    def extract_slots(self, case_text: str, image_bytes: bytes) -> dict[str, Any]:
        if not image_bytes:
            raise ValueError("图像字节内容为空")
        self._ensure_loaded()
        image = self._Image.open(BytesIO(image_bytes)).convert("RGB")

        parsed = self._infer_once(image=image, case_text=case_text, prompt_variant="primary")
        normalized = self._normalize_slot_payload(parsed)
        if self._looks_like_template_copy(normalized):
            retry_parsed = self._infer_once(image=image, case_text=case_text, prompt_variant="retry")
            normalized = self._normalize_slot_payload(retry_parsed)

        normalized["model_name"] = self.model_dir.name
        normalized["task"] = "berry_visible_symptom_slot_extraction"
        return normalized

    def caption_from_slots(self, slot_payload: dict[str, Any], *, case_text: str = "") -> CaptionSchema:
        lesion = self._first_lesion(slot_payload)
        leaf_level = slot_payload.get("leaf_level", {}) if isinstance(slot_payload, dict) else {}

        color, color_conf = self._map_slot(lesion, "color", self._COLOR_MAP, "mixed")
        tissue_state, tissue_conf = self._map_slot(lesion, "tissue_state", self._TISSUE_MAP, "healthy")
        spot_shape, shape_conf = self._map_slot(lesion, "shape", self._SHAPE_MAP, "irregular")
        boundary, boundary_conf = self._map_slot(lesion, "boundary", self._BOUNDARY_MAP, "no_clear_boundary")
        position, position_conf = self._map_slot(
            lesion,
            "distribution_position",
            self._POSITION_MAP,
            "whole_plant",
        )
        pattern, pattern_conf = self._map_slot(
            lesion,
            "distribution_pattern",
            self._PATTERN_MAP,
            "scattered",
        )
        morph_change, morph_conf = self._map_slot(leaf_level, "morph_change", self._MORPH_MAP, "none")
        pest_cues, pest_conf = self._map_slot(
            leaf_level,
            "pest_or_mechanical_hint",
            self._PEST_MAP,
            "no_obvious_pest",
        )

        visible_signs_obj = leaf_level.get("other_visible_signs", {}) if isinstance(leaf_level, dict) else {}
        visible_signs = self._slot_value(visible_signs_obj, default="无法判断")
        visible_signs_conf = self._slot_confidence(visible_signs_obj, default=0.2)
        uncertainty_flags = (
            [
                str(item).strip()
                for item in leaf_level.get("uncertainty_flags", [])
                if str(item).strip()
            ]
            if isinstance(leaf_level, dict)
            else []
        )

        field_confidences = [
            color_conf,
            tissue_conf,
            shape_conf,
            boundary_conf,
            position_conf,
            pattern_conf,
            morph_conf,
            pest_conf,
            visible_signs_conf,
        ]
        low_conf_count = sum(1 for value in field_confidences if value < 0.45)
        confidence = _clamp_unit(_mean(field_confidences, 0.45))
        ood_score = _clamp_unit(
            max(0.05, low_conf_count * 0.08 + len(uncertainty_flags) * 0.12 + (1 - confidence) * 0.35)
        )

        summary_parts = [
            f"颜色{self._human_value(lesion, 'color')}",
            f"组织状态{self._human_value(lesion, 'tissue_state')}",
            f"斑点形态{self._human_value(lesion, 'shape')}",
            f"边界{self._human_value(lesion, 'boundary')}",
            f"分布位置{self._human_value(lesion, 'distribution_position')}",
            f"分布模式{self._human_value(lesion, 'distribution_pattern')}",
            f"叶片形态变化{self._human_value(leaf_level, 'morph_change')}",
            f"虫害或机械损伤线索{self._human_value(leaf_level, 'pest_or_mechanical_hint')}",
        ]
        if visible_signs and visible_signs != "无法判断":
            summary_parts.append(f"其他部位以及整株伴随表现{visible_signs}")

        followup_questions = [f"请复核以下不确定信息：{flag}" for flag in uncertainty_flags]
        if low_conf_count >= 3:
            followup_questions.append("建议补充叶背近景、整株图像和不同角度清晰照片。")

        payload = {
            "visual_summary": "；".join(summary_parts) + "。",
            "symptoms": {
                "color": [color],
                "tissue_state": [tissue_state],
                "spot_shape": [spot_shape],
                "boundary": [boundary],
                "distribution_position": [position],
                "distribution_pattern": [pattern],
                "morph_change": [morph_change],
                "pest_cues": [pest_cues],
                "co_signs": ["unknown"],
            },
            "numeric": {
                "area_ratio": 0.0,
                "severity_score": _clamp_unit(max(0.12, confidence * 0.48)),
            },
            "confidence": confidence,
            "ood_score": ood_score,
            "followup_questions": list(dict.fromkeys(followup_questions))[:4],
            "evidence_refs": [
                "qwen3vl:slot_extraction",
                f"qwen3vl:model:{self.model_dir.name}",
            ],
        }
        _ = case_text
        return CaptionSchema.model_validate(payload)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            import torch
            from PIL import Image
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            if self.prefer_cuda and torch.cuda.is_available():
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            else:
                dtype = torch.float32

            model = Qwen3VLForConditionalGeneration.from_pretrained(
                self.model_dir,
                dtype=dtype,
                low_cpu_mem_usage=True,
            )
            device = torch.device("cuda" if self.prefer_cuda and torch.cuda.is_available() else "cpu")
            model.to(device)
            model.eval()
            processor = AutoProcessor.from_pretrained(self.model_dir)

            self._torch = torch
            self._model = model
            self._processor = processor
            self._Image = Image
            self._loaded = True

    def _infer_once(self, *, image: Any, case_text: str, prompt_variant: str) -> dict[str, Any]:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": self._build_prompt(case_text=case_text, prompt_variant=prompt_variant)},
                ],
            }
        ]
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self._model.device)

        with self._torch.inference_mode():
            generated_ids = self._model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
                use_cache=True,
            )
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self._processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return self._parse_json_output(output_text)

    def _build_prompt(self, *, case_text: str, prompt_variant: str) -> str:
        vocab_text = "\n".join(
            [
                f"- {field}: {', '.join(values)}"
                for field, values in self._FIELD_VOCAB.items()
            ]
        )
        retry_guard = ""
        if prompt_variant == "retry":
            retry_guard = (
                "注意：上一版回答疑似复用了模板内容。"
                "这一次禁止照抄任何示例词汇组合、固定置信度或固定 uncertainty_flags，"
                "必须重新根据当前图像逐项判断；如果证据不足，请填写“无法判断”并降低 confidence。\n\n"
            )
        case_block = ""
        if case_text.strip():
            case_block = (
                "用户补充文字仅作参考，若和图像冲突，以图像可见证据为准：\n"
                f"{case_text.strip()}\n\n"
            )
        return (
            "你是一个水稻病虫害可见症状槽位抽取助手。请根据输入图像，只做可见症状证据的结构化抽取，不做病名诊断。\n"
            "只关注当前图像真正能看见的现象，不要根据训练常识补全不可见内容。\n\n"
            f"{retry_guard}"
            f"{case_block}"
            "请从以下方面分析：\n"
            "1. 病斑层：颜色变化、组织状态、斑点形态、边界特征、分布位置、分布模式\n"
            "2. 叶片层：叶片形态变化、虫害或机械损伤线索、其他部位或整株伴随表现\n\n"
            "value 词表如下，优先从词表中选择；看不清或证据不足时填写“无法判断”：\n"
            f"{vocab_text}\n\n"
            "输出要求：\n"
            "- 只输出 JSON\n"
            "- 每个字段都输出 value 和 confidence\n"
            "- confidence 取 0 到 1 之间的小数\n"
            "- 看不清或证据不足时，value 填“无法判断”，confidence 应较低\n"
            "- 不要输出解释，不要输出 markdown，不要推断病名\n"
            "- 不要照抄模板占位词，不要复用固定置信度组合\n\n"
            "JSON 顶层必须包含两个键：image_evidence、leaf_level。\n"
            "image_evidence.lesions 必须是数组，至少包含 1 个对象；"
            "leaf_level.uncertainty_flags 必须是字符串数组。\n"
            "最终输出必须严格使用以下键结构，但 value 必须替换成真实观测结果：\n"
            "{\n"
            '  "image_evidence": {\n'
            '    "lesions": [\n'
            "      {\n"
            '        "color": {"value": "", "confidence": 0.0},\n'
            '        "tissue_state": {"value": "", "confidence": 0.0},\n'
            '        "shape": {"value": "", "confidence": 0.0},\n'
            '        "boundary": {"value": "", "confidence": 0.0},\n'
            '        "distribution_position": {"value": "", "confidence": 0.0},\n'
            '        "distribution_pattern": {"value": "", "confidence": 0.0}\n'
            "      }\n"
            "    ]\n"
            "  },\n"
            '  "leaf_level": {\n'
            '    "morph_change": {"value": "", "confidence": 0.0},\n'
            '    "pest_or_mechanical_hint": {"value": "", "confidence": 0.0},\n'
            '    "other_visible_signs": {"value": "", "confidence": 0.0},\n'
            '    "uncertainty_flags": []\n'
            "  }\n"
            "}\n"
        )

    @staticmethod
    def _parse_json_output(text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("Qwen3-VL 返回文本为空")
        cleaned = raw.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
        try:
            payload = json.loads(cleaned)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            payload = json.loads(cleaned[start : end + 1])
            if isinstance(payload, dict):
                return payload
        raise ValueError(f"无法解析 Qwen3-VL JSON 输出：{raw[:300]}")

    def _normalize_slot_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        image_evidence = payload.get("image_evidence", {}) if isinstance(payload, dict) else {}
        lesions = image_evidence.get("lesions", []) if isinstance(image_evidence, dict) else []
        first_lesion = lesions[0] if isinstance(lesions, list) and lesions else {}
        if not isinstance(first_lesion, dict):
            first_lesion = {}

        leaf_level = payload.get("leaf_level", {}) if isinstance(payload, dict) else {}
        if not isinstance(leaf_level, dict):
            leaf_level = {}

        return {
            "image_evidence": {
                "lesions": [
                    {
                        "color": self._normalize_slot_object(first_lesion.get("color"), default="无法判断"),
                        "tissue_state": self._normalize_slot_object(first_lesion.get("tissue_state"), default="无法判断"),
                        "shape": self._normalize_slot_object(first_lesion.get("shape"), default="无法判断"),
                        "boundary": self._normalize_slot_object(first_lesion.get("boundary"), default="无法判断"),
                        "distribution_position": self._normalize_slot_object(
                            first_lesion.get("distribution_position"),
                            default="无法判断",
                        ),
                        "distribution_pattern": self._normalize_slot_object(
                            first_lesion.get("distribution_pattern"),
                            default="无法判断",
                        ),
                    }
                ]
            },
            "leaf_level": {
                "morph_change": self._normalize_slot_object(leaf_level.get("morph_change"), default="无法判断"),
                "pest_or_mechanical_hint": self._normalize_slot_object(
                    leaf_level.get("pest_or_mechanical_hint"),
                    default="无法判断",
                ),
                "other_visible_signs": self._normalize_slot_object(
                    leaf_level.get("other_visible_signs"),
                    default="无法判断",
                ),
                "uncertainty_flags": [
                    str(item).strip()
                    for item in leaf_level.get("uncertainty_flags", [])
                    if str(item).strip()
                ]
                if isinstance(leaf_level.get("uncertainty_flags"), list)
                else [],
            },
        }

    def _looks_like_template_copy(self, payload: dict[str, Any]) -> bool:
        lesion = self._first_lesion(payload)
        leaf_level = payload.get("leaf_level", {}) if isinstance(payload, dict) else {}
        if not isinstance(leaf_level, dict):
            leaf_level = {}

        for key, (expected_value, expected_confidence) in self._LEGACY_TEMPLATE_SIGNATURE["lesion"].items():
            slot = lesion.get(key, {})
            if self._slot_value(slot, default="") != expected_value:
                return False
            if abs(self._slot_confidence(slot, default=-1.0) - expected_confidence) > 1e-6:
                return False

        for key, (expected_value, expected_confidence) in self._LEGACY_TEMPLATE_SIGNATURE["leaf_level"].items():
            slot = leaf_level.get(key, {})
            if self._slot_value(slot, default="") != expected_value:
                return False
            if abs(self._slot_confidence(slot, default=-1.0) - expected_confidence) > 1e-6:
                return False

        uncertainty_flags = [
            str(item).strip()
            for item in leaf_level.get("uncertainty_flags", [])
            if str(item).strip()
        ]
        return uncertainty_flags == self._LEGACY_TEMPLATE_SIGNATURE["uncertainty_flags"]

    @staticmethod
    def _normalize_slot_object(value: Any, *, default: str) -> dict[str, Any]:
        if isinstance(value, dict):
            raw_value = str(value.get("value", default)).strip() or default
            confidence = _clamp_unit(float(value.get("confidence", 0.2)))
            return {"value": raw_value, "confidence": confidence}
        if isinstance(value, str):
            raw = value.strip()
            return {"value": raw or default, "confidence": 0.45 if raw else 0.2}
        return {"value": default, "confidence": 0.2}

    @staticmethod
    def _slot_value(value: Any, *, default: str) -> str:
        if isinstance(value, dict):
            return str(value.get("value", default)).strip() or default
        if isinstance(value, str):
            return value.strip() or default
        return default

    @staticmethod
    def _slot_confidence(value: Any, *, default: float) -> float:
        if isinstance(value, dict):
            try:
                return _clamp_unit(float(value.get("confidence", default)))
            except (TypeError, ValueError):
                return default
        return default

    def _map_slot(
        self,
        parent: dict[str, Any],
        key: str,
        mapping: dict[str, str],
        default: str,
    ) -> tuple[str, float]:
        raw = parent.get(key, {}) if isinstance(parent, dict) else {}
        human_value = self._slot_value(raw, default="无法判断")
        confidence = self._slot_confidence(raw, default=0.2)
        mapped = mapping.get(human_value, default)
        if human_value == "无法判断":
            confidence = min(confidence, 0.35)
        return mapped, confidence

    def _human_value(self, parent: dict[str, Any], key: str) -> str:
        raw = parent.get(key, {}) if isinstance(parent, dict) else {}
        return self._slot_value(raw, default="无法判断")

    @staticmethod
    def _first_lesion(slot_payload: dict[str, Any]) -> dict[str, Any]:
        image_evidence = slot_payload.get("image_evidence", {}) if isinstance(slot_payload, dict) else {}
        lesions = image_evidence.get("lesions", []) if isinstance(image_evidence, dict) else []
        first = lesions[0] if isinstance(lesions, list) and lesions else {}
        return first if isinstance(first, dict) else {}
