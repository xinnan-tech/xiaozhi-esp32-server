import queue
import threading
import logging
import time
from typing import Any, Callable

import numpy as np

from ..config import RuntimeConfig
from .detector_assets import DetectorAssetsBuilder

logger = logging.getLogger(__name__)


class WakewordDetector:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self.enabled = config.wakeword_enabled
        self.assets_builder = DetectorAssetsBuilder(config)
        self.audio_source = None
        self.keyword_spotter: Any | None = None
        self.stream: Any | None = None
        self.is_running_flag = False
        self.paused = False
        self.on_detected_callback: Callable[[str, str], None] | None = None
        self.on_error: Callable[[Exception], None] | None = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=100)
        self._worker_thread: threading.Thread | None = None
        self.last_detection_time = 0.0
        self.detection_cooldown = self.config.detector.cooldown_seconds

    def initialize(self) -> None:
        if not self.enabled:
            raise RuntimeError("wakeword detector is disabled")

        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: sherpa-onnx. Install runtime dependencies before initializing detector."
            ) from exc

        assets = self.assets_builder.prepare()
        detector_cfg = self.config.detector

        self.keyword_spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(assets.tokens_file),
            encoder=str(assets.encoder_file),
            decoder=str(assets.decoder_file),
            joiner=str(assets.joiner_file),
            keywords_file=str(assets.keywords_file),
            num_threads=detector_cfg.num_threads,
            sample_rate=self.config.audio.sample_rate,
            feature_dim=80,
            max_active_paths=detector_cfg.max_active_paths,
            keywords_score=detector_cfg.keywords_score,
            keywords_threshold=detector_cfg.keywords_threshold,
            num_trailing_blanks=detector_cfg.num_trailing_blanks,
            provider=detector_cfg.provider,
        )
        self.stream = self.keyword_spotter.create_stream()
        logger.info("detector initialized")
        logger.info("detector model root: %s", assets.model_root)
        logger.info("detector keywords file: %s", assets.keywords_file)

    def on_detected(self, callback: Callable[[str, str], None]) -> None:
        self.on_detected_callback = callback

    def on_audio_data(self, audio_data: np.ndarray) -> None:
        if not self.enabled or not self.is_running_flag or self.paused:
            return

        try:
            self._audio_queue.put_nowait(audio_data.copy())
        except queue.Full:
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(audio_data.copy())
            except queue.Empty:
                pass
        except Exception as exc:
            logger.debug("audio data enqueue failed: %s", exc)

    def start(self, audio_source) -> None:
        if not self.enabled:
            logger.info("wakeword detector disabled")
            return

        if self.keyword_spotter is None or self.stream is None:
            self.initialize()

        if self.is_running_flag:
            return

        self.audio_source = audio_source
        self.audio_source.add_audio_listener(self)
        self.is_running_flag = True
        self.paused = False
        self._worker_thread = threading.Thread(
            target=self._detection_loop,
            name="wakeword-detector",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info("wakeword detector started")

    def stop(self) -> None:
        if not self.is_running_flag and self.audio_source is None and self._worker_thread is None:
            return

        self.is_running_flag = False

        if self.audio_source is not None:
            self.audio_source.remove_audio_listener(self)
            self.audio_source = None

        if self._worker_thread is not None:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("wakeword detector stopped")

    def _detection_loop(self) -> None:
        error_count = 0
        max_errors = 5

        while self.is_running_flag:
            try:
                if self.paused:
                    time.sleep(0.1)
                    continue

                audio_data = self._audio_queue.get(timeout=0.1)
                result = self.process_audio_chunk(audio_data)
                if result and self.on_detected_callback is not None:
                    self.on_detected_callback(result, result)
                error_count = 0
            except queue.Empty:
                continue
            except Exception as exc:
                error_count += 1
                logger.error("wakeword detection loop error(%s/%s): %s", error_count, max_errors, exc)
                if self.on_error is not None:
                    try:
                        self.on_error(exc)
                    except Exception:
                        logger.exception("wakeword error callback failed")
                if error_count >= max_errors:
                    logger.critical("too many wakeword detection errors, stopping detector")
                    break
                time.sleep(1)

        self.is_running_flag = False

    def process_audio_chunk(self, audio_data: np.ndarray) -> str | None:
        if self.keyword_spotter is None or self.stream is None:
            raise RuntimeError("detector is not initialized")

        if audio_data is None or len(audio_data) == 0:
            return None

        if audio_data.dtype == np.int16:
            samples = audio_data.astype(np.float32) / 32768.0
        else:
            samples = audio_data.astype(np.float32)

        sample_rate = self.config.audio.sample_rate
        self.stream.accept_waveform(sample_rate=sample_rate, waveform=samples)

        if not self.keyword_spotter.is_ready(self.stream):
            return None

        self.keyword_spotter.decode_stream(self.stream)
        result = self.keyword_spotter.get_result(self.stream)
        if not result:
            return None

        self.keyword_spotter.reset_stream(self.stream)

        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_cooldown:
            return None

        self.last_detection_time = current_time
        return str(result)
