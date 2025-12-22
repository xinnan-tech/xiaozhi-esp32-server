from enum import Enum


class PluginAction(Enum):
    """插件返回状态枚举"""
    RELEASE = "release"  # 放行，继续原有流程
    INTERCEPT = "intercept"  # 拦截，返回结果
    CLOSE = "close"  # 关闭连接，返回结果


class BasePlugin:
    """插件基类"""

    def __init__(self, logger=None):
        self.name = "BasePlugin"
        self.description = "基础插件类"
        self.logger = logger

    async def pre_process_text(self, conn, text):
        """文本预处理方法

        Returns:
            tuple: (result, action)
                - result: 处理后的文本或响应消息
                - action: PluginAction枚举值 (RELEASE/INTERCEPT/CLOSE)
        """
        return text, PluginAction.RELEASE

    def speak(self, conn, text):
        """发送语音消息（封装TTS和队列操作）"""
        from core.providers.tts.dto.dto import ContentType
        from core.handle.sendAudioHandle import send_stt_message
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_stt_message(conn, text))
        except RuntimeError:
            pass

        if hasattr(conn, 'tts') and conn.tts:
            conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)

    def get_info(self):
        """获取插件信息"""
        return {"name": self.name, "description": self.description}