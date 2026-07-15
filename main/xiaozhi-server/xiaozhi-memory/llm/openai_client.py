"""
OpenAI LLM 客户端
"""
import json
import logging
from typing import List, Dict, Any

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base import LLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """OpenAI API 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = None,
        use_json_mode: bool = None
    ):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is required. Install with: pip install openai")

        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        # 自动检测是否使用 JSON 模式（豆包等模型不支持）
        self.use_json_mode = use_json_mode if use_json_mode is not None else self._supports_json_mode()

    def _supports_json_mode(self) -> bool:
        """检测模型是否支持 JSON 模式"""
        # 豆包模型不支持 JSON 模式
        if "doubao" in self.model.lower() or self.model.startswith("ep-"):
            return False
        # gpt-4o-mini, gpt-4o, gpt-3.5-turbo 等支持
        return True

    async def extract_facts(
        self,
        conversation: str,
        context: Dict[str, Any],
        return_raw: bool = False
    ) -> List[Dict[str, Any]]:
        """
        从对话中提取事实

        Args:
            conversation: 对话文本
            context: 上下文信息
            return_raw: 如果为 True，返回完整 JSON 对象（含 dangers 字段）

        Returns:
            提取的事实列表，或完整 JSON 对象（return_raw=True 时）
        """
        from prompts.fact_extraction import FACT_EXTRACTION_PROMPT

        prompt = FACT_EXTRACTION_PROMPT.format(**context, conversation=conversation)

        try:
            # 构建请求参数
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的个人信息提取助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
            }

            # 只有支持的模型才使用 JSON 模式
            if self.use_json_mode:
                request_params["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**request_params)

            result = json.loads(response.choices[0].message.content)

            if return_raw:
                return result

            facts = result.get("facts", [])

            logger.info(f"Extracted {len(facts)} facts from conversation")
            return facts

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return [] if not return_raw else {"facts": [], "dangers": []}
        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            raise
