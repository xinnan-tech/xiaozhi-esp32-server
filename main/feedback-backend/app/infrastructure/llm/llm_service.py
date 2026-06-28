"""LLM 调用服务 - 封装 OpenAI SDK，支持多提供商"""

import json
from typing import Any, Dict, Optional

from loguru import logger
from openai import OpenAI

from app.shared.config import settings
from app.shared.exceptions import LLMProcessingError


class LLMService:
    """LLM 调用服务"""

    def __init__(self, provider: Optional[str] = None, llm_config: Optional[Dict] = None):
        """
        初始化 LLM 服务

        Args:
            provider: 提供商名称 (openai/dashscope/deepseek)
            llm_config: 自定义 LLM 配置（覆盖全局配置）
        """
        self.provider = provider or settings.get("llm.provider", "openai")
        self.llm_config = llm_config or {}
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """懒加载 OpenAI 客户端（兼容 OpenAI API 协议的所有提供商）"""
        if self._client is None:
            config = self._resolve_config()
            self._client = OpenAI(
                api_key=config["api_key"],
                base_url=config.get("base_url"),
            )
        return self._client

    def _resolve_config(self) -> Dict[str, Any]:
        """解析 LLM 配置：自定义配置 > 全局配置"""
        # 优先使用自定义配置
        if self.llm_config:
            return {
                "api_key": self.llm_config.get("api_key", ""),
                "base_url": self.llm_config.get("base_url"),
                "model": self.llm_config.get("model"),
            }

        # 回退到全局配置
        provider_config = settings.get(f"llm.{self.provider}", {})
        return {
            "api_key": provider_config.get("api_key", ""),
            "base_url": provider_config.get("base_url"),
            "model": provider_config.get("model"),
        }

    @property
    def model(self) -> str:
        """获取模型名称"""
        config = self._resolve_config()
        return config.get("model", "gpt-4o-mini")

    async def chat(self, system_prompt: str, user_message: str,
                   temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """
        单轮对话

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            模型回复文本
        """
        try:
            logger.info(f"LLM 调用: provider={self.provider}, model={self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content.strip()
            logger.info(f"LLM 响应长度: {len(result)} 字符")
            return result
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise LLMProcessingError(str(e))

    async def chat_json(self, system_prompt: str, user_message: str,
                        temperature: float = 0.1) -> Dict[str, Any]:
        """
        单轮对话，期望返回 JSON 格式

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 温度（默认更低以获得更稳定的 JSON 输出）

        Returns:
            解析后的 JSON 字典
        """
        text = await self.chat(system_prompt, user_message, temperature=temperature)

        # 尝试提取 JSON
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        import re
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个 { ... } 块
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"无法从 LLM 响应中提取 JSON，原始文本: {text[:200]}")
        raise LLMProcessingError(f"LLM 返回内容无法解析为 JSON")
