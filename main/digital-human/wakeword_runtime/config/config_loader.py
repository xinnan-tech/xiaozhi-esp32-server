import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WakewordSettings:
    enabled: bool = False


@dataclass
class AudioSettings:
    input_device: str | int | None = None
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class DetectorSettings:
    num_threads: int = 4
    provider: str = "cpu"
    max_active_paths: int = 2
    keywords_score: float = 1.8
    keywords_threshold: float = 0.2
    num_trailing_blanks: int = 1
    cooldown_seconds: float = 1.5


@dataclass
class LoggingSettings:
    level: str = "INFO"
    directory: str = "logs"
    file_name: str = "wakeword-runtime.log"


@dataclass
class RuntimeConfig:
    runtime_root: Path
    wakeword: WakewordSettings
    wake_words: list[str]
    model_dir: Path
    audio: AudioSettings
    detector: DetectorSettings
    logging: LoggingSettings

    def validate(self) -> None:
        if self.wakeword.enabled and not self.wake_words:
            raise ValueError("keywords.txt cannot be empty when wakeword is enabled")

        if self.audio.sample_rate <= 0:
            raise ValueError("audio.sample_rate must be greater than 0")

        if self.audio.channels <= 0:
            raise ValueError("audio.channels must be greater than 0")

        if self.detector.num_threads <= 0:
            raise ValueError("detector.num_threads must be greater than 0")

        if self.detector.cooldown_seconds < 0:
            raise ValueError("detector.cooldown_seconds cannot be negative")

        if not self.logging.level:
            raise ValueError("logging.level cannot be empty")

    @property
    def wakeword_enabled(self) -> bool:
        return self.wakeword.enabled

    @property
    def log_dir(self) -> Path:
        return (self.runtime_root / self.logging.directory).resolve()

    @property
    def log_file(self) -> Path:
        return self.log_dir / self.logging.file_name

    @property
    def log_level(self) -> str:
        return self.logging.level.upper()


def load_config(runtime_root: Path) -> RuntimeConfig:
    config_path = runtime_root / "config.json"
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    wakeword_cfg = dict(raw.get("wakeword", {}))
    raw_model_dir = Path(str(raw.get("model_dir", "models")))
    model_dir = raw_model_dir.resolve() if raw_model_dir.is_absolute() else (runtime_root / raw_model_dir).resolve()
    wake_words = _load_wake_words_from_keywords_file(model_dir)

    audio_cfg = dict(raw.get("audio", {}))
    detector_cfg = dict(raw.get("detector", {}))
    logging_cfg = dict(raw.get("logging", {}))

    config = RuntimeConfig(
        runtime_root=runtime_root,
        wakeword=WakewordSettings(enabled=bool(wakeword_cfg.get("enabled", False))),
        wake_words=wake_words,
        model_dir=model_dir,
        audio=AudioSettings(
            input_device=audio_cfg.get("input_device"),
            sample_rate=int(audio_cfg.get("sample_rate", 16000)),
            channels=int(audio_cfg.get("channels", 1)),
        ),
        detector=DetectorSettings(
            num_threads=int(detector_cfg.get("num_threads", 4)),
            provider=str(detector_cfg.get("provider", "cpu")),
            max_active_paths=int(detector_cfg.get("max_active_paths", 2)),
            keywords_score=float(detector_cfg.get("keywords_score", 1.8)),
            keywords_threshold=float(detector_cfg.get("keywords_threshold", 0.2)),
            num_trailing_blanks=int(detector_cfg.get("num_trailing_blanks", 1)),
            cooldown_seconds=float(detector_cfg.get("cooldown_seconds", 1.5)),
        ),
        logging=LoggingSettings(
            level=str(logging_cfg.get("level", "INFO")).upper(),
            directory=str(logging_cfg.get("dir", "logs")),
            file_name=str(logging_cfg.get("file", "wakeword-runtime.log")),
        ),
    )
    config.validate()
    return config


DEFAULT_WAKE_WORDS = [
    "你好小智",
    "你好小志",
    "小爱同学",
    "你好小鑫",
    "你好小新",
    "小美同学",
    "小龙小龙",
    "喵喵同学",
    "小滨小滨",
    "小冰小冰",
    "嘿你好呀",
]


def _load_wake_words_from_keywords_file(model_dir: Path) -> list[str]:
    keywords_file = model_dir / "keywords.txt"
    if not keywords_file.exists():
        return DEFAULT_WAKE_WORDS.copy()

    wake_words: list[str] = []
    for line in keywords_file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "@" not in text:
            continue

        wake_word = text.split("@", 1)[1].strip()
        if wake_word:
            wake_words.append(wake_word)

    return wake_words if wake_words else DEFAULT_WAKE_WORDS.copy()
