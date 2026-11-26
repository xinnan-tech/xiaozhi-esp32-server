import json
from config.logger import setup_logging
import requests
from core.providers.llm.base import LLMProviderBase
from core.providers.llm.system_prompt import get_system_prompt_for_function
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()

# dify 支持的对话模式
SUPPORTED_MODES = ("chat-messages", "workflows/run", "completion-messages")


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.mode = config.get("mode", "chat-messages")
        self.base_url = config.get("base_url", "https://api.dify.ai/v1").rstrip("/")
        self.session_conversation_map = {}  # 存储session_id和conversation_id的映射
        # 请求超时，避免上游不响应时一直挂着（#1229）
        self.timeout = self.resolve_timeout(config)
        model_key_msg = check_model_key("DifyLLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    def _build_request_json(self, session_id, dialogue):
        """按当前模式拼装请求体，模式不支持时直接报错"""
        # 取最后一条用户消息
        last_msg = next((m for m in reversed(dialogue) if m["role"] == "user"), None)
        if last_msg is None:
            raise ValueError("对话里没有用户消息，无法请求 dify")

        if self.mode == "chat-messages":
            return {
                "query": last_msg["content"],
                "response_mode": "streaming",
                "user": session_id,
                "inputs": {},
                "conversation_id": self.session_conversation_map.get(session_id),
            }
        elif self.mode == "workflows/run":
            return {
                "inputs": {"query": last_msg["content"]},
                "response_mode": "streaming",
                "user": session_id,
            }
        elif self.mode == "completion-messages":
            return {
                "inputs": {"query": last_msg["content"]},
                "response_mode": "streaming",
                "user": session_id,
            }
        raise ValueError(
            f"不支持的 dify 模式: {self.mode}，可用值: {', '.join(SUPPORTED_MODES)}"
        )

    @staticmethod
    def _iter_events(response):
        """解析 dify 的 SSE 流，逐条返回事件

        单条数据解析失败时跳过这一条，不让整段回复直接中断。
        """
        for line in response.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            payload = line[6:].strip()
            if not payload:
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.bind(tag=TAG).warning(f"dify 返回的数据无法解析，已跳过: {e}")
                continue
            if isinstance(event, dict):
                yield event

    def response(self, session_id, dialogue, **kwargs):
        request_json = self._build_request_json(session_id, dialogue)
        conversation_id = self.session_conversation_map.get(session_id)

        try:
            with requests.post(
                f"{self.base_url}/{self.mode}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=request_json,
                stream=True,
                timeout=self.timeout,
            ) as r:
                for event in self._iter_events(r):
                    if self.mode == "chat-messages":
                        # 如果没有找到conversation_id，则获取此次conversation_id
                        if not conversation_id:
                            conversation_id = event.get("conversation_id")
                            self.session_conversation_map[session_id] = (
                                conversation_id  # 更新映射
                            )
                        # 过滤 message_replace 事件，此事件会全量推一次
                        if event.get("event") != "message_replace" and event.get(
                            "answer"
                        ):
                            yield event["answer"]
                    elif self.mode == "workflows/run":
                        if event.get("event") == "workflow_finished":
                            data = event.get("data") or {}
                            if data.get("status") == "succeeded":
                                yield (data.get("outputs") or {}).get("answer", "")
                            else:
                                yield "【服务响应异常】"
                    elif self.mode == "completion-messages":
                        # 过滤 message_replace 事件，此事件会全量推一次
                        if event.get("event") != "message_replace" and event.get(
                            "answer"
                        ):
                            yield event["answer"]
        except requests.exceptions.Timeout:
            logger.bind(tag=TAG).error(
                f"dify 请求超时（连接 {self.timeout[0]}s / 读取 {self.timeout[1]}s）"
            )
            raise

    def response_with_functions(self, session_id, dialogue, functions=None):
        if len(dialogue) == 2 and functions is not None and len(functions) > 0:
            # 第一次调用llm， 取最后一条用户消息，附加tool提示词
            last_msg = dialogue[-1]["content"]
            function_str = json.dumps(functions, ensure_ascii=False)
            modify_msg = get_system_prompt_for_function(function_str) + last_msg
            dialogue[-1]["content"] = modify_msg

        # 如果最后一个是 role="tool"，附加到user上
        if len(dialogue) > 1 and dialogue[-1]["role"] == "tool":
            assistant_msg = "\ntool call result: " + dialogue[-1]["content"] + "\n\n"
            while len(dialogue) > 1:
                if dialogue[-1]["role"] == "user":
                    dialogue[-1]["content"] = assistant_msg + dialogue[-1]["content"]
                    break
                dialogue.pop()

        for token in self.response(session_id, dialogue):
            yield token, None
