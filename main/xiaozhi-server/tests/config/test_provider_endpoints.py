"""供应器默认端点自检：防止不同 provider 的 base_url 被复制粘贴串台。

背景：``config.yaml`` 里每个 provider 的 ``base_url`` / ``url`` 都是照抄对应
厂商文档填的，很容易从相邻的 provider 直接复制粘贴。真实案例：``VLLM``
段的 ``XunfeiSparkLLM`` 抄了上面 ``LLM.DoubaoLLM`` 的火山方舟地址
（ark.cn-beijing.volces.com），选它做视觉模型时会把讯飞的 api_key 发给
火山引擎，而 ``model_name: lite`` 在那个端点上并不存在。

这里用一张「配置块 -> 端点主机名」的对照表把这类串台钉死。新增 provider
时顺手往表里加一行即可。

注意：本用例读的是仓库里**出厂的** ``config.yaml``，不是用户
``data/.config.yaml`` 合并后的结果 —— 要守的就是这份出厂默认值。
"""
from __future__ import annotations

from urllib.parse import urlparse

import pytest

from config.config_loader import get_project_dir, read_config


# (模块段, provider 名, 端点主机名里必须出现的片段)
PROVIDER_ENDPOINT_HOSTS = [
    ("LLM", "AliLLM", "dashscope.aliyuncs.com"),
    ("LLM", "AliAppLLM", "dashscope.aliyuncs.com"),
    ("LLM", "ChatGLMLLM", "bigmodel.cn"),
    ("LLM", "DeepSeekLLM", "deepseek.com"),
    ("LLM", "DifyLLM", "dify.ai"),
    ("LLM", "DoubaoLLM", "volces.com"),
    ("LLM", "VolcesAiGatewayLLM", "volces.com"),
    ("VLLM", "ChatGLMVLLM", "bigmodel.cn"),
    ("VLLM", "QwenVLVLLM", "dashscope.aliyuncs.com"),
    ("VLLM", "XunfeiSparkLLM", "xf-yun.com"),
    ("ASR", "OpenaiASR", "api.openai.com"),
    ("ASR", "GroqASR", "api.groq.com"),
    ("ASR", "Qwen3ASRFlash", "dashscope.aliyuncs.com"),
    ("TTS", "OpenAITTS", "api.openai.com"),
    ("TTS", "DoubaoTTS", "bytedance.com"),
    ("TTS", "TTS302AI", "302ai.cn"),
    ("TTS", "VolcesAiGatewayTTS", "volces.com"),
]


@pytest.fixture(scope="module")
def default_config():
    """仓库里出厂的默认配置（未经用户 data/.config.yaml 覆盖）。"""
    return read_config(get_project_dir() + "config.yaml")


def _endpoint_of(block: dict) -> str:
    """取 provider 配置块里生效的端点。

    顺序与运行时一致：``core/providers/vllm/openai.py`` 和
    ``core/providers/llm/openai/openai.py`` 都是 ``base_url`` 优先、
    ``url`` 兜底；部分 TTS 用 ``api_url``。
    """
    return block.get("base_url") or block.get("url") or block.get("api_url") or ""


@pytest.mark.parametrize(
    "module,provider,expected_host",
    PROVIDER_ENDPOINT_HOSTS,
    ids=[f"{m}.{p}" for m, p, _ in PROVIDER_ENDPOINT_HOSTS],
)
def test_provider_endpoint_matches_platform(
    default_config, module, provider, expected_host
):
    """provider 的端点必须落在它自己那家厂商的域名下。"""
    block = default_config.get(module, {}).get(provider)
    assert block is not None, f"config.yaml 里找不到 {module}.{provider} 配置块"

    endpoint = _endpoint_of(block)
    assert endpoint, f"{module}.{provider} 没有配置 base_url / url / api_url"

    host = urlparse(endpoint).netloc
    assert expected_host in host, (
        f"{module}.{provider} 的端点 {endpoint!r} 解析出的主机是 {host!r}，"
        f"与平台不符（期望包含 {expected_host!r}）—— 疑似从别的 provider 复制粘贴时带串了"
    )
