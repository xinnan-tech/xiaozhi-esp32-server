import json
import gzip
import uuid
import asyncio
import websockets
import opuslib_next
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.max_retries = 3
        self.retry_delay = 2
        self.decoder = opuslib_next.Decoder(16000, 1)
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False  # 添加处理状态标志
        self.audio_cache = []  # 添加音频数据缓存用于保存文件

        # 配置参数
        self.appid = str(config.get("appid"))
        self.cluster = config.get("cluster")
        self.access_token = config.get("access_token")
        self.boosting_table_name = config.get("boosting_table_name", "")
        self.correct_table_name = config.get("correct_table_name", "")
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

        # 火山引擎ASR配置
        self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.uid = config.get("uid", "streaming_asr_service")
        self.workflow = config.get(
            "workflow", "audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate"
        )
        self.result_type = config.get("result_type", "single")
        self.format = config.get("format", "pcm")
        self.codec = config.get("codec", "pcm")
        self.rate = config.get("sample_rate", 16000)
        self.language = config.get("language", "zh-CN")
        self.bits = config.get("bits", 16)
        self.channel = config.get("channel", 1)
        self.auth_method = config.get("auth_method", "token")
        self.secret = config.get("secret", "access_secret")

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, audio, audio_have_voice):
        conn.asr_audio.append(audio)
        conn.asr_audio = conn.asr_audio[-10:]
        
        # 缓存音频数据用于保存文件
        self.audio_cache.append(audio)
        # 限制缓存大小，避免内存占用过多
        if len(self.audio_cache) > 100:
            self.audio_cache = self.audio_cache[-100:]

        # 如果本次有声音，且之前没有建立连接
        if audio_have_voice and self.asr_ws is None and not self.is_processing:
            try:
                self.is_processing = True
                # 建立新的WebSocket连接
                headers = self.token_auth() if self.auth_method == "token" else None
                logger.bind(tag=TAG).info(f"正在连接ASR服务，headers: {headers}")

                self.asr_ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    max_size=1000000000,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=10,
                )

                # 发送初始化请求
                request_params = self.construct_request(str(uuid.uuid4()))
                try:
                    payload_bytes = str.encode(json.dumps(request_params))
                    payload_bytes = gzip.compress(payload_bytes)
                    full_client_request = self.generate_header()
                    full_client_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                    full_client_request.extend(payload_bytes)

                    logger.bind(tag=TAG).info(f"发送初始化请求: {request_params}")
                    await self.asr_ws.send(full_client_request)

                    # 等待初始化响应
                    init_res = await self.asr_ws.recv()
                    result = self.parse_response(init_res)
                    logger.bind(tag=TAG).info(f"收到初始化响应: {result}")

                    # 检查初始化响应
                    if "code" in result and result["code"] != 1000:
                        error_msg = f"ASR服务初始化失败: {result.get('payload_msg', {}).get('error', '未知错误')}"
                        logger.bind(tag=TAG).error(error_msg)
                        raise Exception(error_msg)

                except Exception as e:
                    logger.bind(tag=TAG).error(f"发送初始化请求失败: {str(e)}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).error(f"错误原因: {str(e.__cause__)}")
                    raise e

                # 启动接收ASR结果的异步任务
                self.forward_task = asyncio.create_task(self._forward_asr_results(conn))

                # 发送缓存的音频数据
                if conn.asr_audio and len(conn.asr_audio) > 0:
                    for cached_audio in conn.asr_audio[-10:]:
                        try:
                            pcm_frame = self.decoder.decode(cached_audio, 960)
                            payload = gzip.compress(pcm_frame)
                            audio_request = bytearray(
                                self.generate_audio_default_header()
                            )
                            audio_request.extend(len(payload).to_bytes(4, "big"))
                            audio_request.extend(payload)
                            await self.asr_ws.send(audio_request)
                        except Exception as e:
                            logger.bind(tag=TAG).info(
                                f"发送缓存音频数据时发生错误: {e}"
                            )

            except Exception as e:
                logger.bind(tag=TAG).error(f"建立ASR连接失败: {str(e)}")
                if hasattr(e, "__cause__") and e.__cause__:
                    logger.bind(tag=TAG).error(f"错误原因: {str(e.__cause__)}")
                if self.asr_ws:
                    await self.asr_ws.close()
                    self.asr_ws = None
                self.is_processing = False
                return

        # 发送当前音频数据
        if self.asr_ws and self.is_processing:
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                payload = gzip.compress(pcm_frame)
                audio_request = bytearray(self.generate_audio_default_header())
                audio_request.extend(len(payload).to_bytes(4, "big"))
                audio_request.extend(payload)
                await self.asr_ws.send(audio_request)
            except Exception as e:
                logger.bind(tag=TAG).info(f"发送音频数据时发生错误: {e}")

    async def _forward_asr_results(self, conn):
        try:
            while self.asr_ws and not conn.stop_event.is_set():
                try:
                    response = await self.asr_ws.recv()
                    result = self.parse_response(response)
                    logger.bind(tag=TAG).debug(f"收到ASR结果: {result}")

                    if "payload_msg" in result:
                        payload = result["payload_msg"]
                        # 检查是否是错误码1013（无有效语音）
                        if "code" in payload and payload["code"] == 1013:
                            # 静默处理，不记录错误日志
                            continue

                        if "result" in payload:
                            utterances = payload["result"].get("utterances", [])
                            # 检查duration和空文本的情况
                            if (
                                payload.get("audio_info", {}).get("duration", 0) > 2000
                                and not utterances
                                and not payload["result"].get("text")
                            ):
                                logger.info(f"payload: {payload}")
                                logger.bind(tag=TAG).error(f"识别文本：空")
                                self.text = ""
                                conn.reset_vad_states()
                                await self.handle_voice_stop(conn, [])
                                break

                            for utterance in utterances:
                                if utterance.get("definite", False):
                                    self.text = utterance["text"]
                                    logger.bind(tag=TAG).info(
                                        f"识别到文本: {self.text}"
                                    )
                                    conn.reset_vad_states()
                                    await self.handle_voice_stop(conn, [])
                                    break
                        elif "error" in payload:
                            error_msg = payload.get("error", "未知错误")
                            logger.bind(tag=TAG).error(f"ASR服务返回错误: {error_msg}")
                            break

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

    def stop_ws_connection(self):
        if self.asr_ws:
            asyncio.create_task(self.asr_ws.close())
            self.asr_ws = None
        self.is_processing = False

    def construct_request(self, reqid):
        req = {
            "app": {
                "appid": self.appid,
                "cluster": self.cluster,
                "token": self.access_token,
            },
            "user": {"uid": self.uid},
            "request": {
                "reqid": reqid,
                "workflow": self.workflow,
                "show_utterances": True,
                "result_type": self.result_type,
                "sequence": 1,
                "boosting_table_name": self.boosting_table_name,
                "correct_table_name": self.correct_table_name,
                "end_window_size": 200,
            },
            "audio": {
                "format": self.format,
                "codec": self.codec,
                "rate": self.rate,
                "language": self.language,
                "bits": self.bits,
                "channel": self.channel,
                "sample_rate": self.rate,
            },
        }
        logger.bind(tag=TAG).debug(
            f"构造请求参数: {json.dumps(req, ensure_ascii=False)}"
        )
        return req

    def token_auth(self):
        return {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

    def generate_header(
        self,
        version=0x01,
        message_type=0x01,
        message_type_specific_flags=0x00,
        serial_method=0x01,
        compression_type=0x01,
        reserved_data=0x00,
        extension_header: bytes = b"",
    ):
        header = bytearray()
        header_size = int(len(extension_header) / 4) + 1
        header.append((version << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        header.extend(extension_header)
        return header

    def generate_audio_default_header(self):
        return self.generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x00,
            serial_method=0x01,
            compression_type=0x01,
        )

    def generate_last_audio_default_header(self):
        return self.generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x02,
            serial_method=0x01,
            compression_type=0x01,
        )

    def parse_response(self, res: bytes) -> dict:
        try:
            # 检查响应长度
            if len(res) < 4:
                logger.bind(tag=TAG).error(f"响应数据长度不足: {len(res)}")
                return {"error": "响应数据长度不足"}

            # 获取消息头
            header = res[:4]
            message_type = header[1] >> 4

            # 如果是错误响应
            if message_type == 0x0F:  # SERVER_ERROR_RESPONSE
                code = int.from_bytes(res[4:8], "big", signed=False)
                msg_length = int.from_bytes(res[8:12], "big", signed=False)
                error_msg = json.loads(res[12:].decode("utf-8"))
                return {
                    "code": code,
                    "msg_length": msg_length,
                    "payload_msg": error_msg,
                }

            # 获取JSON数据（跳过12字节头部）
            try:
                json_data = res[12:].decode("utf-8")
                result = json.loads(json_data)
                logger.bind(tag=TAG).debug(f"成功解析JSON响应: {result}")
                return {"payload_msg": result}
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.bind(tag=TAG).error(f"JSON解析失败: {str(e)}")
                logger.bind(tag=TAG).error(f"原始数据: {res}")
                raise

        except Exception as e:
            logger.bind(tag=TAG).error(f"解析响应失败: {str(e)}")
            logger.bind(tag=TAG).error(f"原始响应数据: {res.hex()}")
            raise

    async def speech_to_text(self, opus_data, session_id, audio_format):
        result = self.text
        self.text = ""  # 清空text
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

    async def handle_voice_stop(self, conn, asr_audio_task):
        """处理流式ASR的语音停止事件，包含音频保存逻辑"""
        try:
            # 对于流式ASR，使用缓存的音频数据
            if self.audio_cache and len(self.audio_cache) > 0:
                file_path = None
                pcm_data = []
                
                try:
                    # 判断是否保存为WAV文件
                    if not self.delete_audio_file:
                        # 解码音频数据为PCM
                        for audio_chunk in self.audio_cache:
                            try:
                                pcm_frame = self.decoder.decode(audio_chunk, 960)
                                pcm_data.append(pcm_frame)
                            except Exception as e:
                                logger.bind(tag=TAG).warning(f"解码音频块失败: {e}")
                                continue
                        
                        if pcm_data:
                            file_path = self.save_audio_to_file(pcm_data, conn.session_id)
                            logger.bind(tag=TAG).info(f"已保存音频文件: {file_path}")
                        
                except Exception as e:
                    logger.bind(tag=TAG).error(f"保存音频文件失败: {e}")
                
                # 处理声纹识别（如果有）
                speaker_name = None
                if self.voiceprint_provider and pcm_data:
                    try:
                        combined_pcm_data = b"".join(pcm_data)
                        wav_data = self._pcm_to_wav(combined_pcm_data)
                        if wav_data:
                            speaker_name = await self.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                            if speaker_name:
                                logger.bind(tag=TAG).info(f"声纹识别结果: {speaker_name}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"声纹识别失败: {e}")
                
                # 记录识别结果
                if self.text:
                    logger.bind(tag=TAG).info(f"识别文本: {self.text}")
                if speaker_name:
                    logger.bind(tag=TAG).info(f"识别说话人: {speaker_name}")
                
                # 检查文本长度
                text_len, _ = remove_punctuation_and_length(self.text)
                self.stop_ws_connection()
                
                if text_len > 0:
                    # 构建包含说话人信息的增强文本
                    enhanced_text = self._build_enhanced_text(self.text, speaker_name)
                    
                    # 使用自定义模块进行上报
                    await startToChat(conn, enhanced_text)
                    
                    try:
                        # 确保音频数据格式正确 - 使用原始音频缓存
                        audio_data_for_report = self.audio_cache.copy() if self.audio_cache else []
                        enqueue_asr_report(conn, enhanced_text, audio_data_for_report)
                        logger.bind(tag=TAG).info(f"enqueue_asr_report调用完成，音频包数量: {len(audio_data_for_report)}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"音频上报失败: {e}")
                        # 如果音频上报失败，至少保证文字上报
                        try:
                            enqueue_asr_report(conn, enhanced_text, [])
                            logger.bind(tag=TAG).info(f"文字上报成功（音频上报失败后的备用方案）")
                        except Exception as e2:
                            logger.bind(tag=TAG).error(f"文字上报也失败: {e2}")
                
                # 清空音频缓存
                self.audio_cache.clear()
                
            else:
                # 如果没有音频缓存，仍然进行聊天处理
                if self.text:
                    text_len, _ = remove_punctuation_and_length(self.text)
                    if text_len > 0:
                        await startToChat(conn, self.text)
                        enqueue_asr_report(conn, self.text, [])
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理语音停止事件失败: {e}")
            # 确保清空缓存
            self.audio_cache.clear()
