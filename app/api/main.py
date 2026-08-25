from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes_cases import router as cases_router
from app.api.routes_diagnosis import router as diagnosis_router
from app.api.routes_knowledge import router as knowledge_router
from app.api.routes_runs import router as runs_router
from app.core.config import get_settings
from app.core.pipeline.diagnosis_pipeline import DiagnosisPipeline

APP_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = APP_ROOT / "ui" / "templates"
STATIC_DIR = APP_ROOT / "ui" / "static"
UI_VERSION_FILES = [
    TEMPLATE_DIR / "index.html",
    STATIC_DIR / "app.js",
    STATIC_DIR / "styles.css",
]

app = FastAPI(title="稻影知微水稻病虫害智能检测与预警系统")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _build_static_version() -> str:
    mtimes: list[int] = []
    for file_path in UI_VERSION_FILES:
        try:
            mtimes.append(int(file_path.stat().st_mtime))
        except FileNotFoundError:
            continue
    if not mtimes:
        return "0"
    return str(max(mtimes))


@app.on_event("startup")
def startup_event() -> None:
    settings = get_settings()
    app.state.settings = settings
    app.state.pipeline = DiagnosisPipeline(settings=settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    static_version = _build_static_version()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "static_version": static_version,
            "ui_version_text": f"v{static_version}",
        },
    )


app.include_router(diagnosis_router)
app.include_router(runs_router)
app.include_router(cases_router)
app.include_router(knowledge_router)
