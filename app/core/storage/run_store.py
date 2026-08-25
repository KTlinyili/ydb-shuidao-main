from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class RunStore:
    def __init__(self, run_dir: str):
        self.base_dir = Path(run_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def run_path(self, run_id: str) -> Path:
        return self.base_dir / run_id

    def save_json(self, run_id: str, filename: str, payload: dict[str, Any]) -> Path:
        target_dir = self.run_path(run_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename
        with target_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return target_file

    def load_json(self, run_id: str, filename: str) -> dict[str, Any]:
        target_file = self.run_path(run_id) / filename
        if not target_file.exists():
            raise FileNotFoundError(str(target_file))
        with target_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"{filename} 不是 JSON 对象")
        return data

    def has_run(self, run_id: str) -> bool:
        return self.run_path(run_id).exists()

    def delete_run(self, run_id: str) -> bool:
        target = self.run_path(run_id)
        if not target.exists():
            return False
        shutil.rmtree(target)
        return True

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        """按时间倒序列出所有 run 的 input.json 摘要。"""
        runs: list[dict[str, Any]] = []
        if not self.base_dir.exists():
            return runs
        for run_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if not run_dir.is_dir() or run_dir.name.startswith("_"):
                continue
            input_file = run_dir / "input.json"
            final_file = run_dir / "final.json"
            if not input_file.exists():
                continue
            try:
                with input_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    if final_file.exists():
                        try:
                            with final_file.open("r", encoding="utf-8") as final_handle:
                                final_payload = json.load(final_handle)
                            if isinstance(final_payload, dict):
                                data["top_diagnosis"] = final_payload.get("top_diagnosis", {})
                                data["safety_passed"] = bool(final_payload.get("safety_passed", False))
                        except Exception:  # noqa: BLE001
                            pass
                    runs.append(data)
            except Exception:  # noqa: BLE001
                continue
            if len(runs) >= limit:
                break
        return runs

    def save_error_log(self, payload: dict[str, Any]) -> Path:
        log_dir = self.base_dir / "_error_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        filename = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}.json"
        target_file = log_dir / filename
        with target_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return target_file
