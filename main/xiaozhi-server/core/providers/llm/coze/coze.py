from config.logger import setup_logging
import json
from core.providers.llm.base import LLMProviderBase

# official coze sdk for Python [cozepy](https://github.com/coze-dev/coze-py)
from cozepy import COZE_CN_BASE_URL
from cozepy import (
    Coze,
    TokenAuth,
    Message,
    ChatEventType,
)  # noqa
from core.providers.llm.system_prompt import get_system_prompt_for_function
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.personal_access_token = config.get("personal_access_token")
        self.bot_id = str(config.get("bot_id"))
        self.user_id = str(config.get("user_id"))
        self.session_conversation_map = {}  # 存储session_id和conversation_id的映射
        check_model_key("CozeLLM", self.personal_access_token)

    def response(self, session_id, dialogue):
        coze_api_token = self.personal_access_token
        coze_api_base = COZE_CN_BASE_URL

        last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")

        coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
        conversation_id = self.session_conversation_map.get(session_id)

        # 如果没有找到conversation_id，则创建新的对话
        if not conversation_id:
            conversation = coze.conversations.create(messages=[])
            conversation_id = conversation.id
            self.session_conversation_map[session_id] = conversation_id  # 更新映射

        for event in coze.chat.stream(
            bot_id=self.bot_id,
            user_id=self.user_id,
            additional_messages=[
                Message.build_user_question_text(last_msg["content"]),
            ],
            conversation_id=conversation_id,
        ):
            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                print(event.message.content, end="", flush=True)
                yield event.message.content

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
