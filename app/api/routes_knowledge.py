from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.schemas_http import (
    ClearKnowledgeRequest,
    ClearKnowledgeResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentsPayload,
)
from app.core.pipeline.diagnosis_pipeline import DiagnosisPipeline

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def get_pipeline(request: Request) -> DiagnosisPipeline:
    return request.app.state.pipeline


@router.get("/cases")
def list_cases(request: Request) -> dict:
    pipeline = get_pipeline(request)
    return pipeline.list_cases()


@router.get("/documents", response_model=KnowledgeDocumentsPayload)
def list_documents(request: Request) -> KnowledgeDocumentsPayload:
    pipeline = get_pipeline(request)
    documents = pipeline.kb.load_documents()
    payload = [
        KnowledgeDocumentResponse.model_validate(
            {
                "doc_id": item.get("doc_id", ""),
                "title": item.get("title", ""),
                "source_name": item.get("source_name", ""),
                "content_format": item.get("content_format", "text"),
                "char_count": int(item.get("char_count", 0)),
                "preview": item.get("preview", ""),
                "timestamp": item.get("timestamp", ""),
            }
        )
        for item in documents
    ]
    return KnowledgeDocumentsPayload(documents=payload, total_documents=len(payload))


@router.post("/upload", response_model=KnowledgeDocumentResponse)
async def upload_document(
    request: Request,
    title: str = Form(""),
    text_content: str = Form(""),
    file: UploadFile | None = File(default=None),
) -> KnowledgeDocumentResponse:
    pipeline = get_pipeline(request)
    source_name = ""
    content = str(text_content).strip()
    content_format = "text"

    if file is not None and getattr(file, "filename", None):
        source_name = str(file.filename).strip()
        suffix = source_name.rsplit(".", 1)[-1].lower() if "." in source_name else ""
        if suffix not in {"txt", "md", "markdown"}:
            raise HTTPException(status_code=400, detail="仅支持 .txt、.md、.markdown 文件")
        content_format = "md" if suffix in {"md", "markdown"} else "text"
        raw = await file.read()
        content = _decode_uploaded_text(raw)

    if not content.strip():
        raise HTTPException(status_code=400, detail="必须提供 text_content 或上传文件")

    record = pipeline.kb.save_document(
        title=title.strip() or source_name or "未命名知识条目",
        content=content,
        source_name=source_name,
        content_format=content_format,
    )
    return KnowledgeDocumentResponse.model_validate(record)


@router.post("/clear", response_model=ClearKnowledgeResponse)
def clear_knowledge(request: Request, payload: ClearKnowledgeRequest) -> ClearKnowledgeResponse:
    pipeline = get_pipeline(request)
    try:
        result = pipeline.clear_knowledge_base(target=payload.target)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return ClearKnowledgeResponse(ok=True, **result)


def _decode_uploaded_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="上传文件无法按文本格式解码")
