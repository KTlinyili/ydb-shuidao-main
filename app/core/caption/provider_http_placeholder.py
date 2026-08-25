from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.caption.provider_base import CaptionProvider
from app.core.caption.schema import CaptionSchema


class HttpPlaceholderCaptionProvider(CaptionProvider):
    def __init__(self, timeout: int = 30, mock_json_path: str = ""):
        self.timeout = timeout
        self.mock_json_path = mock_json_path.strip()

    def predict(self, case_text: str, image_bytes: bytes | None = None) -> CaptionSchema:
        if self.mock_json_path:
            mock_payload = self._load_mock_json()
            if isinstance(mock_payload, dict):
                try:
                    payload = self.convert_blip_output_to_caption(
                        blip_output=mock_payload,
                        case_text=case_text,
                    )
                    return CaptionSchema.model_validate(payload)
                except Exception:
                    pass

        if image_bytes:
            blip_output = self._run_blip_model(case_text=case_text, image_bytes=image_bytes)
            if isinstance(blip_output, dict):
                try:
                    payload = self.convert_blip_output_to_caption(
                        blip_output=blip_output,
                        case_text=case_text,
                    )
                    return CaptionSchema.model_validate(payload)
                except Exception:
                    pass
        return self._heuristic_caption(case_text)

    def _load_mock_json(self) -> dict[str, Any] | None:
        path = Path(self.mock_json_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                payload = json.load(f)
        except Exception:
            return None
        if isinstance(payload, dict):
            return payload
        return None

    def _run_blip_model(self, case_text: str, image_bytes: bytes) -> dict[str, Any] | None:
        # TODO: 在这里接入你的 blip.pt 推理函数，返回类似你示例中的结构化 dict。
        # 返回 None 时，系统会自动回退到占位逻辑，保证流程继续可跑。
        _ = (case_text, image_bytes)
        return None

    def convert_blip_output_to_caption(self, blip_output: dict[str, Any], case_text: str) -> dict[str, Any]:
        image_evidence = blip_output.get("image_evidence", {})
        lesions = image_evidence.get("lesions", []) if isinstance(image_evidence, dict) else []
        lesion_list = [item for item in lesions if isinstance(item, dict)]
        top_lesion = lesion_list[0] if lesion_list else {}

        color = self._map_list(top_lesion.get("color"), self._COLOR_MAP, default="mixed")
        tissue_state = self._map_list(top_lesion.get("tissue_state"), self._TISSUE_MAP, default="healthy")
        spot_shape = self._map_list(top_lesion.get("shape"), self._SHAPE_MAP, default="irregular")
        boundary = self._map_list(top_lesion.get("boundary"), self._BOUNDARY_MAP, default="no_clear_boundary")
        distribution_position = self._map_list(
            top_lesion.get("distribution_position"),
            self._POSITION_MAP,
            default="whole_plant",
        )
        distribution_pattern = self._map_list(
            top_lesion.get("distribution_pattern"),
            self._PATTERN_MAP,
            default="scattered",
        )

        leaf_level = blip_output.get("leaf_level", {})
        morph_change = self._map_list(
            leaf_level.get("morph_change") if isinstance(leaf_level, dict) else None,
            self._MORPH_MAP,
            default="none",
        )
        pest_cues = self._map_list(
            leaf_level.get("pest_or_mechanical_hint") if isinstance(leaf_level, dict) else None,
            self._PEST_MAP,
            default="no_obvious_pest",
        )

        farmer_text = blip_output.get("farmer_text", {})
        co_signs_raw: list[str] = []
        if isinstance(farmer_text, dict):
            co_signs_raw.extend(self._as_list(farmer_text.get("location")))
            co_signs_raw.extend(self._as_list(farmer_text.get("watering")))
        co_signs = self._map_list(co_signs_raw, self._COSIGN_MAP, default="unknown")

        area_values: list[float] = []
        conf_values: list[float] = []
        for lesion in lesion_list:
            area = lesion.get("area_ratio")
            if isinstance(area, (int, float)):
                area_values.append(float(area))
            lesion_conf = lesion.get("confidence")
            if isinstance(lesion_conf, dict):
                for value in lesion_conf.values():
                    if isinstance(value, (int, float)):
                        conf_values.append(float(value))
            elif isinstance(lesion_conf, (int, float)):
                conf_values.append(float(lesion_conf))

        area_ratio = self._clamp(sum(area_values) / len(area_values) if area_values else 0.12)
        confidence = self._clamp(sum(conf_values) / len(conf_values) if conf_values else 0.7)
        severity_score = self._clamp(max(area_ratio * 2.2, confidence * 0.65))

        uncertainty_flags = []
        if isinstance(leaf_level, dict):
            uncertainty_flags = [str(x) for x in leaf_level.get("uncertainty_flags", []) if isinstance(x, str)]
        ood_score = self._clamp(0.1 + 0.15 * len(uncertainty_flags))
        followup_questions = [
            f"请复核以下不确定信息：{flag}" for flag in uncertainty_flags if flag.strip()
        ][:3]

        evidence_refs = [
            f"image_lesion:{str(lesion.get('lesion_id')).strip()}"
            for lesion in lesion_list
            if str(lesion.get("lesion_id", "")).strip()
        ]
        if not evidence_refs:
            evidence_refs = ["image_evidence:pending"]

        visual_summary = (
            f"BLIP识别到叶片病斑，主症状为颜色{','.join(color)}、组织状态{','.join(tissue_state)}，"
            f"分布位置{','.join(distribution_position)}，模式{','.join(distribution_pattern)}。"
        )

        return {
            "visual_summary": visual_summary,
            "symptoms": {
                "color": color,
                "tissue_state": tissue_state,
                "spot_shape": spot_shape,
                "boundary": boundary,
                "distribution_position": distribution_position,
                "distribution_pattern": distribution_pattern,
                "morph_change": morph_change,
                "pest_cues": pest_cues,
                "co_signs": co_signs,
            },
            "numeric": {"area_ratio": area_ratio, "severity_score": severity_score},
            "confidence": confidence,
            "ood_score": ood_score,
            "followup_questions": followup_questions,
            "evidence_refs": evidence_refs,
        }

    def _heuristic_caption(self, case_text: str) -> CaptionSchema:
        text = case_text.lower()
        area_ratio = 0.15
        severity_score = 0.4
        confidence = 0.62
        ood = 0.2

        color = ["yellow"]
        tissue = ["chlorosis"]
        shape = ["irregular"]
        boundary = ["blurred"]
        position = ["lower_leaf"]
        pattern = ["expanding"]
        morph = ["curling"]
        pest = ["no_obvious_pest"]
        cosigns = ["unknown"]

        if "霉" in case_text or "mold" in text:
            tissue = ["mold"]
            color = ["gray"]
        if "坏死" in case_text or "black" in text or "褐" in case_text:
            tissue = ["necrosis"]
            color = ["brown"]
            boundary = ["dark_ring"]
            severity_score = 0.55
        if "叶背" in case_text:
            position = ["leaf_back"]
        if "高湿" in case_text or "湿度" in case_text or "雨" in case_text:
            cosigns = ["humidity_high", "rainy_weather"]
        if "通风不足" in case_text or "poor ventilation" in text:
            cosigns.append("poor_ventilation")
        if "浇水偏大" in case_text or "overwater" in text:
            cosigns.append("overwatering")
        if "邻棚" in case_text or "neighboring" in text:
            cosigns.append("neighboring_outbreak")

        payload = {
            "visual_summary": "水稻疑似病虫害，可见异常症状有扩展趋势。",
            "symptoms": {
                "color": color,
                "tissue_state": tissue,
                "spot_shape": shape,
                "boundary": boundary,
                "distribution_position": position,
                "distribution_pattern": pattern,
                "morph_change": morph,
                "pest_cues": pest,
                "co_signs": sorted(set(cosigns)),
            },
            "numeric": {"area_ratio": area_ratio, "severity_score": severity_score},
            "confidence": confidence,
            "ood_score": ood,
            "followup_questions": [
                "请补充叶背近景图片。",
                "请补充整株图片。",
                "是否观察到黑色虫粪或虫害痕迹？",
            ],
            "evidence_refs": ["image_evidence:pending"],
        }
        return CaptionSchema.model_validate(payload)

    @staticmethod
    def _as_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return []

    @classmethod
    def _map_list(cls, value: Any, mapping: dict[str, str], default: str) -> list[str]:
        values = cls._as_list(value)
        if not values:
            return [default]
        mapped: list[str] = []
        for raw in values:
            norm = raw.strip().lower()
            converted = mapping.get(norm, mapping.get(raw.strip(), default))
            mapped.append(converted)
        unique = sorted(set(mapped))
        return unique or [default]

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    _COLOR_MAP = {
        "green": "green",
        "yellow": "yellow",
        "brown": "brown",
        "black": "black",
        "gray": "gray",
        "white": "white",
        "mixed": "mixed",
        "黄化": "yellow",
        "黄": "yellow",
        "褐变": "brown",
        "褐色": "brown",
        "黑色": "black",
        "灰霉": "gray",
        "灰色": "gray",
        "白色": "white",
    }

    _TISSUE_MAP = {
        "healthy": "healthy",
        "chlorosis": "chlorosis",
        "necrosis": "necrosis",
        "mold": "mold",
        "water_soaked": "water_soaked",
        "dry": "dry",
        "健康": "healthy",
        "失绿": "chlorosis",
        "坏死": "necrosis",
        "霉层": "mold",
        "水渍状": "water_soaked",
        "干枯": "dry",
    }

    _SHAPE_MAP = {
        "round": "round",
        "irregular": "irregular",
        "angular": "angular",
        "concentric": "concentric",
        "diffuse": "diffuse",
        "圆形": "round",
        "不规则": "irregular",
        "角斑": "angular",
        "同心轮纹/靶斑": "concentric",
        "同心轮纹": "concentric",
        "弥散": "diffuse",
    }

    _BOUNDARY_MAP = {
        "clear": "clear",
        "blurred": "blurred",
        "yellow_halo": "yellow_halo",
        "dark_ring": "dark_ring",
        "no_clear_boundary": "no_clear_boundary",
        "清晰": "clear",
        "模糊": "blurred",
        "黄色晕圈": "yellow_halo",
        "深色环": "dark_ring",
        "无明显边界": "no_clear_boundary",
    }

    _POSITION_MAP = {
        "lower_leaf": "lower_leaf",
        "upper_leaf": "upper_leaf",
        "leaf_back": "leaf_back",
        "leaf_edge": "leaf_edge",
        "stem": "stem",
        "fruit": "fruit",
        "whole_plant": "whole_plant",
        "中下部叶片": "lower_leaf",
        "上部叶片": "upper_leaf",
        "叶背": "leaf_back",
        "叶缘": "leaf_edge",
        "茎": "stem",
        "果实": "fruit",
        "整株": "whole_plant",
    }

    _PATTERN_MAP = {
        "scattered": "scattered",
        "clustered": "clustered",
        "vein_aligned": "vein_aligned",
        "expanding": "expanding",
        "patchy": "patchy",
        "散在": "scattered",
        "簇状": "clustered",
        "沿脉": "vein_aligned",
        "扩展": "expanding",
        "片状": "patchy",
    }

    _MORPH_MAP = {
        "curling": "curling",
        "wilting": "wilting",
        "deformation": "deformation",
        "thickening": "thickening",
        "none": "none",
        "卷曲": "curling",
        "萎蔫": "wilting",
        "畸形": "deformation",
        "增厚": "thickening",
        "无": "none",
    }

    _PEST_MAP = {
        "insect_holes": "insect_holes",
        "frass": "frass",
        "webbing": "webbing",
        "eggs": "eggs",
        "no_obvious_pest": "no_obvious_pest",
        "虫孔": "insect_holes",
        "虫粪": "frass",
        "网丝": "webbing",
        "虫卵": "eggs",
        "无": "no_obvious_pest",
    }

    _COSIGN_MAP = {
        "humidity_high": "humidity_high",
        "poor_ventilation": "poor_ventilation",
        "overwatering": "overwatering",
        "rainy_weather": "rainy_weather",
        "neighboring_outbreak": "neighboring_outbreak",
        "unknown": "unknown",
        "greenhouse": "humidity_high",
        "recently increased": "overwatering",
    }
