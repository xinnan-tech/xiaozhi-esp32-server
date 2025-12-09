import time
import numpy as np
import torch
import opuslib_next
from config.logger import setup_logging
from core.providers.vad.base import VADProviderBase

TAG = __name__
logger = setup_logging()


class ExpFilter:
    """Exponential filter for smoothing probability values (from LiveKit)
    
    Smooths noisy VAD probability outputs to reduce false triggers.
    Formula: smoothed = α × current + (1-α) × previous
    
    Args:
        alpha: Smoothing factor (0-1). Higher = faster response, less smoothing.
               LiveKit default is 0.35.
    """
    def __init__(self, alpha: float = 0.35):
        self._alpha = alpha
        self._filtered_value: float | None = None

    def apply(self, sample: float) -> float:
        if self._filtered_value is None:
            self._filtered_value = sample
        else:
            self._filtered_value = self._alpha * sample + (1 - self._alpha) * self._filtered_value
        return self._filtered_value

    def reset(self):
        self._filtered_value = None


class VADProvider(VADProviderBase):
    def __init__(self, config):
        logger.bind(tag=TAG).info("SileroVAD", config)
        self.model, _ = torch.hub.load(
            repo_or_dir=config["model_dir"],
            source="local",
            model="silero_vad",
            force_reload=False,
        )

        self.decoder = opuslib_next.Decoder(16000, 1)

        # VAD parameters
        threshold = config.get("threshold", "0.6")
        threshold_low = config.get("threshold_low", "0.3")
        min_silence_duration_ms = config.get("min_silence_duration_ms", "200")

        self.vad_threshold = float(threshold) if threshold else 0.5
        self.vad_threshold_low = float(threshold_low) if threshold_low else 0.3
        self.silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 200
        )

        # sliding window threshold
        frame_window_threshold = config.get("frame_window_threshold", "3")
        self.frame_window_threshold = int(frame_window_threshold) if frame_window_threshold else 3

    def is_vad(self, conn, opus_packet):
        try:
            now_ms = time.time() * 1000
            conn._vad_frame_count = getattr(conn, '_vad_frame_count', 0) + 1
            
            pcm_frame = self.decoder.decode(opus_packet, 960)
            conn.client_audio_buffer.extend(pcm_frame)

            # process complete frames in buffer (512 samples per frame)
            client_have_voice = False
            while len(conn.client_audio_buffer) >= 512 * 2:
                # extract first 512 samples (1024 bytes)
                chunk = conn.client_audio_buffer[: 512 * 2]
                conn.client_audio_buffer = conn.client_audio_buffer[512 * 2 :]

                # convert to tensor format for model
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)

                # run VAD inference
                with torch.no_grad():
                    speech_prob = self.model(audio_tensor, 16000).item()

                # dual threshold judgment (hysteresis)
                if speech_prob >= self.vad_threshold:
                    is_voice = True
                elif speech_prob <= self.vad_threshold_low:
                    is_voice = False
                else:
                    is_voice = conn.last_is_voice

                conn.last_is_voice = is_voice

                # record first voice frame time (when is_voice becomes True)
                if is_voice and not hasattr(conn, '_vad_first_voice_time'):
                    conn._vad_first_voice_time = now_ms

                # update sliding window
                conn.client_voice_window.append(is_voice)
                client_have_voice = (
                    conn.client_voice_window.count(True) >= self.frame_window_threshold
                )

                # 检测语音开始（边缘检测）
                if not conn.client_have_voice and client_have_voice:
                    conn._latency_voice_start_time = time.time() * 1000
                    # calculate delay from first voice frame to VAD confirmation
                    first_voice_time = getattr(conn, '_vad_first_voice_time', None)
                    if first_voice_time:
                        voice_to_confirm = conn._latency_voice_start_time - first_voice_time
                        logger.bind(tag=TAG).info(
                            f"🎤 [延迟追踪] VAD检测到开始说话 | "
                            f"首个声音帧到确认: {voice_to_confirm:.0f}ms"
                        )
                    else:
                        logger.bind(tag=TAG).info(f"🎤 [延迟追踪] VAD检测到开始说话")
                
                # 检测语音结束（需要确保开始时间已设置）
                if conn.client_have_voice and not client_have_voice:
                    stop_duration = time.time() * 1000 - conn.last_activity_time
                    if stop_duration >= self.silence_threshold_ms:
                        if conn.client_listen_mode != "manual":
                            conn.client_voice_stop = True
                            # 记录用户说完的时间（端到端延迟的起点）
                            conn._latency_voice_end_time = time.time() * 1000
                            
                            # 安全检查：确保时间戳已设置
                            start_time = getattr(conn, '_latency_voice_start_time', None)
                            
                            if start_time:
                                voice_duration = conn._latency_voice_end_time - start_time
                                logger.bind(tag=TAG).info(
                                    f"🎤 [延迟追踪] VAD检测到说话结束 | "
                                    f"语音时长: {voice_duration:.0f}ms"
                                )
                            
                            # reset for next utterance
                            conn._latency_voice_start_time = None
                            if hasattr(conn, '_vad_first_voice_time'):
                                del conn._vad_first_voice_time
                            
                if client_have_voice:
                    conn.client_have_voice = True
                    conn.last_activity_time = time.time() * 1000

            return client_have_voice
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"解码错误: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error processing audio packet: {e}")
