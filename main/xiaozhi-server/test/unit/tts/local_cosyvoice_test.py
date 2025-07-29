import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import torch
import uuid
from datetime import datetime
import asyncio
import numpy as np
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.local_cosyvoice import TTSProvider


class MockTTSProvider(TTSProviderBase):
    def generate_filename(self):
        return f"/tmp/mock_tts_{str(uuid.uuid4())}.wav"

    async def text_to_speak(self, text, output_file):
        pass


class TestTTSProviderBase(unittest.TestCase):

    def setUp(self):
        self.config = {"output_dir": "/tmp/audio"}
        self.provider = MockTTSProvider(self.config, True)

    @patch('core.providers.tts.base.MarkdownCleaner.clean_markdown')
    @patch('asyncio.run')
    @patch('os.path.exists')
    def test_successful_tts_generation(self, mock_exists, mock_run, mock_clean):
        mock_clean.return_value = "清理后的文本"
        mock_exists.side_effect = [False, True, True]

        result = self.provider.to_tts("你好世界")

        self.assertIsNotNone(result)
        mock_run.assert_called_once()
        mock_clean.assert_called_once_with("你好世界")

    @patch('core.providers.tts.base.MarkdownCleaner.clean_markdown')
    @patch('asyncio.run')
    @patch('os.path.exists')
    def test_tts_with_retries(self, mock_exists, mock_run, mock_clean):
        mock_clean.return_value = "清理后的文本"
        mock_exists.side_effect = [False, False, False, False, True]

        result = self.provider.to_tts("你好世界")

        self.assertIsNotNone(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('core.providers.tts.base.MarkdownCleaner.clean_markdown')
    @patch('asyncio.run')
    @patch('os.path.exists')
    def test_tts_max_retries_exceeded(self, mock_exists, mock_run, mock_clean):
        mock_clean.return_value = "清理后的文本"
        mock_exists.return_value = False

        result = self.provider.to_tts("你好世界")

        self.assertEqual(mock_run.call_count, 5)

    @patch('core.providers.tts.base.MarkdownCleaner.clean_markdown')
    @patch('asyncio.run')
    def test_tts_with_exception(self, mock_run, mock_clean):
        mock_clean.return_value = "清理后的文本"
        mock_run.side_effect = Exception("TTS 错误")

        result = self.provider.to_tts("你好世界")

        self.assertIsNone(result)

    @patch('pydub.AudioSegment.from_file')
    @patch('opuslib_next.Encoder')
    def test_audio_to_opus_conversion(self, mock_encoder_class, mock_from_file):
        mock_audio = MagicMock()
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.__len__.return_value = 3000
        mock_audio.raw_data = b'\x00\x01' * 48000
        mock_from_file.return_value = mock_audio

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b'encoded_data'
        mock_encoder_class.return_value = mock_encoder

        result, duration = self.provider.audio_to_opus_data("test.wav")

        self.assertEqual(duration, 3.0)
        self.assertTrue(len(result) > 0)
        self.assertTrue(all(item == b'encoded_data' for item in result))


class TestCosyVoiceTTSProvider(unittest.TestCase):

    def setUp(self):
        self.config = {
            "output_dir": "/tmp/audio",
            "cosyvoice_path": "/path/to/cosyvoice",
            "cosyvoice_model_dir": "/path/to/models"
        }
        self.mock_cosyvoice = MagicMock()
        self.mock_torch = MagicMock()
        self.mock_torchaudio = MagicMock()

        self.patches = [
            patch('sys.path', new_callable=list),
            patch.dict('sys.modules', {
                'cosyvoice.cli.cosyvoice': MagicMock(),
                'cosyvoice.utils.file_utils': MagicMock(),
                'torch': self.mock_torch,
                'torchaudio': self.mock_torchaudio
            })
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    def test_initialization_with_defaults(self, mock_cosyvoice_class):
        provider = TTSProvider(self.config, True)

        self.assertEqual(provider.cosy_voice_path, "/path/to/cosyvoice")
        self.assertEqual(provider.cosy_voice_model_dir, "/path/to/models")
        self.assertEqual(provider.matcha_tts_path, "/path/to/cosyvoice/third_party/Matcha-TTS")
        self.assertTrue(provider.prompt_speech_16k.endswith("/asset/zero_shot_prompt.wav"))
        self.assertIsNone(provider.prompt_speech_16k_text)

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    def test_initialization_with_custom_values(self, mock_cosyvoice_class):
        custom_config = self.config.copy()
        custom_config.update({
            "matcha_tts_path": "/custom/matcha",
            "prompt_speech_16k": "/custom/prompt.wav",
            "prompt_speech_16k_text": "你好"
        })

        provider = TTSProvider(custom_config, True)

        self.assertEqual(provider.matcha_tts_path, "/custom/matcha")
        self.assertEqual(provider.prompt_speech_16k, "/custom/prompt.wav")
        self.assertEqual(provider.prompt_speech_16k_text, "你好")

    @patch.object(TTSProvider, '_initialize_model')
    @patch('uuid.uuid4')
    @patch('core.providers.tts.local_cosyvoice.datetime')  # 修改这一行
    def test_generate_filename(self, mock_datetime, mock_uuid, _):
        mock_datetime.now.return_value.date.return_value = "2023-01-01"
        mock_uuid.return_value.hex = "abcd1234"

        provider = TTSProvider(self.config, True)
        provider.format = "wav"
        filename = provider.generate_filename()

        self.assertEqual(filename, "/tmp/audio/tts-2023-01-01@abcd1234.wav")

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    def test_inference_to_single_file(self, _):
        provider = TTSProvider(self.config, True)
        cosyvoice = MagicMock()
        cosyvoice.sample_rate = 16000

        mock_speech1 = torch.tensor([0.1, 0.2])
        mock_speech2 = torch.tensor([0.3, 0.4])
        mock_inference_func = MagicMock()
        mock_inference_func.return_value = [
            {"tts_speech": mock_speech1},
            {"tts_speech": mock_speech2}
        ]

        with patch.object(torch, 'cat', return_value="combined_speech"):
            result = provider.inference_to_single_file(
                mock_inference_func, "/tmp/output.wav", "测试文本"
            )

            mock_inference_func.assert_called_once_with("测试文本")
            self.assertEqual(result, "combined_speech")

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    def test_inference_to_single_file_empty_result(self, _):
        provider = TTSProvider(self.config, True)

        mock_inference_func = MagicMock()
        mock_inference_func.return_value = []

        result = provider.inference_to_single_file(
            mock_inference_func, "/tmp/output.wav", "测试文本"
        )

        self.assertIsNone(result)

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    @patch('core.providers.tts.local_cosyvoice.cosyvoice', new_callable=MagicMock)
    @patch('core.providers.tts.local_cosyvoice.torch', new_callable=MagicMock)
    @patch('core.providers.tts.local_cosyvoice.torchaudio', new_callable=MagicMock)
    async def test_text_to_speak_with_prompt_text(self, _, __, mock_cosyvoice, ___):
        provider = TTSProvider(self.config, True)
        provider.prompt_speech_16k_text = "提示文本"

        with patch.object(provider, 'inference_to_single_file') as mock_inference:
            await provider.text_to_speak("你好世界", "/tmp/output.wav")

            mock_inference.assert_called_once_with(
                mock_cosyvoice.inference_cross_lingual,
                "/tmp/output.wav",
                "你好世界",
                provider.prompt_speech_16k_text,
                provider.prompt_speech_16k,
                stream=False
            )

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    @patch('core.providers.tts.local_cosyvoice.cosyvoice', new_callable=MagicMock)
    @patch('core.providers.tts.local_cosyvoice.torch', new_callable=MagicMock)
    @patch('core.providers.tts.local_cosyvoice.torchaudio', new_callable=MagicMock)
    async def test_text_to_speak_without_prompt_text(self, _, __, mock_cosyvoice, ___):
        provider = TTSProvider(self.config, True)
        provider.prompt_speech_16k_text = None

        with patch.object(provider, 'inference_to_single_file') as mock_inference:
            await provider.text_to_speak("你好世界", "/tmp/output.wav")

            mock_inference.assert_called_once_with(
                mock_cosyvoice.inference_zero_shot,
                "/tmp/output.wav",
                "你好世界",
                provider.prompt_speech_16k,
                stream=False
            )

    @patch('core.providers.tts.local_cosyvoice.CosyVoice2')
    async def test_text_to_speak_handles_exception(self, _):
        provider = TTSProvider(self.config, True)

        with patch.object(provider, 'inference_to_single_file', side_effect=Exception("TTS错误")):
            try:
                await provider.text_to_speak("你好世界", "/tmp/output.wav")
                # 如果不抛出异常则测试通过
            except Exception:
                self.fail("text_to_speak方法没有正确处理异常")
