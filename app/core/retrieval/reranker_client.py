from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class RerankerClient:
    base_url: str
    api_key: str
    model: str
    timeout: int = 30

    def is_enabled(self) -> bool:
        return bool(self.base_url.strip() and self.api_key.strip() and self.model.strip())

    def rerank(self, query: str, documents: list[str]) -> list[float] | None:
        if not self.is_enabled() or not documents:
            return None

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        scores = self._extract_scores(data, expected_len=len(documents))
        if scores is None:
            return None
        return scores

    def _extract_scores(self, data: Any, expected_len: int) -> list[float] | None:
        if not isinstance(data, dict):
            return None

        # 兼容常见返回格式：
        # - {"results":[{"index":0, "relevance_score":0.9}, ...]}
        # - {"data":[{"index":0, "score":0.9}, ...]}
        entries = data.get("results")
        if not isinstance(entries, list):
            entries = data.get("data")
        if not isinstance(entries, list):
            return None

        scores = [0.0] * expected_len
        filled = 0
        for item in entries:
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            if not isinstance(idx, int) or idx < 0 or idx >= expected_len:
                continue

            raw_score = item.get("relevance_score", item.get("score"))
            if not isinstance(raw_score, (int, float)):
                continue
            scores[idx] = float(raw_score)
            filled += 1

        if filled == 0:
            return None
        return scores
