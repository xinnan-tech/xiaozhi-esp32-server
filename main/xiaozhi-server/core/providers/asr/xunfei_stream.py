import json
import hmac
import base64
import hashlib
import asyncio
import websockets
import opuslib_next
from time import mktime
from datetime import datetime
from urllib.parse import urlencode
from typing import List
from config.logger import setup_logging
from wsgiref.handlers import format_date_time
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

# 帧状态常量
STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.decoder = opuslib_next.Decoder(16000, 1)
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False
        self.server_ready = False
        self.last_frame_sent = False  # 标记是否已发送最终帧
        self.best_text = ""  # 保存最佳识别结果
        self.has_final_result = False  # 标记是否收到最终识别结果

        # 讯飞配置
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")

        if not all([self.app_id, self.api_key, self.api_secret]):
            raise ValueError("必须提供app_id、api_key和api_secret")

        # 识别参数
        self.iat_params = {
            "domain": config.get("domain", "slm"),
            "language": config.get("language", "zh_cn"),
            "accent": config.get("accent", "mandarin"),
            "dwa": config.get("dwa", "wpgs"),
            "result": {"encoding": "utf8", "compress": "raw", "format": "plain"},
        }

        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

    def create_url(self) -> str:
        """生成认证URL"""
        url = "ws://iat.cn-huabei-1.xf-yun.com/v1"
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "iat.cn-huabei-1.xf-yun.com" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v1 " + "HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = (
            'api_key="%s", algorithm="%s", headers="%s", signature="%s"'
            % (self.api_key, "hmac-sha256", "host date request-line", signature_sha)
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "iat.cn-huabei-1.xf-yun.com",
        }

        # 拼接鉴权参数，生成url
        url = url + "?" + urlencode(v)
        return url

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, audio, audio_have_voice):
        # 先调用父类方法处理基础逻辑
        await super().receive_audio(conn, audio, audio_have_voice)

        # 存储音频数据用于声纹识别
        if not hasattr(conn, "asr_audio_for_voiceprint"):
            conn.asr_audio_for_voiceprint = []
        conn.asr_audio_for_voiceprint.append(audio)

        # 如果本次有声音，且之前没有建立连接
        if audio_have_voice and self.asr_ws is None and not self.is_processing:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(f"建立ASR连接失败: {str(e)}")
                await self._cleanup(conn)
                return

        # 发送当前音频数据
        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                await self._send_audio_frame(pcm_frame, STATUS_CONTINUE_FRAME)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"发送音频数据时发生错误: {e}")
                await self._cleanup(conn)

    async def _start_recognition(self, conn):
        """开始识别会话"""
        try:
            self.is_processing = True
            # 建立WebSocket连接
            ws_url = self.create_url()
            logger.bind(tag=TAG).info(f"正在连接ASR服务: {ws_url[:50]}...")

            self.asr_ws = await websockets.connect(
                ws_url,
                max_size=1000000000,
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10,
            )

            logger.bind(tag=TAG).info("ASR WebSocket连接已建立")
            self.server_ready = False
            self.last_frame_sent = False
            self.best_text = ""
            self.forward_task = asyncio.create_task(self._forward_results(conn))

            # 发送首帧音频
            if conn.asr_audio and len(conn.asr_audio) > 0:
                first_audio = conn.asr_audio[-1] if conn.asr_audio else b""
                pcm_frame = (
                    self.decoder.decode(first_audio, 960) if first_audio else b""
                )
                await self._send_audio_frame(pcm_frame, STATUS_FIRST_FRAME)
                self.server_ready = True
                logger.bind(tag=TAG).info("已发送首帧，开始识别")

                # 发送缓存的音频数据
                for cached_audio in conn.asr_audio[-10:]:
                    try:
                        pcm_frame = self.decoder.decode(cached_audio, 960)
                        await self._send_audio_frame(pcm_frame, STATUS_CONTINUE_FRAME)
                    except Exception as e:
                        logger.bind(tag=TAG).info(f"发送缓存音频数据时发生错误: {e}")
                        break

        except Exception as e:
            logger.bind(tag=TAG).error(f"建立ASR连接失败: {str(e)}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.bind(tag=TAG).error(f"错误原因: {str(e.__cause__)}")
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            raise

    async def _send_audio_frame(self, audio_data: bytes, status: int):
        """发送音频帧"""
        if not self.asr_ws:
            return

        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        frame_data = {
            "header": {"status": status, "app_id": self.app_id},
            "parameter": {"iat": self.iat_params},
            "payload": {
                "audio": {"audio": audio_b64, "sample_rate": 16000, "encoding": "raw"}
            },
        }

        await self.asr_ws.send(json.dumps(frame_data, ensure_ascii=False))

        # 标记是否发送了最终帧
        if status == STATUS_LAST_FRAME:
            self.last_frame_sent = True
            logger.bind(tag=TAG).info("标记最终帧已发送")

    async def _forward_results(self, conn):
        """转发识别结果"""
        try:
            while self.asr_ws and not conn.stop_event.is_set():
                # 获取当前连接的音频数据
                audio_data = getattr(conn, "asr_audio_for_voiceprint", [])
                try:
                    # 如果已发送最终帧，增加超时时间等待完整结果
                    timeout = 3.0 if self.last_frame_sent else 30.0
                    response = await asyncio.wait_for(
                        self.asr_ws.recv(), timeout=timeout
                    )
                    result = json.loads(response)
                    logger.bind(tag=TAG).debug(f"收到ASR结果: {result}")

                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    code = header.get("code", 0)
                    status = header.get("status", 0)

                    if code != 0:
                        logger.bind(tag=TAG).error(
                            f"识别错误，错误码: {code}, 消息: {header.get('message', '')}"
                        )
                        if code in [10114, 10160]:  # 连接问题
                            break
                        continue

                    # 处理识别结果
                    if payload and "result" in payload:
                        text_data = payload["result"]["text"]
                        if text_data:
                            # 解码base64文本
                            decoded_text = base64.b64decode(text_data).decode("utf-8")
                            text_json = json.loads(decoded_text)

                            # 提取文本内容
                            text_ws = text_json.get("ws", [])
                            result_text = ""
                            for i in text_ws:
                                for j in i.get("cw", []):
                                    w = j.get("w", "")
                                    result_text += w

                            # 更新识别文本 - 实时更新策略
                            # 只检查是否为空字符串，不再过滤任何标点符号
                            # 这样可以确保所有识别到的内容，包括标点符号都能被实时更新
                            if result_text and result_text.strip():
                                # 实时更新：正常情况下都更新，提高响应速度
                                should_update = True

                                # 保存最佳文本
                                # 1. 如果是识别完成状态或最终帧后收到的结果，优先保存
                                # 2. 否则保存最长的有意义文本
                                # 取消对标点符号的过滤，只检查是否为空
                                # 这样可以保留所有识别到的内容，包括各种标点符号
                                is_valid_text = len(result_text.strip()) > 0

                                if (
                                    self.last_frame_sent or status == 2
                                ) and is_valid_text:
                                    self.best_text = result_text
                                    self.has_final_result = True  # 标记已收到最终结果
                                    logger.bind(tag=TAG).debug(
                                        f"保存最终识别结果: {self.best_text}"
                                    )
                                elif (
                                    len(result_text) > len(self.best_text)
                                    and is_valid_text
                                    and not self.has_final_result
                                ):
                                    self.best_text = result_text
                                    logger.bind(tag=TAG).debug(
                                        f"保存中间最佳文本: {self.best_text}"
                                    )

                                # 如果已发送最终帧，只过滤空文本
                                if self.last_frame_sent:
                                    # 只拒绝完全空的结果
                                    if not result_text.strip():
                                        should_update = False
                                        logger.bind(tag=TAG).warning(
                                            f"最终帧后拒绝空文本"
                                        )

                                if should_update:
                                    # 处理流式识别结果，避免简单替换导致内容丢失
                                    # 1. 如果是中间状态（非最终帧后），可能需要替换为更完整的识别
                                    # 2. 如果是最终帧后收到的结果，可能是对前面文本的补充
                                    if self.last_frame_sent:
                                        # 最终帧后收到的结果可能是标点符号等补充内容
                                        # 检查是否需要合并文本而不是替换
                                        # 如果当前文本是纯标点而前面已有内容，应该追加而不是替换
                                        if len(
                                            self.text
                                        ) > 0 and result_text.strip() in [
                                            "。",
                                            ".",
                                            "?",
                                            "？",
                                            "!",
                                            "！",
                                            ",",
                                            "，",
                                            ";",
                                            "；",
                                        ]:
                                            # 对于标点符号，追加到现有文本后
                                            self.text = (
                                                self.text.rstrip().rstrip("。.")
                                                + result_text
                                            )
                                        else:
                                            # 其他情况保持替换逻辑
                                            self.text = result_text
                                    else:
                                        # 中间状态替换为新的识别结果
                                        self.text = result_text

                                    logger.bind(tag=TAG).info(
                                        f"实时更新识别文本: {self.text} (最终帧已发送: {self.last_frame_sent})"
                                    )

                    # 识别完成，但如果还没发送最终帧，继续等待
                    if status == 2:
                        logger.bind(tag=TAG).info(
                            f"识别完成状态已到达，当前识别文本: {self.text}"
                        )

                        # 如果还没发送最终帧，继续等待
                        if not self.last_frame_sent:
                            logger.bind(tag=TAG).info(
                                "识别完成但最终帧未发送，继续等待..."
                            )
                            continue

                        # 已发送最终帧且收到完成状态，使用最佳策略选择最终结果
                        # 优先使用识别完成状态下的最新结果，而不是仅仅基于长度
                        if self.best_text:
                            # 如果当前文本是在最终帧发送后或识别完成状态下收到的，优先使用
                            if (
                                self.last_frame_sent or status == 2
                            ) and self.text.strip():
                                logger.bind(tag=TAG).info(
                                    f"使用完成状态下的最新识别结果: {self.text}"
                                )
                            elif len(self.best_text) > len(self.text):
                                logger.bind(tag=TAG).info(
                                    f"使用更长的最佳文本作为最终结果: {self.text} -> {self.best_text}"
                                )
                                self.text = self.best_text

                        logger.bind(tag=TAG).info(f"获取到最终完整文本: {self.text}")
                        conn.reset_vad_states()
                        if len(audio_data) > 15:  # 确保有足够音频数据
                            # 准备处理结果
                            pass
                        break

                except asyncio.TimeoutError:
                    if self.last_frame_sent:
                        # 超时时也使用最佳文本
                        if self.best_text and len(self.best_text) > len(self.text):
                            logger.bind(tag=TAG).info(
                                f"超时，使用最佳文本: {self.text} -> {self.best_text}"
                            )
                            self.text = self.best_text
                        logger.bind(tag=TAG).info(
                            f"最终帧后超时，使用结果: {self.text}"
                        )
                        break
                    # 如果还没发送最终帧，继续等待
                    continue
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("ASR服务连接已关闭")
                    self.is_processing = False
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"处理ASR结果时发生错误: {str(e)}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).error(f"错误原因: {str(e.__cause__)}")
                    self.is_processing = False
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR结果转发任务发生错误: {str(e)}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.bind(tag=TAG).error(f"错误原因: {str(e.__cause__)}")
        finally:
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            if conn:
                if hasattr(conn, "asr_audio_for_voiceprint"):
                    conn.asr_audio_for_voiceprint = []
                if hasattr(conn, "asr_audio"):
                    conn.asr_audio = []
                if hasattr(conn, "has_valid_voice"):
                    conn.has_valid_voice = False

    async def handle_voice_stop(self, conn, asr_audio_task: List[bytes]):
        """处理语音停止，发送最后一帧并处理识别结果"""
        try:
            # 先发送最后一帧表示音频结束
            if self.asr_ws and self.is_processing:
                try:
                    # 取最后一个有效的音频帧作为最后一帧数据
                    last_frame = b""
                    if asr_audio_task:
                        last_audio = asr_audio_task[-1]
                        last_frame = self.decoder.decode(last_audio, 960)
                    await self._send_audio_frame(last_frame, STATUS_LAST_FRAME)
                    logger.bind(tag=TAG).info("已发送最后一帧")

                    # 发送最终帧后，给_forward_results适当时间处理最终结果
                    await asyncio.sleep(0.25)

                    logger.bind(tag=TAG).info(f"准备处理最终识别结果: {self.text}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"发送最后一帧失败: {e}")

            # 调用父类的handle_voice_stop方法处理识别结果
            await super().handle_voice_stop(conn, asr_audio_task)
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理语音停止失败: {e}")
            import traceback

            logger.bind(tag=TAG).debug(f"异常详情: {traceback.format_exc()}")

    def stop_ws_connection(self):
        if self.asr_ws:
            asyncio.create_task(self.asr_ws.close())
            self.asr_ws = None
        self.is_processing = False

    async def _cleanup(self, conn):
        """清理资源"""
        logger.bind(tag=TAG).info(
            f"开始ASR会话清理 | 当前状态: processing={self.is_processing}, server_ready={self.server_ready}"
        )

        # 发送最后一帧
        if self.asr_ws and self.is_processing:
            try:
                await self._send_audio_frame(b"", STATUS_LAST_FRAME)
                await asyncio.sleep(0.1)
                logger.bind(tag=TAG).info("已发送最后一帧")
            except Exception as e:
                logger.bind(tag=TAG).error(f"发送最后一帧失败: {e}")

        # 状态重置
        self.is_processing = False
        self.server_ready = False
        self.last_frame_sent = False
        self.best_text = ""
        self.has_final_result = False
        logger.bind(tag=TAG).info("ASR状态已重置")

        # 清理任务
        if self.forward_task and not self.forward_task.done():
            self.forward_task.cancel()
            try:
                await asyncio.wait_for(self.forward_task, timeout=1.0)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.bind(tag=TAG).debug(f"forward_task取消异常: {e}")
            finally:
                self.forward_task = None

        # 关闭连接
        if self.asr_ws:
            try:
                logger.bind(tag=TAG).debug("正在关闭WebSocket连接")
                await asyncio.wait_for(self.asr_ws.close(), timeout=2.0)
                logger.bind(tag=TAG).debug("WebSocket连接已关闭")
            except Exception as e:
                logger.bind(tag=TAG).error(f"关闭WebSocket连接失败: {e}")
            finally:
                self.asr_ws = None

        # 清理连接的音频缓存
        if conn:
            if hasattr(conn, "asr_audio_for_voiceprint"):
                conn.asr_audio_for_voiceprint = []
            if hasattr(conn, "asr_audio"):
                conn.asr_audio = []
            if hasattr(conn, "has_valid_voice"):
                conn.has_valid_voice = False

        logger.bind(tag=TAG).info("ASR会话清理完成")

    async def speech_to_text(self, opus_data, session_id, audio_format):
        """获取识别结果"""
        result = self.text
        self.text = ""
        return result, None

    async def close(self):
        """资源清理方法"""
        if self.asr_ws:
            await self.asr_ws.close()
            self.asr_ws = None
        if self.forward_task:
            self.forward_task.cancel()
            try:
                await self.forward_task
            except asyncio.CancelledError:
                pass
            self.forward_task = None
        self.is_processing = False
        # 清理所有连接的音频缓冲区
        if hasattr(self, "_connections"):
            for conn in self._connections.values():
                if hasattr(conn, "asr_audio_for_voiceprint"):
                    conn.asr_audio_for_voiceprint = []
                if hasattr(conn, "asr_audio"):
                    conn.asr_audio = []
                if hasattr(conn, "has_valid_voice"):
                    conn.has_valid_voice = False
