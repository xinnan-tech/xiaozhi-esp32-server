"""
xinnan-tech/xiaozhi-esp32-server Gemini LLM provider — rewritten to use the
new `google-genai` SDK (1.67+) instead of the legacy `google-generativeai`
(0.8.5).

Why the rewrite (vs the smaller patch we shipped earlier):

The original provider uses `google-generativeai`, whose `GenerationConfig`
dataclass has a fixed field list — it rejects both kw-arg and dict-form
`thinking_config`. So there is no way to disable Gemini 2.5/3.x Flash's
default "thinking" mode through that SDK; the model always thinks before
producing tokens, adding 3-6 seconds of TTFT in our voice pipeline.

The new `google-genai` SDK exposes `types.ThinkingConfig(thinking_budget=N)`
on `GenerateContentConfig`. Setting `thinking_budget=0` disables thinking
entirely, restoring the ~0.6 s TTFT documented by artificialanalysis.ai.

The two SDKs have similar shape but different module paths and class names,
so we keep the public interface (`LLMProvider.response`,
`response_with_functions`, `_generate`) untouched and only swap the engine
underneath. Streaming chunks expose `.text` and `.function_call` in the same
way, so the yield logic stays.

Earlier `timeout=self.timeout` kwarg issue is gone — new SDK doesn't accept
that kwarg either, and we just leave timeouts to the underlying HTTP client.
"""

import json
import os
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List

import requests
from google import genai
from google.genai import types as gtypes

from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key
from config.logger import setup_logging
from requests import RequestException

log = setup_logging()
TAG = __name__


def test_proxy(proxy_url: str, test_url: str) -> bool:
    try:
        resp = requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url})
        return 200 <= resp.status_code < 400
    except RequestException:
        return False


def setup_proxy_env(http_proxy: str | None, https_proxy: str | None):
    """Probe proxies and set HTTP(S)_PROXY env vars if they work."""
    test_http_url = "http://www.google.com"
    test_https_url = "https://www.google.com"

    ok_http = ok_https = False

    if http_proxy:
        ok_http = test_proxy(http_proxy, test_http_url)
        if ok_http:
            os.environ["HTTP_PROXY"] = http_proxy
            log.bind(tag=TAG).info(f"HTTP proxy OK: {http_proxy}")
        else:
            log.bind(tag=TAG).warning(f"HTTP proxy unreachable: {http_proxy}")

    if https_proxy:
        ok_https = test_proxy(https_proxy, test_https_url)
        if ok_https:
            os.environ["HTTPS_PROXY"] = https_proxy
            log.bind(tag=TAG).info(f"HTTPS proxy OK: {https_proxy}")
        else:
            log.bind(tag=TAG).warning(f"HTTPS proxy unreachable: {https_proxy}")

    if ok_http and not ok_https:
        if test_proxy(http_proxy, test_https_url):
            os.environ["HTTPS_PROXY"] = http_proxy
            ok_https = True
            log.bind(tag=TAG).info(f"Reusing HTTP proxy as HTTPS: {http_proxy}")

    if not ok_http and not ok_https:
        log.bind(tag=TAG).error("All Gemini proxies unreachable")
        raise RuntimeError("All Gemini proxies unreachable")


class LLMProvider(LLMProviderBase):
    """
    Uses google-genai (new SDK). Important difference from the legacy provider:
    `thinking_budget` is exposed via cfg and defaults to 0 — Gemini 2.5/3.x
    Flash default to thinking=on, which kills voice-assistant TTFT.

    Config knobs (all under LLM.GeminiLLM in .config.yaml):
        type: gemini
        model_name: gemini-2.5-flash
        api_key: AIza...
        thinking_budget: 0      # 0 = off (default), -1 = dynamic, N = budget
        temperature: 0.7
        max_output_tokens: 2048
    """

    def __init__(self, cfg: Dict[str, Any]):
        self.model_name = cfg.get("model_name", "gemini-2.5-flash")
        self.api_key = cfg["api_key"]
        http_proxy = cfg.get("http_proxy")
        https_proxy = cfg.get("https_proxy")

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            log.bind(tag=TAG).error(model_key_msg)

        if http_proxy or https_proxy:
            log.bind(tag=TAG).info("Testing Gemini proxy connectivity...")
            setup_proxy_env(http_proxy, https_proxy)

        self.client = genai.Client(api_key=self.api_key)

        thinking_budget = int(cfg.get("thinking_budget", 0))
        log.bind(tag=TAG).info(
            f"Gemini provider ready: model={self.model_name} "
            f"thinking_budget={thinking_budget}"
        )

        self.base_cfg_kwargs = dict(
            temperature=float(cfg.get("temperature", 0.7)),
            top_p=float(cfg.get("top_p", 0.9)),
            top_k=int(cfg.get("top_k", 40)),
            max_output_tokens=int(cfg.get("max_output_tokens", 2048)),
            thinking_config=gtypes.ThinkingConfig(thinking_budget=thinking_budget),
        )

    @staticmethod
    def _build_tools(funcs: List[Dict[str, Any]] | None):
        if not funcs:
            return None
        return [
            gtypes.Tool(
                function_declarations=[
                    gtypes.FunctionDeclaration(
                        name=f["function"]["name"],
                        description=f["function"]["description"],
                        parameters=f["function"]["parameters"],
                    )
                    for f in funcs
                ]
            )
        ]

    def response(self, session_id, dialogue, **kwargs):
        yield from self._generate(dialogue, None)

    def response_with_functions(self, session_id, dialogue, functions=None):
        yield from self._generate(dialogue, self._build_tools(functions))

    def _generate(self, dialogue, tools):
        role_map = {"assistant": "model", "user": "user"}
        contents: list = []

        for m in dialogue:
            r = m["role"]
            if r == "assistant" and "tool_calls" in m:
                tc = m["tool_calls"][0]
                contents.append({
                    "role": "model",
                    "parts": [{
                        "function_call": {
                            "name": tc["function"]["name"],
                            "args": json.loads(tc["function"]["arguments"]),
                        }
                    }],
                })
                continue
            if r == "tool":
                contents.append({
                    "role": "model",
                    "parts": [{"text": str(m.get("content", ""))}],
                })
                continue
            contents.append({
                "role": role_map.get(r, "user"),
                "parts": [{"text": str(m.get("content", ""))}],
            })

        cfg_kwargs = dict(self.base_cfg_kwargs)
        if tools:
            cfg_kwargs["tools"] = tools
        config = gtypes.GenerateContentConfig(**cfg_kwargs)

        stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config,
        )

        try:
            for chunk in stream:
                if not chunk.candidates:
                    continue
                cand = chunk.candidates[0]
                if not cand.content or not cand.content.parts:
                    continue
                for part in cand.content.parts:
                    if getattr(part, "function_call", None):
                        fc = part.function_call
                        yield None, [
                            SimpleNamespace(
                                id=uuid.uuid4().hex,
                                type="function",
                                function=SimpleNamespace(
                                    name=fc.name,
                                    arguments=json.dumps(
                                        dict(fc.args), ensure_ascii=False
                                    ),
                                ),
                            )
                        ]
                        return
                    if getattr(part, "text", None):
                        yield part.text if tools is None else (part.text, None)
        finally:
            if tools is not None:
                yield None, None

    @staticmethod
    def _safe_finish_stream(stream):
        """The new SDK's stream object exhausts via iteration; nothing to close."""
        try:
            for _ in stream:
                pass
        except Exception:
            pass
