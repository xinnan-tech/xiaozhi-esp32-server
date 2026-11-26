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
        # session_id -> (conversation_id, chat_id)：上一轮没跑完的 chat。
        # 客户端打断时上游的 chat 还占着会话，下一轮开始前要把它取消掉。
        self.pending_chats = {}
        model_key_msg = check_model_key("CozeLLM", self.personal_access_token)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    def _cancel_chat(self, coze, conversation_id, chat_id, reason):
        """取消一个还在跑的 coze chat，把会话释放出来"""
        try:
            coze.chat.cancel(conversation_id=conversation_id, chat_id=chat_id)
            logger.bind(tag=TAG).info(f"{reason}，已取消 coze chat {chat_id}")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"取消 coze chat 失败: {e}")

    def response(self, session_id, dialogue, **kwargs):
        coze_api_token = self.personal_access_token
        coze_api_base = COZE_CN_BASE_URL

        last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")

        coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
        conversation_id = self.session_conversation_map.get(session_id)

        # 上一轮被客户端打断时，上游的 chat 还占着这个会话，这一轮开始前先把它
        # 取消掉，否则会撞上 4016 Conversation occupied
        pending = self.pending_chats.pop(session_id, None)
        if pending:
            self._cancel_chat(
                coze, pending[0], pending[1], "上一轮对话没有正常结束"
            )

        # 如果没有找到conversation_id，则创建新的对话
        if not conversation_id:
            conversation = coze.conversations.create(messages=[])
            conversation_id = conversation.id
            self.session_conversation_map[session_id] = conversation_id  # 更新映射

        chat_id = None
        chat_finished = False
        try:
            for event in coze.chat.stream(
                bot_id=self.bot_id,
                user_id=self.user_id,
                additional_messages=[
                    Message.build_user_question_text(last_msg["content"]),
                ],
                conversation_id=conversation_id,
            ):
                # conversation.chat.created 事件里带着本次 chat 的 id
                if event.chat is not None and event.chat.id:
                    chat_id = event.chat.id
                    self.pending_chats[session_id] = (conversation_id, chat_id)
                if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                    chat_finished = True
                    pending = self.pending_chats.get(session_id)
                    if pending and pending[1] == chat_id:
                        self.pending_chats.pop(session_id, None)
                if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                    print(event.message.content, end="", flush=True)
                    yield event.message.content
        except Exception as e:
            # 4016：同一个会话里上一轮 chat 还占着（上一轮被客户端打断时没结束干净），
            # 这里把本地记的会话 id 清掉，下一轮重新建会话，避免一直卡住
            if "4016" in str(e) or "Conversation occupied" in str(e):
                logger.bind(tag=TAG).error(
                    "Coze 会话被占用，已清除本地会话 id，下一轮重新创建会话"
                )
                self.session_conversation_map.pop(session_id, None)
            raise
        finally:
            # 客户端打断时这个生成器会被提前关闭（GeneratorExit），上游的 chat
            # 还占着会话，下一轮请求就会撞上 4016。这里主动取消掉，且保留
            # conversation_id，上下文不会丢。
            if chat_id and not chat_finished:
                pending = self.pending_chats.get(session_id)
                if pending and pending[1] == chat_id:
                    self.pending_chats.pop(session_id, None)
                self._cancel_chat(coze, conversation_id, chat_id, "对话被打断")

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
