import os
import sys
from config.logger import setup_logging
import importlib
from datetime import datetime
from core.utils.util import read_config, get_project_dir

logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    # 创建TTS实例
    if os.path.exists(os.path.join('core', 'providers', 'tts', f'{class_name}.py')):
        lib_name = f'core.providers.tts.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
        return sys.modules[lib_name].TTSProvider(*args, **kwargs)

    raise ValueError(f"不支持的TTS类型: {class_name}，请检查该配置的type是否设置正确")


if __name__ == "__main__":
    """
      响应速度测试
    """
    config = read_config(get_project_dir() + "config.yaml")
    tts = create_instance(
        config["selected_module"]["TTS"]
        if not 'type' in config["TTS"][config["selected_module"]["TTS"]]
        else
        config["TTS"][config["selected_module"]["TTS"]]["type"],
        config["TTS"][config["selected_module"]["TTS"]],
        config["delete_audio"]
    )
    tts.output_file = get_project_dir() + tts.output_file
    start = datetime.now()
    file_path = tts.to_tts("你好，测试,我是人工智能小智")
    print("语音合成耗时：" + str(datetime.now() - start))
    start = datetime.now()
    tts.wav_to_opus_data(file_path)
    print("语音opus耗时：" + str(datetime.now() - start))
