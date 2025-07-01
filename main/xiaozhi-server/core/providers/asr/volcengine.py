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
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length

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
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.forward_task: Optional[asyncio.Task] = None
        self.is_processing: bool = False
        self.text: str = "" # 用于存储当前识别的文本
        self.decoder = opuslib_next.Decoder(16000, 1) # 如果输入是 opus
        self.current_session_id: Optional[str] = None
        self.audio_buffer = bytearray() # 用于缓存音频数据

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)
        self.current_session_id = conn.session_id # 保存当前会话 ID
        self.conn = conn

    async def receive_audio(self, conn, audio: bytes, audio_have_voice: bool):
        if not self.current_session_id:
            self.current_session_id = conn.session_id
            logger.bind(tag=TAG).info(f"自动生成新的会话ID: {self.current_session_id}")
        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
        # 如果本次没有声音，本段也没声音，就把声音丢弃了
        conn.asr_audio.append(audio)
        if have_voice == False and conn.client_have_voice == False:
            conn.asr_audio = conn.asr_audio[-10:]
            return

        if have_voice and not self.is_processing:
            try:
                self.is_processing = True
                logger.bind(tag=TAG).info( f"session: {self.current_session_id} 开启会话")
                await self.start_session(self.current_session_id)
                pcm_frame = self.decode_opus(conn.asr_audio)
                await self._send_audio_chunk(b''.join(pcm_frame))
                conn.asr_audio.clear()
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to establish ASR connection: {e}", exc_info=True)
                if self.ws:
                    await self.ws.close()
                    self.ws = None
                self.is_processing = False
                return

        # 发送当前音频数据
        if self.ws and self.is_processing:
            try:
                logger.bind(tag=TAG).debug( f"session: {self.current_session_id} 发送语音数size: {len(audio)}")
                pcm_frame = self.decode_opus(conn.asr_audio)
                await self._send_audio_chunk(b''.join(pcm_frame))
                conn.asr_audio.clear()
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error sending audio data: {e}", exc_info=True)
        # TODO: 是否用conn.client_voice_stop  判断会话结束       
        if self.is_eou(conn, self.text) and self.ws and self.is_processing:
            logger.bind(tag=TAG).info( f"session: {self.current_session_id} 结束会话")
            await self.finish_session(self.current_session_id)
    
    async def _send_audio_chunk(self, pcm_data: bytes):
        if not self.ws or not self.is_processing:
            return
        
        # 火山引擎流式 ASR 可能需要将 PCM 数据进行 Base64 编码或直接发送二进制
        # 这里假设直接发送二进制，并构造成 JSON 消息
        # 请参考火山引擎流式 ASR 文档确定正确的格式
        base64_audio = base64.b64encode(pcm_data).decode("utf-8")
        audio_event = {
            "audio": base64_audio,
            "type": "input_audio_buffer.append"
        }
        await self.ws.send(json.dumps(audio_event))
        logger.bind(tag=TAG).debug(f"Sent audio chunk, size: {len(pcm_data)} ")


    async def _forward_asr_results(self):
        try:
            logger.bind(tag=TAG).debug(f"session: {self.current_session_id} ASR forward start.")
            while self.ws and not self.conn.stop_event.is_set() and self.is_processing:
                try:
                    message = await self.ws.recv()
                    event = json.loads(message)
                    logger.bind(tag=TAG).debug(f"session: {self.current_session_id} Received ASR result: {event}")

                    # 解析火山引擎流式 ASR 的响应格式
                    # 以下为示例，具体字段需要参考文档
                    message_type = event.get("type")
                    if message_type == 'conversation.item.input_audio_transcription.result': # 假设的中间结果类型
                        transcript_segment = event.get("transcript", "")
                        is_final = event.get("is_final", False)
                        self.text += transcript_segment # 累加中间结果
                        if is_final:
                            logger.bind(tag=TAG).info(f"Final ASR result: {self.text}")
                            self.conn.reset_vad_states() # 假设有 VAD 状态重置
                            await self.handle_voice_stop(self.conn, None) # 触发语音结束处理
                            # self.text = "" # 清空，等待下一次识别
                            # 注意：这里可能需要更复杂的逻辑来处理会话结束和文本清空
                    elif message_type == 'conversation.item.input_audio_transcription.completed': # 假设的最终完成类型
                        final_transcript = event.get("transcript", self.text)
                        logger.bind(tag=TAG).info(f"ASR transcription completed: {final_transcript}")
                        self.text = final_transcript # 确保使用最终结果
                        self.conn.reset_vad_states()
                        await self.handle_voice_stop(self.conn, None)
                        self.text = "" # 清空
                        # await self.stop_ws_connection() # 收到完成后可以考虑关闭连接
                        break # 结束接收任务
                    elif message_type == 'error': # 假设的错误类型
                        error_msg = event.get("message", "Unknown ASR error")
                        logger.bind(tag=TAG).error(f"ASR service error: {error_msg}")
                        break

                except websockets.ConnectionClosed:
                    await self.stop_ws_connection()
                    logger.bind(tag=TAG).error("ASR WebSocket connection closed.")
                    break
                except json.JSONDecodeError:
                    logger.bind(tag=TAG).error(f"Failed to decode JSON from ASR: {message}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing ASR result: {e}", exc_info=True)
                    break
        finally:
            logger.bind(tag=TAG).debug(f"session: {self.current_session_id} ASR forward task finished.")
            self.is_processing = False
            

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

      
    async def start_session(self, session_id):
        logger.bind(tag=TAG).debug(f"开始会话 {session_id}")
        try:
            # 建立新连接
            await self._ensure_connection()
            # 发送会话启动请求
            """创建流式识别开始的请求消息，具体格式需参考火山引擎文档"""
            config = {
                "input_audio_format": "pcm",
                "input_audio_codec": "raw",
                "input_audio_sample_rate": 16000,
                "input_audio_bits": 16,
                "input_audio_channel": 1,
                "input_audio_transcription": {
                    "model": self.model_name,
                },
                "session_id": session_id, # 确保有 session_id
            }
            event = {
                "type": "transcription_session.update", # 假设的开始消息类型
                "session": config
            }
            await self.ws.send(json.dumps(event))
            logger.bind(tag=TAG).debug(f"会话启动请求已发送, Send Event: {event}")
            # 启动监听任务
            if self.forward_task is None:
                self.forward_task = asyncio.create_task(self._forward_asr_results())
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动会话失败: {str(e)}")
            # 确保清理资源
            if hasattr(self, "forward_task"):
                try:
                    self.forward_task.cancel()
                    await self.forward_task
                except:
                    pass
                self.forward_task = None
            await self.stop_ws_connection()
            raise

    async def finish_session(self, session_id):    
        try:
            self.audio_buffer.clear()
            #self.is_processing = False
            if self.ws:
                done_payload = {
                    "type": "input_audio_buffer.commit"
                }
            await self.ws.send(json.dumps(done_payload))
            logger.bind(tag=TAG).debug(f"会话结束请求已发送,Send Event: {done_payload}")

        except Exception as e:
            await self.stop_ws_connection()
            logger.bind(tag=TAG).error(f"关闭会话失败: {str(e)}")
        
        # 等待监听任务完成
        if hasattr(self, "forward_task"):
            try:
                await self.forward_task
                logger.bind(tag=TAG).debug(f"退出monitor task")
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"等待监听任务完成时发生错误: {str(e)}"
                )
            finally:
                self.forward_task = None
                self.current_session_id = None
                
    # 处理语音停止
    async def handle_voice_stop(self, conn, asr_audio_task):
        raw_text, _ = await self.speech_to_text(
            asr_audio_task, conn.session_id, conn.audio_format
        )  # 确保ASR模块返回原始文本
        conn.logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
        text_len, _ = remove_punctuation_and_length(raw_text)
        #await self.finish_session(self.current_session_id)
        if text_len > 0:
            # 使用自定义模块进行上报
            await startToChat(conn, raw_text)
            enqueue_asr_report(conn, raw_text, asr_audio_task)
                  
    async def _ensure_connection(self):
        # TODO: 建立健康检查机制，实现连接复用
        #await self.stop_ws_connection()
        if self.ws is None:
            try:
                logger.bind(tag=TAG).info(f"Connecting to ASR service:{self.ws_url}")
                headers = {"Authorization": f"Bearer {self.api_key}"}
                self.ws = await websockets.connect(self.ws_url, additional_headers=headers)
                logger.bind(tag=TAG).info("WebSocket connection established.")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to connect to WebSocket: {e}")
                self.ws = None
                raise
            
    async def stop_ws_connection(self):
        logger.bind(tag=TAG).info("Stopping ASR WebSocket connection...")     
        if self.ws:
            try:
                await self.ws.close()
                logger.bind(tag=TAG).info("ASR WebSocket connection closed successfully.")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error closing ASR WebSocket: {e}")
            finally:
                self.ws = None