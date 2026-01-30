import time
import queue
import threading
from typing import Any, List
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from config.manage_api_client import report as manage_report
from config.logger import setup_logging

logger = setup_logging()


class ReportProcessor(MessageProcessor):
    """上报处理器：完整迁移reportHandle.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """这个处理器不直接处理消息，而是被其他处理器调用"""
        return False
    
    def enqueue_asr_report(self, context: SessionContext, text: str, audio_data: List[bytes]):
        """ASR上报队列 - 完整迁移自enqueue_asr_report"""
        if not context.report_asr_enable:
            return
            
        report_time = int(time.time())
        
        # 将上报任务放入队列
        context.report_queue.put({
            "type": 1,  # 用户类型
            "text": text,
            "audio_data": audio_data,
            "report_time": report_time
        })
        
        # 确保上报线程已启动
        self._ensure_report_thread(context)
    
    def enqueue_tts_report(self, context: SessionContext, text: str, opus_data: bytes):
        """TTS上报队列 - 完整迁移自enqueue_tts_report"""
        if not context.report_tts_enable:
            return
            
        report_time = int(time.time())
        
        # 将上报任务放入队列
        context.report_queue.put({
            "type": 2,  # 智能体类型
            "text": text,
            "audio_data": opus_data,
            "report_time": report_time
        })
        
        # 确保上报线程已启动
        self._ensure_report_thread(context)
    
    def _ensure_report_thread(self, context: SessionContext):
        """确保上报线程已启动"""
        if context.report_thread is None or not context.report_thread.is_alive():
            context.report_thread = threading.Thread(
                target=self._report_worker,
                args=(context,),
                daemon=True
            )
            context.report_thread.start()
            logger.info(f"上报线程已启动: {context.session_id}")
    
    def _report_worker(self, context: SessionContext):
        """上报工作线程 - 完整迁移自ConnectionHandler中的上报逻辑"""
        logger.info(f"上报工作线程启动: {context.session_id}")
        
        while not context.stop_event.is_set():
            try:
                # 从队列获取上报任务
                report_task = context.report_queue.get(timeout=1)
                
                # 执行上报
                self._execute_report(context, report_task)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"上报工作线程异常: {e}")
        
        logger.info(f"上报工作线程退出: {context.session_id}")
    
    def _execute_report(self, context: SessionContext, report_task: dict):
        """执行聊天记录上报操作 - 完整迁移自report函数"""
        try:
            report_type = report_task["type"]
            text = report_task["text"]
            audio_data = report_task["audio_data"]
            report_time = report_task["report_time"]
            
            # 处理音频数据
            processed_audio = None
            if audio_data:
                if isinstance(audio_data, list):
                    # ASR音频数据（多个音频片段）
                    processed_audio = self._process_asr_audio(audio_data)
                elif isinstance(audio_data, bytes):
                    # TTS音频数据（opus格式）
                    processed_audio = self._opus_to_wav(audio_data)
            
            # 执行上报
            manage_report(
                mac_address=context.device_id,
                session_id=context.session_id,
                chat_type=report_type,
                content=text,
                audio=processed_audio,
                report_time=report_time,
            )
            
            logger.debug(f"上报成功: type={report_type}, text={text[:50]}...")
            
        except Exception as e:
            logger.error(f"聊天记录上报失败: {e}")
    
    def _process_asr_audio(self, audio_data_list: List[bytes]) -> bytes:
        """处理ASR音频数据"""
        try:
            # 将多个音频片段合并
            combined_audio = b''.join(audio_data_list)
            return combined_audio
        except Exception as e:
            logger.error(f"处理ASR音频数据失败: {e}")
            return b''
    
    def _opus_to_wav(self, opus_data: bytes) -> bytes:
        """将Opus数据转换为WAV格式的字节流 - 完整迁移自opus_to_wav"""
        try:
            import opuslib_next
            import io
            import wave
            
            # Opus解码器配置
            sample_rate = 16000
            channels = 1
            
            # 创建Opus解码器
            decoder = opuslib_next.Decoder(sample_rate, channels)
            
            # 解码Opus数据
            pcm_data = decoder.decode(opus_data, frame_size=960)
            
            # 创建WAV文件
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            
            return wav_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Opus转WAV失败: {e}")
            return b''
    
    def cleanup_session(self, context: SessionContext):
        """清理会话上报资源"""
        # 停止上报线程
        if context.report_thread and context.report_thread.is_alive():
            context.stop_event.set()
            context.report_thread.join(timeout=5)
        
        # 清理上报队列
        try:
            while not context.report_queue.empty():
                context.report_queue.get_nowait()
        except queue.Empty:
            pass
        
        logger.info(f"上报资源清理完成: {context.session_id}")

