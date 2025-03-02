import os
import pytest
import time
from core.providers.tts.base import TTSProviderBase
from pydub.generators import Sine

class DummyTTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file=False):
        super().__init__(config, delete_audio_file)

    def generate_filename(self):
        return "test_tts.mp3"

    async def text_to_speak(self, text, output_file):
        """使用 pydub 生成一个简单的 1s MP3 语音文件"""
        sample_rate = 16000  # 16kHz
        duration = 1000  # 1秒
        sine_wave = Sine(440).to_audio_segment(duration=duration).set_frame_rate(sample_rate)
        sine_wave.export(output_file, format="mp3")

@pytest.fixture
def tts_provider():
    config = {"output_file": "test_output.mp3"}
    return DummyTTSProvider(config)

def test_tts_generation(tts_provider):
    test_text = "你好，这是一段测试语音。"
    tts_file = tts_provider.to_tts(test_text)
    
    assert tts_file is not None, "TTS 生成的文件路径为空"
    assert os.path.exists(tts_file), f"TTS 语音文件 {tts_file} 未生成"
    
    # 清理测试文件
    time.sleep(1)
    os.remove(tts_file)

def test_mp3_to_opus_conversion(tts_provider):
    test_text = "你好，这是一段测试语音。"
    tts_file = tts_provider.to_tts(test_text)
    
    if os.path.exists(tts_file):
        opus_datas, duration = tts_provider.wav_to_opus_data(tts_file)
        assert opus_datas, "MP3 转 OPUS 失败，未生成 OPUS 数据"
        assert duration > 0, "转换后的 OPUS 时长应大于 0"
    
    # 清理测试文件
    time.sleep(1)
    if os.path.exists(tts_file):
        os.remove(tts_file)
