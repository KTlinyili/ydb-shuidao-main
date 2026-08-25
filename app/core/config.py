from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _first_nonempty_env(*names: str) -> str:
    for name in names:
        raw = os.getenv(name)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return ""


def _resolve_multiagent_openai_base_url(default_openai_base: str) -> str:
    value = _first_nonempty_env(
        "MULTIAGENT_OPENAI_BASE_URL",
        "OPENAI_BASE_URL",
        "BASELINE_OPENAI_BASE_URL",
    )
    return value or default_openai_base


def _resolve_multiagent_openai_api_key() -> str:
    return _first_nonempty_env(
        "MULTIAGENT_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "BASELINE_OPENAI_API_KEY",
    )


def _resolve_multiagent_openai_model() -> str:
    value = _first_nonempty_env(
        "MULTIAGENT_OPENAI_MODEL",
        "OPENAI_MODEL",
        "BASELINE_OPENAI_MODEL",
    )
    return value or "gpt-4o-mini"


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int

    llm_primary_provider: str
    llm_fallback_provider: str
    strict_real_output: bool

    # 多智能体主路径：openai | dnxapi | local_transformers | ollama；未设时回退 LLM_PRIMARY_PROVIDER
    multiagent_llm: str
    baseline_llm_provider: str

    # 仅 baseline_single_llm（client 名 openai）。优先读 BASELINE_OPENAI_*，未设时兼容旧版 OPENAI_*
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    openai_trust_env: bool

    # 多智能体走 API 时（client 名 multiagent_openai）。只读 MULTIAGENT_OPENAI_* 与通用 OPENAI_*，绝不读 BASELINE_OPENAI_*
    multiagent_openai_base_url: str
    multiagent_openai_api_key: str
    multiagent_openai_model: str
    multiagent_openai_trust_env: bool

    # DNXAPI 采用 OpenAI-compatible 接入
    dnxapi_base_url: str
    dnxapi_api_key: str
    dnxapi_model: str
    dnxapi_trust_env: bool

    local_llm_model_dir: str
    local_llm_max_new_tokens: int
    local_llm_structured_max_new_tokens: int
    local_llm_report_max_new_tokens: int
    local_llm_trust_remote_code: bool
    local_llm_device_map: str
    local_llm_attn_implementation: str
    local_llm_enable_tf32: bool
    local_llm_enable_thinking: bool
    local_llm_structured_decoding_backend: str
    local_llm_structured_decoding_required: bool
    berry_qa_expert_model_dir: str
    berry_qa_expert_adapter_model_dir: str

    ollama_base_url: str
    ollama_model: str

    caption_mock_json_path: str
    enable_local_qwen3_vl: bool
    qwen3_vl_model_dir: str
    qwen3_vl_max_new_tokens: int
    reranker_base_url: str
    reranker_api_key: str
    reranker_model: str

    run_dir: str
    cases_dir: str
    kb_dir: str
    enable_local_dinov3: bool
    dinov3_repo_dir: str
    dinov3_backbone_weights: str
    dinov3_classifier_head_weights: str
    dinov3_segmentation_head_weights: str
    dinov3_classes_file: str
    dinov3_classifier_classes_json: str
    dinov3_image_size: int
    dinov3_segmentation_threshold: float

    request_timeout: int
    n_rounds: int
    max_expert_retries: int
    max_parallel_agents_per_layer: int
    max_concurrency_per_route: int

    enable_offline_default: bool
    agent_model_routing_json: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    model_dir = PROJECT_ROOT / "model"
    default_openai_base = "https://api.openai.com/v1"
    baseline_base = _first_nonempty_env("BASELINE_OPENAI_BASE_URL", "OPENAI_BASE_URL")
    if not baseline_base:
        baseline_base = default_openai_base
    baseline_model = _first_nonempty_env("BASELINE_OPENAI_MODEL", "OPENAI_MODEL")
    if not baseline_model:
        baseline_model = "gpt-4o-mini"
    # 多智能体 API 与基线 OPENAI_* / BASELINE_* 完全分离，禁止从 OPENAI_* 回退填充
    ma_base = _resolve_multiagent_openai_base_url(default_openai_base)
    ma_key = _resolve_multiagent_openai_api_key()
    ma_model = _resolve_multiagent_openai_model()
    return Settings(
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=_get_int("APP_PORT", 8000),
        llm_primary_provider=os.getenv("LLM_PRIMARY_PROVIDER", "openai").strip().lower(),
        llm_fallback_provider=os.getenv("LLM_FALLBACK_PROVIDER", "ollama").strip().lower(),
        strict_real_output=_get_bool("STRICT_REAL_OUTPUT", True),
        multiagent_llm=(
            os.getenv("MULTIAGENT_LLM", "").strip().lower()
            or os.getenv("LLM_PRIMARY_PROVIDER", "openai").strip().lower()
        ),
        baseline_llm_provider=os.getenv("BASELINE_LLM_PROVIDER", "openai").strip().lower(),
        openai_base_url=baseline_base,
        openai_api_key=_first_nonempty_env("BASELINE_OPENAI_API_KEY", "OPENAI_API_KEY"),
        openai_model=baseline_model,
        openai_trust_env=(
            _get_bool("BASELINE_OPENAI_TRUST_ENV", False)
            if os.getenv("BASELINE_OPENAI_TRUST_ENV") is not None
            else _get_bool("OPENAI_TRUST_ENV", False)
        ),
        multiagent_openai_base_url=ma_base,
        multiagent_openai_api_key=ma_key,
        multiagent_openai_model=ma_model,
        multiagent_openai_trust_env=_get_bool("MULTIAGENT_OPENAI_TRUST_ENV", False),
        dnxapi_base_url=os.getenv("DNXAPI_BASE_URL", "").strip(),
        dnxapi_api_key=os.getenv("DNXAPI_API_KEY", "").strip(),
        dnxapi_model=os.getenv("DNXAPI_MODEL", "").strip(),
        dnxapi_trust_env=_get_bool("DNXAPI_TRUST_ENV", False),
        local_llm_model_dir=os.getenv("LOCAL_LLM_MODEL_DIR", "").strip(),
        local_llm_max_new_tokens=_get_int("LOCAL_LLM_MAX_NEW_TOKENS", 2048),
        local_llm_structured_max_new_tokens=_get_int("LOCAL_LLM_STRUCTURED_MAX_NEW_TOKENS", 768),
        local_llm_report_max_new_tokens=_get_int("LOCAL_LLM_REPORT_MAX_NEW_TOKENS", 1400),
        local_llm_trust_remote_code=_get_bool("LOCAL_LLM_TRUST_REMOTE_CODE", True),
        local_llm_device_map=os.getenv("LOCAL_LLM_DEVICE_MAP", "").strip().lower(),
        local_llm_attn_implementation=os.getenv("LOCAL_LLM_ATTN_IMPLEMENTATION", "flash_attention_2").strip(),
        local_llm_enable_tf32=_get_bool("LOCAL_LLM_ENABLE_TF32", True),
        local_llm_enable_thinking=_get_bool("LOCAL_LLM_ENABLE_THINKING", False),
        local_llm_structured_decoding_backend=os.getenv(
            "LOCAL_LLM_STRUCTURED_DECODING_BACKEND",
            "none",
        ).strip(),
        local_llm_structured_decoding_required=_get_bool(
            "LOCAL_LLM_STRUCTURED_DECODING_REQUIRED",
            False,
        ),
        berry_qa_expert_model_dir=os.getenv("BERRY_QA_EXPERT_MODEL_DIR", "").strip(),
        berry_qa_expert_adapter_model_dir=os.getenv(
            "BERRY_QA_EXPERT_ADAPTER_MODEL_DIR",
            "",
        ).strip(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip(),
        caption_mock_json_path=os.getenv("CAPTION_MOCK_JSON_PATH", "").strip(),
        enable_local_qwen3_vl=_get_bool("ENABLE_LOCAL_QWEN3_VL", True),
        qwen3_vl_model_dir=os.getenv("QWEN3_VL_MODEL_DIR", str(model_dir / "qwen3-vl-4B")).strip(),
        qwen3_vl_max_new_tokens=_get_int("QWEN3_VL_MAX_NEW_TOKENS", 512),
        reranker_base_url=os.getenv("RERANKER_BASE_URL", "").strip(),
        reranker_api_key=os.getenv("RERANKER_API_KEY", "").strip(),
        reranker_model=os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-4B").strip(),
        run_dir=os.getenv("RUN_DIR", "runs").strip(),
        cases_dir=os.getenv("CASES_DIR", "case_library").strip(),
        kb_dir=os.getenv("KB_DIR", "knowledge_bases").strip(),
        enable_local_dinov3=_get_bool("ENABLE_LOCAL_DINOV3", True),
        dinov3_repo_dir=os.getenv("DINOV3_REPO_DIR", str(model_dir / "dinov3")).strip(),
        dinov3_backbone_weights=os.getenv(
            "DINOV3_BACKBONE_WEIGHTS",
            str(model_dir / "dinov3_vitl16_pretrain.pth"),
        ).strip(),
        dinov3_classifier_head_weights=os.getenv(
            "DINOV3_CLASSIFIER_HEAD_WEIGHTS",
            str(model_dir / "best_classifier_head.pth"),
        ).strip(),
        dinov3_segmentation_head_weights=os.getenv(
            "DINOV3_SEGMENTATION_HEAD_WEIGHTS",
            str(model_dir / "best_segmentation_head.pth"),
        ).strip(),
        dinov3_classes_file=os.getenv("DINOV3_CLASSES_FILE", str(model_dir / "classes.txt")).strip(),
        dinov3_classifier_classes_json=os.getenv("DINOV3_CLASSIFIER_CLASSES_JSON", "").strip(),
        dinov3_image_size=_get_int("DINOV3_IMAGE_SIZE", 256),
        dinov3_segmentation_threshold=_get_float("DINOV3_SEGMENTATION_THRESHOLD", 0.5),
        request_timeout=_get_int("REQUEST_TIMEOUT", 60),
        n_rounds=_get_int("N_ROUNDS", 2),
        max_expert_retries=_get_int("MAX_EXPERT_RETRIES", 2),
        max_parallel_agents_per_layer=_get_int("MAX_PARALLEL_AGENTS_PER_LAYER", 3),
        max_concurrency_per_route=_get_int("MAX_CONCURRENCY_PER_ROUTE", 2),
        enable_offline_default=_get_bool("ENABLE_OFFLINE_DEFAULT", True),
        agent_model_routing_json=os.getenv("AGENT_MODEL_ROUTING_JSON", "").strip(),
    )
