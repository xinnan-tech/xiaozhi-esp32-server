"""智能体配置领域实体"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AgentConfig:
    """智能体配置实体 - 管理对话轮次、提示词、LLM 等可配置项"""
    id: str
    agent_name: str
    agent_id: Optional[str] = None          # 对应 xiaozhi-server 的智能体 ID
    dialogue_rounds: int = 7                # 对话轮次（问几个问题）
    questions: Optional[List[str]] = None   # 问题列表
    prompts_config: Optional[Dict[str, Any]] = None  # 提示词配置
    llm_config: Optional[Dict[str, Any]] = None      # LLM 配置
    review_config: Optional[Dict[str, Any]] = None    # 点评生成规则
    status: int = 1
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None

    def is_enabled(self) -> bool:
        return self.status == 1

    def get_questions(self) -> List[str]:
        """获取问题列表，如果没有自定义则返回空列表"""
        return self.questions or []

    def get_prompt_path(self, prompt_type: str) -> Optional[str]:
        """获取指定类型的提示词模板路径"""
        if self.prompts_config and prompt_type in self.prompts_config:
            return self.prompts_config[prompt_type]
        return None

    def get_llm_provider(self) -> Optional[str]:
        """获取 LLM 提供商"""
        if self.llm_config:
            return self.llm_config.get("provider")
        return None

    def get_review_length(self, review_type: str) -> dict:
        """获取点评长度限制"""
        if self.review_config and review_type in self.review_config:
            return self.review_config[review_type]
        # 默认长度
        defaults = {
            "long": {"min": 80, "max": 150},
            "short": {"min": 30, "max": 60},
        }
        return defaults.get(review_type, {})
