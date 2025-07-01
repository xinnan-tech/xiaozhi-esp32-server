import time
import numpy as np
import torch
import opuslib_next
from config.logger import setup_logging
from core.providers.vad.base import VADProviderBase

TAG = __name__
logger = setup_logging()


class VADProvider(VADProviderBase):
    def __init__(self, config):
        logger.bind(tag=TAG).info("SileroVAD", config)
        self.model, _ = torch.hub.load(
            repo_or_dir=config["model_dir"],
            source="local",
            model="silero_vad",
            force_reload=False,
        )
        self.stop_duration = 0
        self.decoder = opuslib_next.Decoder(16000, 1)

        # 处理空字符串的情况
        threshold = config.get("threshold", "0.5")
        min_silence_duration_ms = config.get("min_silence_duration_ms", "1000")

        self.vad_threshold = float(threshold) if threshold else 0.5
        self.silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 1000
        )

    def is_vad(self, conn, opus_packet):
        try:
            pcm_frame = self.decoder.decode(opus_packet, 960)
            conn.client_audio_buffer.extend(pcm_frame)  # 将新数据加入缓冲区

            # 初始化帧计数器
            if not hasattr(conn, "client_voice_frame_count"):
                conn.client_voice_frame_count = 0

            # 处理缓冲区中的完整帧（每次处理512采样点）
            client_have_voice = False
            while len(conn.client_audio_buffer) >= 512 * 2:
                # 提取前512个采样点（1024字节）
                chunk = conn.client_audio_buffer[: 512 * 2]
                conn.client_audio_buffer = conn.client_audio_buffer[512 * 2 :]

                # 转换为模型需要的张量格式
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)

                # 检测语音活动
                with torch.no_grad():
                    speech_prob = self.model(audio_tensor, 16000).item()
                is_voice = speech_prob >= self.vad_threshold

                if is_voice:
                    conn.client_voice_frame_count += 1
                else:
                    conn.client_voice_frame_count = 0

                # 只有连续4帧检测到语音才认为有语音
                client_have_voice = conn.client_voice_frame_count >= 4

                # 如果之前有声音，但本次没有声音，且与上次有声音的时间差已经超过了静默阈值，则认为已经说完一句话
                if conn.client_have_voice and not client_have_voice:
                    self.stop_duration = (
                        time.time() * 1000 - conn.client_have_voice_last_time
                    )
                    if self.stop_duration >= self.silence_threshold_ms:
                        conn.client_voice_stop = True
                if client_have_voice:
                    conn.client_have_voice = True
                    conn.client_have_voice_last_time = time.time() * 1000

            return client_have_voice
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"解码错误: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error processing audio packet: {e}")
            
    def is_eou(self, conn, text) :
            """End of Utterance（话语结束检测），是基于语义理解的自动判断用户发言是否结束的技术"""
            return conn.client_voice_stop 
        
    def get_silence_duration(self, conn) :
        """返回语音静音时长，单位ms"""
        if conn.client_voice_stop == True:
            return self.stop_duration
        return 0