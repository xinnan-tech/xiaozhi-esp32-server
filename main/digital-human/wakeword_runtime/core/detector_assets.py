from dataclasses import dataclass
from pathlib import Path

from ..config import RuntimeConfig

REQUIRED_MODEL_FILES = (
    "encoder.onnx",
    "decoder.onnx",
    "joiner.onnx",
    "tokens.txt",
)


@dataclass
class DetectorAssets:
    model_root: Path
    tokens_file: Path
    encoder_file: Path
    decoder_file: Path
    joiner_file: Path
    keywords_file: Path


class DetectorAssetsBuilder:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def prepare(self) -> DetectorAssets:
        model_root = self._resolve_model_root()
        keywords_file = self._write_keywords_file(model_root)
        return DetectorAssets(
            model_root=model_root,
            tokens_file=model_root / "tokens.txt",
            encoder_file=model_root / "encoder.onnx",
            decoder_file=model_root / "decoder.onnx",
            joiner_file=model_root / "joiner.onnx",
            keywords_file=keywords_file,
        )

    def _resolve_model_root(self) -> Path:
        preferred = self.config.model_dir
        if self._has_required_files(preferred):
            return preferred

        raise FileNotFoundError(
            "No valid model directory found. Expected configured model files to exist."
        )

    def _write_keywords_file(self, model_root: Path) -> Path:
        try:
            from pypinyin import Style, pinyin
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: pypinyin. Install runtime dependencies before generating keywords."
            ) from exc

        wake_words = self.config.wake_words
        if not wake_words:
            raise ValueError("keywords.txt cannot be empty")

        keywords_path = model_root / "keywords.txt"
        lines: list[str] = []
        for keyword_text in wake_words:
            initials = pinyin(keyword_text, style=Style.INITIALS, strict=False)
            finals = pinyin(
                keyword_text,
                style=Style.FINALS_TONE,
                strict=False,
                neutral_tone_with_five=True,
            )

            tokens: list[str] = []
            for initial_parts, final_parts in zip(initials, finals):
                initial = initial_parts[0].strip()
                final = final_parts[0].strip()
                if initial:
                    tokens.append(initial)
                if final:
                    tokens.append(final)

            if not tokens:
                raise ValueError(
                    f"failed to generate pinyin tokens for wake word: {keyword_text}"
                )

            lines.append(f"{' '.join(tokens)} @{keyword_text}")

        keywords_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return keywords_path

    def _has_required_files(self, directory: Path) -> bool:
        if not directory.exists():
            return False
        return all((directory / file_name).exists() for file_name in REQUIRED_MODEL_FILES)
