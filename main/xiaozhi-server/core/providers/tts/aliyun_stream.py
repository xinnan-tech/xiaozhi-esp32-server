import uuid
import json
import hmac
import hashlib
import base64
import time
import queue
import asyncio
import traceback
import websockets
import websockets.protocol
import os
import random
import threading
import concurrent.futures
import sys
from datetime import datetime
from urllib import parse
from typing import Optional
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from core.utils.tts import MarkdownCleaner
from core.utils import opus_encoder_utils, textUtils
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",  # 使用上海地域进行Token获取
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        
        query_string = AccessToken._encode_dict(parameters)
        string_to_sign = (
            "GET"
            + "&"
            + AccessToken._encode_text("/")
            + "&"
            + AccessToken._encode_text(query_string)
        )
        
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        signature = AccessToken._encode_text(signature)
        
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (
            signature,
            query_string,
        )
        
        import requests
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            key = "Token"
            if key in root_obj:
                token = root_obj[key]["Id"]
                expire_time = root_obj[key]["ExpireTime"]
                return token, expire_time
        return None, None


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # 设置为流式接口类型
        self.interface_type = InterfaceType.SINGLE_STREAM
        
        # 基础配置
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.appkey = config.get("appkey")
        self.format = config.get("format", "pcm")
        self.audio_file_type = config.get("format", "pcm")
        
        # 采样率配置
        sample_rate = config.get("sample_rate", "16000")
        self.sample_rate = int(sample_rate) if sample_rate else 16000
        
        # 音色配置 - CosyVoice大模型音色
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "longxiaochun")  # CosyVoice默认音色
        
        # 音频参数配置
        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50
        
        speech_rate = config.get("speech_rate", "0")
        self.speech_rate = int(speech_rate) if speech_rate else 0
        
        pitch_rate = config.get("pitch_rate", "0")
        self.pitch_rate = int(pitch_rate) if pitch_rate else 0
        
        # WebSocket配置
        self.host = config.get("host", "nls-gateway-cn-beijing.aliyuncs.com")
        self.ws_url = f"wss://{self.host}/ws/v1"
        self.ws = None
        
        # 流式相关配置
        self.before_stop_play_files = []
        self.segment_count = 0
        
        # 创建Opus编码器
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )
        
        # PCM缓冲区
        self.pcm_buffer = bytearray()
        
        # Token管理
        if self.access_key_id and self.access_key_secret:
            self._refresh_token()
        else:
            self.token = config.get("token")
            self.expire_time = None

    def _refresh_token(self):
        """刷新Token并记录过期时间"""
        if self.access_key_id and self.access_key_secret:
            self.token, expire_time_str = AccessToken.create_token(
                self.access_key_id, self.access_key_secret
            )
            if not expire_time_str:
                raise ValueError("无法获取有效的Token过期时间")

            try:
                expire_str = str(expire_time_str).strip()
                if expire_str.isdigit():
                    expire_time = datetime.fromtimestamp(int(expire_str))
                else:
                    expire_time = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%SZ")
                self.expire_time = expire_time.timestamp() - 60
            except Exception as e:
                raise ValueError(f"无效的过期时间格式: {expire_str}") from e
        else:
            self.expire_time = None

        if not self.token:
            raise ValueError("无法获取有效的访问Token")

    def _is_token_expired(self):
        """检查Token是否过期"""
        if not self.expire_time:
            return False
        return time.time() > self.expire_time

    async def _ensure_connection(self):
        """确保WebSocket连接可用"""
        # 检查连接状态，兼容不同版本的websockets库
        need_reconnect = False
        if self.ws is None:
            need_reconnect = True
        else:
            try:
                # 尝试访问closed属性，如果不存在则检查state
                if hasattr(self.ws, 'closed'):
                    need_reconnect = self.ws.closed
                elif hasattr(self.ws, 'state'):
                    # websockets 新版本使用state属性
                    need_reconnect = self.ws.state != websockets.protocol.State.OPEN
                else:
                    # 如果都没有，尝试发送ping来检测连接状态
                    try:
                        await asyncio.wait_for(self.ws.ping(), timeout=2.0)
                    except:
                        need_reconnect = True
            except:
                need_reconnect = True
        
        if need_reconnect:
            # 清理旧连接
            if self.ws:
                try:
                    if hasattr(self.ws, 'close'):
                        if asyncio.iscoroutinefunction(self.ws.close):
                            await self.ws.close()
                        else:
                            self.ws.close()
                except:
                    pass
                finally:
                    self.ws = None
            
            if self._is_token_expired():
                logger.bind(tag=TAG).warning("Token已过期，正在自动刷新...")
                self._refresh_token()
            
            # 重试连接机制
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    self.ws = await asyncio.wait_for(
                        websockets.connect(
                            self.ws_url,
                            additional_headers={
                                "X-NLS-Token": self.token,
                            },
                            ping_interval=30,
                            ping_timeout=10,
                            close_timeout=10,
                        ),
                        timeout=10.0
                    )
                    logger.bind(tag=TAG).info("阿里云CosyVoice流式TTS WebSocket连接建立成功")
                    return
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"WebSocket连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                    else:
                        logger.bind(tag=TAG).error(f"WebSocket连接最终失败: {e}")
                        raise

    def tts_text_priority_thread(self):
        """流式文本处理线程"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if message.sentence_type == SentenceType.FIRST:
                    # 初始化参数
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.segment_count = 0
                    self.tts_audio_first_sentence = True
                    self.before_stop_play_files.clear()
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        self.to_tts_single_stream(segment_text)

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    self.before_stop_play_files.append(
                        (message.content_file, message.content_detail)
                    )

                if message.sentence_type == SentenceType.LAST:
                    # 处理剩余的文本
                    self._process_remaining_text(True)

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )

    def _process_remaining_text(self, is_last=False):
        """处理剩余的文本并生成语音"""
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars:]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                self.to_tts_single_stream(segment_text, is_last)
                self.processed_chars += len(full_text)
            else:
                self._process_before_stop_play_files()
        else:
            self._process_before_stop_play_files()

    def to_tts_single_stream(self, text, is_last=False):
        """流式TTS处理 - 使用线程池执行异步任务"""
        try:
            text = MarkdownCleaner.clean_markdown(text)
            
            # 使用线程池来执行异步任务，避免事件循环冲突
            def run_async_task():
                """在新线程中运行异步任务"""
                try:
                    # 创建新的事件循环用于这个线程
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Windows下设置事件循环策略
                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    
                    try:
                        # 运行TTS任务
                        loop.run_until_complete(self._tts_request_unified(text, is_last))
                        return True
                    finally:
                        # 安全关闭事件循环
                        try:
                            # 取消所有未完成的任务
                            pending = asyncio.all_tasks(loop)
                            if pending:
                                for task in pending:
                                    task.cancel()
                                # 等待任务取消完成
                                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception as cleanup_error:
                            logger.bind(tag=TAG).debug(f"清理事件循环异常: {cleanup_error}")
                        finally:
                            loop.close()
                            
                except Exception as e:
                    logger.bind(tag=TAG).error(f"异步任务执行失败: {e}")
                    return False
            
            # 使用线程池执行异步任务
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_task)
                success = future.result(timeout=30)  # 30秒超时
                
                if success:
                    logger.bind(tag=TAG).info(f"语音生成成功: {text}")
                else:
                    logger.bind(tag=TAG).error(f"语音生成失败: {text}")
                    self.tts_audio_queue.put((SentenceType.LAST, [], None))
                
        except concurrent.futures.TimeoutError:
            logger.bind(tag=TAG).error(f"TTS任务超时: {text}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS处理异常: {text}, 错误: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))
        
        return None

    async def text_to_speak(self, text, is_last=False):
        """流式处理TTS音频"""
        try:
            # 确保连接可用
            await self._ensure_connection()
            ws_connection = self.ws
            
            # 确保Token有效
            if self._is_token_expired():
                self._refresh_token()
            
            # 生成task_id和message_id
            task_id = str(uuid.uuid4()).replace('-', '')
            
            # 第一阶段：发送StartSynthesis指令（设置参数）
            start_message_id = str(uuid.uuid4()).replace('-', '')
            start_request = {
                "header": {
                    "message_id": start_message_id,
                    "task_id": task_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "StartSynthesis",
                    "appkey": self.appkey,
                },
                "payload": {
                    "voice": self.voice,
                    "format": self.format,
                    "sample_rate": self.sample_rate,
                    "volume": self.volume,
                    "speech_rate": self.speech_rate,
                    "pitch_rate": self.pitch_rate,
                }
            }
            
            await ws_connection.send(json.dumps(start_request))
            logger.bind(tag=TAG).debug(f"发送StartSynthesis指令: {start_message_id}")
            
            # 第二阶段：发送RunSynthesis指令（发送文本）
            run_message_id = str(uuid.uuid4()).replace('-', '')
            run_request = {
                "header": {
                    "message_id": run_message_id,
                    "task_id": task_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "RunSynthesis",
                    "appkey": self.appkey,
                },
                "payload": {
                    "text": text
                }
            }
            
            await ws_connection.send(json.dumps(run_request))
            logger.bind(tag=TAG).debug(f"发送RunSynthesis指令: {text} (message_id: {run_message_id})")
            
            # 立即发送StopSynthesis指令，避免IDLE_TIMEOUT
            stop_message_id = str(uuid.uuid4()).replace('-', '')
            stop_request = {
                "header": {
                    "message_id": stop_message_id,
                    "task_id": task_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "StopSynthesis",
                    "appkey": self.appkey,
                }
            }
            
            await ws_connection.send(json.dumps(stop_request))
            logger.bind(tag=TAG).debug(f"发送StopSynthesis指令: {stop_message_id}")
            
            # 初始化缓冲区和计数器
            self.pcm_buffer.clear()
            self.segment_count = 0  # 重置分段计数器
            opus_datas_cache = []
            
            # 发送第一个音频包
            self.tts_audio_queue.put((SentenceType.FIRST, [], text))
            
            # 标记是否需要发送StopSynthesis
            synthesis_completed = False
            
            # 处理响应 - 设置超时避免长时间等待
            try:
                async def process_messages():
                    nonlocal synthesis_completed
                    async for message in ws_connection:
                        try:
                            if isinstance(message, str):
                                # 处理JSON消息
                                data = json.loads(message)
                                header = data.get("header", {})
                                event_name = header.get("name")
                                
                                if event_name == "SynthesisStarted":
                                    logger.bind(tag=TAG).debug(f"TTS合成已启动: {task_id}")
                                    
                                elif event_name == "SynthesisCompleted":
                                    logger.bind(tag=TAG).debug(f"TTS合成完成: {text}")
                                    synthesis_completed = True
                                    break
                                    
                                elif event_name == "TaskFailed":
                                    error_msg = header.get("status_text", "未知错误")
                                    logger.bind(tag=TAG).error(f"TTS合成失败: {error_msg}")
                                    synthesis_completed = True
                                    break
                            
                            elif isinstance(message, bytes):
                                # 处理二进制音频数据
                                self.pcm_buffer.extend(message)
                                
                                # 计算每帧的字节数
                                frame_bytes = int(
                                    self.opus_encoder.sample_rate
                                    * self.opus_encoder.channels
                                    * self.opus_encoder.frame_size_ms
                                    / 1000
                                    * 2
                                )
                                
                                # 分帧处理PCM数据
                                while len(self.pcm_buffer) >= frame_bytes:
                                    frame = bytes(self.pcm_buffer[:frame_bytes])
                                    del self.pcm_buffer[:frame_bytes]
                                    
                                    # 编码为Opus
                                    opus_packets = self.opus_encoder.encode_pcm_to_opus(frame, False)
                                    if opus_packets:
                                        if self.segment_count < 10:
                                            self.tts_audio_queue.put(
                                                (SentenceType.MIDDLE, opus_packets, None)
                                            )
                                            self.segment_count += 1
                                        else:
                                            opus_datas_cache.extend(opus_packets)
                        
                        except json.JSONDecodeError:
                            logger.bind(tag=TAG).warning("收到无效的JSON消息")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"处理响应消息失败: {e}")
                
                await asyncio.wait_for(process_messages(), timeout=15)  # 15秒超时
                            
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning(f"TTS请求超时，但可能已获取部分音频数据: {text}")
            except websockets.ConnectionClosed:
                logger.bind(tag=TAG).debug("WebSocket连接已正常关闭")
            except Exception as e:
                logger.bind(tag=TAG).error(f"处理WebSocket消息失败: {e}")
            
            # 因为已经提前发送了StopSynthesis，这里不需要再次发送
            # 直接处理剩余的PCM数据
            if self.pcm_buffer:
                opus_packets = self.opus_encoder.encode_pcm_to_opus(
                    bytes(self.pcm_buffer), end_of_stream=True
                )
                if opus_packets:
                    if self.segment_count < 10:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_packets, None)
                        )
                        self.segment_count += 1
                    else:
                        opus_datas_cache.extend(opus_packets)
                self.pcm_buffer.clear()
            
            # 发送缓存的数据
            if self.segment_count >= 10 and opus_datas_cache:
                self.tts_audio_queue.put(
                    (SentenceType.MIDDLE, opus_datas_cache, None)
                )
            
            # 如果是最后一段，处理待播放文件
            if is_last:
                self._process_before_stop_play_files()
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS异步请求异常: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

    async def _tts_request_unified(self, text: str, is_last: bool) -> None:
        """统一的TTS请求方法"""
        ws_connection = None
        
        try:
            # 确保Token有效
            if self._is_token_expired():
                self._refresh_token()
            
            # 总是创建独立连接，避免与其他线程的事件循环冲突
            ws_url = f"wss://{self.host}/ws/v1"
            ws_connection = await asyncio.wait_for(
                websockets.connect(
                    ws_url,
                    additional_headers={
                        "X-NLS-Token": self.token,
                    },
                    ping_interval=15,   # 每15秒发送ping，保持连接活跃
                    ping_timeout=5,     # ping超时时间5秒
                    close_timeout=3,    # 关闭超时时间3秒
                ),
                timeout=8.0  # 连接超时时间8秒
            )
            logger.bind(tag=TAG).debug(f"建立独立WebSocket连接: {text}")
            
            # 生成task_id
            task_id = str(uuid.uuid4()).replace('-', '')
            
            # 第一阶段：发送StartSynthesis指令（设置参数）
            start_message_id = str(uuid.uuid4()).replace('-', '')
            start_request = {
                "header": {
                    "message_id": start_message_id,
                    "task_id": task_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "StartSynthesis",
                    "appkey": self.appkey,
                },
                "payload": {
                    "voice": self.voice,
                    "format": self.format,
                    "sample_rate": self.sample_rate,
                    "volume": self.volume,
                    "speech_rate": self.speech_rate,
                    "pitch_rate": self.pitch_rate,
                }
            }
            
            await ws_connection.send(json.dumps(start_request))
            logger.bind(tag=TAG).debug(f"发送StartSynthesis指令: {start_message_id}")
            
            # 第二阶段：发送RunSynthesis指令（发送文本）
            run_message_id = str(uuid.uuid4()).replace('-', '')
            run_request = {
                "header": {
                    "message_id": run_message_id,
                    "task_id": task_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "RunSynthesis",
                    "appkey": self.appkey,
                },
                "payload": {
                    "text": text
                }
            }
            
            await ws_connection.send(json.dumps(run_request))
            logger.bind(tag=TAG).debug(f"发送RunSynthesis指令: {text} (message_id: {run_message_id})")
            
            # 立即发送StopSynthesis指令，避免IDLE_TIMEOUT
            stop_message_id = str(uuid.uuid4()).replace('-', '')
            stop_request = {
                "header": {
                    "message_id": stop_message_id,
                    "task_id": task_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "StopSynthesis",
                    "appkey": self.appkey,
                }
            }
            
            await ws_connection.send(json.dumps(stop_request))
            logger.bind(tag=TAG).debug(f"发送StopSynthesis指令: {stop_message_id}")
            
            # 初始化处理参数 - 使用独立缓冲区
            pcm_buffer = bytearray()
            opus_datas_cache = []
            segment_count = 0
            self.segment_count = 0  # 同时重置实例变量
            synthesis_completed = False
            
            # 发送第一个音频包
            self.tts_audio_queue.put((SentenceType.FIRST, [], text))
            
            # 处理响应 - 设置超时时间避免长时间等待
            timeout_duration = 15  # 15秒超时
            try:
                # 使用asyncio.wait_for替代asyncio.timeout以保证兼容性
                async def process_messages():
                    nonlocal synthesis_completed, segment_count, pcm_buffer, opus_datas_cache  # 声明使用外层变量
                    async for message in ws_connection:
                        try:
                            if isinstance(message, str):
                                # 处理JSON消息
                                data = json.loads(message)
                                header = data.get("header", {})
                                event_name = header.get("name")
                                
                                if event_name == "SynthesisStarted":
                                    logger.bind(tag=TAG).debug(f"TTS合成已启动: {task_id}")
                                    
                                elif event_name == "SynthesisCompleted":
                                    logger.bind(tag=TAG).debug(f"TTS合成完成: {text}")
                                    synthesis_completed = True
                                    break
                                    
                                elif event_name == "TaskFailed":
                                    error_msg = header.get("status_text", "未知错误")
                                    logger.bind(tag=TAG).error(f"TTS合成失败: {error_msg}")
                                    synthesis_completed = True
                                    break
                            
                            elif isinstance(message, bytes):
                                # 处理二进制音频数据
                                pcm_buffer.extend(message)
                                
                                # 计算每帧的字节数
                                frame_bytes = int(
                                    self.opus_encoder.sample_rate
                                    * self.opus_encoder.channels
                                    * self.opus_encoder.frame_size_ms
                                    / 1000
                                    * 2
                                )
                                
                                # 分帧处理PCM数据
                                while len(pcm_buffer) >= frame_bytes:
                                    frame = bytes(pcm_buffer[:frame_bytes])
                                    del pcm_buffer[:frame_bytes]  # 清除已处理的数据
                                    
                                    # 编码为Opus
                                    opus_packets = self.opus_encoder.encode_pcm_to_opus(frame, False)
                                    if opus_packets:
                                        if segment_count < 10:
                                            self.tts_audio_queue.put(
                                                (SentenceType.MIDDLE, opus_packets, None)
                                            )
                                            segment_count += 1
                                        else:
                                            opus_datas_cache.extend(opus_packets)
                        
                        except json.JSONDecodeError:
                            logger.bind(tag=TAG).warning("收到无效的JSON消息")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"处理响应消息失败: {e}")
                
                await asyncio.wait_for(process_messages(), timeout=timeout_duration)
                            
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning(f"TTS请求超时，但可能已获取部分音频数据: {text}")
            except websockets.ConnectionClosed:
                logger.bind(tag=TAG).debug("WebSocket连接已正常关闭")
            except Exception as e:
                logger.bind(tag=TAG).error(f"处理WebSocket消息失败: {e}")
            
            # 因为已经提前发送了StopSynthesis，这里不需要再次发送
            # 直接处理剩余的PCM数据
            if pcm_buffer:
                opus_packets = self.opus_encoder.encode_pcm_to_opus(
                    bytes(pcm_buffer), end_of_stream=True
                )
                if opus_packets:
                    if segment_count < 10:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_packets, None)
                        )
                        segment_count += 1
                    else:
                        opus_datas_cache.extend(opus_packets)
            
            # 发送缓存的数据
            if segment_count >= 10 and opus_datas_cache:
                self.tts_audio_queue.put(
                    (SentenceType.MIDDLE, opus_datas_cache, None)
                )
            
            # 如果是最后一段，处理待播放文件
            if is_last:
                self._process_before_stop_play_files()
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS请求异常: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))
        finally:
            # 确保WebSocket连接被关闭
            if ws_connection:
                try:
                    if hasattr(ws_connection, 'close'):
                        if asyncio.iscoroutinefunction(ws_connection.close):
                            await ws_connection.close()
                        else:
                            ws_connection.close()
                except Exception as e:
                    logger.bind(tag=TAG).debug(f"关闭WebSocket连接时出现异常: {e}")
    async def close(self):
        """资源清理"""
        if self.ws:
            try:
                # 兼容不同版本的websockets库关闭方式
                if hasattr(self.ws, 'close'):
                    if asyncio.iscoroutinefunction(self.ws.close):
                        await self.ws.close()
                    else:
                        self.ws.close()
                elif hasattr(self.ws, 'close_connection'):
                    await self.ws.close_connection()
            except Exception as e:
                logger.bind(tag=TAG).debug(f"关闭WebSocket连接时出现异常: {e}")
            finally:
                self.ws = None
        
        if hasattr(self, "opus_encoder"):
            self.opus_encoder.close()
        
        await super().close()

    def _process_before_stop_play_files(self):
        """处理停止前的待播放文件"""
        for tts_file, text in self.before_stop_play_files:
            if tts_file and os.path.exists(tts_file):
                audio_datas = self._process_audio_file(tts_file)
                self.tts_audio_queue.put((SentenceType.MIDDLE, audio_datas, text))
        self.before_stop_play_files.clear()
        self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def _process_audio_file(self, tts_file):
        """处理音频文件并转换为指定格式"""
        audio_datas = []
        if self.conn.audio_format == "pcm":
            audio_datas, _ = self.audio_to_pcm_data(tts_file)
        else:
            audio_datas, _ = self.audio_to_opus_data(tts_file)

        if (
            self.delete_audio_file
            and tts_file is not None
            and os.path.exists(tts_file)
            and tts_file.startswith(self.output_file)
        ):
            os.remove(tts_file)
        return audio_datas

    def to_tts(self, text: str) -> list:
        """非流式TTS处理，用于测试及保存音频文件的场景"""
        start_time = time.time()
        text = MarkdownCleaner.clean_markdown(text)
        
        try:
            # 使用同步方式进行TTS转换
            if self._is_token_expired():
                self._refresh_token()
                
            # 构造请求数据
            request_json = {
                "appkey": self.appkey,
                "token": self.token,
                "text": text,
                "format": "pcm",
                "sample_rate": self.sample_rate,
                "voice": self.voice,
                "volume": self.volume,
                "speech_rate": self.speech_rate,
                "pitch_rate": self.pitch_rate,
            }
            
            # 使用HTTP接口进行同步请求
            import requests
            api_url = f"https://{self.host}/stream/v1/tts"
            headers = {"Content-Type": "application/json"}
            
            resp = requests.post(api_url, json=request_json, headers=headers)
            
            if resp.status_code == 401:  # Token过期特殊处理
                self._refresh_token()
                resp = requests.post(api_url, json=request_json, headers=headers)
            
            if resp.headers["Content-Type"].startswith("audio/"):
                pcm_data = resp.content
                
                # 使用opus编码器处理PCM数据
                opus_datas = []
                frame_bytes = int(
                    self.opus_encoder.sample_rate
                    * self.opus_encoder.channels
                    * self.opus_encoder.frame_size_ms
                    / 1000
                    * 2
                )
                
                # 分帧处理PCM数据
                for i in range(0, len(pcm_data), frame_bytes):
                    frame = pcm_data[i:i + frame_bytes]
                    if len(frame) == frame_bytes:
                        opus = self.opus_encoder.encode_pcm_to_opus(frame, False)
                        if opus:
                            opus_datas.extend(opus)
                
                logger.bind(tag=TAG).info(f"TTS请求成功: {text}, 耗时: {time.time() - start_time}秒")
                return opus_datas
            else:
                logger.bind(tag=TAG).error(f"TTS请求失败: {resp.content}")
                return []
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS请求异常: {e}")
            return []
    
    def _get_segment_text(self):
        """获取当前可以处理的文本段"""
        if not self.tts_text_buff:
            return None
        
        full_text = "".join(self.tts_text_buff)
        if len(full_text) <= self.processed_chars:
            return None
        
        # 获取未处理的文本
        remaining_text = full_text[self.processed_chars:]
        
        # 如果文本较短或者到达了句子结尾标点，直接处理
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n']
        if len(remaining_text) < 20:
            return None
        
        # 查找句子结尾
        for i, char in enumerate(remaining_text):
            if char in sentence_endings and i > 10:  # 至少10个字符
                segment = remaining_text[:i+1]
                segment_text = textUtils.get_string_no_punctuation_or_emoji(segment)
                if segment_text:
                    self.processed_chars += i + 1
                    return segment_text
        
        # 如果没有找到句子结尾，但文本足够长，按长度分段
        if len(remaining_text) > 50:
            segment = remaining_text[:30]
            segment_text = textUtils.get_string_no_punctuation_or_emoji(segment)
            if segment_text:
                self.processed_chars += 30
                return segment_text
        
        return None
