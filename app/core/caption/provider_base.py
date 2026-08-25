from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.caption.schema import CaptionSchema


class CaptionProvider(ABC):
    @abstractmethod
    def predict(self, case_text: str, image_bytes: bytes | None = None) -> CaptionSchema:
        raise NotImplementedError

