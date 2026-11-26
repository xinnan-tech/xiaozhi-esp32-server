import pytest

from core.providers.llm.xinference.xinference import LLMProvider


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:9997",
        "http://localhost:9997/",
        "http://localhost:9997/v1",
        "http://localhost:9997/v1/",
        " http://localhost:9997/v1 ",
    ],
)
def test_base_url_points_at_v1(base_url):
    provider = LLMProvider({"model_name": "qwen", "base_url": base_url})
    assert str(provider.client.base_url) == "http://localhost:9997/v1/"


@pytest.mark.parametrize("base_url", [None, ""])
def test_missing_base_url_uses_default(base_url):
    provider = LLMProvider({"model_name": "qwen", "base_url": base_url})
    assert str(provider.client.base_url) == "http://localhost:9997/v1/"
