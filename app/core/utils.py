from __future__ import annotations

import json
import re
from typing import Any, Dict


def extract_json_block(text: str) -> str:
    if not text:
        return ""

    fenced = re.search(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    any_fenced = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if any_fenced:
        return any_fenced.group(1).strip()

    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        return obj.group(0).strip()

    return text.strip()


def parse_json_object(text: str) -> Dict[str, Any]:
    block = extract_json_block(text)
    if not block:
        return {}
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError:
        fixed = re.sub(r",(\s*[}\]])", r"\1", block)
        parsed = json.loads(fixed)
    if isinstance(parsed, dict):
        return parsed
    return {"data": parsed}


def ensure_list_str(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    result: list[str] = []
    for item in items:
        value = str(item).strip()
        if value:
            result.append(value)
    return result

