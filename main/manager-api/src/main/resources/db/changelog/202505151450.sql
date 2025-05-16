-- 修改自定义TTS接口请求定义
update `ai_model_provider` set `fields` =
'[{"key":"url","label":"服务地址","type":"string"},{"key":"method","label":"请求方式","type":"string"},{"key":"params","label":"请求参数","type":"dict","dict_name":"params"},{"key":"headers","label":"请求头","type":"dict","dict_name":"headers"},{"key":"format","label":"音频格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]'
where `id` = 'SYSTEM_TTS_custom';

-- 修改自定义TTS配置说明
UPDATE `ai_model_config` SET
`doc_link` = NULL,
`remark` = '自定义TTS配置说明：
1. 支持自定义TTS接口服务
2. 使用GET/POST方式请求
3. 需要网络连接
4. 输出文件保存在tmp/目录
配置说明：
1. 在params中配置请求参数,使用JSON格式
   例如：{"text": "{prompt_text}", "voice": "{voice}", "speed": "{speed}"}
2. 在headers中配置请求头
3. 设置返回音频格式' WHERE `id` = 'TTS_CustomTTS';