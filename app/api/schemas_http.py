from __future__ import annotations

from pydantic import BaseModel, Field


class RunResponse(BaseModel):
    run_id: str
    knowledge_write_layer: str
    case_write_layer: str = ""
    final: dict
    reports: dict = Field(default_factory=dict)
    execution_meta: dict = Field(default_factory=dict)


class ImageProbeResponse(BaseModel):
    slot_extraction: dict = Field(default_factory=dict)
    image_analysis: dict
    display: dict = Field(default_factory=dict)
    caption: dict
    vision_result: dict = Field(default_factory=dict)


class FinalResponse(BaseModel):
    run_id: str
    final: dict


class TraceResponse(BaseModel):
    run_id: str
    trace: dict


class ClearKnowledgeRequest(BaseModel):
    target: str = "all"


class ClearKnowledgeResponse(BaseModel):
    ok: bool
    target: str
    before_verified: int
    before_unverified: int
    before_documents: int = 0
    after_verified: int
    after_unverified: int
    after_documents: int = 0
    cleared_total: int


class KnowledgeDocumentResponse(BaseModel):
    doc_id: str
    title: str
    source_name: str = ""
    content_format: str
    char_count: int
    preview: str = ""
    timestamp: str


class KnowledgeDocumentsPayload(BaseModel):
    documents: list[KnowledgeDocumentResponse] = Field(default_factory=list)
    total_documents: int = 0
