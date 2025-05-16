import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    conn.logger.bind(tag=TAG).info(f"收到文本消息：{message}")
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                conn.client_have_voice = True
                conn.client_voice_stop = False
            elif msg_json["state"] == "stop":
                conn.client_have_voice = True
                conn.client_voice_stop = True
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.asr_server_receive = False
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    text = msg_json["text"]
                    _, text = remove_punctuation_and_length(text)

                    # 识别是否是唤醒词
                    is_wakeup_words = text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, text)
                        await send_tts_message(conn, "stop", None)
                    elif is_wakeup_words:
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, text, [])
                        # 否则需要LLM对文字内容进行答复
                        await startToChat(conn, text)
        elif msg_json["type"] == "iot":
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "server":
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "config_update_response",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "config_update_response",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "config_update_response",
                                "status": "success",
                                "message": "配置更新成功",
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "config_update_response",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
    except json.JSONDecodeError:
        await conn.websocket.send(message)
