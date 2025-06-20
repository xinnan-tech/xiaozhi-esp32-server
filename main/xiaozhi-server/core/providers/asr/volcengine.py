import time
import wave
import os
from typing import Optional, Tuple, List
import uuid
import websockets
import json
import base64

from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()
import asyncio
import opuslib_next # 假设需要 opus 解码


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.interface_type = InterfaceType.STREAM # 修改为流式
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.output_dir = config.get("output_dir")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"
        if self.output_dir is None:
            self.output_dir = "tmp/"
        self.delete_audio_file = delete_audio_file
        self.ws_url = f"wss://{self.host}/v1/realtime?model={self.model_name}"
        self.success_code = 1000
        self.seg_duration = 15000

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 新增流式处理所需的状态变量
        self.asr_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.forward_task: Optional[asyncio.Task] = None
        self.is_processing: bool = False
        self.text: str = "" # 用于存储当前识别的文本
        self.decoder = opuslib_next.Decoder(16000, 1) # 如果输入是 opus
        self.current_session_id: Optional[str] = None
        self.audio_buffer = bytearray() # 用于缓存音频数据

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)
        self.current_session_id = conn.session_id # 保存当前会话 ID

    async def receive_audio(self, conn, audio: bytes, audio_have_voice: bool):
        if not self.current_session_id:
            self.current_session_id = conn.session_id

        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
        # 如果本次没有声音，本段也没声音，就把声音丢弃了
        conn.asr_audio.append(audio)
        if have_voice == False and conn.client_have_voice == False:
            conn.asr_audio = conn.asr_audio[-10:]
            return

        if have_voice and self.asr_ws is None and not self.is_processing:
            try:
                self.is_processing = True
                logger.bind(tag=TAG).info(f"Connecting to ASR service: {self.ws_url}")
                auth_header = {"Authorization": f"Bearer {self.api_key}"}
                self.asr_ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=auth_header,
                    close_timeout=10
                )

                # 启动任务来接收和处理 ASR 结果
                self.forward_task = asyncio.create_task(self._forward_asr_results(conn))
                 
                # 发送初始化/会话开始请求
                init_request = self._create_stream_start_msg() # 需要实现此方法
                await self.asr_ws.send(json.dumps(init_request))
                logger.bind(tag=TAG).info(f"Sent init request: {init_request}")

                # 发送缓存的音频数据
                if conn.asr_audio and len(conn.asr_audio) > 0:
                    pcm_frame = self.decode_opus(conn.asr_audio)
                    await self._send_audio_chunk(b''.join(pcm_frame), False if have_voice else True)
                    conn.asr_audio.clear()

            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to establish ASR connection: {e}", exc_info=True)
                if self.asr_ws:
                    await self.asr_ws.close()
                    self.asr_ws = None
                self.is_processing = False
                return

        # 发送当前音频数据
        if self.asr_ws and self.is_processing:
            try:
                logger.bind(tag=TAG).debug(f"Append audio data")
                pcm_frame = self.decode_opus(conn.asr_audio)
                await self._send_audio_chunk(b''.join(pcm_frame),False if have_voice else True)
                conn.asr_audio.clear()
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error sending audio data: {e}", exc_info=True)
    
    async def _send_audio_chunk(self, pcm_data: bytes, completed = False):
        if not self.asr_ws or not self.is_processing:
            return
        
        # 火山引擎流式 ASR 可能需要将 PCM 数据进行 Base64 编码或直接发送二进制
        # 这里假设直接发送二进制，并构造成 JSON 消息
        # 请参考火山引擎流式 ASR 文档确定正确的格式
        base64_audio = base64.b64encode(pcm_data).decode("utf-8")
        audio_event = {
            "audio": base64_audio,
        }
        audio_event["type"] = "input_audio_buffer.commit" if completed else "input_audio_buffer.append"
        await self.asr_ws.send(json.dumps(audio_event))
        logger.bind(tag=TAG).debug(f"Sent audio chunk, size: {len(pcm_data)} , completed: {completed}")

    def _create_stream_start_msg(self) -> dict:
        """创建流式识别开始的请求消息，具体格式需参考火山引擎文档"""
        # 参考之前的 _create_session_msg，但可能需要不同的参数和类型
        config = {
            "input_audio_format": "pcm",
            "input_audio_codec": "raw",
            "input_audio_sample_rate": 16000,
            "input_audio_bits": 16,
            "input_audio_channel": 1,
            "input_audio_transcription": {
                "model": self.model_name,
            #    "stream": True # 标识为流式
            },
            "session_id": self.current_session_id or str(uuid.uuid4()), # 确保有 session_id
        }
        event = {
            "type": "transcription_session.update", # 假设的开始消息类型
            "session": config
        }
        return event

    async def _forward_asr_results(self, conn):
        try:
            while self.asr_ws and not conn.stop_event.is_set() and self.is_processing:
                try:
                    message = await self.asr_ws.recv()
                    event = json.loads(message)
                    logger.bind(tag=TAG).debug(f"Received ASR result: {event}")

                    # 解析火山引擎流式 ASR 的响应格式
                    # 以下为示例，具体字段需要参考文档
                    message_type = event.get("type")
                    if message_type == 'conversation.item.input_audio_transcription.result': # 假设的中间结果类型
                        transcript_segment = event.get("transcript", "")
                        is_final = event.get("is_final", False)
                        self.text += transcript_segment # 累加中间结果
                        if is_final:
                            logger.bind(tag=TAG).info(f"Final ASR result: {self.text}")
                            conn.reset_vad_states() # 假设有 VAD 状态重置
                            await self.handle_voice_stop(conn, None) # 触发语音结束处理
                            # self.text = "" # 清空，等待下一次识别
                            # 注意：这里可能需要更复杂的逻辑来处理会话结束和文本清空
                    elif message_type == 'conversation.item.input_audio_transcription.completed': # 假设的最终完成类型
                        final_transcript = event.get("transcript", self.text)
                        logger.bind(tag=TAG).info(f"ASR transcription completed: {final_transcript}")
                        self.text = final_transcript # 确保使用最终结果
                        conn.reset_vad_states()
                        await self.handle_voice_stop(conn, None)
                        self.text = "" # 清空
                        # await self.stop_ws_connection() # 收到完成后可以考虑关闭连接
                        break # 结束接收任务
                    elif message_type == 'error': # 假设的错误类型
                        error_msg = event.get("message", "Unknown ASR error")
                        logger.bind(tag=TAG).error(f"ASR service error: {error_msg}")
                        break

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("ASR WebSocket connection closed.")
                    break
                except json.JSONDecodeError:
                    logger.bind(tag=TAG).error(f"Failed to decode JSON from ASR: {message}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing ASR result: {e}", exc_info=True)
                    break
        finally:
            logger.bind(tag=TAG).info("ASR forward task finished.")
            # 确保在任务结束时，如果连接还存在，则关闭
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            # self.text = "" # 确保文本清空

    def stop_ws_connection(self):
        logger.bind(tag=TAG).info("Stopping ASR WebSocket connection...")     
        if self.asr_ws:
            try:
                asyncio.create_task(self.asr_ws.close())
                logger.bind(tag=TAG).info("ASR WebSocket connection closed successfully.")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error closing ASR WebSocket: {e}")
            finally:
                self.asr_ws = None
        self.audio_buffer.clear()
        # self.text = "" # 确保文本清空

    @staticmethod
    def slice_data(data: bytes, chunk_size: int) -> (list, bool):
        """
        slice data
        :param data: wav data
        :param chunk_size: the segment size in one request
        :return: segment data, last flag
        """
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset : offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset:data_len], True

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """在流式模式下，此方法通常返回当前已识别的文本，并在语音结束时由 _forward_asr_results 处理。"""
    
        file_path = None
        if not self.delete_audio_file and self.current_session_id:
            # 注意：这里的 pcm_data 来源需要明确，流式处理中可能需要累积所有 PCM 数据
            # 或者在语音结束后统一处理。当前实现中 pcm_data 未定义。
            # 暂时注释掉文件保存逻辑，因为 pcm_data 的获取方式在流式中不明确
            # pcm_data_to_save = b"".join(self.decode_opus(opus_data)) if audio_format != "pcm" else b"".join(opus_data)
            # if pcm_data_to_save:
            #     file_path = self.save_audio_to_file([pcm_data_to_save], self.current_session_id)
            pass # 暂时不处理文件保存

        current_text = self.text
        return current_text, file_path

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