from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RealOutputRequiredError(RuntimeError):
    stage: str
    agent_name: str
    provider: str
    model: str
    reason: str
    raw_error_type: str = "RuntimeError"

    def __str__(self) -> str:
        return (
            f"stage={self.stage} agent={self.agent_name} provider={self.provider} "
            f"model={self.model} reason={self.reason}"
        )

    def to_detail(self) -> dict[str, str]:
        return {
            "code": "REAL_OUTPUT_REQUIRED",
            "stage": self.stage,
            "agent_name": self.agent_name,
            "provider": self.provider,
            "model": self.model,
            "message": self.reason,
            "error_type": self.raw_error_type,
        }

