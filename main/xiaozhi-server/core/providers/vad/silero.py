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

        self.decoder = opuslib_next.Decoder(16000, 1)
        # Handle empty string case
        threshold = config.get("threshold", "0.5")
        threshold_low = config.get("threshold_low", "0.2")
        min_silence_duration_ms = config.get("min_silence_duration_ms", "1000")
        self.vad_threshold = float(threshold) if threshold else 0.5
        self.vad_threshold_low = float(threshold_low) if threshold_low else 0.2
        self.silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 1000
        )

        # At least how many frames needed to be considered as having voice
        self.frame_window_threshold = int(config.get("frame_window_threshold", 3))

    def is_vad(self, conn, opus_packet):
        try:
            pcm_frame = self.decoder.decode(opus_packet, 960)
            conn.client_audio_buffer.extend(
                pcm_frame)  # Add new data to buffer

            # Process complete frames in buffer (process 512 samples each time)
            client_have_voice = False
            while len(conn.client_audio_buffer) >= 512 * 2:
                # Extract first 512 samples (1024 bytes)
                chunk = conn.client_audio_buffer[: 512 * 2]
                conn.client_audio_buffer = conn.client_audio_buffer[512 * 2:]

                # Convert to tensor format required by model
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)

                # Detect voice activity
                with torch.no_grad():
                    speech_prob = self.model(audio_tensor, 16000).item()

                # Dual threshold judgment
                if speech_prob >= self.vad_threshold:
                    is_voice = True
                elif speech_prob <= self.vad_threshold_low:
                    is_voice = False
                else:
                    is_voice = conn.last_is_voice
                    # If sound doesn't drop below minimum value, continue previous state, judge as having sound

                conn.last_is_voice = is_voice

                # Update sliding window
                conn.client_voice_window.append(is_voice)
                client_have_voice = (conn.client_voice_window.count(
                    True) >= self.frame_window_threshold)

            # If previously had voice, but this time no voice, and time difference since last voice exceeds silence threshold, consider sentence finished
            if conn.client_have_voice and not client_have_voice:
                stop_duration = time.time() * 1000 - conn.last_activity_time
                if stop_duration >= self.silence_threshold_ms:
                    conn.client_voice_stop = True

            if client_have_voice:
                conn.client_have_voice = True
                conn.last_activity_time = time.time() * 1000

            return client_have_voice

        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"Decode error: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error processing audio packet: {e}")
