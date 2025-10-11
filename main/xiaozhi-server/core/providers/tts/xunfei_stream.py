import os
import time
import uuid
import json
import hmac
import queue
import base64
import hashlib
import asyncio
import traceback
import websockets
from asyncio import Task
from config.logger import setup_logging
from core.utils import opus_encoder_utils
from core.utils.tts import MarkdownCleaner
from urllib.parse import urlencode, urlparse
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()


class XunfeiWSAuth:
    @staticmethod
    def create_auth_url(api_key, api_secret, api_url):
        """生成讯飞WebSocket认证URL"""
        parsed_url = urlparse(api_url)
        host = parsed_url.netloc
        path = parsed_url.path

        # 获取UTC时间，讯飞要求使用RFC1123格式
        now = time.gmtime()
        date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', now)

        # 构造签名字符串
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

        # 计算签名
        signature_sha = hmac.new(
            api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        # 构造authorization
        authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 构造最终的WebSocket URL
        v = {
            "authorization": authorization,
            "date": date,
            "host": host
        }
        url = api_url + '?' + urlencode(v)
        return url


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        # 设置为流式接口类型
        self.interface_type = InterfaceType.DUAL_STREAM

        # 基础配置
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")

        # 接口地址
        self.api_url = config.get("api_url", "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6")

        # 音色配置
        self.voice = config.get("voice", "x5_lingxiaoxuan_flow")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")

        # 音频参数配置
        speed = config.get("speed", "50")
        self.speed = int(speed) if speed else 50

        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50

        pitch = config.get("pitch", "50")
        self.pitch = int(pitch) if pitch else 50

        # 音频编码配置
        self.format = config.get("format", "raw")

        sample_rate = config.get("sample_rate", "24000")
        self.sample_rate = int(sample_rate) if sample_rate else 24000

        # 口语化配置
        self.oral_level = config.get("oral_level", "mid")

        spark_assist = config.get("spark_assist", "1")
        self.spark_assist = int(spark_assist) if spark_assist else 1

        stop_split = config.get("stop_split", "0")
        self.stop_split = int(stop_split) if stop_split else 0
    
        remain = config.get("remain", "0")
        self.remain = int(remain) if remain else 0

        # WebSocket配置
        self.ws = None
        self._monitor_task = None

        # 序列号管理
        self.text_seq = 0

        # 创建Opus编码器
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=self.sample_rate, channels=1, frame_size_ms=60
        )

        # 验证必需参数
        if not all([self.app_id, self.api_key, self.api_secret]):
            raise ValueError("讯飞TTS需要配置app_id、api_key和api_secret")

    async def _ensure_connection(self):
        """确保WebSocket连接可用"""
        try:
            logger.bind(tag=TAG).info("开始建立新连接...")

            # 生成认证URL
            auth_url = XunfeiWSAuth.create_auth_url(
                self.api_key, self.api_secret, self.api_url
            )

            self.ws = await websockets.connect(
                auth_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
            )
            logger.bind(tag=TAG).info("WebSocket连接建立成功")
            return self.ws
        except Exception as e:
            logger.bind(tag=TAG).error(f"建立连接失败: {str(e)}")
            self.ws = None
            raise

    def tts_text_priority_thread(self):
        """流式文本处理线程"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).debug(
                    f"收到TTS任务｜{message.sentence_type.name} ｜ {message.content_type.name} | 会话ID: {self.conn.sentence_id}"
                )

                if message.sentence_type == SentenceType.FIRST:
                    # 重置序列号
                    self.text_seq = 0
                    self.conn.client_abort = False
                # 增加序列号
                self.text_seq += 1
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("收到打断信息，终止TTS文本处理线程")
                    continue

                if message.sentence_type == SentenceType.FIRST:
                    # 初始化参数
                    try:
                        if not getattr(self.conn, "sentence_id", None):
                            self.conn.sentence_id = uuid.uuid4().hex
                            logger.bind(tag=TAG).info(f"自动生成新的 会话ID: {self.conn.sentence_id}")

                        logger.bind(tag=TAG).info("开始启动TTS会话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.start_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
                        self.before_stop_play_files.clear()
                        logger.bind(tag=TAG).info("TTS会话启动成功")

                    except Exception as e:
                        logger.bind(tag=TAG).error(f"启动TTS会话失败: {str(e)}")
                        continue

                # 处理文本内容
                if ContentType.TEXT == message.content_type:
                    if message.content_detail:
                        try:
                            logger.bind(tag=TAG).debug(
                                f"开始发送TTS文本: {message.content_detail}"
                            )
                            future = asyncio.run_coroutine_threadsafe(
                                self.text_to_speak(message.content_detail, None),
                                loop=self.conn.loop,
                            )
                            future.result()
                            logger.bind(tag=TAG).debug("TTS文本发送成功")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"发送TTS文本失败: {str(e)}")
                            # 不使用continue，确保后续处理不被中断

                # 处理文件内容
                if ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        # 先处理文件音频数据
                        self._process_audio_file_stream(message.content_file, callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail))

                # 处理会话结束
                if message.sentence_type == SentenceType.LAST:
                    try:
                        logger.bind(tag=TAG).info("开始结束TTS会话...")
                        asyncio.run_coroutine_threadsafe(
                            self.finish_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"结束TTS会话失败: {str(e)}")
                        continue

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )

    async def text_to_speak(self, text, _):
        """发送文本到TTS服务进行合成"""
        try:
            if self.ws is None:
                logger.bind(tag=TAG).warning(f"WebSocket连接不存在，终止发送文本")
                return

            filtered_text = MarkdownCleaner.clean_markdown(text)

            # 发送文本合成请求
            run_request = self._build_base_request(status=1,text=filtered_text)
            await self.ws.send(json.dumps(run_request))
            return

        except Exception as e:
            logger.bind(tag=TAG).error(f"发送TTS文本失败: {str(e)}")
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
            raise

    async def start_session(self, session_id):
        logger.bind(tag=TAG).info(f"开始会话～～{session_id}")
        try:
            # 会话开始时检测上个会话的监听状态
            if (
                self._monitor_task is not None
                and isinstance(self._monitor_task, Task)
                and not self._monitor_task.done()
            ):
                logger.bind(tag=TAG).info(
                    "检测到未完成的上个会话，关闭监听任务和连接..."
                )
                await self.close()

            # 建立新连接
            await self._ensure_connection()

            # 启动监听任务
            self._monitor_task = asyncio.create_task(self._start_monitor_tts_response())

            # 发送会话启动请求
            start_request = self._build_base_request(status=0)

            await self.ws.send(json.dumps(start_request))
            logger.bind(tag=TAG).info("会话启动请求已发送")
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动会话失败: {str(e)}")
            # 确保清理资源
            await self.close()
            raise

    async def finish_session(self, session_id):
        logger.bind(tag=TAG).info(f"关闭会话～～{session_id}")
        try:
            if self.ws:
                # 发送会话结束请求
                stop_request = self._build_base_request(status=2)
                await self.ws.send(json.dumps(stop_request))
                logger.bind(tag=TAG).info("会话结束请求已发送")

                if self._monitor_task:
                    try:
                        await self._monitor_task
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"等待监听任务完成时发生错误: {str(e)}")
                    finally:
                        self._monitor_task = None
        except Exception as e:
            logger.bind(tag=TAG).error(f"关闭会话失败: {str(e)}")
            await self.close()
            raise

    async def close(self):
        """资源清理"""
        if self._monitor_task:
            try:
                self._monitor_task.cancel()
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.bind(tag=TAG).warning(f"关闭时取消监听任务错误: {e}")
            self._monitor_task = None

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

    async def _start_monitor_tts_response(self):
        """监听TTS响应"""
        try:
            while not self.conn.stop_event.is_set():
                try:
                    msg = await self.ws.recv()

                    # 检查客户端是否中止
                    if self.conn.client_abort:
                        logger.bind(tag=TAG).info("收到打断信息，终止监听TTS响应")
                        break

                    try:
                        data = json.loads(msg)
                        header = data.get("header", {})
                        code = header.get("code")

                        if code == 0:
                            payload = data.get("payload", {})
                            audio_payload = payload.get("audio", {})

                            if audio_payload:
                                status = audio_payload.get("status", 0)
                                audio_data = audio_payload.get("audio", "")
                                if status == 0:
                                    logger.bind(tag=TAG).debug("TTS合成已启动")
                                    self.tts_audio_queue.put(
                                        (SentenceType.FIRST, [], None)
                                    )
                                elif status == 2:
                                    logger.bind(tag=TAG).debug("收到结束状态的音频数据，TTS合成完成")
                                    self._process_before_stop_play_files()
                                    break
                                else:
                                    if self.conn.tts_MessageText:
                                        logger.bind(tag=TAG).info(
                                            f"句子语音生成成功： {self.conn.tts_MessageText}"
                                        )
                                        self.tts_audio_queue.put(
                                            (SentenceType.FIRST, [], self.conn.tts_MessageText)
                                        )
                                        self.conn.tts_MessageText = None
                                    try:
                                        audio_bytes = base64.b64decode(audio_data)
                                        self.opus_encoder.encode_pcm_to_opus_stream(
                                            audio_bytes, False, self.handle_opus
                                        )

                                    except Exception as e:
                                        logger.bind(tag=TAG).error(f"处理音频数据失败: {e}")

                        else:
                            message = header.get("message", "未知错误")
                            logger.bind(tag=TAG).error(f"TTS合成错误: {code} - {message}")
                            break

                    except json.JSONDecodeError:
                        logger.bind(tag=TAG).warning("收到无效的JSON消息")

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("WebSocket连接已关闭")
                    break

                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"处理TTS响应时出错: {e}\n{traceback.format_exc()}"
                    )
                    break

            # 链接不可复用
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        # 监听任务退出时清理引用
        finally:
            self._monitor_task = None

    def to_tts(self, text: str) -> list:
        """非流式TTS处理，用于测试及保存音频文件的场景"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 存储音频数据
            audio_data = []

            async def _generate_audio():
                # 生成认证URL
                auth_url = XunfeiWSAuth.create_auth_url(
                    self.api_key, self.api_secret, self.api_url
                )

                # 建立WebSocket连接
                ws = await websockets.connect(
                    auth_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                )

                try:
                    filtered_text = MarkdownCleaner.clean_markdown(text)

                    text_request = self._build_base_request(status=2,text=filtered_text)

                    await ws.send(json.dumps(text_request))

                    task_finished = False
                    while not task_finished:
                        msg = await ws.recv()

                        data = json.loads(msg)
                        header = data.get("header", {})
                        code = header.get("code")

                        if code == 0:
                            payload = data.get("payload", {})
                            audio_payload = payload.get("audio", {})
                            if audio_payload:
                                status = audio_payload.get("status", 0)
                                audio_base64 = audio_payload.get("audio", "")
                                if status == 1:
                                    try:
                                        audio_bytes = base64.b64decode(audio_base64)
                                        self.opus_encoder.encode_pcm_to_opus_stream(
                                            audio_bytes,
                                            end_of_stream=False,
                                            callback=lambda opus: audio_data.append(opus)
                                        )
                                    except Exception as e:
                                        logger.bind(tag=TAG).error(f"处理音频数据失败: {e}")
                                elif status == 2:
                                    task_finished = True
                                    logger.bind(tag=TAG).debug("TTS任务完成")

                        else:
                            message = header.get("message", "未知错误")
                            raise Exception(f"合成失败: {code} - {message}")

                finally:
                    # 清理资源
                    try:
                        await ws.close()
                    except:
                        pass

            loop.run_until_complete(_generate_audio())
            loop.close()

            return audio_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"生成音频数据失败: {str(e)}")
            return []        
    
    def _build_base_request(self, status,text=" "):
        """构建基础请求结构"""
        return {
            "header": {
                "app_id": self.app_id,
                "status": status,
            },
            "parameter": {
                "oral": {
                    "oral_level": self.oral_level,
                    "spark_assist": self.spark_assist,
                    "stop_split": self.stop_split,
                    "remain": self.remain
                },
                "tts": {
                    "vcn": self.voice,
                    "speed": self.speed,
                    "volume": self.volume,
                    "pitch": self.pitch,
                    "bgs": 0,
                    "reg": 0,
                    "rdn": 0,
                    "rhy": 0,
                    "audio": {
                        "encoding": self.format,
                        "sample_rate": self.sample_rate,
                        "channels": 1,
                        "bit_depth": 16,
                        "frame_size": 0
                    }
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": status,
                    "seq": self.text_seq,
                    "text": base64.b64encode(text.encode('utf-8')).decode('utf-8')
                }
            }
        }
