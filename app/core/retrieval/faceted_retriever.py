from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Any

from app.core.caption.schema import CaptionSchema
from app.core.retrieval.reranker_client import RerankerClient


class FacetedRetriever:
    def __init__(self, reranker: RerankerClient | None = None):
        self.reranker = reranker

    def build_signature(self, caption: CaptionSchema) -> str:
        s = caption.symptoms
        return " ".join(
            [
                f"color:{','.join([x.value for x in s.color])}",
                f"tissue:{','.join([x.value for x in s.tissue_state])}",
                f"shape:{','.join([x.value for x in s.spot_shape])}",
                f"boundary:{','.join([x.value for x in s.boundary])}",
                f"position:{','.join([x.value for x in s.distribution_position])}",
                f"pattern:{','.join([x.value for x in s.distribution_pattern])}",
                f"morph:{','.join([x.value for x in s.morph_change])}",
                f"pest:{','.join([x.value for x in s.pest_cues])}",
                f"cosign:{','.join([x.value for x in s.co_signs])}",
                f"area:{caption.numeric.area_ratio:.3f}",
                f"severity:{caption.numeric.severity_score:.3f}",
            ]
        )

    def retrieve(
        self,
        caption: CaptionSchema,
        candidates: list[dict[str, Any]],
        k: int = 3,
    ) -> list[dict[str, Any]]:
        query = self.build_signature(caption)
        scored: list[tuple[float, dict[str, Any], str]] = []
        for record in candidates:
            text = json.dumps(record, ensure_ascii=False)
            score = SequenceMatcher(None, query, text).ratio()
            scored.append((score, record, text))
        scored.sort(key=lambda x: x[0], reverse=True)

        if self.reranker and scored:
            docs = [item[2] for item in scored]
            rerank_scores = self.reranker.rerank(query=query, documents=docs)
            if rerank_scores is not None and len(rerank_scores) == len(scored):
                reranked: list[tuple[float, dict[str, Any]]] = []
                for idx, (_, record, _) in enumerate(scored):
                    reranked.append((rerank_scores[idx], record))
                reranked.sort(key=lambda x: x[0], reverse=True)
                return [item[1] for item in reranked[:k]]

        return [item[1] for item in scored[:k]]

