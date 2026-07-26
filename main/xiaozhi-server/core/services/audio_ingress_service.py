import time
from typing import Any, Optional

import numpy as np
import opuslib_next

from config.logger import setup_logging


logger = setup_logging()


class AudioIngressService:
    """Decode transport audio once and apply optional server-side AEC."""

    def __init__(self, decoder_factory=None):
        self._decoder_factory = decoder_factory or opuslib_next.Decoder

    def process(self, context: Any, opus_packet: bytes, timestamp: int = 0) -> Optional[bytes]:
        pcm_frame = self.decode(context, opus_packet)
        if pcm_frame and timestamp > 0 and getattr(context, "client_aec", False):
            return self.apply_aec(context, timestamp, pcm_frame)
        return pcm_frame

    def decode(self, context: Any, opus_packet: bytes) -> Optional[bytes]:
        if not opus_packet:
            return None

        sample_rate = int(getattr(context, "input_sample_rate", 16000) or 16000)
        channels = int(getattr(context, "input_channels", 1) or 1)
        frame_duration = int(
            getattr(context, "input_frame_duration", 60) or 60
        )
        decoder_config = (sample_rate, channels)

        try:
            if getattr(context, "_audio_ingress_decoder_config", None) != decoder_config:
                context._audio_ingress_decoder = self._decoder_factory(sample_rate, channels)
                context._audio_ingress_decoder_config = decoder_config
                self._register_cleanup(context)

            frame_size = max(1, sample_rate * frame_duration // 1000)
            pcm_frame = context._audio_ingress_decoder.decode(bytes(opus_packet), frame_size)
            return bytes(pcm_frame)
        except Exception as exc:
            logger.debug("Opus decode failed: {}", exc)
            return None

    def apply_aec(self, context: Any, timestamp: int, pcm_frame: bytes) -> bytes:
        """Apply the AEC algorithm used by the upstream gateway path."""
        try:
            self._expire_aec_references(context)
            audio_cache = getattr(context, "aec_audio_cache", None)
            if not pcm_frame or not audio_cache:
                return pcm_frame

            mic_audio = np.frombuffer(pcm_frame, dtype=np.int16).astype(np.float32)
            mic_rms = np.sqrt(np.mean(mic_audio**2))
            if mic_rms < 100:
                return pcm_frame

            sorted_timestamps = sorted(audio_cache.keys())
            if len(sorted_timestamps) < 2:
                return pcm_frame

            sample_count = len(mic_audio)
            closest_idx = min(
                range(len(sorted_timestamps)),
                key=lambda index: abs(sorted_timestamps[index] - timestamp),
            )

            mic_window = np.hanning(sample_count)
            mic_fft = np.fft.rfft(mic_audio * mic_window)
            mic_psd = np.abs(mic_fft) ** 2
            mic_log_psd = 10 * np.log10(mic_psd + 1e-8)
            mic_power = np.dot(mic_log_psd, mic_log_psd)

            best_corr = -1
            best_ref_idx = closest_idx
            best_ref_rms = 0.0
            for offset in range(-2, 3):
                test_idx = closest_idx + offset
                if test_idx < 0 or test_idx >= len(sorted_timestamps):
                    continue

                test_ref = np.frombuffer(
                    audio_cache[sorted_timestamps[test_idx]], dtype=np.int16
                ).astype(np.float32)
                test_ref_rms = np.sqrt(np.mean(test_ref**2))
                if test_ref_rms < 50:
                    continue

                test_fft = np.fft.rfft(test_ref * np.hanning(len(test_ref)))
                test_log_psd = 10 * np.log10(np.abs(test_fft) ** 2 + 1e-8)
                cross_power = np.dot(mic_log_psd, test_log_psd)
                reference_power = np.dot(test_log_psd, test_log_psd)
                corr = abs(cross_power) / (
                    np.sqrt(mic_power) * np.sqrt(reference_power) + 1e-8
                )
                if corr > best_corr:
                    best_corr = corr
                    best_ref_idx = test_idx
                    best_ref_rms = test_ref_rms

            best_ref = np.frombuffer(
                audio_cache[sorted_timestamps[best_ref_idx]], dtype=np.int16
            ).astype(np.float32)
            if best_ref_rms < 50:
                return pcm_frame

            aligned_ref = best_ref[:sample_count]
            if len(aligned_ref) < sample_count:
                aligned_ref = np.pad(aligned_ref, (0, sample_count - len(aligned_ref)))

            mic_mag = np.abs(mic_fft)
            mic_phase = np.angle(mic_fft)
            ref_mag = np.abs(np.fft.rfft(aligned_ref * np.hanning(sample_count)))
            scale = np.sum(mic_mag * ref_mag) / (np.dot(ref_mag, ref_mag) + 1e-8)
            coefficient = max(
                0.5, min(3.0, 1.0 + scale * 3 + (best_corr - 0.97) * 30)
            )
            result_mag = np.maximum(
                mic_mag - ref_mag * scale * coefficient * 1.5, mic_mag * 0.1
            )
            output = np.fft.irfft(result_mag * np.exp(1j * mic_phase), sample_count)
            if best_corr >= 0.97 and best_ref_rms > 500:
                output *= 0.3

            return np.clip(output, -32768, 32767).astype(np.int16).tobytes()
        except Exception as exc:
            logger.warning("AEC processing failed: {}", exc)
            return pcm_frame

    def cache_output_reference(
        self, context: Any, opus_packet: bytes, timestamp: int
    ) -> None:
        if not getattr(context, "client_aec", False) or timestamp <= 0:
            return

        try:
            sample_rate = int(
                getattr(
                    context,
                    "output_sample_rate",
                    getattr(context, "sample_rate", 24000),
                )
                or 24000
            )
            channels = int(getattr(context, "output_channels", 1) or 1)
            frame_duration = int(
                getattr(context, "output_frame_duration", 60) or 60
            )
            decoder_config = (sample_rate, channels)
            decoder = getattr(context, "_audio_reference_decoder", None)
            if (
                decoder is None
                or getattr(context, "_audio_reference_decoder_config", None)
                != decoder_config
            ):
                decoder = self._decoder_factory(sample_rate, channels)
                context._audio_reference_decoder = decoder
                context._audio_reference_decoder_config = decoder_config
                self._register_cleanup(context)
            frame_size = max(1, sample_rate * frame_duration // 1000)
            pcm_data = bytes(decoder.decode(bytes(opus_packet), frame_size))
            input_rate = int(getattr(context, "input_sample_rate", 16000) or 16000)
            if sample_rate != input_rate:
                pcm_data = self._resample_pcm(pcm_data, sample_rate, input_rate)
            self._expire_aec_references(context)
            context.aec_audio_cache[timestamp] = pcm_data
            context.aec_audio_cache_time[timestamp] = time.time()
        except Exception as exc:
            logger.debug("AEC reference decode failed: {}", exc)

    @staticmethod
    def _expire_aec_references(context: Any) -> None:
        cache = getattr(context, "aec_audio_cache", {})
        cache_times = getattr(context, "aec_audio_cache_time", {})
        config = getattr(context, "config", {}) or {}
        max_age = max(1, int(config.get("aec_reference_max_age_seconds", 120)))
        max_frames = max(2, int(config.get("aec_reference_max_frames", 256)))
        now = time.time()

        expired = [
            timestamp
            for timestamp, cached_at in list(cache_times.items())
            if now - cached_at > max_age
        ]
        overflow = max(0, len(cache) - max_frames + 1)
        if overflow:
            expired.extend(sorted(cache_times, key=cache_times.get)[:overflow])
        for timestamp in set(expired):
            cache.pop(timestamp, None)
            cache_times.pop(timestamp, None)

    def cleanup(self, context: Any) -> None:
        for name in (
            "_audio_ingress_decoder",
            "_audio_ingress_decoder_config",
            "_audio_reference_decoder",
            "_audio_reference_decoder_config",
        ):
            if hasattr(context, name):
                delattr(context, name)
        if hasattr(context, "aec_audio_cache"):
            context.aec_audio_cache.clear()
        if hasattr(context, "aec_audio_cache_time"):
            context.aec_audio_cache_time.clear()

    def _register_cleanup(self, context: Any) -> None:
        if getattr(context, "_audio_ingress_cleanup_registered", False):
            return
        register_cleanup = getattr(context, "register_cleanup", None)
        if callable(register_cleanup):
            register_cleanup(lambda: self.cleanup(context))
            context._audio_ingress_cleanup_registered = True

    @staticmethod
    def _resample_pcm(pcm_data: bytes, source_rate: int, target_rate: int) -> bytes:
        if not pcm_data or source_rate == target_rate:
            return pcm_data
        source = np.frombuffer(pcm_data, dtype=np.int16)
        if len(source) < 2:
            return pcm_data
        target_size = max(1, round(len(source) * target_rate / source_rate))
        source_positions = np.linspace(0.0, 1.0, len(source), endpoint=False)
        target_positions = np.linspace(0.0, 1.0, target_size, endpoint=False)
        target = np.interp(target_positions, source_positions, source)
        return np.clip(target, -32768, 32767).astype(np.int16).tobytes()
