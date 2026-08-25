from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


class CaseLibrary:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.verified_dir = self.base_dir / "verified"
        self.unverified_dir = self.base_dir / "unverified"
        self.verified_file = self.verified_dir / "cases.jsonl"
        self.unverified_file = self.unverified_dir / "cases.jsonl"
        self.verified_dir.mkdir(parents=True, exist_ok=True)
        self.unverified_dir.mkdir(parents=True, exist_ok=True)

    def save_case(self, record: dict[str, Any], verified: bool) -> None:
        target = self.verified_file if verified else self.unverified_file
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_cases(self, verified: bool) -> list[dict[str, Any]]:
        source = self.verified_file if verified else self.unverified_file
        return self._load_jsonl(source)

    def load_all_cases(self) -> dict[str, Any]:
        verified = self.load_cases(verified=True)
        unverified = self.load_cases(verified=False)
        return {
            "verified": verified,
            "unverified": unverified,
            "total_verified": len(verified),
            "total_unverified": len(unverified),
        }

    def retrieve_text(self, query: str, verified: bool = True, k: int = 3) -> list[dict[str, Any]]:
        records = self.load_cases(verified=verified)
        scored: list[tuple[float, dict[str, Any]]] = []
        for record in records:
            text = json.dumps(record, ensure_ascii=False)
            score = SequenceMatcher(None, query, text).ratio()
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
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

                citations = [str(value).strip() for value in turn.get("citations", []) if str(value).strip()]
                citations = [value for value in citations if not value.startswith("fallback_")]
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

    def delete_by_run_id(self, run_id: str) -> dict[str, int]:
        removed_verified = self._delete_from_file(self.verified_file, run_id)
        removed_unverified = self._delete_from_file(self.unverified_file, run_id)
        return {
            "removed_verified": removed_verified,
            "removed_unverified": removed_unverified,
            "removed_total": removed_verified + removed_unverified,
        }

    def _delete_from_file(self, source: Path, run_id: str) -> int:
        records = self._load_jsonl(source)
        kept: list[dict[str, Any]] = []
        removed = 0
        for item in records:
            if str(item.get("run_id", "")).strip() == run_id:
                removed += 1
                continue
            kept.append(item)
        if removed:
            self._write_jsonl(source, kept)
        return removed

    def _load_jsonl(self, source: Path) -> list[dict[str, Any]]:
        if not source.exists():
            return []
        records: list[dict[str, Any]] = []
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    records.append(payload)
        return records

    @staticmethod
    def _write_jsonl(source: Path, records: list[dict[str, Any]]) -> None:
        source.parent.mkdir(parents=True, exist_ok=True)
        with source.open("w", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
