-- Translate model provider names and descriptions from Chinese to English

-- Update provider names
UPDATE ai_model_provider 
SET name = 'SileroVAD Voice Activity Detection'
WHERE name = 'SileroVAD语音活动检测';

UPDATE ai_model_provider 
SET name = 'FunASR Speech Recognition'
WHERE name = 'FunASR语音识别';

UPDATE ai_model_provider 
SET name = 'SherpaASR Speech Recognition'
WHERE name = 'SherpaASR语音识别';

UPDATE ai_model_provider 
SET name = 'Volcano Engine Speech Recognition'
WHERE name = '火山引擎语音识别';

UPDATE ai_model_provider 
SET name = 'Tencent Speech Recognition'
WHERE name = '腾讯语音识别';

UPDATE ai_model_provider 
SET name = 'Tencent Speech Synthesis'
WHERE name = '腾讯语音合成';

UPDATE ai_model_provider 
SET name = 'Alibaba Cloud Speech Recognition'
WHERE name = '阿里云语音识别';

UPDATE ai_model_provider 
SET name = 'Alibaba Cloud Speech Recognition (Streaming)'
WHERE name = '阿里云语音识别(流式)';

UPDATE ai_model_provider 
SET name = 'Baidu Speech Recognition'
WHERE name = '百度语音识别';

UPDATE ai_model_provider 
SET name = 'OpenAI Speech Recognition'
WHERE name = 'OpenAI语音识别';

UPDATE ai_model_provider 
SET name = 'Volcano Engine Speech Recognition (Streaming)'
WHERE name = '火山引擎语音识别(流式)';

UPDATE ai_model_provider 
SET name = 'Alibaba Bailian Interface'
WHERE name = '阿里百炼接口';

UPDATE ai_model_provider 
SET name = 'Volcano Engine LLM'
WHERE name = '火山引擎LLM';

UPDATE ai_model_provider 
SET name = 'Volcano Engine TTS'
WHERE name = '火山引擎TTS';

UPDATE ai_model_provider 
SET name = 'Alibaba Cloud TTS'
WHERE name = '阿里云TTS';

UPDATE ai_model_provider 
SET name = 'Volcano Dual-Stream Speech Synthesis'
WHERE name = '火山双流式语音合成';

UPDATE ai_model_provider 
SET name = 'Linkerai Speech Synthesis'
WHERE name = 'Linkerai语音合成';

UPDATE ai_model_provider 
SET name = 'Alibaba Cloud Speech Synthesis (Streaming)'
WHERE name = '阿里云语音合成(流式)';

UPDATE ai_model_provider 
SET name = 'Index-TTS-vLLM Streaming Speech Synthesis'
WHERE name = 'Index-TTS-vLLM流式语音合成';

UPDATE ai_model_provider 
SET name = 'Mem0AI Memory'
WHERE name = 'Mem0AI记忆';

UPDATE ai_model_provider 
SET name = 'No Memory'
WHERE name = '无记忆';

UPDATE ai_model_provider 
SET name = 'Local Short Memory'
WHERE name = '本地短记忆';

UPDATE ai_model_provider 
SET name = 'No Intent Recognition'
WHERE name = '无意图识别';

UPDATE ai_model_provider 
SET name = 'LLM Intent Recognition'
WHERE name = 'LLM意图识别';

UPDATE ai_model_provider 
SET name = 'Function Call Intent Recognition'
WHERE name = '函数调用意图识别';

UPDATE ai_model_provider 
SET name = 'FunASR Server Speech Recognition'
WHERE name = 'FunASR服务语音识别';

UPDATE ai_model_provider 
SET name = 'MiniMax Speech Synthesis'
WHERE name = 'MiniMax语音合成';

UPDATE ai_model_provider 
SET name = 'OpenAI Speech Synthesis'
WHERE name = 'OpenAI语音合成';

-- Update model config names
UPDATE ai_model_config 
SET model_name = 'Zhipu AI'
WHERE model_name = '智谱AI';

UPDATE ai_model_config 
SET model_name = 'Tongyi Qianwen'
WHERE model_name = '通义千问';

UPDATE ai_model_config 
SET model_name = 'Tongyi Bailian'
WHERE model_name = '通义百炼';

UPDATE ai_model_config 
SET model_name = 'Doubao Large Model'
WHERE model_name = '豆包大模型';

UPDATE ai_model_config 
SET model_name = 'Google Gemini'
WHERE model_name = '谷歌Gemini';

UPDATE ai_model_config 
SET model_name = 'Tencent Speech Recognition'
WHERE model_name = '腾讯语音识别';

UPDATE ai_model_config 
SET model_name = 'Alibaba Cloud Speech Recognition'
WHERE model_name = '阿里云语音识别';

UPDATE ai_model_config 
SET model_name = 'Baidu Speech Recognition'
WHERE model_name = '百度语音识别';

UPDATE ai_model_config 
SET model_name = 'MiniMax Speech Synthesis'
WHERE model_name = 'MiniMax语音合成';

UPDATE ai_model_config 
SET model_name = 'OpenAI Speech Synthesis'
WHERE model_name = 'OpenAI语音合成';

UPDATE ai_model_config 
SET model_name = 'Volcano Dual-Stream Speech Synthesis'
WHERE model_name = '火山双流式语音合成';

UPDATE ai_model_config 
SET model_name = 'Linkerai Speech Synthesis'
WHERE model_name = 'Linkerai语音合成';

UPDATE ai_model_config 
SET model_name = 'Mem0AI Memory'
WHERE model_name = 'Mem0AI记忆';

UPDATE ai_model_config 
SET model_name = 'Function Call Intent Recognition'
WHERE model_name = '函数调用意图识别';

UPDATE ai_model_config 
SET model_name = 'Zhipu Visual AI'
WHERE model_name = '智谱视觉AI';

UPDATE ai_model_config 
SET model_name = 'Qianwen Visual Model'
WHERE model_name = '千问视觉模型';

UPDATE ai_model_config 
SET model_name = 'Volcano Edge Large Model Gateway'
WHERE model_name = '火山引擎边缘大模型网关';

-- Update TTS voice names
UPDATE ai_tts_voice 
SET voice_name = 'Alibaba Cloud Xiaoyun'
WHERE voice_name = '阿里云小云';