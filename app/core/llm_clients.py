from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

from app.core.config import Settings


@dataclass(frozen=True)
class LLMRoute:
    provider: str
    model: str
    adapter_model: str = ""
    client_name: str = ""


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    request_id: str = ""
    used_fallback: bool = False


def merge_json_schema_guidance_into_messages(
    messages: list[dict[str, Any]],
    json_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """把 JSON Schema 约束并入对话，且兼容 Qwen 等 chat_template。

    若再前置一条独立的 system，会得到 [system_schema, system_task, user, ...]，
    transformers 的 Qwen3 apply_chat_template 会报 TemplateError：
    「System message must be at the beginning.」——必须把 schema 合并进**第一条** system。
    """
    guidance = (
        "你必须返回一个严格符合该 Schema 的 JSON 对象。"
        "禁止输出 Markdown，禁止附加解释文本。\n"
        f"JSON Schema:\n{json.dumps(json_schema, ensure_ascii=False)}"
    )
    if not messages:
        return [{"role": "system", "content": guidance}]
    out: list[dict[str, Any]] = [dict(m) for m in messages]
    first = out[0]
    if str(first.get("role", "")).strip().lower() == "system":
        base = str(first.get("content", "")).strip()
        out[0] = {
            **first,
            "content": (base + "\n\n" + guidance).strip() if base else guidance,
        }
        return out
    return [{"role": "system", "content": guidance}, *out]


class BaseLLMClient(ABC):
    provider_name: str

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
        model: str | None = None,
        adapter_model: str | None = None,
        max_new_tokens: int | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class OpenAICompatibleClient(BaseLLMClient):
    provider_name = "openai"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        trust_env: bool = False,
        api_key_env_name: str = "OPENAI_API_KEY",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.trust_env = trust_env
        self.api_key_env_name = api_key_env_name

    def generate(
        self,
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
        model: str | None = None,
        adapter_model: str | None = None,
        max_new_tokens: int | None = None,
    ) -> LLMResponse:
        _ = adapter_model
        _ = max_new_tokens
        model_name = (model or self.model).strip()
        if not self.api_key:
            hint = self.api_key_env_name
            if hint == "BASELINE_OPENAI_API_KEY":
                hint = "BASELINE_OPENAI_API_KEY（或兼容 OPENAI_API_KEY）"
            raise RuntimeError(f"{hint} 为空")
        if not model_name:
            raise RuntimeError("OpenAI 模型名为空")

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        normalized_schema = self._normalize_response_schema(json_schema) if json_schema else None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        used_fallback = False
        with httpx.Client(timeout=timeout, trust_env=self.trust_env) as client:
            if normalized_schema:
                payload_schema = dict(payload)
                payload_schema["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "strict": True,
                        "schema": normalized_schema,
                    },
                }
                resp = client.post(url, headers=headers, json=payload_schema)
                if resp.status_code >= 400:
                    text = resp.text.lower()
                    if (
                        resp.status_code == 400
                        and (
                            "response_format type is unavailable" in text
                            or "invalid schema for response_format" in text
                            or "invalid_json_schema" in text
                        )
                    ):
                        # Some OpenAI-compatible providers reject strict json_schema or only support json_object.
                        used_fallback = True
                        payload_json_object = dict(payload)
                        payload_json_object["response_format"] = {"type": "json_object"}
                        payload_json_object["messages"] = self._inject_schema_guidance(
                            messages=messages,
                            json_schema=normalized_schema,
                        )
                        resp = client.post(url, headers=headers, json=payload_json_object)
                if resp.status_code >= 400:
                    detail = resp.text
                    raise httpx.HTTPStatusError(
                        f"OpenAI 兼容接口返回 {resp.status_code} 错误：{detail}",
                        request=resp.request,
                        response=resp,
                    )
                data = resp.json()
                request_id = str(resp.headers.get("x-request-id", "")).strip()
            else:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    detail = resp.text
                    raise httpx.HTTPStatusError(
                        f"OpenAI 兼容接口返回 {resp.status_code} 错误：{detail}",
                        request=resp.request,
                        response=resp,
                    )
                data = resp.json()
                request_id = str(resp.headers.get("x-request-id", "")).strip()

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            content = "\n".join(parts).strip()
        text = str(content).strip()
        if not text:
            raise RuntimeError("OpenAI 返回内容为空")
        return LLMResponse(
            content=text,
            provider=self.provider_name,
            model=model_name,
            request_id=request_id,
            used_fallback=used_fallback,
        )

    @staticmethod
    def _inject_schema_guidance(
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return merge_json_schema_guidance_into_messages(messages, json_schema)

    @classmethod
    def _normalize_response_schema(cls, json_schema: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(json_schema)
        cls._normalize_response_schema_node(normalized)
        return normalized

    @classmethod
    def _normalize_response_schema_node(cls, node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            node.pop("title", None)
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties.keys())
                node.setdefault("additionalProperties", False)
            for value in node.values():
                cls._normalize_response_schema_node(value)
            return
        if isinstance(node, list):
            for item in node:
                cls._normalize_response_schema_node(item)


class OllamaClient(BaseLLMClient):
    provider_name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(
        self,
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
        model: str | None = None,
        adapter_model: str | None = None,
        max_new_tokens: int | None = None,
    ) -> LLMResponse:
        _ = adapter_model
        _ = max_new_tokens
        model_name = (model or self.model).strip()
        if not model_name:
            raise RuntimeError("Ollama 模型名为空")

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_schema:
            payload["format"] = json_schema

        url = f"{self.base_url}/api/chat"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            request_id = str(resp.headers.get("x-request-id", "")).strip()

        content = ""
        if isinstance(data.get("message"), dict):
            content = str(data["message"].get("content", "")).strip()
        if not content:
            content = str(data.get("response", "")).strip()
        if not content:
            raise RuntimeError("Ollama 返回内容为空")
        return LLMResponse(content=content, provider=self.provider_name, model=model_name, request_id=request_id)


class LocalTransformersClient(BaseLLMClient):
    provider_name = "local_transformers"

    def __init__(
        self,
        default_model_dir: str = "",
        *,
        max_new_tokens: int = 2048,
        trust_remote_code: bool = True,
        prefer_cuda: bool = True,
        device_map_mode: str = "",
        attn_implementation: str = "",
        enable_tf32: bool = True,
        enable_thinking: bool = False,
        structured_decoding_backend: str = "none",
        structured_decoding_required: bool = False,
    ):
        self.default_model_dir = default_model_dir.strip()
        self.max_new_tokens = max_new_tokens
        self.trust_remote_code = trust_remote_code
        self.prefer_cuda = prefer_cuda
        self.device_map_mode = device_map_mode.strip().lower()
        self.attn_implementation = attn_implementation.strip()
        self.enable_tf32 = enable_tf32
        self.enable_thinking = bool(enable_thinking)
        self.structured_decoding_backend = self._normalize_structured_decoding_backend(structured_decoding_backend)
        self.structured_decoding_required = structured_decoding_required
        self._lock = Lock()
        self._cache: dict[str, tuple[Any, Any, Any]] = {}

    def generate(
        self,
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
        model: str | None = None,
        adapter_model: str | None = None,
        max_new_tokens: int | None = None,
    ) -> LLMResponse:
        _ = timeout
        model_name = (model or self.default_model_dir).strip()
        adapter_name = str(adapter_model or "").strip()
        if not model_name:
            raise RuntimeError("本地 Transformers 模型路径为空")

        torch, tokenizer, local_model = self._get_or_load_model(model_name, adapter_name)
        prompt_messages = (
            merge_json_schema_guidance_into_messages(messages, json_schema) if json_schema else messages
        )
        prompt_text = self._apply_chat_template(
            tokenizer=tokenizer,
            prompt_messages=prompt_messages,
        )
        inputs = tokenizer(prompt_text, return_tensors="pt")
        input_device = self._resolve_input_device(local_model)
        if input_device is not None:
            inputs = {key: value.to(input_device) for key, value in inputs.items()}

        constraint_kwargs, constraint_warning = self._build_structured_constraint_kwargs(
            tokenizer=tokenizer,
            json_schema=json_schema,
        )
        if constraint_warning and self.structured_decoding_required:
            raise RuntimeError(constraint_warning)

        generation_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max(1, int(max_new_tokens or self.max_new_tokens)),
            "use_cache": True,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }
        generation_kwargs.update(constraint_kwargs)
        if temperature > 0.05:
            generation_kwargs["do_sample"] = True
            generation_kwargs["temperature"] = max(0.05, float(temperature))
            generation_kwargs["top_p"] = 0.95
        else:
            generation_kwargs["do_sample"] = False

        with torch.inference_mode():
            output_ids = local_model.generate(**generation_kwargs)

        generated_ids = output_ids[:, inputs["input_ids"].shape[-1] :]
        text = tokenizer.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0].strip()
        if not text:
            raise RuntimeError("本地 Transformers 返回内容为空")
        return LLMResponse(
            content=text,
            provider=self.provider_name,
            model=model_name if not adapter_name else f"{model_name}::{adapter_name}",
            used_fallback=bool(constraint_warning),
        )

    def _apply_chat_template(
        self,
        *,
        tokenizer: Any,
        prompt_messages: list[dict[str, Any]],
    ) -> str:
        """Qwen3 等模型在 transformers 中默认可能开启 thinking；通过 enable_thinking 显式关闭（与 annotate_images 一致）。"""
        kwargs: dict[str, Any] = {
            "tokenize": False,
            "add_generation_prompt": True,
        }
        try:
            sig = inspect.signature(tokenizer.apply_chat_template)
        except (TypeError, ValueError):
            sig = None
        if sig is not None:
            params = list(sig.parameters.values())
            names = {p.name for p in params}
            accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
            if "enable_thinking" in names or accepts_var_kw:
                kwargs["enable_thinking"] = self.enable_thinking
        return str(tokenizer.apply_chat_template(prompt_messages, **kwargs))

    def _get_or_load_model(self, model_name: str, adapter_model: str = "") -> tuple[Any, Any, Any]:
        model_path = str(Path(model_name))
        adapter_path = str(Path(adapter_model)).strip() if adapter_model else ""
        cache_key = self._build_cache_key(model_path, adapter_path)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            if self.enable_tf32 and torch.cuda.is_available():
                torch.backends.cuda.matmul.allow_tf32 = True
                if hasattr(torch.backends, "cudnn"):
                    torch.backends.cudnn.allow_tf32 = True

            preferred_device = torch.device("cuda" if self.prefer_cuda and torch.cuda.is_available() else "cpu")
            preferred_dtype = self._select_dtype(torch)
            device_map = self._normalize_device_map_mode(preferred_device)

            load_kwargs: dict[str, Any] = {
                "dtype": preferred_dtype,
                "low_cpu_mem_usage": True,
                "trust_remote_code": self.trust_remote_code,
            }
            if device_map is not None:
                load_kwargs["device_map"] = device_map
            if self.attn_implementation and preferred_device.type == "cuda":
                load_kwargs["attn_implementation"] = self.attn_implementation

            try:
                local_model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    **load_kwargs,
                )
            except Exception as err:
                if "attn_implementation" in load_kwargs:
                    fallback_kwargs = dict(load_kwargs)
                    fallback_kwargs.pop("attn_implementation", None)
                    try:
                        local_model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            **fallback_kwargs,
                        )
                        load_kwargs = fallback_kwargs
                    except Exception:
                        if not self._should_retry_without_device_map(err, device_map):
                            raise
                        fallback_kwargs.pop("device_map", None)
                        fallback_kwargs["low_cpu_mem_usage"] = False
                        local_model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            **fallback_kwargs,
                        )
                        device_map = None
                elif not self._should_retry_without_device_map(err, device_map):
                    raise
                else:
                    fallback_kwargs = dict(load_kwargs)
                    fallback_kwargs.pop("device_map", None)
                    fallback_kwargs["low_cpu_mem_usage"] = False
                    local_model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        **fallback_kwargs,
                    )
                    device_map = None

            if device_map is None:
                local_model.to(preferred_device)
            if adapter_path:
                local_model = self._attach_adapter(local_model=local_model, adapter_model=adapter_path)
            local_model.eval()

            tokenizer = self._load_tokenizer(
                AutoTokenizer=AutoTokenizer,
                model_path=model_path,
                adapter_path=adapter_path,
            )
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token_id = tokenizer.eos_token_id
            if tokenizer.pad_token is None and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token

            cached = (torch, tokenizer, local_model)
            self._cache[cache_key] = cached
            return cached

    @staticmethod
    def _build_cache_key(model_path: str, adapter_path: str = "") -> str:
        if adapter_path:
            return f"{model_path}::{adapter_path}"
        return model_path

    def _load_tokenizer(self, *, AutoTokenizer: Any, model_path: str, adapter_path: str = "") -> Any:
        load_errors: list[str] = []
        candidates = [adapter_path, model_path] if adapter_path else [model_path]
        for source in candidates:
            if not source:
                continue
            try:
                return AutoTokenizer.from_pretrained(
                    source,
                    trust_remote_code=self.trust_remote_code,
                    use_fast=False,
                )
            except Exception as err:  # noqa: BLE001
                load_errors.append(f"{source}: {err}")
        detail = "; ".join(load_errors) if load_errors else "没有可用 tokenizer 来源"
        raise RuntimeError(f"本地 Transformers 路由加载 tokenizer 失败（{detail}）")

    def _attach_adapter(self, *, local_model: Any, adapter_model: str) -> Any:
        adapter_path = str(Path(adapter_model)).strip()
        if not adapter_path:
            return local_model
        if not Path(adapter_path).exists():
            raise RuntimeError(f"本地 Transformers 适配器路径不存在：{adapter_path}")
        try:
            PeftModel = self._load_peft_model_class()
        except Exception as err:  # noqa: BLE001
            raise RuntimeError(
                f"加载 adapter_model“{adapter_path}”需要 PEFT，请先安装 peft。"
            ) from err
        return PeftModel.from_pretrained(local_model, adapter_path)

    @staticmethod
    def _load_peft_model_class() -> Any:
        from peft import PeftModel

        return PeftModel

    def _normalize_device_map_mode(self, preferred_device: Any) -> str | None:
        mode = self.device_map_mode
        if not mode or mode in {"none", "off", "disabled", "false"}:
            return None
        if mode in {"auto", "balanced", "balanced_low_0", "sequential"}:
            return mode
        if mode == "cuda":
            return str(preferred_device)
        if mode == "cpu":
            return "cpu"
        if mode.startswith("cuda:"):
            return mode
        return None

    @staticmethod
    def _normalize_structured_decoding_backend(raw: str) -> str:
        mode = str(raw or "").strip().lower().replace("-", "_")
        if not mode or mode in {"none", "off", "disabled", "false"}:
            return "none"
        if mode in {"auto", "lm_format_enforcer"}:
            return mode
        raise RuntimeError(
            "LOCAL_LLM_STRUCTURED_DECODING_BACKEND 必须是 none、auto、lm_format_enforcer 之一"
        )

    def _build_structured_constraint_kwargs(
        self,
        *,
        tokenizer: Any,
        json_schema: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        if not json_schema:
            return {}, ""
        backend = self.structured_decoding_backend
        if backend == "none":
            return {}, ""
        if backend in {"auto", "lm_format_enforcer"}:
            try:
                JsonSchemaParser, build_prefix_allowed_tokens_fn = self._load_lm_format_enforcer_support()
                parser = JsonSchemaParser(json_schema)
                prefix_allowed_tokens_fn = build_prefix_allowed_tokens_fn(tokenizer, parser)
            except Exception as err:  # noqa: BLE001
                return {}, f"结构化解码后端不可用：lm_format_enforcer（{err}）"
            return {
                "prefix_allowed_tokens_fn": prefix_allowed_tokens_fn,
                "renormalize_logits": True,
            }, ""
        return {}, ""

    @staticmethod
    def _load_lm_format_enforcer_support() -> tuple[Any, Any]:
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import (
            build_transformers_prefix_allowed_tokens_fn,
        )

        return JsonSchemaParser, build_transformers_prefix_allowed_tokens_fn

    @staticmethod
    def _select_dtype(torch: Any) -> Any:
        if torch.cuda.is_available():
            return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        return torch.float32

    @staticmethod
    def _should_retry_without_device_map(err: Exception, device_map: str | dict[str, Any] | None) -> bool:
        if device_map is None:
            return False
        text = str(err).lower()
        patterns = (
            "using a `device_map`",
            "using a device_map",
            "requires `accelerate`",
            "requires accelerate",
            "tp_plan",
            "device context manager",
            "torch.set_default_device",
        )
        return any(pattern in text for pattern in patterns)

    @staticmethod
    def _resolve_input_device(local_model: Any) -> Any | None:
        try:
            device = local_model.device
            if getattr(device, "type", "") != "meta":
                return device
        except Exception:
            pass
        try:
            for parameter in local_model.parameters():
                device = parameter.device
                if getattr(device, "type", "") != "meta":
                    return device
        except Exception:
            return None
        return None

class RoutedLLMClient:
    def __init__(self, providers: dict[str, BaseLLMClient], strict_real_output: bool = True):
        self.providers = providers
        self.strict_real_output = strict_real_output

    def generate(
        self,
        route: LLMRoute,
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
        max_new_tokens: int | None = None,
    ) -> LLMResponse:
        provider_name = route.provider.strip().lower()
        client_name = route.client_name.strip().lower() or provider_name
        client = self.providers.get(client_name)
        if client is None:
            raise RuntimeError(f"不支持的 provider：{route.provider}（client={client_name}）")
        response = client.generate(
            messages=messages,
            json_schema=json_schema,
            temperature=temperature,
            timeout=timeout,
            model=route.model,
            adapter_model=route.adapter_model,
            max_new_tokens=max_new_tokens,
        )
        if self.strict_real_output and not response.content.strip():
            raise RuntimeError("严格模式下模型返回为空")
        return response


MULTI_AGENT_ROUTE_KEYS = [
    "diagnosis_evidence_officer",
    "differential_officer",
    "cultivation_management_officer",
    "berry_qa_expert",
    "coordinator_round_summary",
    "coordinator_final",
    "safety_reviewer",
    "multi_agent_report_writer",
]
BASELINE_ROUTE_KEY = "baseline_single_llm"
DEFAULT_AGENT_ROUTE_KEYS = [*MULTI_AGENT_ROUTE_KEYS, BASELINE_ROUTE_KEY]


def _is_openai_compatible_provider(provider: str) -> bool:
    return provider in {"openai", "dnxapi"}


def _default_multi_agent_route(settings: Settings) -> LLMRoute:
    provider = settings.multiagent_llm.strip().lower() or "openai"
    if provider == "local_transformers":
        return LLMRoute(provider=provider, model=settings.local_llm_model_dir)
    if provider == "ollama":
        return LLMRoute(provider=provider, model=settings.ollama_model)
    if provider == "dnxapi":
        return LLMRoute(provider="dnxapi", model=settings.dnxapi_model, client_name="dnxapi")
    return LLMRoute(
        provider="openai",
        model=settings.multiagent_openai_model,
        client_name="multiagent_openai",
    )


def _default_baseline_route(settings: Settings) -> LLMRoute:
    if settings.baseline_llm_provider == "dnxapi":
        return LLMRoute(provider="dnxapi", model=settings.dnxapi_model, client_name="dnxapi")
    return LLMRoute(provider="openai", model=settings.openai_model, client_name="openai")


def _parse_routing_json(raw: str) -> dict[str, LLMRoute]:
    text = raw.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as err:
        raise RuntimeError("AGENT_MODEL_ROUTING_JSON 不是合法 JSON") from err
    if not isinstance(parsed, dict):
        raise RuntimeError("AGENT_MODEL_ROUTING_JSON 必须是 JSON 对象")

    routes: dict[str, LLMRoute] = {}
    for key, value in parsed.items():
        if not isinstance(value, dict):
            raise RuntimeError(f"{key} 的路由配置必须是对象")
        provider = str(value.get("provider", "")).strip().lower()
        model = str(value.get("model", "")).strip()
        adapter_model = str(value.get("adapter_model", "")).strip()
        client_name = str(value.get("client_name", "")).strip().lower()
        if not provider or not model:
            raise RuntimeError(f"{key} 的路由配置必须包含 provider 和 model")
        routes[str(key)] = LLMRoute(
            provider=provider,
            model=model,
            adapter_model=adapter_model,
            client_name=client_name,
        )
    return routes


def build_agent_model_routing(settings: Settings) -> dict[str, LLMRoute]:
    multi_agent_default_route = _default_multi_agent_route(settings)
    baseline_default_route = _default_baseline_route(settings)
    primary = (settings.multiagent_llm or "").strip().lower() or "openai"
    use_local_expert_paths = primary == "local_transformers"
    # 仅当整系统主路径为 local_transformers 时，才启用本地目录与 JSON 中的 local_transformers 专家路由。
    # openai / dnxapi / ollama 主路径下统一走默认 API，避免 .env 里残留的微调目录把个别专家拉回本地。
    use_local_expert_paths = primary == "local_transformers"

    routes: dict[str, LLMRoute] = {name: multi_agent_default_route for name in MULTI_AGENT_ROUTE_KEYS}
    routes[BASELINE_ROUTE_KEY] = baseline_default_route
    if use_local_expert_paths and settings.berry_qa_expert_model_dir:
        routes["berry_qa_expert"] = LLMRoute(
            provider="local_transformers",
            model=settings.berry_qa_expert_model_dir,
            adapter_model="",
        )
    custom = _parse_routing_json(settings.agent_model_routing_json)
    if not use_local_expert_paths:
        custom = {
            key: (
                route
                if key not in MULTI_AGENT_ROUTE_KEYS or route.provider != "local_transformers"
                else multi_agent_default_route
            )
            for key, route in custom.items()
        }
    routes.update(custom)

    for key in MULTI_AGENT_ROUTE_KEYS:
        route = routes.get(key)
        if route is None:
            continue
        if route.provider == "openai":
            routes[key] = LLMRoute(
                provider="openai",
                model=route.model,
                adapter_model=route.adapter_model,
                client_name="multiagent_openai",
            )
        elif route.provider == "dnxapi":
            routes[key] = LLMRoute(
                provider="dnxapi",
                model=route.model,
                adapter_model=route.adapter_model,
                client_name="dnxapi",
            )
    berry_route = routes.get("berry_qa_expert")
    if berry_route is not None:
        routes["berry_qa_expert"] = LLMRoute(
            provider=berry_route.provider,
            model=berry_route.model,
            adapter_model="",
            client_name=berry_route.client_name,
        )
    # 基线只走 baseline 专用客户端（openai），模型可来自 JSON 覆盖，缺省用 BASELINE_OPENAI_* / OPENAI_*
    bl = routes.get(BASELINE_ROUTE_KEY)
    if bl is not None and _is_openai_compatible_provider(bl.provider):
        if bl.provider == "dnxapi":
            model = (bl.model or "").strip() or settings.dnxapi_model
            routes[BASELINE_ROUTE_KEY] = LLMRoute(
                provider="dnxapi",
                model=model,
                adapter_model="",
                client_name="dnxapi",
            )
        else:
            model = (bl.model or "").strip() or settings.openai_model
            routes[BASELINE_ROUTE_KEY] = LLMRoute(
                provider="openai",
                model=model,
                adapter_model="",
                client_name="openai",
            )
    else:
        routes[BASELINE_ROUTE_KEY] = _default_baseline_route(settings)
    return routes


def build_llm_client(settings: Settings) -> RoutedLLMClient:
    multi_mode = (settings.multiagent_llm or "").strip().lower() or "openai"
    if multi_mode == "openai":
        if not settings.multiagent_openai_api_key.strip():
            raise RuntimeError(
                "MULTIAGENT_LLM=openai（或未设置 MULTIAGENT_LLM 且主路径为 openai）时，"
                "须配置 MULTIAGENT_OPENAI_API_KEY（或兼容填写 OPENAI_API_KEY）。"
                "基线单模型仅使用 BASELINE_OPENAI_* / OPENAI_*，不会自动作为多智能体 API 凭据。"
            )
    if multi_mode == "dnxapi":
        if not settings.dnxapi_api_key.strip():
            raise RuntimeError("MULTIAGENT_LLM=dnxapi 时，须配置 DNXAPI_API_KEY。")
        if not settings.dnxapi_base_url.strip():
            raise RuntimeError("MULTIAGENT_LLM=dnxapi 时，须配置 DNXAPI_BASE_URL。")
        if not settings.dnxapi_model.strip():
            raise RuntimeError("MULTIAGENT_LLM=dnxapi 时，须配置 DNXAPI_MODEL。")

    providers: dict[str, BaseLLMClient] = {
        "openai": OpenAICompatibleClient(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            trust_env=settings.openai_trust_env,
            api_key_env_name="BASELINE_OPENAI_API_KEY",
        ),
        "multiagent_openai": OpenAICompatibleClient(
            base_url=settings.multiagent_openai_base_url,
            api_key=settings.multiagent_openai_api_key,
            model=settings.multiagent_openai_model,
            trust_env=settings.multiagent_openai_trust_env,
            api_key_env_name="MULTIAGENT_OPENAI_API_KEY",
        ),
        "dnxapi": OpenAICompatibleClient(
            base_url=settings.dnxapi_base_url,
            api_key=settings.dnxapi_api_key,
            model=settings.dnxapi_model,
            trust_env=settings.dnxapi_trust_env,
            api_key_env_name="DNXAPI_API_KEY",
        ),
        "local_transformers": LocalTransformersClient(
            default_model_dir=settings.local_llm_model_dir,
            max_new_tokens=settings.local_llm_max_new_tokens,
            trust_remote_code=settings.local_llm_trust_remote_code,
            device_map_mode=settings.local_llm_device_map,
            attn_implementation=settings.local_llm_attn_implementation,
            enable_tf32=settings.local_llm_enable_tf32,
            enable_thinking=settings.local_llm_enable_thinking,
            structured_decoding_backend=settings.local_llm_structured_decoding_backend,
            structured_decoding_required=settings.local_llm_structured_decoding_required,
        ),
        "ollama": OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        ),
    }
    return RoutedLLMClient(
        providers=providers,
        strict_real_output=settings.strict_real_output,
    )
