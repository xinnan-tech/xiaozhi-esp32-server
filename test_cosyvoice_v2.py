import os
import asyncio
from core.providers.tts.cosyvoice import TTSProvider

async def test_cosyvoice_tts():
    # 配置参数
    config = {
        "api_url": "http://127.0.0.1:9881/tts",
        "mode": "3s极速复刻",  # 预训练音色, 3s极速复刻, 跨语种复刻, 自然语言控制
        "speaker": "anna",
        "prompt_audio": "data/voice/佩奇-孩子们听到没有快点下来不然你们就吃不到蛋糕咯.mp3",
        "prompt_text": "孩子们听到没有快点下来不然你们就吃不到蛋糕咯",
        "instruct_text": "请用开心的语气说话",
        "seed": 0,
        "speed": 1.0,
        "stream": False,
        "timeout": 30,
        "output_file": "tmp/",
        "response_format": "wav"
    }
    
    # 确保输出目录存在
    os.makedirs(config["output_file"], exist_ok=True)
    
    # 创建TTS提供者实例
    tts_provider = TTSProvider(config, delete_audio_file=False)
    
    # 测试文本
    text = "你好呀，小睿睿，我是你的好朋友佩奇，我有个小弟弟叫做乔治，她最喜欢恐龙，嗷呜！"
    
    try:
        # 生成TTS
        output_file = await tts_provider.text_to_speak(text, os.path.join(config["output_file"], "test_output.wav"))
        print(f"TTS生成成功，输出文件: {output_file}")
    except Exception as e:
        print(f"TTS生成失败: {str(e)}")

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_cosyvoice_tts()) 