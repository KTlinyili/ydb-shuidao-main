from __future__ import annotations

from typing import Any


_CAPTION_VALUE_CN = {
    "green": "绿色",
    "yellow": "黄化",
    "brown": "褐变",
    "black": "黑斑",
    "gray": "灰霉",
    "white": "白色霉层",
    "mixed": "混合",
    "healthy": "健康",
    "chlorosis": "黄化",
    "necrosis": "坏死",
    "mold": "霉层",
    "water_soaked": "水浸状",
    "dry": "干枯",
    "round": "圆形",
    "irregular": "不规则",
    "angular": "角斑",
    "concentric": "同心轮纹",
    "diffuse": "弥散",
    "clear": "清晰",
    "blurred": "模糊",
    "yellow_halo": "黄色晕圈",
    "dark_ring": "深色环纹",
    "no_clear_boundary": "无明显边界",
    "lower_leaf": "中下部叶片",
    "upper_leaf": "上部叶片",
    "leaf_back": "叶背",
    "leaf_edge": "叶缘",
    "stem": "茎部",
    "fruit": "果实",
    "whole_plant": "整株",
    "scattered": "散在",
    "clustered": "簇状",
    "vein_aligned": "沿叶脉",
    "expanding": "扩展",
    "patchy": "片状",
    "curling": "卷曲",
    "wilting": "萎蔫",
    "deformation": "畸形",
    "thickening": "增厚",
    "none": "无明显变化",
    "insect_holes": "虫孔",
    "frass": "虫粪",
    "webbing": "蛛网",
    "eggs": "虫卵",
    "no_obvious_pest": "无明显虫害线索",
    "humidity_high": "湿度高",
    "poor_ventilation": "通风不足",
    "overwatering": "浇水过多",
    "rainy_weather": "近期多雨",
    "neighboring_outbreak": "邻近区域疑似发病",
    "unknown": "无法判断",
}


def _to_cn(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""
    return _CAPTION_VALUE_CN.get(text, text)


def _localize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_to_cn(item) for item in values if str(item).strip()]


def localize_caption_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    symptoms = data.get("symptoms", {})
    if isinstance(symptoms, dict):
        localized_symptoms: dict[str, Any] = {}
        for key, value in symptoms.items():
            localized_symptoms[key] = _localize_list(value)
        data["symptoms"] = localized_symptoms
    return data
