from __future__ import annotations

import json
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import uuid4


class GovernanceKnowledgeBase:
    def __init__(self, kb_dir: str):
        self.base_dir = Path(kb_dir)
        self.verified_dir = self.base_dir / "verified"
        self.unverified_dir = self.base_dir / "unverified"
        self.documents_dir = self.base_dir / "documents"
        self.verified_file = self.verified_dir / "cases.jsonl"
        self.unverified_file = self.unverified_dir / "cases.jsonl"
        self.documents_file = self.documents_dir / "documents.jsonl"
        self.verified_dir.mkdir(parents=True, exist_ok=True)
        self.unverified_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def save_case(self, record: dict[str, Any], verified: bool) -> None:
        target = self.verified_file if verified else self.unverified_file
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_cases(self, verified: bool) -> list[dict[str, Any]]:
        source = self.verified_file if verified else self.unverified_file
        return self._load_jsonl(source)

    def save_document(
        self,
        *,
        title: str,
        content: str,
        source_name: str = "",
        content_format: str = "text",
    ) -> dict[str, Any]:
        clean_title = str(title).strip() or "未命名知识条目"
        clean_content = str(content).strip()
        if not clean_content:
            raise ValueError("文档内容为空")

        clean_format = str(content_format).strip().lower() or "text"
        if clean_format not in {"text", "md"}:
            clean_format = "text"

        preview = clean_content.replace("\r", " ").replace("\n", " ")[:220]
        record = {
            "doc_id": f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            "title": clean_title,
            "source_name": str(source_name).strip(),
            "content_format": clean_format,
            "content": clean_content,
            "char_count": len(clean_content),
            "preview": preview,
            "timestamp": datetime.now().isoformat(),
            "entry_type": "document",
        }
        with self.documents_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def load_documents(self) -> list[dict[str, Any]]:
        return self._load_jsonl(self.documents_file)

    def retrieve_documents(self, query: str, k: int = 4) -> list[dict[str, Any]]:
        documents = self.load_documents()
        scored: list[tuple[float, dict[str, Any]]] = []
        for document in documents:
            text = f"{document.get('title', '')}\n{document.get('content', '')}"
            score = SequenceMatcher(None, query, text).ratio()
            scored.append((score, document))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:k]]

    def load_all_knowledge(self) -> dict[str, Any]:
        verified = self.load_cases(verified=True)
        unverified = self.load_cases(verified=False)
        documents = self.load_documents()
        return {
            "verified": verified,
            "unverified": unverified,
            "documents": documents,
            "total_verified": len(verified),
            "total_unverified": len(unverified),
            "total_documents": len(documents),
        }

    def _load_jsonl(self, source: Path) -> list[dict[str, Any]]:
        if not source.exists():
            return []
        records: list[dict[str, Any]] = []
        with source.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    records.append(payload)
        return records

    def retrieve_text(self, query: str, verified: bool = True, k: int = 3) -> list[dict[str, Any]]:
        records = self.load_cases(verified=verified)
        scored: list[tuple[float, dict[str, Any]]] = []
        for record in records:
            text = json.dumps(record, ensure_ascii=False)
            score = SequenceMatcher(None, query, text).ratio()
            scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:k]]

    def should_write_verified(self, trace: dict[str, Any], safety: dict[str, Any]) -> bool:
        if not bool(safety.get("safety_passed", False)):
            return False

        rounds = trace.get("rounds", [])
        if not rounds:
            return False

        has_citation = False
        has_supporting_evidence = False
        for round_item in rounds:
            for turn in round_item.get("expert_turns", []):
                agent_name = str(turn.get("agent_name", "")).strip()
                if not agent_name or agent_name == "unknown":
                    continue
                if bool(turn.get("invalid_turn", False)):
                    continue

                citations = [str(x).strip() for x in turn.get("citations", []) if str(x).strip()]
                citations = [x for x in citations if not x.startswith("fallback_")]
                if citations:
                    has_citation = True
                evidence_board = turn.get("evidence_board", [])
                has_board_support = any(
                    isinstance(item, dict) and any(str(part).strip() for part in item.get("supporting", []))
                    for item in evidence_board
                )
                if turn.get("supporting_evidence") or has_board_support:
                    has_supporting_evidence = True
        return has_citation and has_supporting_evidence

    def clear_cases(self, target: str = "all") -> dict[str, int | str]:
        scope = target.strip().lower() if isinstance(target, str) else "all"
        if scope not in {"all", "verified", "unverified", "documents"}:
            raise ValueError("target 仅支持 all（全部）、verified（已核实）、unverified（待核实）、documents（知识文档）")

        before_verified = self._count_cases(self.verified_file)
        before_unverified = self._count_cases(self.unverified_file)
        before_documents = self._count_cases(self.documents_file)

        if scope in {"all", "verified"}:
            self._truncate_file(self.verified_file)
        if scope in {"all", "unverified"}:
            self._truncate_file(self.unverified_file)
        if scope in {"all", "documents"}:
            self._truncate_file(self.documents_file)

        after_verified = self._count_cases(self.verified_file)
        after_unverified = self._count_cases(self.unverified_file)
        after_documents = self._count_cases(self.documents_file)

        return {
            "target": scope,
            "before_verified": before_verified,
            "before_unverified": before_unverified,
            "before_documents": before_documents,
            "after_verified": after_verified,
            "after_unverified": after_unverified,
            "after_documents": after_documents,
            "cleared_total": (
                (before_verified - after_verified)
                + (before_unverified - after_unverified)
                + (before_documents - after_documents)
            ),
        }

    @staticmethod
    def _count_cases(source: Path) -> int:
        if not source.exists():
            return 0
        count = 0
        with source.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    @staticmethod
    def _truncate_file(source: Path) -> None:
        source.parent.mkdir(parents=True, exist_ok=True)
        with source.open("w", encoding="utf-8"):
            pass
