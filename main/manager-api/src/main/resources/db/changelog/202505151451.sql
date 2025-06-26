-- 修改自定义TTS接口请求定义
update `ai_model_provider` set `fields` =
'[{"key":"url","label":"服务地址","type":"string"},{"key":"method","label":"请求方式","type":"string"},{"key":"params","label":"请求参数","type":"dict","dict_name":"params"},{"key":"headers","label":"请求头","type":"dict","dict_name":"headers"},{"key":"format","label":"音频格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]'
where `id` = 'SYSTEM_TTS_custom';

-- 修改自定义TTS配置说明
UPDATE `ai_model_config` SET
`doc_link` = NULL,
`remark` = '自定义TTS配置说明：
1. 自定义的TTS接口服务，请求参数可自定义，可接入众多TTS服务
2. 以本地部署的KokoroTTS为例
3. 如果只有cpu运行：docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
4. 如果只有gpu运行：docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu:latest
配置说明：
1. 在params中配置请求参数,使用JSON格式
   例如KokoroTTS：{ "input": "{prompt_text}", "speed": 1, "voice": "zm_yunxi", "stream": true, "download_format": "mp3", "response_format": "mp3", "return_download_link": true }
2. 在headers中配置请求头
3. 设置返回音频格式' WHERE `id` = 'TTS_CustomTTS';