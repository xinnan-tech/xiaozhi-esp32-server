# 导入所需的模块
from config.logger import setup_logging  # 导入日志设置模块
import json  # 导入JSON模块，用于处理JSON数据
from core.handle.abortHandle import handleAbortMessage  # 导入处理中止消息的模块
from core.handle.helloHandle import handleHelloMessage  # 导入处理问候消息的模块
from core.handle.receiveAudioHandle import startToChat  # 导入处理音频消息的模块
from core.handle.iotHandle import handleIotDescriptors  # 导入处理IoT描述符的模块

# 定义当前模块的标签，通常用于日志记录
TAG = __name__

# 设置日志记录器
logger = setup_logging()

async def handleTextMessage(conn, message):
    """处理文本消息"""
    logger.bind(tag=TAG).info(f"收到文本消息：{message}")  # 记录收到的文本消息

    try:
        msg_json = json.loads(message)  # 将消息解析为JSON格式
        if isinstance(msg_json, int):  # 如果消息是整数类型（异常情况）
            await conn.websocket.send(message)  # 直接返回消息
            return

        # 根据消息类型处理不同的逻辑
        if msg_json["type"] == "hello":  # 如果消息类型是问候
            await handleHelloMessage(conn)  # 调用处理问候消息的函数
        elif msg_json["type"] == "abort":  # 如果消息类型是中止
            await handleAbortMessage(conn)  # 调用处理中止消息的函数
        elif msg_json["type"] == "listen":  # 如果消息类型是监听
            if "mode" in msg_json:  # 如果消息中包含监听模式
                conn.client_listen_mode = msg_json["mode"]  # 更新客户端的监听模式
                logger.bind(tag=TAG).debug(f"客户端拾音模式：{conn.client_listen_mode}")  # 记录监听模式

            # 根据监听状态更新客户端状态
            if msg_json["state"] == "start":  # 如果监听状态为开始
                conn.client_have_voice = True  # 设置客户端有声音
                conn.client_voice_stop = False  # 设置客户端声音未停止
            elif msg_json["state"] == "stop":  # 如果监听状态为停止
                conn.client_have_voice = True  # 设置客户端有声音
                conn.client_voice_stop = True  # 设置客户端声音已停止
            elif msg_json["state"] == "detect":  # 如果监听状态为检测
                conn.asr_server_receive = False  # 设置ASR服务器不接收数据
                conn.client_have_voice = False  # 设置客户端无声音
                conn.asr_audio.clear()  # 清空ASR音频缓存
                if "text" in msg_json:  # 如果消息中包含文本
                    await startToChat(conn, msg_json["text"])  # 启动聊天
        elif msg_json["type"] == "iot":  # 如果消息类型是IoT
            if "descriptors" in msg_json:  # 如果消息中包含描述符
                await handleIotDescriptors(conn, msg_json["descriptors"])  # 调用处理IoT描述符的函数
    except json.JSONDecodeError:  # 如果JSON解析失败
        await conn.websocket.send(message)  # 直接返回原始消息