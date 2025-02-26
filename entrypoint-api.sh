#!/bin/bash

# 检查 asr-models/SenseVoiceSmall 目录是否存在
if [ ! -d "asr-models/SenseVoiceSmall" ]; then
    # 如果目录不存在，执行下载脚本
    python modelscope_model_download.py
fi

# 执行 app.py
python app.py

